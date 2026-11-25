// D49: the one list of harness hook entries. install.ts writes both tools' config from it.
// Command placeholders: {bun} = the bun binary, {root} = the harness directory.

export interface ManifestEntry {
  id: string
  tool: "claude" | "opencode"
  event: string // Claude hook event name, or "*" for the OpenCode plugin
  transport: "command" | "plugin"
  matcher?: string
  onFailure?: "block" | "continue"
  command?: string[]
}

export const HARNESS_ID_FLAG = "--harness-id="

function claude(id: string, event: string, arg: string, matcher?: string): ManifestEntry {
  return {
    id,
    tool: "claude",
    event,
    transport: "command",
    ...(matcher ? { matcher } : {}),
    onFailure: "continue",
    command: ["{bun}", "{root}/src/adapters/claude.ts", arg],
  }
}

export const MANIFEST: ManifestEntry[] = [
  claude("claude-session-start", "SessionStart", "session.start"),
  claude("claude-prompt", "UserPromptSubmit", "prompt"),
  claude("claude-pre-tool", "PreToolUse", "tool.before", "*"),
  claude("claude-post-tool", "PostToolUse", "tool.after", "*"),
  claude("claude-stop", "Stop", "stop"),
  claude("claude-subagent-stop", "SubagentStop", "stop"),
  claude("claude-session-end", "SessionEnd", "session.end"),
  {
    id: "claude-guard-lite",
    tool: "claude",
    event: "PreToolUse",
    transport: "command",
    matcher: "Bash",
    onFailure: "block",
    command: ["{bun}", "{root}/guard-lite.ts"],
  },
  { id: "opencode-plugin", tool: "opencode", event: "*", transport: "plugin", onFailure: "continue" },
]
