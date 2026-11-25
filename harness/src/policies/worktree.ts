// tool.before: lazy worktree registration (D37) and the main-checkout-write rule (Phase 5).
import { existsSync } from "node:fs"
import { tmpdir } from "node:os"
import { dirname, resolve, sep } from "node:path"
import { mode } from "../ledger/registry.ts"
import { parse } from "../shell/parse.ts"
import { register, worktreesRoot } from "../worktree/lifecycle.ts"
import { allow, git, hit, q1, type Env, type Out } from "./util.ts"

const MESSAGE = "Work in a worktree: call `worktree_new`. It records the pointer for other agents."
const GIT_WRITES = new Set(["commit", "checkout", "merge", "rebase"])
const GIT_OPT_WITH_ARG = new Set(["-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"])

function existingDir(p: string): string | null {
  let d = dirname(resolve(p))
  while (d !== dirname(d) && !existsSync(d)) d = dirname(d)
  return existsSync(d) ? d : null
}

// The main checkout is the one whose git dir is also the common git dir. A linked worktree has its own.
// A clone under a temp or scratch folder is throwaway work, not a main checkout (seen live: 34 of 51 advise rows).
function scratch(dir: string): boolean {
  const home = process.env.HOME ?? ""
  const roots = (process.env.HARNESS_SCRATCH_ROOTS?.split(":") ?? [tmpdir(), "/tmp", process.env.TMPDIR, `${home}/.agents/skill-workspace`]).filter(Boolean) as string[]
  return roots.some((r) => dir === r || dir.startsWith(r.endsWith("/") ? r : `${r}/`))
}

function inMainCheckout(dir: string): boolean {
  if (scratch(resolve(dir))) return false
  const r = git(["rev-parse", "--path-format=absolute", "--is-inside-work-tree", "--git-dir", "--git-common-dir"], dir)
  const [inside, gitDir, common] = r.out.split("\n")
  return r.ok && inside === "true" && !!gitDir && gitDir === common
}

// Directories where this shell command runs git commit, checkout, merge or rebase.
function gitWriteDirs(command: string, cwd: string): string[] {
  const dirs: string[] = []
  for (const a of parse(command).commands) {
    if (a[0] !== "git") continue
    let dir = cwd
    let i = 1
    for (; i < a.length; i++) {
      if (a[i] === "-C" && a[i + 1] !== undefined) dir = resolve(dir, a[++i])
      else if (GIT_OPT_WITH_ARG.has(a[i])) i++
      else if (!a[i].startsWith("-")) break
    }
    if (GIT_WRITES.has(a[i])) dirs.push(dir)
  }
  return dirs
}

const under = (p: string, root: string) => p === root || p.startsWith(root + sep)

// A worktree made by hand under ~/.worktrees/ is recorded on the first write in it. Returns its new id.
function lazyRegister(env: Env, dir: string | null): string | null {
  if (!dir || !under(resolve(dir), worktreesRoot())) return null
  const known = q1(env.db, "select 1 as x from worktrees where substr(?, 1, length(path) + 1) = path || '/' or path = ?", dir, dir)
  if (known) return null
  const top = git(["rev-parse", "--show-toplevel"], dir)
  if (!top.ok || !top.out || !under(top.out, worktreesRoot())) return null
  try {
    const r = register(env.db, { session: env.ev.session, path: top.out })
    return r.registered ? r.id : null
  } catch {
    return null
  }
}

export function guardWorktree(env: Env): Out | null {
  const { ev, db } = env
  const i = ev.input ?? {}
  const isShell = ev.toolName === "shell"
  const target = isShell ? String(i.cwd ?? ev.cwd) : String(i.path ?? "")
  if (!isShell && !target) return null

  const dir = isShell ? target : existingDir(target)
  const registered = lazyRegister(env, dir)
  const extra = registered ? { data: { worktreeRegistered: registered } } : {}

  if (mode(db, "main-checkout-write") === "off") return registered ? allow(extra) : null
  const hitDir = isShell ? gitWriteDirs(String(i.command ?? ""), target).find(inMainCheckout) : dir && inMainCheckout(dir) ? dir : undefined
  if (hitDir) {
    const o = hit(env, "main-checkout-write", MESSAGE, { dir: hitDir, ...(extra.data ?? {}) })
    if (o) return o
  }
  return registered ? allow(extra) : null
}
