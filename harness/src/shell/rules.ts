// Shell guard rules (spec: Phase 1 Guard rules, D5, D31, D36, D37, D72). Pure functions.
// The guard stops agent mistakes, not a hostile agent (D72).
import { posix as path } from "node:path"
import { INLINE_FLAG, INTERP_CODE, parse, type Dirs, type Parsed } from "./parse"
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

const DECODED_MSG = "Running decoded text as a shell is not allowed. Run the command itself."

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

// The directory a command runs in after the `cd`s before it. null when a `cd` target is not literal.
function effectiveCwd(dirs: Dirs | undefined, ctx: ShellCtx): string | null {
  let cwd: string | null = ctx.cwd
  for (const d of dirs ?? []) {
    const e = d === null ? null : expand(d, ctx)
    if (e === null || e.includes("$") || e.includes("`") || (cwd === null && !e.startsWith("/"))) cwd = null
    else cwd = path.resolve(cwd ?? "/", e)
  }
  return cwd
}

// Absolute path of a write target, or null if it holds a variable or substitution we cannot resolve.
function resolveTarget(raw: string, ctx: ShellCtx, cwd: string | null = ctx.cwd): string | null {
  const e = expand(raw, ctx)
  if (e.includes("$") || e.includes("`")) return null
  if (cwd === null && !e.startsWith("/")) return null
  return path.resolve(cwd ?? "/", globPrefix(e))
}

