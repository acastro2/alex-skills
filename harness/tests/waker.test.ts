import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { existsSync, mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { openLedger } from "../src/ledger/db.ts"
import { append, upsertSession } from "../src/ledger/journal.ts"
import { deliver, opencodeRequest, takeInbox, type WakeMessage } from "../src/waker/deliver.ts"
import { addWatch, wakerTick } from "../src/waker/waker.ts"

let dir: string
let db: Database
let sent: WakeMessage[]
const fakeDeliver = async (m: WakeMessage) => {
  sent.push(m)
  return { ok: true, via: "fake" }
}

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-waker-"))
  process.env.HARNESS_STATE_DIR = dir
  db = openLedger()
  sent = []
  upsertSession(db, { id: "root", tool: "opencode" })
})

afterEach(() => {
  db.close()
  delete process.env.HARNESS_STATE_DIR
  rmSync(dir, { recursive: true, force: true })
})

// A fake gh: `view` answers come from the queue's current value.
function fakeGh(view: () => object, logs = "") {
  const calls: string[][] = []
  const gh = async (cmd: string[]) => {
    calls.push(cmd)
    if (cmd[1] === "pr") return { code: 0, stdout: JSON.stringify(view()), stderr: "" }
    return { code: 0, stdout: logs, stderr: "" }
  }
  return { gh, calls }
}

const open = { state: "OPEN", reviewDecision: "", mergeable: "MERGEABLE", statusCheckRollup: [], headRefOid: "a" }

describe("PR watch (Phase 2 table)", () => {
  test("OPEN then MERGED delivers once with the next step, and the watch is done", async () => {
    db.query("insert into workstreams(id, owner_session_id) values('w1', 'root')").run()
    db.query("insert into workstream_steps(id, workstream_id, position, text, state) values('st1', 'w1', 1, 'ship phase 3', 'pending')").run()
    addWatch(db, { session: "root", kind: "pr", target: "o/r#7" })
    let cur: object = open
    const { gh } = fakeGh(() => cur)
    await wakerTick(db, { gh, deliver: fakeDeliver })
    expect(sent).toHaveLength(0)
    cur = { ...open, state: "MERGED" }
    await wakerTick(db, { gh, deliver: fakeDeliver })
    await wakerTick(db, { gh, deliver: fakeDeliver })
    expect(sent).toHaveLength(1)
    expect(sent[0]!.text).toStartWith("PR #7 merged. Run the next planned step.")
    expect(sent[0]!.text).toContain("ship phase 3")
    expect(sent[0]!.tool).toBe("opencode")
    expect(JSON.parse((db.query("select last_state from watches").get() as { last_state: string }).last_state).done).toBe(true)
  })

  test("approved delivers the token message once", async () => {
    addWatch(db, { session: "root", kind: "pr", target: "o/r#7" })
    const { gh } = fakeGh(() => ({ ...open, reviewDecision: "APPROVED" }))
    await wakerTick(db, { gh, deliver: fakeDeliver })
    await wakerTick(db, { gh, deliver: fakeDeliver })
    expect(sent.map((m) => m.text)).toEqual(["PR #7 approved. Merge needs Alex's token."])
  })

  test("a failed check delivers the job name and the last 80 log lines", async () => {
    addWatch(db, { session: "root", kind: "pr", target: "o/r#7" })
    const log = Array.from({ length: 120 }, (_, i) => `line ${i + 1}`).join("\n")
    const rollup = [{ __typename: "CheckRun", name: "unit", conclusion: "FAILURE", detailsUrl: "https://github.com/o/r/actions/runs/99/job/1" }]
    const { gh, calls } = fakeGh(() => ({ ...open, statusCheckRollup: rollup }), log)
    await wakerTick(db, { gh, deliver: fakeDeliver })
    expect(sent).toHaveLength(1)
    expect(sent[0]!.text).toContain("unit")
    expect(sent[0]!.text).toContain("line 120")
    expect(sent[0]!.text).toContain("line 41")
    expect(sent[0]!.text).not.toContain("line 40\n")
    expect(calls.some((c) => c.includes("--log-failed") && c.includes("99"))).toBe(true)
  })

  test("a conflict delivers the rebase message", async () => {
    addWatch(db, { session: "root", kind: "pr", target: "o/r#7" })
    const { gh } = fakeGh(() => ({ ...open, mergeable: "CONFLICTING" }))
    await wakerTick(db, { gh, deliver: fakeDeliver })
    expect(sent[0]!.text).toBe("PR #7 has a conflict with its base. Rebase and re-run the acceptance commands.")
  })

  test("no change means no delivery; watches past 24 h are removed", async () => {
    addWatch(db, { session: "root", kind: "pr", target: "o/r#7" })
    const { gh } = fakeGh(() => open)
    await wakerTick(db, { gh, deliver: fakeDeliver })
    await wakerTick(db, { gh, deliver: fakeDeliver })
    expect(sent).toHaveLength(0)
    await wakerTick(db, { gh, deliver: fakeDeliver, now: () => Date.now() + 25 * 3600_000 })
    expect(db.query("select count(*) as c from watches").get()).toEqual({ c: 0 })
  })
})

