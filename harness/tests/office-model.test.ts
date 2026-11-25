import { describe, expect, test } from "bun:test"
import { ENDED_DIM_MS, type LedgerSnapshot, officeState, officeStateFromServer, type ServerSnapshot, tickerSpeed } from "../src/ui/office-model.ts"

// Criteria: docs/specs/harness-office.md, O5 (8 desks and a rack), O10 (assignment), O14 (log scale), "one lit accent".

const NOW = 10_000_000
type S = LedgerSnapshot["sessions"][number]

const session = (id: string, extra: Partial<S> = {}): S => ({
  id,
  tool: "opencode",
  parent_session_id: null,
  repo: "skills",
  goal: `goal ${id}`,
  running: false,
  stuck: false,
  waitingQuestion: false,
  started_at: NOW - 3_600_000,
  ended_at: null,
  last_activity: NOW - 60_000,
  ...extra,
})

const snapshot = (sessions: S[], extra: Partial<LedgerSnapshot> = {}): LedgerSnapshot => ({
  now: NOW,
  host: "vm",
  harnessOff: false,
  sessions,
  worktrees: [],
  wakes: [],
  journalRate: 0,
  denies: 0,
  grants: [],
  steeringShare: null,
  jobs: [],
  rules: [],
  bell: false,
  ...extra,
})

const deskOf = (state: ReturnType<typeof officeState>, id: string) => state.desks.findIndex((d) => d?.session === id)

describe("desks and rack (O5)", () => {
  test("more than 8 sessions give 8 desks and a rack with the rest", () => {
    const sessions = Array.from({ length: 11 }, (_, i) => session(`s${i}`, { last_activity: NOW - i * 1000 }))
    const state = officeState(snapshot(sessions))
    expect(state.desks.filter(Boolean)).toHaveLength(8)
    expect(state.rack.total).toBe(3)
    expect(state.rack.slots).toHaveLength(3)
    const seated = new Set(state.desks.filter(Boolean).map((d) => d!.session))
    for (const r of state.rack.slots) expect(seated.has(r.session)).toBe(false)
  })

  test("a worker's desk is placed beside its parent", () => {
    const sessions = [session("a"), session("b"), session("c"), session("w1", { parent_session_id: "c", running: true })]
    const state = officeState(snapshot(sessions))
    const parent = deskOf(state, "c")
    expect(parent).toBeGreaterThanOrEqual(0)
    expect(state.sides[parent]?.session).toBe("w1")
    expect(state.sides[parent]?.side).toBe(true)
    expect(state.desks.some((d) => d?.session === "w1")).toBe(false)
  })
})

describe("desk assignment (O10)", () => {
  const eight = () => Array.from({ length: 8 }, (_, i) => session(`s${i}`, { running: true, last_activity: NOW - (i + 1) * 10_000 }))

  test("a racked session that becomes a waiting question takes the longest-idle desk", () => {
    const first = officeState(snapshot([...eight(), session("late", { last_activity: NOW - 5_000 })]))
    expect(first.rack.slots.map((r) => r.session)).toEqual(["late"])
    // s7 has the oldest last_activity, so s7 is the longest idle.
    const ask = [...eight(), session("late", { waitingQuestion: true, last_activity: NOW - 5_000 })]
    const second = officeState(snapshot(ask), first)
    expect(deskOf(second, "late")).toBe(deskOf(first, "s7"))
    expect(second.rack.slots.map((r) => r.session)).toEqual(["s7"])
    // Nothing else moved.
    for (let i = 0; i < 7; i++) expect(deskOf(second, `s${i}`)).toBe(deskOf(first, `s${i}`))
  })

  test("slots stay the same across two snapshots when nothing ends", () => {
    const sessions = [session("a", { running: true }), session("b"), session("c", { waitingQuestion: true }), session("d", { stuck: true })]
    const first = officeState(snapshot(sessions))
    const changed = [session("a"), session("b", { running: true }), session("c"), session("d"), session("e", { waitingQuestion: true })]
    const second = officeState(snapshot(changed), first)
    for (const id of ["a", "b", "c", "d"]) expect(deskOf(second, id)).toBe(deskOf(first, id))
  })

  test("an ended desk dims for 10 minutes, then frees", () => {
    const live = officeState(snapshot([session("a"), session("b")]))
    const ended = officeState(snapshot([session("a", { ended_at: NOW - 60_000 }), session("b")]), live)
    expect(ended.desks[deskOf(ended, "a")]?.dim).toBe(true)
    expect(deskOf(ended, "a")).toBe(deskOf(live, "a"))
    const gone = officeState(snapshot([session("a", { ended_at: NOW - ENDED_DIM_MS - 1 }), session("b")], { now: NOW }), ended)
    expect(deskOf(gone, "a")).toBe(-1)
    expect(gone.rack.total).toBe(0)
  })
})

