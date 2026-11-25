// Claude Code PreToolUse hook: the destructive shell rules only, with no ledger and no network.
// Reads {tool_name, tool_input:{command}, cwd} on stdin. Prints a deny decision, or nothing.
// It always exits 0: a broken guard must not block the session.
import { checkShell } from "./src/shell/rules"
import { DESTRUCTIVE, shellCtx } from "./src/shell/ctx"

try {
  const input = JSON.parse(await Bun.stdin.text())
  const command = input?.tool_input?.command
  if (input?.tool_name === "Bash" && typeof command === "string") {
    const cwd: string = typeof input.cwd === "string" && input.cwd ? input.cwd : process.cwd()
    const hit = checkShell(command, shellCtx(cwd, DESTRUCTIVE))
    if (hit) {
      console.log(
        JSON.stringify({
          hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: hit.message },
        }),
      )
    }
  }
} catch {
  // allow
}