describe("stall nudge (D77, D78)", () => {
  const MIN = 60_000
  const toolRow = (session: string, agoMin: number, data?: unknown) =>
    append(db, { session_id: session, turn: 1, event: "tool.after", data, time: Date.now() - agoMin * MIN })

  test("a worker silent for 11 minutes gets one nudge, not two", async () => {
    upsertSession(db, { id: "w", tool: "claude", parent_session_id: "root" })
    toolRow("w", 11)
    await wakerTick(db, { deliver: fakeDeliver })
    await wakerTick(db, { deliver: fakeDeliver })
    expect(sent.map((m) => m.session)).toEqual(["w"])
    expect(sent[0]!.kind).toBe("stall")
  })

  test("a worker silent for 5 minutes gets nothing", async () => {
    upsertSession(db, { id: "w", tool: "claude", parent_session_id: "root" })
    toolRow("w", 5)
    await wakerTick(db, { deliver: fakeDeliver })
    expect(sent).toHaveLength(0)
  })

  test("a root session whose last reply asked a question gets none, one with a pending todo and no question gets one", async () => {
    upsertSession(db, { id: "asker", tool: "claude" })
    upsertSession(db, { id: "doer", tool: "claude" })
    for (const s of ["asker", "doer"]) toolRow(s, 12, { todos: [{ content: "x", status: "pending" }] })
    append(db, { session_id: "asker", turn: 1, event: "stop", data: { reply: "Which option do you want?" }, time: Date.now() - 11 * MIN })
    append(db, { session_id: "doer", turn: 1, event: "stop", data: { reply: "Working on it." }, time: Date.now() - 11.5 * MIN })
    // the stop rows are newer than the tool rows for "asker" only if they come last: re-add a tool row after them
    toolRow("asker", 11)
    toolRow("doer", 11)
    await wakerTick(db, { deliver: fakeDeliver })
    expect(sent.map((m) => m.session)).toEqual(["doer"])
  })

  test("a root session with all todos done gets none", async () => {
    upsertSession(db, { id: "fin", tool: "claude" })
    toolRow("fin", 12, { todos: [{ content: "x", status: "completed" }] })
    toolRow("fin", 11)
    await wakerTick(db, { deliver: fakeDeliver })
    expect(sent).toHaveLength(0)
  })

  test("the 6th nudge in a turn journals stuck instead of delivering", async () => {
    upsertSession(db, { id: "w", tool: "claude", parent_session_id: "root" })
    for (let i = 0; i < 5; i++) append(db, { session_id: "w", turn: 1, event: "nudge", data: { kind: "stall" }, time: Date.now() - (30 + i) * MIN })
    toolRow("w", 11)
    await wakerTick(db, { deliver: fakeDeliver })
    expect(sent).toHaveLength(0)
    expect(db.query("select count(*) as c from journal where event = 'stuck' and session_id = 'w'").get()).toEqual({ c: 1 })
  })
})

describe("deliver", () => {
  test("OpenCode: posts to the synthetic-message endpoint and journals wake.delivered", async () => {
    let seen: string[] = []
    const r = await deliver(db, { session: "root", tool: "opencode", text: "hi", kind: "t" }, async (cmd) => {
      seen = cmd
      return { code: 0, stdout: "{}", stderr: "" }
    })
    expect(r).toEqual({ ok: true, via: "opencode:synthetic" })
    expect(seen.slice(0, 4)).toEqual(["opencode", "api", "post", "/api/session/root/synthetic"])
    expect(JSON.parse(seen[5]!).text).toBe("hi")
    const row = db.query("select event, data_json from journal where session_id = 'root'").get() as { event: string; data_json: string }
    expect(row.event).toBe("wake.delivered")
    expect(JSON.parse(row.data_json)).toEqual({ kind: "t", text: "hi", via: "opencode:synthetic" })
  })

  test("OpenCode failure journals wake.failed", async () => {
    const r = await deliver(db, { session: "root", tool: "opencode", text: "hi" }, async () => ({ code: 1, stdout: "", stderr: "boom" }))
    expect(r.ok).toBe(false)
    expect((db.query("select event from journal where session_id = 'root'").get() as { event: string }).event).toBe("wake.failed")
  })

  test("Claude: text lands in the inbox and takeInbox returns it once", async () => {
    upsertSession(db, { id: "c1", tool: "claude" })
    await deliver(db, { session: "c1", tool: "claude", text: "one" })
    await deliver(db, { session: "c1", tool: "claude", text: "two" })
    expect(takeInbox("c1")).toBe("one\ntwo")
    expect(takeInbox("c1")).toBeNull()
    expect(existsSync(join(dir, "inbox", "c1.txt"))).toBe(false)
  })

  test("request shape", () => {
    expect(opencodeRequest("ses_1", "x")[3]).toBe("/api/session/ses_1/synthetic")
  })
})
