import { describe, expect, test } from "bun:test"
import { existsSync } from "node:fs"
import { join } from "node:path"
import { fromClaude, fromOpenCode } from "../src/adapters/normalize.ts"

const ROOT = join(import.meta.dir, "..")

async function runClaude(event: string, stdin: unknown, env: Record<string, string> = {}) {
  const p = Bun.spawn([process.execPath, "src/adapters/claude.ts", event], {
    cwd: ROOT,
    stdin: new TextEncoder().encode(JSON.stringify(stdin)),
    stdout: "pipe",
    stderr: "pipe",
    env: { ...process.env, ...env },
  })
  const [stdout, stderr, code] = await Promise.all([new Response(p.stdout).text(), new Response(p.stderr).text(), p.exited])
  return { stdout, stderr, code }
}

const preToolUse = (tool_name: string, tool_input: unknown) => ({
  cwd: "/tmp",
  permission_mode: "default",
  prompt_id: "p1",
  session_id: "s1",
  tool_input,
  tool_name,
  tool_use_id: "t1",
  transcript_path: "/tmp/t.jsonl",
})

describe("claude adapter", () => {
  test("allow prints nothing and exits 0 while core.decide is the stub", async () => {
    const r = await runClaude("tool.before", preToolUse("Bash", { command: "echo hi" }))
    expect(r).toEqual({ stdout: "", stderr: "", code: 0 })
  })

  test("failure mode: a thrown error denies a destructive shell command only when the rules module exists", async () => {
    const r = await runClaude("tool.before", preToolUse("Bash", { command: "rm -rf /home/x" }), { HARNESS_TEST_THROW: "1" })
    expect(r.code).toBe(0)
    if (existsSync(join(ROOT, "src/shell/rules.ts"))) {
      const out = JSON.parse(r.stdout)
      expect(out.hookSpecificOutput.hookEventName).toBe("PreToolUse")
      expect(out.hookSpecificOutput.permissionDecision).toBe("deny")
      expect(out.hookSpecificOutput.permissionDecisionReason).toBeTruthy()
    } else {
      expect(r.stdout).toBe("")
    }
  })

  test("failure mode: other events and tools pass silently", async () => {
    const env = { HARNESS_TEST_THROW: "1" }
    expect((await runClaude("tool.before", preToolUse("Read", { file_path: "/x" }), env)).stdout).toBe("")
    expect((await runClaude("stop", { session_id: "s1", last_assistant_message: "x" }, env))).toEqual({ stdout: "", stderr: "", code: 0 })
  })
})

describe("normalize", () => {
  test("Claude Bash -> shell {command, cwd}", () => {
    const ev = fromClaude("tool.before", preToolUse("Bash", { command: "ls" }))
    expect(ev.toolName).toBe("shell")
    expect(ev.input).toEqual({ command: "ls", cwd: "/tmp" })
    expect(ev.session).toBe("s1")
    expect(ev.tool).toBe("claude")
    expect(ev.parentSession).toBeNull()
  })

  test("Claude Edit -> edit {path}; Write keeps content", () => {
    const edit = fromClaude("tool.before", preToolUse("Edit", { file_path: "/a/b.ts", old_string: "x", new_string: "y" }))
    expect(edit.toolName).toBe("edit")
    expect(edit.input?.path).toBe("/a/b.ts")
    const write = fromClaude("tool.before", preToolUse("Write", { file_path: "/a/c.ts", content: "hi" }))
    expect(write.toolName).toBe("write")
    expect(write.input).toEqual({ path: "/a/c.ts", content: "hi" })
  })

  test("Claude Task and Agent -> subagent {prompt, model, agent}", () => {
    for (const name of ["Task", "Agent"]) {
      const ev = fromClaude("tool.before", preToolUse(name, { prompt: "do it", model: "haiku", subagent_type: "general" }))
      expect(ev.toolName).toBe("subagent")
      expect(ev.input).toEqual({ prompt: "do it", model: "haiku", agent: "general" })
    }
  })

  test("Claude MCP tool -> mcp:<server>:<tool>", () => {
    expect(fromClaude("tool.before", preToolUse("mcp__jev__ask_jev", {})).toolName).toBe("mcp:jev:ask_jev")
  })

  test("Claude stop carries reply and stopActive", () => {
    const ev = fromClaude("stop", { session_id: "s1", cwd: "/tmp", last_assistant_message: "done", stop_hook_active: true })
    expect(ev.reply).toBe("done")
    expect(ev.stopActive).toBe(true)
  })

  test("session.start carries the hook's source, so compaction can be told apart", () => {
    expect(fromClaude("session.start", { session_id: "c1", source: "compact" }).source).toBe("compact")
    expect(fromOpenCode("session.start", { sessionID: "o1", source: "compact" }).source).toBe("compact")
  })

  // Seen live 2026-11-25: dropping sessionID made every worker follow-up look like a spawn with no model.
  test("a subagent follow-up keeps its sessionID, and a Claude background agent keeps its flag", () => {
    const oc = fromOpenCode("tool.before", { sessionID: "o1", tool: "subagent", input: { agent: "general", prompt: "more", sessionID: "ses_w" } })
    expect(oc.input?.sessionID).toBe("ses_w")
    const cc = fromClaude("tool.before", { session_id: "c1", tool_name: "Agent", tool_input: { subagent_type: "general-purpose", prompt: "p", run_in_background: true } })
    expect(cc.input?.run_in_background).toBe(true)
  })

  test("OpenCode shell, edit, subagent map to the canonical names and inputs", () => {
    const sh = fromOpenCode("tool.before", { sessionID: "o1", cwd: "/w", tool: "shell", input: { command: "ls" } })
    expect(sh.toolName).toBe("shell")
    expect(sh.input).toEqual({ command: "ls", cwd: "/w" })
    expect(sh.tool).toBe("opencode")

    const ed = fromOpenCode("tool.before", { sessionID: "o1", tool: "edit", input: { filePath: "/a/b.ts" } })
    expect(ed.toolName).toBe("edit")
    expect(ed.input?.path).toBe("/a/b.ts")

    const sub = fromOpenCode("tool.before", { sessionID: "o1", tool: "subagent", input: { prompt: "p", model: "m", agent: "general" } })
    expect(sub.toolName).toBe("subagent")
    expect(sub.input).toEqual({ prompt: "p", model: "m", agent: "general" })
  })

  test("OpenCode MCP tool and parent session", () => {
    const ev = fromOpenCode("tool.before", { sessionID: "o2", parentSession: "o1", tool: "jev_ask_jev", input: { a: 1 } })
    expect(ev.toolName).toBe("mcp:jev:ask_jev")
    expect(ev.parentSession).toBe("o1")
  })
})
