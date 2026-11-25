// Shell guard rules (spec: Phase 1 Guard rules, D5, D31, D36, D37, D72). Pure functions.
// The guard stops agent mistakes, not a hostile agent (D72).
import { posix as path } from "node:path"
import { parse, type Parsed } from "./parse"
import { CONFIG_MSG, LEDGER_MSG, inside, isHarnessConfigPath, isLedgerPath } from "./paths"

export interface ShellCtx {
  cwd: string
  home: string
  repoRoot?: string | null
  allowRoots: string[]
  isTrackedOrIgnored?: (absPath: string) => boolean
  branch?: string // current branch of the repo at cwd; unknown means every `git merge` is denied
  only?: readonly string[] // run only these rule ids (guard-lite)
}

export interface ShellHit {
  ruleId: string
  message: string
}

const MSG = {
  "recursive-delete": "Recursive delete outside the allowlist, or of a path the harness cannot see (a $VAR or $(...)). Write the literal path, or ask Alex.",
  "merge-in-shell": "Use the `merge_pr` tool to land a PR. To update a branch, rebase: `git rebase origin/main`.",
  "destructive-git": "Destructive git is blocked. Use a safe form, or ask Alex.",
  "harness-self": "Only Alex runs harness commands. Ask Alex.",
  "ledger-write": LEDGER_MSG,
  "harness-config-write": CONFIG_MSG,
} as const

const set = (...s: string[]) => new Set(s)

// Words that are not options, skipping `--` and the values of the given value flags.
function positionals(args: string[], valueFlags: ReadonlySet<string> = new Set()): string[] {
  const out: string[] = []
  let dd = false
  for (let i = 0; i < args.length; i++) {
    const a = args[i]
    if (dd) out.push(a)
    else if (a === "--") dd = true
    else if (valueFlags.has(a)) i++
    else if (!(a.startsWith("-") && a.length > 1)) out.push(a)
  }
  return out
}

const beforeDD = (args: string[]) => {
  const i = args.indexOf("--")
  return i < 0 ? args : args.slice(0, i)
}
const hasShort = (args: string[], ch: string) => beforeDD(args).some((a) => /^-[A-Za-z]+$/.test(a) && a.includes(ch))

// ---- paths ----

function expand(p: string, ctx: ShellCtx): string {
  if (p === "~" || p.startsWith("~/")) return ctx.home + p.slice(1)
  return p.replace(/^\$\{?HOME\}?(?=\/|$)/, ctx.home)
}

