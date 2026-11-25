// The one interface between the tools and the harness core (spec: Shape, Interface).
// Adapters translate each tool's hook format into HarnessEvent and a Decision back.

export type EventName = "tool.before" | "tool.after" | "prompt" | "stop" | "session.start" | "session.end"

export type HostTool = "claude" | "opencode"

// Canonical tool names. Adapters map: Claude Bash / OpenCode shell -> "shell";
// Edit, MultiEdit / edit, patch -> "edit"; Write / write -> "write"; Read / read -> "read";
// Agent, Task / subagent -> "subagent"; MCP tools -> "mcp:<server>:<tool>"; anything else as-is, lowercase.
export type ToolName = "shell" | "edit" | "write" | "read" | "subagent" | (string & {})

export interface HarnessEvent {
  v: 1
  event: EventName
  tool: HostTool
  session: string
  parentSession?: string | null
  cwd: string
  time: number // Unix ms
  toolName?: ToolName
  // Normalized input. shell: { command, cwd? }. edit/write/read: { path, content? }.
  // subagent: { prompt, model?, agent? }. Other tools: the raw input.
  input?: Record<string, unknown>
  output?: string // tool.after only
  failed?: boolean // tool.after only
  prompt?: string // prompt only
  reply?: string // stop only: the last assistant message
  stopActive?: boolean // stop only: the tool already sent the agent back this turn
  source?: string // session.start only: "startup", "resume", "clear" or "compact"
}

export type Outcome = "allow" | "deny" | "modify" | "ask"

export interface Decision {
  outcome: Outcome
  message?: string // shown to the agent on deny, ask and stop send-back
  input?: Record<string, unknown> // modify on tool.before: the replacement input
  context?: string // modify on tool.after, prompt or session.start: text added for the agent
  ruleId?: string
}

export const ALLOW: Decision = { outcome: "allow" }

// What every policy module exports. A policy returns null when it has nothing to say.
export type Policy = (ev: HarnessEvent) => Decision | null | Promise<Decision | null>
