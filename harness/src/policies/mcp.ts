// tool.before for the harness MCP server's own tools: bind each call to the caller's session (D29, D34).
// The server cannot tell who calls it. Without this, a model could name another session's id.
import { RULES, mode } from "../ledger/registry.ts"
import { type Env, type Out } from "./util.ts"

const RULE = "mcp-session"

export function guardMcp(env: Env): Out | null {
  const { ev } = env
  if (!ev.toolName?.startsWith("mcp:harness:") || !ev.session) return null
  const input = ev.input ?? {}
  if (input.session === ev.session) return null
  // OpenCode's permission event shows no MCP arguments, only `resources`. The plugin's execute.before
  // binds the session there, so there is nothing to check here.
  if (ev.tool === "opencode" && !("session" in input) && "resources" in input) return null

  // The rule joins the registry in a later change; until then the binding is always enforced.
  const ruleId = RULES.some((r) => r.id === RULE) ? RULE : undefined
  if (ruleId && mode(env.db, ruleId) === "off") return null

  if (ev.tool === "claude") {
    return { decision: { outcome: "modify", input: { ...input, session: ev.session }, ruleId }, ruleId, reason: "session set from the hook", data: { rule: RULE } }
  }
  // OpenCode cannot change the input (Phase 0): the deny message carries the fix.
  const message = `Pass session: "${ev.session}" to this harness tool.`
  return { decision: { outcome: "deny", message, ruleId }, ruleId, reason: message, data: { rule: RULE } }
}
