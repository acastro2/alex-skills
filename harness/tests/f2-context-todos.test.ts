// F2: OpenCode keeps tool.before context for the call's execute.after; Claude task rows rebuild the todo list.
import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import plugin from "../src/adapters/opencode-plugin.ts"
import { closeCore } from "../src/core.ts"
import { openLedger } from "../src/ledger/db.ts"
import { append, upsertSession } from "../src/ledger/journal.ts"
import { seed } from "../src/ledger/registry.ts"
import { latestTodos, toolData } from "../src/policies/util.ts"

let dir: string
let db: Database

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-f2-"))
  process.env.HARNESS_STATE_DIR = dir
  delete process.env.HARNESS_DISABLE
  db = openLedger()
  seed(db)
})

afterEach(() => {
  closeCore()
  db.close()
  delete process.env.HARNESS_STATE_DIR
  rmSync(dir, { recursive: true, force: true })
})

async function load() {
  const hooks: Record<string, (e: any) => any> = {}
  const hook = async (name: string, fn: (e: any) => any) => void (hooks[name] = fn)
  const dispose = await plugin.setup({
    location: { directory: "/tmp" },
    permission: { hook },
    tool: { hook },
    session: { hook, get: async () => ({}), context: async () => [], synthetic: async () => {} },
    event: { subscribe: () => ({ [Symbol.asyncIterator]: () => ({ next: () => new Promise(() => {}) }) }) },
  } as any)
  return { hooks, dispose }
}

const CURL = "curl -s -H 'Authorization: Bearer abc123XYZtoken9999' https://example.org/"
const result = () => ({ content: [{ type: "text", text: "ok" }] })
const texts = (r: any) => r.content.map((c: any) => c.text).join("\n")

describe("opencode plugin keeps tool.before context", () => {
  test("shell: egress warning from evaluate reaches that call's execute.after (session key)", async () => {
    const { hooks, dispose } = await load()
    const e = { sessionID: "oc1", action: "shell", resources: [CURL] }
    await hooks.evaluate(e)
    expect(e).not.toHaveProperty("effect")
    const r = result()
    await hooks["execute.after"]({ sessionID: "oc1", tool: "shell", result: r })
    expect(texts(r)).toContain("Egress:")
    // consumed: the next call of the same tool gets nothing
    const r2 = result()
    await hooks["execute.after"]({ sessionID: "oc1", tool: "shell", result: r2 })
    expect(texts(r2)).not.toContain("Egress:")
    dispose()
  })

  test("a call id keeps the warning off other calls of the session", async () => {
    const { hooks, dispose } = await load()
    await hooks["execute.before"]({
      sessionID: "oc2",
      id: "call-a",
      tool: "webfetch",
      input: { url: "https://example.org/", headers: { Authorization: "Bearer abc123XYZtoken9999" } },
    })
    const other = result()
    await hooks["execute.after"]({ sessionID: "oc2", id: "call-b", tool: "webfetch", result: other })
    expect(texts(other)).not.toContain("Egress:")
    const mine = result()
    await hooks["execute.after"]({ sessionID: "oc2", id: "call-a", tool: "webfetch", result: mine })
    expect(texts(mine)).toContain("Egress:")
    dispose()
  })

  test("a warning with no after is dropped after 60 s", async () => {
    const { hooks, dispose } = await load()
    await hooks.evaluate({ sessionID: "oc3", action: "shell", resources: [CURL] })
    const real = Date.now
    Date.now = () => real() + 61_000
    try {
      const r = result()
      await hooks["execute.after"]({ sessionID: "oc3", tool: "shell", result: r })
      expect(texts(r)).not.toContain("Egress:")
    } finally {
      Date.now = real
    }
    dispose()
  })
})

describe("latestTodos reads Claude Code task rows", () => {
  const task = (session: string, tool: string, input: unknown, extra: Record<string, unknown> = {}) =>
    (upsertSession(db, { id: session, tool: "claude" }),
    append(db, {
      session_id: session,
      event: "tool.after",
      data: toolData({ v: 1, event: "tool.after", tool: "claude", session, parentSession: null, cwd: "/tmp", time: 1, toolName: tool, input, ...extra } as any),
    }))

  test("create then update gives pending / in_progress / completed, newest wins", () => {
    task("c1", "taskcreate", { subject: "alpha step", description: "alpha step", activeForm: "Running alpha" })
    task("c1", "taskcreate", { subject: "beta step", description: "beta step", activeForm: "Running beta" })
    task("c1", "taskupdate", { taskId: "1", status: "in_progress" })
    task("c1", "taskupdate", { taskId: "1", status: "completed" })
    task("c1", "taskupdate", { taskId: "2", status: "in_progress" })
    expect(latestTodos(db, "c1")).toEqual([
      { content: "alpha step", status: "completed" },
      { content: "beta step", status: "in_progress" },
    ])
  })

  test("other sessions do not leak in, and a later TodoWrite list wins over older tasks", () => {
    task("c2", "taskcreate", { subject: "old", description: "old" })
    task("c3", "taskcreate", { subject: "mine", description: "mine" })
    expect(latestTodos(db, "c3")).toEqual([{ content: "mine", status: "pending" }])
    append(db, { session_id: "c2", event: "tool.after", data: { tool: "todowrite", todos: [{ content: "w", status: "pending" }] } })
    expect(latestTodos(db, "c2")).toEqual([{ content: "w", status: "pending" }])
  })
})
