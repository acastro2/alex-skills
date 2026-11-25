import type { Database } from "bun:sqlite"
import { resolve } from "node:path"
import { parse } from "../shell/parse.ts"
import { bundleFor } from "./bundle.ts"
import { git } from "./verify.ts"

const MESSAGE = "Verify first: call `verify`; the harness needs a green bundle for this exact commit to land on main."
const MAIN = new Set(["main", "master"])

interface Push {
  cwd: string
  refspecs: string[]
  everything: boolean
}

const GIT_OPT_WITH_ARG = new Set(["-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"])
const PUSH_OPT_WITH_ARG = new Set(["--repo", "--receive-pack", "--exec", "-o", "--push-option"])

function findPush(command: string, cwd: string): Push | null {
  for (const a of parse(command).commands) {
    if (a[0] !== "git") continue
    let dir = cwd
    let i = 1
    for (; i < a.length; i++) {
      if (a[i] === "-C" && a[i + 1] !== undefined) dir = resolve(dir, a[++i])
      else if (GIT_OPT_WITH_ARG.has(a[i])) i++
      else if (!a[i].startsWith("-")) break
    }
    if (a[i] !== "push") continue
    const pos: string[] = []
    let everything = false
    for (i++; i < a.length; i++) {
      const w = a[i]
      if (w === "--all" || w === "--mirror") everything = true
      if (PUSH_OPT_WITH_ARG.has(w)) i++
      else if (!w.startsWith("-")) pos.push(w)
    }
    return { cwd: dir, refspecs: pos.slice(1), everything } // pos[0] is the remote
  }
  return null
}

const lines = (s: string) => s.split("\n").filter(Boolean)

// What this push adds: a diff against the remote copy of the target, else against main, else the parent.
function pushedFiles(cwd: string, head: string, targets: string[]): string[] | null {
  const ok = (rev: string) => git(cwd, "rev-parse", "--verify", "--quiet", `${rev}^{commit}`).out.trim()
  const bases: (string | null)[] = [
    ...targets.map((t) => ok(`origin/${t}`) || null),
    ok("@{upstream}") || null,
  ]
  for (const m of ["origin/main", "origin/master", "main", "master"]) {
    const sha = ok(m)
    if (!sha || sha === head) continue
    bases.push(git(cwd, "merge-base", head, sha).out.trim() || null)
  }
  bases.push(ok("HEAD^") || null)
  const base = bases.find((b) => b && b !== head)
  if (!base) return null
  return lines(git(cwd, "diff", "--name-only", `${base}..${head}`).out)
}

// Spec D44. The core decides the mode (registry push-gate, default advise); this only says what it would deny.
export function pushGate(db: Database, o: { cwd: string; command: string }): { ruleId: "push-gate"; message: string } | null {
  const push = findPush(o.command, o.cwd)
  if (!push) return null
  const head = git(push.cwd, "rev-parse", "HEAD")
  if (head.code !== 0) return null // no commit, nothing to prove
  const sha = head.out.trim()
  const current = git(push.cwd, "branch", "--show-current").out.trim()
  const targets = push.refspecs.length
    ? push.refspecs.map((r) => {
        const dst = r.replace(/^\+/, "").split(":").pop() as string
        return (dst === "HEAD" ? current : dst).replace(/^refs\/heads\//, "")
      })
    : [current]

  const files = pushedFiles(push.cwd, sha, targets)
  if (files && files.length && files.every((f) => f.endsWith(".md"))) return null

  const deny = { ruleId: "push-gate" as const, message: MESSAGE }
  const b = bundleFor(db, sha)
  if (!b) return deny
  if (b.verdict === "green") return null
  return push.everything || targets.some((t) => MAIN.has(t)) ? deny : null
}