// D5: allowed when inside an allow root, or tracked/ignored inside the repo. Repo root and .git never.
function targetDenied(raw: string, ctx: ShellCtx, cwd: string | null = ctx.cwd): boolean {
  const p = resolveTarget(raw, ctx, cwd)
  if (p === null) return true
  const repo = ctx.repoRoot ? path.resolve(ctx.repoRoot) : null
  if (repo && (p === repo || inside(p, repo + "/.git"))) return true
  // The allow root itself is never a delete target (`rm -rf /tmp`); a glob (`/tmp/*`) only reaches inside it.
  const e = expand(raw, ctx)
  const globbed = globPrefix(e) !== e
  if (ctx.allowRoots.some((r) => inside(p, path.resolve(r)) && (globbed || p !== path.resolve(r)))) return false
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

// Interpreter inline code that deletes a tree: python shutil.rmtree, perl rmtree/remove_tree, ruby FileUtils.rm_rf,
// node/bun rmSync/rm/rmdirSync with `recursive`. A literal first argument gets the rm -rf allowlist; anything else is outside.
const RM_ALWAYS = /(?:shutil\.rmtree|\brmtree|\bremove_tree|FileUtils\.(?:rm_rf|rm_r|rmtree|remove_dir|remove_entry(?:_secure)?)|\brm_rf)\s*\(?\s*/g
const RM_NODE = /\b(?:rmSync|rmdirSync|rm|rmdir)\s*\(/g
const RECURSIVE_ON = /recursive['"]?\s*:\s*(?!false|0\b)/
const LITERAL_ARG = /^\s*[rbfuRBFU]{0,2}(['"`])([^'"`$\\{]*)\1\s*(?:[,)\]};]|$)/

function callArgs(code: string, from: number): string {
  let depth = 1
  for (let j = from; j < code.length; j++) {
    if (code[j] === "(") depth++
    else if (code[j] === ")" && --depth === 0) return code.slice(from, j)
  }
  return code.slice(from)
}

function codeDeletes(code: string, ctx: ShellCtx, cwd: string | null): boolean {
  for (const [re, needsRecursive] of [[RM_ALWAYS, false], [RM_NODE, true]] as const) {
    for (const m of code.matchAll(re)) {
      const start = m.index + m[0].length
      if (needsRecursive && !RECURSIVE_ON.test(callArgs(code, start))) continue
      const lit = LITERAL_ARG.exec(code.slice(start))
      if (!lit || targetDenied(lit[2], ctx, cwd)) return true
    }
  }
  return false
}

function recursiveDelete(P: Parsed, ctx: ShellCtx): boolean {
  for (const [n, c] of P.commands.entries()) {
    const args = c.slice(1)
    const cwd = effectiveCwd(P.dirs[n], ctx)
    if (INTERP_CODE.test(c[0]) && args.some((a) => INLINE_FLAG.test(a)) && codeDeletes(args.join("\n"), ctx, cwd)) return true
    const targets = c[0] === "rm" ? rmTargets(args) : c[0] === "find" ? findTargets(args) : c[0] === "rsync" ? rsyncTargets(args) : null
    if (targets === null) continue
    // No visible target (for example `xargs rm -rf`): the real targets are unknown.
    if (targets.length === 0 || targets.some((t) => targetDenied(t, ctx, cwd))) return true
  }
  // A heredoc body an interpreter reads from stdin is inline code too.
  return P.inline.some((b) => codeDeletes(b.code, ctx, effectiveCwd(b.dirs, ctx)))
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
          before.some(
            (a) =>
              a === "--force" || a.startsWith("--force-") || a === "--mirror" || a === "--delete" || /^-[A-Za-z]*[fd][A-Za-z]*$/.test(a),
          ) ||
          rest.some((a) => a.length > 1 && (a[0] === "+" || a[0] === ":"))
        )
          return true
        break
      case "checkout":
        if (rest.includes(".") || before.includes("--force") || hasShort(before, "f")) return true
        break
      case "switch":
        if (before.some((a) => a === "--force" || a === "--discard-changes") || hasShort(before, "f")) return true
        break
      case "stash":
        if (rest[0] === "clear") return true
        break
      case "restore": {
        if (!rest.includes(".")) break
        const staged = rest.includes("--staged") || hasShort(rest, "S")
        const worktree = rest.includes("--worktree") || hasShort(rest, "W")
        if (!staged || worktree) return true
        break
      }
      case "branch": {
        // -D, or a delete (-d, --delete) together with force (-f, --force).
        const del = before.includes("--delete") || hasShort(before, "d")
        const force = before.includes("--force") || hasShort(before, "f")
        if (hasShort(before, "D") || (del && force)) return true
        break
      }
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
const INTERPRETERS = /^(bun|bunx|node|nodejs|deno|tsx|ts-node|npx|sh|bash|zsh|python[\d.]*)$/

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
    if (prog === "opencode" && (args[0] === "run" || args[0] === "api")) agentCli = true
    if ((prog === "claude" || prog === "cursor-agent") && (args.includes("--print") || hasShort(args, "p"))) agentCli = true
    if (prog === "codex" && args.includes("exec")) agentCli = true
  }
  // A grant or kill-switch phrase anywhere in the line, so `echo MERGE-OK 3 | claude -p` is caught too.
  // Same phrases as command() in ledger/authority.ts (its regexes are private).
  return agentCli && AUTHORITY_PHRASE.test(line)
}

const AUTHORITY_PHRASE = /MERGE-OK|HARNESS-OK|\bharness (?:off|on|wrong|rollback)\b/

// ---- ledger-write and harness-config-write ----

const DEST_LAST = set("cp", "ln", "install", "rsync")
const ALL_ARGS = set("mv", "rm", "touch", "truncate", "tee", "chmod", "chown", "chgrp", "mkdir", "rmdir", "unlink", "shred", "sqlite3", "sqlite")
const CODE_FLAGS = set("-c", "-e", "-p", "-E", "--eval", "--print", "eval")

interface Target {
  path: string
  dirs: Dirs
  db?: boolean // the database argument of a sqlite3 CLI
}

interface Writes {
  targets: Target[]
  code: string[] // argv of interpreters run with inline code
}

function writes(P: Parsed): Writes {
  const all: Target[] = P.redirects.map((path, n) => ({ path, dirs: P.redirectDirs[n] }))
  const code: string[] = P.inline.map((b) => b.code)
  for (const [n, c] of P.commands.entries()) {
    const targets: string[] = []
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
    targets.forEach((t, k) => all.push({ path: t, dirs: P.dirs[n], db: (prog === "sqlite3" || prog === "sqlite") && k === 0 }))
  }
  return { targets: all, code }
}

const resolveWrite = (t: Target, ctx: ShellCtx) => resolveTarget(t.path, ctx, effectiveCwd(t.dirs, ctx))

// Inline code (python -c, bun -e) that names a protected path counts as a write only when it also
// writes something. A read-only script that loads settings.json is not a write (seen live 2026-11-25).
const WRITE_CODE = /open\([^)]*,\s*['"][^'"]*[wax+]|\.write(?:_text|_bytes|File|FileSync)?\(|Bun\.write|json\.dump\(|appendFile|unlink|rmSync|\brename|shutil\.|os\.(?:remove|replace)|truncate|writelines/
const writesCode = (code: string[]) => WRITE_CODE.test(code.join("\n"))

// Any sqlite library call on the ledger is a write route, even a read-looking one: the same call runs `delete`.
const SQLITE_API = /\bDatabase\(|sqlite3\.connect|\.exec\(|\.execute\(|\.run\(/
const NAMES_LEDGER = /\.local\/state\/harness|ledger\.db/

function ledgerWrite(W: Writes, ctx: ShellCtx): boolean {
  if (W.code.some((s) => s.includes(".local/state/harness")) && writesCode(W.code)) return true
  const code = W.code.join("\n")
  if (NAMES_LEDGER.test(code) && SQLITE_API.test(code)) return true
  return W.targets.some((t) => {
    const p = resolveWrite(t, ctx)
    // An unresolved sqlite3 path ($VAR, $(...)) that names harness or ledger.db is denied.
    if (p === null) return !!t.db && /harness|ledger\.db/.test(t.path)
    return isLedgerPath(p, ctx.home)
  })
}

function harnessConfigWrite(W: Writes, ctx: ShellCtx): boolean {
  if (W.code.some((s) => /\.claude\/settings|opencode\.jsonc?|\.config\/opencode\/plugins\/harness/.test(s)) && writesCode(W.code)) return true
  return W.targets.some((t) => {
    const p = resolveWrite(t, ctx)
    return p !== null && isHarnessConfigPath(p, ctx.home)
  })
}

// ---- entry ----

export function checkShell(line: string, ctx: ShellCtx): ShellHit | null {
  const P = parse(line)
  let W: Writes | null = null
  const writesOf = () => (W ??= writes(P))
  // Order matters: the first match wins.
  const rules: Array<[keyof typeof MSG, () => boolean, string?]> = [
    ["harness-self", () => harnessSelf(P, line, ctx)],
    ["harness-self", () => P.decodedShell, DECODED_MSG],
    ["ledger-write", () => ledgerWrite(writesOf(), ctx)],
    ["harness-config-write", () => harnessConfigWrite(writesOf(), ctx)],
    ["destructive-git", () => destructiveGit(P)],
    ["merge-in-shell", () => mergeInShell(P, ctx)],
    ["recursive-delete", () => recursiveDelete(P, ctx)],
  ]
  for (const [ruleId, hit, message] of rules) {
    if (ctx.only && !ctx.only.includes(ruleId)) continue
    if (hit()) return { ruleId, message: message ?? MSG[ruleId] }
  }
  return null
}
