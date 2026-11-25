// stale-worker: a background worker that went quiet gets one nudge to its parent per 30 min, from the
// parent's own call and from the waker; an orphaned OpenCode child is aborted; the shells of a worker die with
// its parent. Time is the event's own `time`, so no test sleeps. Processes are real.
import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { fromClaude } from "../src/adapters/normalize.ts"
import { closeCore, decide } from "../src/core.ts"
import { openLedger } from "../src/ledger/db.ts"
import { wakerTick } from "../src/waker/waker.ts"
import type { WakeMessage } from "../src/waker/deliver.ts"
import type { HarnessEvent } from "../src/types.ts"

let dir: string
let db: Database
let sent: WakeMessage[]
const spawned: { kill: () => void }[] = []
const T0 = 1_700_000_000_000
const MIN = 60_000

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-stale-"))
  process.env.HARNESS_STATE_DIR = dir
  process.env.HARNESS_JUDGE = "fallback"
  delete process.env.HARNESS_DISABLE
  delete process.env.HARNESS_STALE_WORKER_MIN
  db = openLedger()
  sent = []
})

afterEach(() => {
  for (const p of spawned.splice(0)) p.kill()
  closeCore()
  db.close()
  for (const k of ["HARNESS_STATE_DIR", "HARNESS_JUDGE", "HARNESS_DISABLE", "HARNESS_STALE_WORKER_MIN"]) delete process.env[k]
  rmSync(dir, { recursive: true, force: true })
})

const fakeDeliver = async (m: WakeMessage) => {
  sent.push(m)
  return { ok: true, via: "fake" }
}

// agentId is how the Claude adapter marks an event that fires inside a subagent.
const ev = (over: Partial<HarnessEvent> & { agentId?: string }): HarnessEvent =>
  ({ v: 1, event: "tool.after", tool: "claude", session: "p1", parentSession: null, cwd: "/tmp", time: T0, ...over }) as HarnessEvent

const GOAL = "Renumber ADRs and write ADR-074..078"
const spawnInput = { prompt: `${GOAL}\nACCEPTANCE:\n- \`true\``, model: "m", agent: "general", run_in_background: true }
const openInput = { ...spawnInput, prompt: `${spawnInput.prompt}\n\nHARNESS-CONTRACT v1` } // OpenCode cannot have the contract appended
const hhmm = (t: number) => new Date(t).toTimeString().slice(0, 5)
const rows = (sql: string, ...p: (string | number)[]) => db.query(sql).all(...p) as Record<string, any>[]
const wakes = () => sent.filter((m) => m.kind === "worker.stale") // the stall nudge to a quiet child is another rule
const stale = () => rows("select * from journal where event = 'worker.stale' order by seq")

// Claude: the Agent tool returns at launch with the agent id, and the parent's session starts at `at`.
async function spawnClaude(at = T0, agentId = "a1b2c3d4e5f60718", parent = "p1") {
  await decide(ev({ event: "prompt", prompt: "go", session: parent, time: at }))
  await decide(ev({ event: "tool.before", toolName: "subagent", session: parent, input: spawnInput, time: at + 1 }))
  await decide(ev({ toolName: "subagent", session: parent, input: spawnInput, output: `Async agent launched.\nagentId: ${agentId}\nThe agent is working in the background.`, time: at + 2 }))
  return agentId
}
const agentCall = (agentId: string, time: number, over: Partial<HarnessEvent> = {}) => decide(ev({ toolName: "read", input: { path: "/tmp/x" }, agentId, time, ...over }))
const parentCall = (time: number) => decide(ev({ toolName: "read", input: { path: "/tmp/y" }, time }))

// OpenCode: the child has its own session; the spawn output names it.
async function spawnOpenCode(at = T0, child = "ses_child1", parent = "ps1") {
  const o = { tool: "opencode" as const, session: parent }
  await decide(ev({ ...o, event: "prompt", prompt: "go", time: at }))
  await decide(ev({ ...o, event: "tool.before", toolName: "subagent", input: openInput, time: at + 1 }))
  await decide(ev({ ...o, toolName: "subagent", input: openInput, output: `Started in the background.\nsessionID: ${child}`, time: at + 2 }))
  return { child, parent }
}
const childCall = (child: string, parent: string, time: number, over: Partial<HarnessEvent> = {}) =>
  decide(ev({ tool: "opencode", session: child, parentSession: parent, toolName: "read", input: { path: "/tmp/x" }, time, ...over }))

