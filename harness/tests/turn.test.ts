// Architecture #1 + #4 (review 2026-11-27, decided with Alex): one Turn module answers "what did this session
// do this turn", built from the journal through decide(), so policies stop re-deriving it with SQL and
// regex on bare field names. Tool identity is a closed `kind`, set by the adapters' normalize step.
import { afterEach, beforeEach, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { closeCore, decide } from "../src/core.ts"
import { openLedger } from "../src/ledger/db.ts"
import { toolKind, turnOf } from "../src/turn.ts"
import type { HarnessEvent } from "../src/types.ts"

let dir: string
let db: Database
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-turn-"))
  process.env.HARNESS_STATE_DIR = dir
  process.env.HARNESS_JUDGE = "fallback"
  db = openLedger()
})
afterEach(() => {
  closeCore()
  db.close()
  delete process.env.HARNESS_STATE_DIR
  delete process.env.HARNESS_JUDGE
  rmSync(dir, { recursive: true, force: true })
})

const ev = (over: Partial<HarnessEvent>): HarnessEvent => ({ v: 1, event: "tool.after", tool: "claude", session: "s1", parentSession: null, cwd: "/r", time: Date.now(), ...over })
const after = (toolName: string, input: Record<string, unknown>, over: Partial<HarnessEvent> = {}) => decide(ev({ toolName, input, output: "ok", ...over }))

test("toolKind maps every host spelling to one closed kind", () => {
  expect(toolKind("shell")).toBe("shell")
  expect(toolKind("edit")).toBe("edit")
  expect(toolKind("write")).toBe("edit")
  expect(toolKind("subagent")).toBe("subagent")
  expect(toolKind("question")).toBe("question")
  expect(toolKind("askuserquestion")).toBe("question")
  expect(toolKind("taskcreate")).toBe("todo")
  expect(toolKind("todowrite")).toBe("todo")
  expect(toolKind("mcp:browse:screenshot")).toBe("browse")
  expect(toolKind("mcp:browse:handoff")).toBe("browse")
  expect(toolKind("webfetch")).toBe("fetch")
  expect(toolKind("mcp:harness:verify")).toBe("harness")
  expect(toolKind("mcp:atlassian:createJiraIssue")).toBe("external-write")
  expect(toolKind("mcp:slack:slack_send_message")).toBe("external-write")
  expect(toolKind("mcp:atlassian:getJiraIssue")).toBe("mcp")
  expect(toolKind("read")).toBe("read")
})

test("turnOf answers what this session did this turn, and only this turn", async () => {
  await decide(ev({ event: "prompt", prompt: "first" }))
  await after("write", { path: "/r/old.ts" })
  await decide(ev({ event: "prompt", prompt: "fix the bug" }))
  await after("edit", { path: "/r/a.ts" })
  await after("write", { path: "/r/ui/app.css" })
  await after("shell", { command: "git commit -qam x", cwd: "/r" })
  await after("shell", { command: "git push origin main", cwd: "/r" }, { failed: true })
  await after("mcp:browse:screenshot", { tab: "t" })
  await after("mcp:browse:handoff", { tab: "t" })
  await after("mcp:harness:verify", { commands: ["true"] })
  await decide(ev({ session: "s2", event: "prompt", prompt: "other" }))
  await decide(ev({ session: "s2", toolName: "edit", input: { path: "/r/other.ts" }, output: "ok" }))

  const t = turnOf(db, "s1")
  expect(t.prompt).toBe("fix the bug")
  expect(t.edited).toEqual(["/r/a.ts", "/r/ui/app.css"])
  expect(t.shell.map((s) => s.command)).toEqual(["git commit -qam x", "git push origin main"])
  expect(t.shell.map((s) => s.failed)).toEqual([false, true])
  expect(t.browsed).toBe(true)
  expect(t.triedHandoff).toBe(true)
  expect(t.kinds()).toEqual(new Set(["edit", "shell", "browse", "harness"]))
  expect(t.calls.length).toBe(7)
  // Nothing from the earlier turn or the other session.
  expect(t.edited).not.toContain("/r/old.ts")
  expect(t.edited).not.toContain("/r/other.ts")
})

test("a fresh session has an empty turn, not an error", () => {
  const t = turnOf(db, "nobody")
  expect(t.calls).toEqual([])
  expect(t.edited).toEqual([])
  expect(t.browsed).toBe(false)
  expect(t.prompt).toBeNull()
})