const globPrefix = (p: string) => {
  const i = p.search(/[*?[{]/)
  return i < 0 ? p : p.slice(0, i)
}

// Absolute path of a write target, or null if it holds a variable or substitution we cannot resolve.
function resolveTarget(raw: string, ctx: ShellCtx): string | null {
  const e = expand(raw, ctx)
  if (e.includes("$") || e.includes("`")) return null
  return path.resolve(ctx.cwd, globPrefix(e))
}

// D5: allowed when inside an allow root, or tracked/ignored inside the repo. Repo root and .git never.
function targetDenied(raw: string, ctx: ShellCtx): boolean {
  const p = resolveTarget(raw, ctx)
  if (p === null) return true
  const repo = ctx.repoRoot ? path.resolve(ctx.repoRoot) : null
  if (repo && (p === repo || inside(p, repo + "/.git"))) return true
  if (ctx.allowRoots.some((r) => inside(p, path.resolve(r)))) return false
  if (repo && inside(p, repo) && ctx.isTrackedOrIgnored?.(p)) return false
  return true
}

// ---- recursive-delete ----

function rmTargets(args: string[]): string[] | null {
  const recursive = beforeDD(args).some((a) => a === "--recursive" || /^-[A-Za-z]*[rR][A-Za-z]*$/.test(a))
  return recursive ? positionals(args) : null
}

function findTargets(args: string[]): string[] | null {
  const del =
    args.includes("-delete") ||
    args.some((a, k) => ["-exec", "-execdir", "-ok", "-okdir"].includes(a) && args[k + 1]?.replace(/^.*\//, "") === "rm")
  if (!del) return null
  let i = 0
  while (i < args.length && (["-H", "-L", "-P"].includes(args[i]) || args[i].startsWith("-O"))) i++
  const starts: string[] = []
  for (; i < args.length && !args[i].startsWith("-") && !["(", ")", "!"].includes(args[i]); i++) starts.push(args[i])
  return starts.length ? starts : ["."]
}

const RSYNC_ARGS = set("-e", "-f", "--rsh", "--exclude", "--include", "--exclude-from", "--include-from", "--filter", "--files-from", "--backup-dir", "--partial-dir", "--log-file", "--temp-dir", "--compare-dest", "--copy-dest", "--link-dest", "--timeout", "--port")

function rsyncTargets(args: string[]): string[] | null {
  if (!args.some((a) => a === "--del" || a.startsWith("--delete"))) return null
  const pos = positionals(args, RSYNC_ARGS)
  if (pos.length < 2) return null
  const dest = pos[pos.length - 1]
  if (dest.startsWith("rsync://") || /^([^/:@]+@)?[^/:@]+:/.test(dest)) return null // remote
  return [dest]
}

function recursiveDelete(P: Parsed, ctx: ShellCtx): boolean {
  for (const c of P.commands) {
    const args = c.slice(1)
    const targets = c[0] === "rm" ? rmTargets(args) : c[0] === "find" ? findTargets(args) : c[0] === "rsync" ? rsyncTargets(args) : null
    if (targets === null) continue
    // No visible target (for example `xargs rm -rf`): the real targets are unknown.
    if (targets.length === 0 || targets.some((t) => targetDenied(t, ctx))) return true
  }
  return false
}

// ---- git ----

const GIT_VALUE_OPTS = set("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env")

function gitCmd(argv: string[]) {
  let i = 1
  let dirChanged = false
  while (i < argv.length && argv[i].startsWith("-")) {
    const a = argv[i]
    if (a === "-C" || a.startsWith("--git-dir") || a.startsWith("--work-tree")) dirChanged = true
    i += GIT_VALUE_OPTS.has(a) ? 2 : 1
  }
  return { sub: argv[i], rest: argv.slice(i + 1), dirChanged }
}

function destructiveGit(P: Parsed): boolean {
  for (const c of P.commands) {
    if (c[0] !== "git") continue
    const { sub, rest } = gitCmd(c)
    const before = beforeDD(rest)
    switch (sub) {
      case "reset":
        if (rest.includes("--hard")) return true
        break
      case "clean":
        return true
      case "push":
        if (
          before.some((a) => a === "--force" || a.startsWith("--force-") || /^-[A-Za-z]*f[A-Za-z]*$/.test(a)) ||
          rest.some((a) => a.length > 1 && a[0] === "+")
        )
          return true
        break
      case "checkout":
        if (rest.includes(".")) return true
        break
      case "restore": {
        if (!rest.includes(".")) break
        const staged = rest.includes("--staged") || hasShort(rest, "S")
        const worktree = rest.includes("--worktree") || hasShort(rest, "W")
        if (!staged || worktree) return true
        break
      }
      case "branch":
        if (before.some((a) => /^-[A-Za-z]*D[A-Za-z]*$/.test(a))) return true
        break
    }
  }
  return false
}

const isMainName = (a: string) => /(^|\/)(main|master)$/.test(a)

function mergeInShell(P: Parsed, ctx: ShellCtx): boolean {
  for (const c of P.commands) {
    const args = c.slice(1)
    if (c[0] === "gh") {
      const pos = positionals(args, set("-R", "--repo"))
      if (pos[0] === "pr" && pos[1] === "merge") return true
      if (pos[0] === "api" && args.some((a) => a.includes("/merge") || a.includes("mergePullRequest"))) return true
    } else if (c[0] === "git") {
      const { sub, rest, dirChanged } = gitCmd(c)
      if (sub !== "merge") continue
      // The target is the current branch. It is unknown after -C, so deny.
      if (dirChanged || !ctx.branch || isMainName(ctx.branch)) return true
      if (rest.some((a) => !a.startsWith("-") && isMainName(a))) return true
    }
  }
  return false
}

// ---- harness-self ----

const SELF_VERBS = set("off", "on", "wrong", "rollback")
const ESCALATE = set("sudo", "su", "pkexec", "doas")
const INTERPRETERS = /^(bun|bunx|node|deno|tsx|ts-node|npx|sh|bash|zsh|python[\d.]*)$/

function harnessSelf(P: Parsed, line: string, ctx: ShellCtx): boolean {
  if (P.programs.some((p) => ESCALATE.has(p))) return true
  let agentCli = false
  for (const c of P.commands) {
    const [prog, ...args] = c
    if (prog === "harness" && SELF_VERBS.has(args[0])) return true
    if (prog === "harness-rollback" || prog === "install.ts") return true
    if (INTERPRETERS.test(prog)) {
      const cli = args.findIndex((a) => /(^|\/)cli\.ts$/.test(a))
      if (cli >= 0 && SELF_VERBS.has(args[cli + 1])) return true
      if (args.some((a) => /(^|\/)harness-rollback$/.test(a) || /(^|\/)harness\/install\.ts$/.test(a))) return true
      if (args.some((a) => a === "install.ts") && path.basename(ctx.cwd) === "harness") return true
    }
    if (prog === "docker" && (args.includes("run") || args.includes("exec"))) {
      if (
        hasShort(args, "v") ||
        args.some((a) => /^(--volume|--mount|--privileged)(=|$)/.test(a) || /^-v./.test(a))
      )
        return true
    }
    if (prog === "opencode" && args[0] === "run") agentCli = true
    if (prog === "claude" && (args.includes("--print") || hasShort(args, "p"))) agentCli = true
  }
  // A grant word anywhere in the line, so `echo MERGE-OK 3 | claude -p` is caught too.
  return agentCli && /MERGE-OK|HARNESS-OK/.test(line)
}

// ---- ledger-write and harness-config-write ----

const DEST_LAST = set("cp", "ln", "install", "rsync")
const ALL_ARGS = set("mv", "rm", "touch", "truncate", "tee", "chmod", "chown", "chgrp", "mkdir", "rmdir", "unlink", "shred", "sqlite3", "sqlite")
const INTERP_CODE = /^(python[\d.]*|bun|node|deno|perl|ruby|php)$/
const CODE_FLAGS = set("-c", "-e", "-p", "-E", "--eval", "--print", "eval")

interface Writes {
  targets: string[]
  code: string[] // argv of interpreters run with inline code
}

function writes(P: Parsed): Writes {
  const targets = [...P.redirects]
  const code: string[] = []
  for (const c of P.commands) {
    const prog = c[0]
    const args = c.slice(1)
    if (DEST_LAST.has(prog)) {
      const t = args.findIndex((a) => a === "-t" || a === "--target-directory")
      const long = args.find((a) => a.startsWith("--target-directory="))
      if (t >= 0 && args[t + 1] !== undefined) targets.push(args[t + 1])
      else if (long) targets.push(long.slice("--target-directory=".length))
      else {
        const pos = positionals(args, set("-S", "--suffix"))
        if (pos.length) targets.push(pos[pos.length - 1])
      }
    } else if (ALL_ARGS.has(prog)) {
      targets.push(...positionals(args, prog === "truncate" ? set("-s", "-r", "--size", "--reference") : set()))
    } else if (prog === "dd") {
      for (const a of args) if (a.startsWith("of=")) targets.push(a.slice(3))
    } else if ((prog === "sed" && args.some((a) => /^-[A-Za-z]*i/.test(a) || a.startsWith("--in-place"))) ||
      (prog === "perl" && args.some((a) => /^-[A-Za-z]*i/.test(a)))) {
      targets.push(...positionals(args, set("-e", "-f", "--expression", "--file")))
    } else if (INTERP_CODE.test(prog) && args.some((a) => CODE_FLAGS.has(a))) {
      code.push(...args)
    }
  }
  return { targets, code }
}

// Inline code (python -c, bun -e) that names a protected path counts as a write only when it also
// writes something. A read-only script that loads settings.json is not a write (seen live 2026-11-25).
const WRITE_CODE = /open\([^)]*,\s*['"][^'"]*[wax+]|\.write(?:_text|_bytes|File|FileSync)?\(|Bun\.write|json\.dump\(|appendFile|unlink|rmSync|\brename|shutil\.|os\.(?:remove|replace)|truncate|writelines/
const writesCode = (code: string[]) => WRITE_CODE.test(code.join("\n"))

function ledgerWrite(W: Writes, ctx: ShellCtx): boolean {
  if (W.code.some((s) => s.includes(".local/state/harness")) && writesCode(W.code)) return true
  return W.targets.some((t) => {
    const p = resolveTarget(t, ctx)
    return p !== null && isLedgerPath(p, ctx.home)
  })
}

function harnessConfigWrite(W: Writes, ctx: ShellCtx): boolean {
  if (W.code.some((s) => /\.claude\/settings|opencode\.jsonc?|\.config\/opencode\/plugins\/harness/.test(s)) && writesCode(W.code)) return true
  return W.targets.some((t) => {
    const p = resolveTarget(t, ctx)
    return p !== null && isHarnessConfigPath(p, ctx.home)
  })
}

// ---- entry ----

export function checkShell(line: string, ctx: ShellCtx): ShellHit | null {
  const P = parse(line)
  let W: Writes | null = null
  const writesOf = () => (W ??= writes(P))
  // Order matters: the first match wins.
  const rules: Array<[keyof typeof MSG, () => boolean]> = [
    ["harness-self", () => harnessSelf(P, line, ctx)],
    ["ledger-write", () => ledgerWrite(writesOf(), ctx)],
    ["harness-config-write", () => harnessConfigWrite(writesOf(), ctx)],
    ["destructive-git", () => destructiveGit(P)],
    ["merge-in-shell", () => mergeInShell(P, ctx)],
    ["recursive-delete", () => recursiveDelete(P, ctx)],
  ]
  for (const [ruleId, hit] of rules) {
    if (ctx.only && !ctx.only.includes(ruleId)) continue
    if (hit()) return { ruleId, message: MSG[ruleId] }
  }
  return null
}