describe("the parent's own call", () => {
  test("a Claude agent quiet for 15 min is named once, with the verified TaskStop input, then not again for 30 min", async () => {
    const id = await spawnClaude()
    await agentCall(id, T0 + MIN)
    expect((await parentCall(T0 + 15 * MIN)).context).toBeUndefined() // 14 min quiet

    const d = await parentCall(T0 + 17 * MIN) // 16 min quiet
    expect(d.context).toBe(
      `Worker a1b2c3d4 (${GOAL}) has been idle since ${hhmm(T0 + MIN)}. Stop it with TaskStop with {"task_id": "${id}"}, or say why it stays.`,
    )
    expect(stale()).toHaveLength(1)
    expect(JSON.parse(stale()[0].data_json)).toMatchObject({ worker_session: id, idle_since: T0 + MIN, via: "inject" })

    expect((await parentCall(T0 + 40 * MIN)).context).toBeUndefined() // 23 min after the nudge
    expect((await parentCall(T0 + 48 * MIN)).context).toContain("Worker a1b2c3d4") // 31 min after
    expect(stale()).toHaveLength(2)
  })

  test("HARNESS_STALE_WORKER_MIN sets the limit", async () => {
    process.env.HARNESS_STALE_WORKER_MIN = "1"
    await spawnClaude()
    expect((await parentCall(T0 + 30_000)).context).toBeUndefined()
    expect((await parentCall(T0 + 2 * MIN + 10)).context).toContain("has been idle since")
  })

  test("an agent that keeps working, or that stopped, is not stale", async () => {
    const id = await spawnClaude()
    for (let m = 5; m <= 60; m += 5) await agentCall(id, T0 + m * MIN)
    expect((await parentCall(T0 + 70 * MIN)).context).toBeUndefined() // last call 10 min ago

    const stopped = await spawnClaude(T0 + 80 * MIN, "b2b2b2b2b2b2b2b2", "p2")
    await decide(ev({ event: "stop", session: "p2", reply: "done", agentId: stopped, time: T0 + 81 * MIN }))
    expect((await decide(ev({ session: "p2", toolName: "read", input: { path: "/tmp/z" }, time: T0 + 140 * MIN }))).context).toBeUndefined()

    // It was resumed after the stop and went quiet again.
    await agentCall(stopped, T0 + 100 * MIN, { session: "p2" })
    expect((await decide(ev({ session: "p2", toolName: "read", input: { path: "/tmp/z" }, time: T0 + 140 * MIN }))).context).toContain("Worker b2b2b2b2")
  })

  test("a call that never returned is what the worker waits on", async () => {
    const id = await spawnClaude()
    await decide(ev({ event: "tool.before", toolName: "shell", input: { command: "tail -f /dev/null", cwd: "/tmp" }, agentId: id, time: T0 + MIN }))
    const d = await parentCall(T0 + 20 * MIN)
    expect(d.context).toBe(
      `Worker a1b2c3d4 (${GOAL}) has been idle since ${hhmm(T0 + MIN)}, waiting on a shell call that has not returned (tail -f /dev/null). Stop it with TaskStop with {"task_id": "${id}"}, or say why it stays.`,
    )
  })

  test("the nudge goes to the parent, never into a subagent's own call; the rule off sends nothing", async () => {
    const id = await spawnClaude()
    expect((await agentCall(id, T0 + 30 * MIN, { agentId: "someone-else" })).context).toBeUndefined()
    expect((await parentCall(T0 + 31 * MIN)).context).toContain("Worker a1b2c3d4")

    process.env.HARNESS_DISABLE = "stale-worker"
    closeCore()
    expect((await parentCall(T0 + 120 * MIN)).context).toBeUndefined()
  })

  test("an OpenCode child names the interrupt endpoint, and its stop row ends the case", async () => {
    const { child, parent } = await spawnOpenCode()
    await childCall(child, parent, T0 + 2 * MIN)
    const d = await decide(ev({ tool: "opencode", session: parent, event: "prompt", prompt: "status?", time: T0 + 20 * MIN }))
    expect(d.context).toContain(`Worker child1 (${GOAL}) has been idle since ${hhmm(T0 + 2 * MIN)}.`)
    expect(d.context).toContain(`opencode api post "/api/session/ses_child1/interrupt?resume=false"`)

    const done = await spawnOpenCode(T0 + 100 * MIN, "ses_child2", "ps2")
    await childCall(done.child, done.parent, T0 + 101 * MIN, { event: "stop", toolName: undefined, input: undefined, reply: "ok" })
    expect((await decide(ev({ tool: "opencode", session: "ps2", event: "prompt", prompt: "status?", time: T0 + 200 * MIN }))).context).toBeUndefined()
  })

  test("what it waits on: a registered process that still runs, else the background shell it started", async () => {
    const id = await spawnClaude()
    const p = Bun.spawn(["sleep", "300"], { stdio: ["ignore", "ignore", "ignore"] })
    spawned.push({ kill: () => p.kill("SIGKILL") })
    await agentCall(id, Date.now(), { toolName: "shell", input: { command: "sleep 300 & echo PID: $!", cwd: "/tmp", run_in_background: true }, output: `PID: ${p.pid}` })
    const d = await parentCall(Date.now() + 20 * MIN)
    expect(d.context).toContain(`, waiting on 1 shell (sleep 300`)
    expect(d.context).toContain(`PID ${p.pid}`)

    const other = await spawnClaude(T0, "c3c3c3c3c3c3c3c3", "p3")
    await agentCall(other, T0 + 1, { session: "p3", toolName: "shell", input: { command: "sleep 600", cwd: "/tmp", run_in_background: true }, output: "Command running in background with ID: b1" })
    const d2 = await decide(ev({ session: "p3", toolName: "read", input: { path: "/tmp/z" }, time: T0 + 20 * MIN }))
    expect(d2.context).toContain(", waiting on a background shell (sleep 600).")
  })
})

