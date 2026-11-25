import type { EventName, HarnessEvent, ToolName } from "../types.ts"

type Obj = Record<string, any>

const BUILTIN_OPENCODE = new Set(["shell", "edit", "write", "read", "subagent"])

export function claudeToolName(name: string): ToolName {
  switch (name) {
    case "Bash":
      return "shell"
    case "Edit":
    case "MultiEdit":
      return "edit"
    case "Write":
      return "write"
    case "Read":
      return "read"
    case "Agent":
    case "Task":
      return "subagent"
  }
  const mcp = /^mcp__(.+?)__(.+)$/.exec(name)
  if (mcp) return `mcp:${mcp[1]}:${mcp[2]}`
  return name.toLowerCase()
}

export function opencodeToolName(name: string): ToolName {
  if (name === "patch") return "edit"
  if (BUILTIN_OPENCODE.has(name)) return name
  // MCP tools are named <server>_<tool>. shortcut: any other name with "_" counts as MCP.
  const i = name.indexOf("_")
  if (i > 0) return `mcp:${name.slice(0, i)}:${name.slice(i + 1)}`
  return name.toLowerCase()
}

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined
}

function compact<T extends Obj>(o: T): T {
  for (const k of Object.keys(o)) if (o[k] === undefined) delete o[k]
  return o
}

/** Normalize a tool input by canonical tool name. `cwd` fills shell.cwd. */
function normalizeInput(tool: ToolName, raw: Obj, cwd: string, opencode: boolean): Record<string, unknown> {
  switch (tool) {
    case "shell":
      return compact({ command: str(raw.command) ?? "", cwd: str(raw.cwd) ?? str(raw.workdir) ?? cwd })
    case "edit":
    case "write":
    case "read":
      return compact({
        path: str(opencode ? (raw.filePath ?? raw.path) : (raw.file_path ?? raw.path)) ?? "",
        content: str(raw.content) ?? str(raw.new_string) ?? str(raw.newString),
      })
    case "subagent":
      return compact({
        prompt: str(raw.prompt) ?? "",
        model: str(raw.model),
        agent: str(opencode ? raw.agent : (raw.subagent_type ?? raw.agent)),
        sessionID: str(raw.sessionID), // a follow-up to a running worker (OpenCode)
        run_in_background: raw.run_in_background === true ? true : undefined, // Claude Code background agent
      })
    default:
      return raw
  }
}

function flatten(v: unknown): string {
  if (v == null) return ""
  if (typeof v === "string") return v
  if (typeof v === "object") {
    const o = v as Obj
    if (typeof o.stdout === "string" || typeof o.stderr === "string") {
      return [o.stdout, o.stderr].filter((s) => typeof s === "string" && s).join("\n")
    }
    if (typeof o.output === "string") return o.output
  }
  return JSON.stringify(v)
}

export function fromClaude(name: EventName, stdin: any): HarnessEvent {
  const s: Obj = stdin ?? {}
  const cwd = str(s.cwd) ?? process.cwd()
  const ev: HarnessEvent = {
    v: 1,
    event: name,
    tool: "claude",
    session: str(s.session_id) ?? "",
    parentSession: null,
    cwd,
    time: Date.now(),
  }
  if (name === "tool.before" || name === "tool.after") {
    const toolName = claudeToolName(str(s.tool_name) ?? "")
    ev.toolName = toolName
    ev.input = normalizeInput(toolName, s.tool_input ?? {}, cwd, false)
    if (name === "tool.after") {
      ev.output = flatten(s.tool_response)
      // shortcut: only an explicit is_error counts; a failed Bash may arrive as PostToolUseFailure instead.
      ev.failed = s.tool_response?.is_error === true
    }
  }
  if (name === "session.start" && str(s.source)) ev.source = str(s.source)
  if (name === "prompt") ev.prompt = str(s.prompt) ?? ""
  if (name === "stop") {
    ev.reply = str(s.last_assistant_message) ?? ""
    ev.stopActive = s.stop_hook_active === true
  }
  return ev
}

/**
 * OpenCode input is what the plugin collects from its hooks:
 * { sessionID, parentSession?, cwd?, tool?, input?, result?, error?, failed?, prompt?, reply?, stopActive? }
 */
export function fromOpenCode(name: EventName, data: any): HarnessEvent {
  const d: Obj = data ?? {}
  const cwd = str(d.cwd) ?? process.cwd()
  const ev: HarnessEvent = {
    v: 1,
    event: name,
    tool: "opencode",
    session: str(d.sessionID) ?? "",
    parentSession: str(d.parentSession) ?? null,
    cwd,
    time: Date.now(),
  }
  if (name === "tool.before" || name === "tool.after") {
    const toolName = opencodeToolName(str(d.tool) ?? "")
    ev.toolName = toolName
    ev.input = normalizeInput(toolName, d.input ?? {}, cwd, true)
    if (name === "tool.after") {
      ev.output = flatten(d.result?.output ?? d.result ?? d.error)
      ev.failed = d.failed === true || d.status === "error"
    }
  }
  if (name === "session.start" && str(d.source)) ev.source = str(d.source)
  if (name === "prompt") ev.prompt = str(d.prompt) ?? ""
  if (name === "stop") {
    ev.reply = str(d.reply) ?? ""
    ev.stopActive = d.stopActive === true
  }
  return ev
}
