// Where each rule runs, in one place. core.ts dispatches tool.before from GUARDS, stop.ts runs STOP_CHECKS,
// and ruleEvents() reads the registry, so a rule's event column cannot drift from the code unnoticed.
// Adding a tool.before rule: add its guard here and its row in registry.ts. A stop rule: add it to STOP_CHECKS
// (declared next to its checks in stop.ts, re-exported here) and registry.ts.
import { RULES } from "../ledger/registry.ts"
import type { Kind } from "../turn.ts"
import { guardEgress } from "./egress.ts"
import { guardPath, guardShell } from "./guard.ts"
import { guardMcp } from "./mcp.ts"
import { guardPagePort } from "./pageport.ts"
import { guardSpawn } from "./spawn.ts"
import type { Env, Out } from "./util.ts"
import { guardPush, recordWorker } from "./worker.ts"
import { guardWorktree } from "./worktree.ts"

export { STOP_CHECKS } from "./stop.ts"
export type { StopCheck } from "./stop.ts"

export interface Guard {
  name: string
  kinds: Kind[]
  rules: string[] // the rule ids this guard can emit
  run(env: Env): Out | null
}

// A worker spawn is recorded unless the spawn is denied (the recording stays a side effect of the spawn guard).
function spawn(env: Env): Out | null {
  const o = guardSpawn(env)
  if (o?.decision.outcome !== "deny") recordWorker(env)
  return o
}

// The order here is the order of evaluation within a kind. The first deny wins (chain() in core.ts).
export const GUARDS: Guard[] = [
  { name: "shell", kinds: ["shell"], rules: ["recursive-delete", "merge-in-shell", "destructive-git", "harness-self", "ledger-write", "harness-config-write"], run: guardShell },
  { name: "path", kinds: ["edit"], rules: ["ledger-write", "harness-config-write"], run: guardPath },
  { name: "spawn", kinds: ["subagent"], rules: ["spawn-model", "spawn-acceptance"], run: spawn },
  { name: "mcp", kinds: ["harness"], rules: ["mcp-session"], run: guardMcp },
  { name: "page-port", kinds: ["shell", "browse"], rules: ["page-port"], run: guardPagePort },
  { name: "push", kinds: ["shell"], rules: ["push-gate"], run: guardPush },
  { name: "worktree", kinds: ["shell", "edit"], rules: ["main-checkout-write"], run: guardWorktree },
  { name: "egress", kinds: ["shell", "fetch", "mcp", "external-write"], rules: ["egress"], run: guardEgress },
]

export const guardsFor = (kind: Kind): Guard[] => GUARDS.filter((g) => g.kinds.includes(kind))

// Every event a rule runs on: its registry event plus the ones it declares in `also`.
export function ruleEvents(id: string): Set<string> {
  const r = RULES.find((x) => x.id === id)
  if (!r) throw new Error(`unknown rule: ${id}`)
  return new Set([r.event, ...(r.also ?? [])])
}