describe("the waker tick", () => {
  test("an idle parent gets the same text once per 30 min, journaled as worker.stale; a busy parent gets none", async () => {
    const id = await spawnClaude()
    await agentCall(id, T0 + MIN)
    await decide(ev({ event: "stop", reply: "waiting on the agent", time: T0 + 2 * MIN }))

    await wakerTick(db, { deliver: fakeDeliver, now: () => T0 + 10 * MIN })
    expect(wakes()).toHaveLength(0)
    await wakerTick(db, { deliver: fakeDeliver, now: () => T0 + 17 * MIN })
    expect(wakes()).toHaveLength(1)
    expect(wakes()[0]).toMatchObject({ session: "p1", tool: "claude", kind: "worker.stale" })
    expect(wakes()[0].text).toContain(`has been idle since ${hhmm(T0 + MIN)}. Stop it with TaskStop with {"task_id": "${id}"}`)
    expect(JSON.parse(stale()[0].data_json).via).toBe("waker")

    await wakerTick(db, { deliver: fakeDeliver, now: () => T0 + 19 * MIN })
    expect(wakes()).toHaveLength(1)
    await wakerTick(db, { deliver: fakeDeliver, now: () => T0 + 48 * MIN })
    expect(wakes()).toHaveLength(2)

    // The parent works at the moment of a tick: its own next call delivers, not the waker.
    await parentCall(T0 + 60 * MIN - 30_000)
    await wakerTick(db, { deliver: fakeDeliver, now: () => T0 + 60 * MIN })
    expect(wakes()).toHaveLength(2)
  })

  test("an OpenCode child is aborted after 60 min stale when the parent ended, once; Claude never", async () => {
    const { child, parent } = await spawnOpenCode()
    await childCall(child, parent, T0 + MIN)
    const calls: string[][] = []
    const run = async (cmd: string[]) => (calls.push(cmd), { code: 0, stdout: '{"interrupted":true}', stderr: "" })
    await decide(ev({ tool: "opencode", session: parent, event: "session.end", time: T0 + 5 * MIN }))

    await wakerTick(db, { deliver: fakeDeliver, run, now: () => T0 + 60 * MIN }) // 59 min stale
    expect(calls).toHaveLength(0)
    await wakerTick(db, { deliver: fakeDeliver, run, now: () => T0 + 62 * MIN })
    expect(calls).toEqual([["opencode", "api", "post", "/api/session/ses_child1/interrupt?resume=false"]])
    const aborted = rows("select outcome, data_json from journal where event = 'worker.aborted'")
    expect(aborted).toHaveLength(1)
    expect(aborted[0].outcome).toBe("ok")
    expect(rows("select ended_at from sessions where id = ?", child)[0].ended_at).toBe(T0 + 62 * MIN)
    await wakerTick(db, { deliver: fakeDeliver, run, now: () => T0 + 200 * MIN })
    expect(calls).toHaveLength(1)
    expect(wakes()).toHaveLength(0) // an ended parent gets no nudge

    const id = await spawnClaude(T0, "d4d4d4d4d4d4d4d4", "p4")
    await decide(ev({ session: "p4", event: "session.end", time: T0 + 5 * MIN }))
    await wakerTick(db, { deliver: fakeDeliver, run, now: () => T0 + 300 * MIN })
    expect(calls).toHaveLength(1)
    expect(id).toBeTruthy()
  })

  test("an OpenCode child whose parent is still alive is nudged, not aborted", async () => {
    const { child, parent } = await spawnOpenCode()
    await childCall(child, parent, T0 + MIN)
    await decide(ev({ tool: "opencode", session: parent, event: "stop", reply: "waiting", time: T0 + 2 * MIN }))
    const calls: string[][] = []
    const run = async (cmd: string[]) => (calls.push(cmd), { code: 0, stdout: "", stderr: "" })
    await wakerTick(db, { deliver: fakeDeliver, run, now: () => T0 + 90 * MIN })
    expect(calls).toHaveLength(0)
    expect(wakes()).toHaveLength(1)
    expect(wakes()[0]).toMatchObject({ session: parent, tool: "opencode" })
  })
})

