// Claude Code command hook: `bun src/adapters/claude.ts <event> [--harness-id=<id>]`.
// Reads the hook JSON on stdin, asks the core, prints the Claude output shape.
import { decide } from "../core.ts"
import type { Decision, EventName } from "../types.ts"
import { claudeToolName, fromClaude } from "./normalize.ts"

export const DECIDE_TIMEOUT_MS = 2500
const EVENTS: EventName[] = ["session.start", "prompt", "tool.before", "tool.after", "stop", "session.end"]

export interface HookResult {
  stdout?: string
  stderr?: string
  code: number
}

const SILENT: HookResult = { code: 0 }

function denyOutput(message: string): HookResult {
  return {
    code: 0,
    stdout: JSON.stringify({
      hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: message },
    }),
  }
}

function contextOutput(hookEventName: string, additionalContext: string): HookResult {
  return { code: 0, stdout: JSON.stringify({ hookSpecificOutput: { hookEventName, additionalContext } }) }
}

/** Put a modified normalized input back into Claude's own field names, keeping the other fields. */
function toClaudeInput(tool: string | undefined, original: Record<string, any>, next: Record<string, any>) {
  const out: Record<string, any> = { ...original }
  const { path, agent, cwd, ...rest } = next
  if (tool === "shell") {
    if (next.command !== undefined) out.command = next.command
    return out
  }
  if (tool === "edit" || tool === "write" || tool === "read") {
    if (path !== undefined) out.file_path = path
    if (next.content !== undefined && "content" in original) out.content = next.content
    return out
  }
  if (tool === "subagent") {
    if (next.prompt !== undefined) out.prompt = next.prompt
    if (next.model !== undefined) out.model = next.model
    if (agent !== undefined) out.subagent_type = agent
    return out
  }
  return { ...out, ...next }
}

function toResult(name: EventName, stdin: any, d: Decision): HookResult {
  const toolName = stdin?.tool_name
  switch (name) {
    case "tool.before": {
      const reason = d.message ?? ""
      if (d.outcome === "deny") return denyOutput(reason)
      if (d.outcome === "ask") {
        return {
          code: 0,
          stdout: JSON.stringify({
            hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: reason },
          }),
        }
      }
      if (d.outcome === "modify" && d.input) {
        const canonical = claudeToolName(toolName ?? "")
        return {
          code: 0,
          stdout: JSON.stringify({
            hookSpecificOutput: {
              hookEventName: "PreToolUse",
              permissionDecision: "allow",
              updatedInput: toClaudeInput(canonical, stdin?.tool_input ?? {}, d.input),
            },
          }),
        }
      }
      return SILENT
    }
    case "tool.after":
      return d.context ? contextOutput("PostToolUse", d.context) : SILENT
    case "prompt":
      return d.context ? contextOutput("UserPromptSubmit", d.context) : SILENT
    case "session.start":
      return d.context ? contextOutput("SessionStart", d.context) : SILENT
    case "stop":
      return d.outcome === "deny" ? { code: 2, stderr: d.message ?? "Stopped by harness." } : SILENT
    default:
      return SILENT
  }
}

/** Failure-mode shell check: a deny message when the destructive rules hit, else null. A missing rules module = allow. */
export async function shellFailureCheck(command: string, cwd?: string): Promise<string | null> {
  try {
    const { checkShell } = await import("../shell/rules.ts")
    const { shellCtx, DESTRUCTIVE } = await import("../shell/ctx.ts")
    const hit = checkShell(command, shellCtx(cwd || process.cwd(), DESTRUCTIVE))
    return hit ? hit.message : null
  } catch {
    return null
  }
}

/** Failure mode: only a destructive shell command is still denied; everything else passes. */
async function failureMode(name: EventName, stdin: any): Promise<HookResult> {
  if (name !== "tool.before" || stdin?.tool_name !== "Bash") return SILENT
  const command = stdin?.tool_input?.command
  if (typeof command !== "string") return SILENT
  const msg = await shellFailureCheck(command, stdin?.cwd)
  return msg === null ? SILENT : denyOutput(msg)
}

export function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`decide timed out after ${ms} ms`)), ms)
    p.then(
      (v) => (clearTimeout(t), resolve(v)),
      (e) => (clearTimeout(t), reject(e)),
    )
  })
}

export async function handle(name: EventName, raw: string): Promise<HookResult> {
  let stdin: any = {}
  try {
    stdin = raw.trim() ? JSON.parse(raw) : {}
    if (process.env.HARNESS_TEST_THROW === "1") throw new Error("HARNESS_TEST_THROW")
    const ev = fromClaude(name, stdin)
    const d = await withTimeout(decide(ev), DECIDE_TIMEOUT_MS)
    return toResult(name, stdin, d)
  } catch {
    return failureMode(name, stdin)
  }
}

if (import.meta.main) {
  const name = process.argv[2] as EventName
  let result: HookResult = SILENT
  if (EVENTS.includes(name)) {
    const raw = await Bun.stdin.text().catch(() => "")
    result = await handle(name, raw)
  }
  if (result.stdout) process.stdout.write(result.stdout + "\n")
  if (result.stderr) process.stderr.write(result.stderr + "\n")
  // Exit explicitly: a timed-out decide may leave work pending.
  process.exit(result.code)
}
