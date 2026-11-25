// Path rules for edit/write tools. rules.ts reuses the same predicates for shell writes.
import { posix as path } from "node:path"

export const LEDGER_MSG = "Only the harness writes its state."
export const CONFIG_MSG =
  "Change the harness source in a worktree, get a green bundle, show Alex the diff, and ask for HARNESS-OK. `harness_apply` installs it."

export interface PathHit {
  ruleId: string
  message: string
}

export function inside(p: string, root: string): boolean {
  return p === root || p.startsWith(root === "/" ? "/" : root + "/")
}

export function isLedgerPath(abs: string, home: string): boolean {
  return inside(abs, path.join(home, ".local/state/harness"))
}

export function isHarnessConfigPath(abs: string, home: string): boolean {
  return (
    /\/\.claude\/settings[^/]*\.json$/.test(abs) ||
    /^opencode\.jsonc?$/.test(path.basename(abs)) ||
    abs.startsWith(path.join(home, ".config/opencode/plugins/harness"))
  )
}

export function checkPath(
  absPath: string,
  _op: "edit" | "write",
  ctx: { home: string; cwd: string },
): PathHit | null {
  const abs = path.resolve(ctx.cwd, absPath)
  if (isLedgerPath(abs, ctx.home)) return { ruleId: "ledger-write", message: LEDGER_MSG }
  if (isHarnessConfigPath(abs, ctx.home)) return { ruleId: "harness-config-write", message: CONFIG_MSG }
  return null
}