describe("the parent ends", () => {
  test("the shells registered under a worker session are killed with it", async () => {
    const { child, parent } = await spawnOpenCode()
    const p = Bun.spawn(["sleep", "300"], { stdio: ["ignore", "ignore", "ignore"] })
    spawned.push({ kill: () => p.kill("SIGKILL") })
    await decide(ev({ tool: "opencode", session: child, parentSession: parent, toolName: "shell", input: { command: "sleep 300 & echo PID: $!", cwd: "/tmp" }, output: `PID: ${p.pid}`, time: Date.now() }))
    expect(rows("select pid from processes where session_id = ? and ended_at is null", child)).toEqual([{ pid: p.pid }])

    const d = await decide(ev({ tool: "opencode", session: parent, event: "session.end", time: Date.now() }))
    expect(d.outcome).toBe("allow")
    expect(rows("select event from journal where event = 'process.killed' and session_id = ?", child)).toHaveLength(1)
    for (let i = 0; i < 40 && Bun.spawnSync(["ps", "-o", "stat=", "-p", String(p.pid)], { stdout: "pipe" }).stdout.toString().trim().replace(/^Z.*/, "") !== ""; i++) await Bun.sleep(50)
    expect(Bun.spawnSync(["ps", "-o", "stat=", "-p", String(p.pid)], { stdout: "pipe" }).stdout.toString().trim().replace(/^Z.*/, "")).toBe("")
  })
})

describe("the Claude adapter", () => {
  test("a hook inside a subagent carries its agent id; one in the main agent does not", () => {
    const sub = fromClaude("tool.after", { session_id: "s", tool_name: "Read", tool_input: {}, agent_id: "a1", agent_type: "general-purpose" }) as HarnessEvent & { agentId?: string }
    expect(sub.agentId).toBe("a1")
    const stop = fromClaude("stop", { session_id: "s", hook_event_name: "SubagentStop", agent_id: "a1", last_assistant_message: "x" }) as HarnessEvent & { agentId?: string }
    expect(stop.agentId).toBe("a1")
    expect((fromClaude("stop", { session_id: "s" }) as HarnessEvent & { agentId?: string }).agentId).toBeUndefined()
  })

  test("the ids Claude Code returns in an object reach the output text", () => {
    // Shapes copied from a real run (Claude Code 2.1.332): Agent run_in_background, Bash run_in_background.
    const launched = fromClaude("tool.after", { session_id: "s", tool_name: "Agent", tool_input: { run_in_background: true }, tool_response: { isAsync: true, status: "async_launched", agentId: "a67504cb3acd24f97" } })
    expect(launched.output).toContain("\nagentId: a67504cb3acd24f97")
    const bash = fromClaude("tool.after", { session_id: "s", tool_name: "Bash", tool_input: { command: "sleep 600", run_in_background: true }, tool_response: { stdout: "", stderr: "", backgroundTaskId: "bqiexpd22" } })
    expect(bash.output).toContain("backgroundTaskId: bqiexpd22")
  })
})