describe("ticker speed (O14)", () => {
  test("grows with the journal rate, on a log scale", () => {
    const rates = [0, 1, 10, 100, 1000]
    const speeds = rates.map(tickerSpeed)
    for (let i = 1; i < speeds.length; i++) expect(speeds[i]).toBeGreaterThan(speeds[i - 1])
    expect(speeds[0]).toBe(0)
    // One notch per row would double the speed from 100 to 200 rows; a log scale adds about 15%.
    expect(tickerSpeed(200) / tickerSpeed(100)).toBeLessThan(1.2)
    // Each tenfold step adds about the same (log scale).
    expect(Math.abs(speeds[4] - speeds[3] - (speeds[3] - speeds[2]))).toBeLessThan(0.05)
    expect(officeState(snapshot([], { journalRate: 100 })).ticker.speed).toBe(tickerSpeed(100))
  })
})

describe("the one lit accent", () => {
  const worktree = (sync: "conflict" | "current") => ({ id: "w1", repo: "skills", branch: "feat", state: "active" as const, sync_state: sync, session_id: null })

  test("a waiting question beats stuck, and stuck beats a conflict", () => {
    const sessions = [session("q", { waitingQuestion: true }), session("k", { stuck: true }), session("r", { running: true })]
    const all = officeState(snapshot(sessions, { worktrees: [worktree("conflict")] }))
    expect(all.accent).toEqual({ kind: "question", id: "q" })
    expect(all.desks.filter((d) => d?.lit).map((d) => d!.session)).toEqual(["q"])

    const noQuestion = officeState(snapshot([session("k", { stuck: true }), session("r")], { worktrees: [worktree("conflict")] }))
    expect(noQuestion.accent).toEqual({ kind: "stuck", id: "k" })

    const conflictOnly = officeState(snapshot([session("r")], { worktrees: [worktree("conflict")] }))
    expect(conflictOnly.accent).toEqual({ kind: "conflict", id: "w1" })
    expect(conflictOnly.drawers.find((d) => d?.id === "w1")?.lit).toBe(true)

    expect(officeState(snapshot([session("r")], { worktrees: [worktree("current")] })).accent).toBeNull()
  })
})

describe("the page snapshot (lane D shape)", () => {
  const server = (): ServerSnapshot => ({
    host: "lima-agent",
    ledger: {
      now: NOW,
      harnessOn: true,
      sessions: [
        { id: "a", tool: "claude", parent_session_id: null, repo: "r", goal: "g", running: false, stuck: false, waiting: true, started_at: NOW - 1000, ended_at: null, last_event_at: null },
      ],
      questions: [{}],
      worktrees: [],
      rules: [{ id: "r1", mode: "enforce" }],
      wakes: [{ time: NOW - 500, session_id: "a", reason: "pr" }, { time: NOW - 400, session_id: null, reason: null }],
      grants: [{ id: "g1", used_at: null, expires_at: NOW - 1 }, { id: "g2", used_at: null, expires_at: NOW + 1000 }],
      jobs: [],
      recent: [],
      journalPerMin: 12,
      steeringShare7d: 0.3,
    },
  })

  test("the host name, the question and the pending grants come through", () => {
    const state = officeStateFromServer(server())
    expect(state.host).toBe("lima-agent")
    expect(state.summary).toContain("lima-agent")
    expect(state.accent).toEqual({ kind: "question", id: "a" })
    expect(state.stamp.pending).toBe(1)
    expect(state.capsules).toHaveLength(1)
    expect(state.bell).toBe(true)
  })
})
