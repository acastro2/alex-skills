// Pure truth module for the office floor (spec: docs/specs/harness-office.md, "The office").
// Ledger rows in, figure state out. No I/O, no clock: `now` comes from the snapshot.
// The figure (ui/office) draws this state; every number on its card is made here.

export interface LedgerSnapshot {
  now: number
  host: string
  harnessOff: boolean
  sessions: {
    id: string
    tool: "claude" | "opencode"
    parent_session_id: string | null
    repo: string | null
    goal: string | null
    running: boolean
    stuck: boolean
    waitingQuestion: boolean
    started_at: number
    ended_at: number | null
    last_activity: number
  }[]
  worktrees: {
    id: string
    repo: string
    branch: string
    state: "active" | "landed" | "held" | "removed"
    sync_state: "current" | "behind" | "conflict" | null
    session_id: string | null
  }[]
  wakes: { session_id: string; kind: string; time: number }[]
  journalRate: number
  denies: number
  grants: { id: string; time: number; used_at: number | null }[]
  steeringShare: number | null
  jobs: { name: string; next_at: number | null }[]
  rules: { id: string; mode: "enforce" | "advise" | "inject" | "off" }[]
  bell: boolean
}

export const MAX_DESKS = 8
export const MAX_RACK = 12
export const MAX_DRAWERS = 8
export const MAX_BREAKERS = 12
export const ENDED_DIM_MS = 10 * 60_000 // O10: an ended desk dims for 10 minutes, then frees
export const WAKE_FLIGHT_MS = 2_600 // a capsule is in the tube this long after a wake
export const BASELINE_SHARE = 0.28 // the measured week (PRODUCT.md)
export const GAUGE_SWEEP = 135 // needle runs -135 to +135 degrees

export type AccentKind = "question" | "stuck" | "conflict"
export interface Accent {
  kind: AccentKind
  id: string // session id for question and stuck, worktree id for conflict
}

export interface DeskState {
  slot: number // 0..7. A side desk shares the slot of its parent.
  side: boolean
  session: string
  slug: string
  tool: "claude" | "opencode"
  goal: string | null
  repo: string | null
  parent: string | null
  running: boolean
  stuck: boolean
  question: boolean
  ended: boolean
  lamp: boolean // desk lamp lit: a turn runs
  flag: boolean // red flag up: stuck
  tray: boolean // card in the in-tray: a question waits
  dim: boolean // ended, not yet freed
  lit: boolean // the one accent
  label: string
}

export interface RackSlot {
  session: string
  lit: boolean
  label: string
}

export interface DrawerState {
  slot: number // 0..7, sticky
  id: string
  repo: string
  branch: string
  state: "active" | "landed" | "held" | "removed"
  open: boolean
  removed: boolean // kept one snapshot after removal so the drawer slides shut
  conflict: boolean
  behind: boolean
  lit: boolean
  label: string
}

export interface CapsuleState {
  key: string
  session: string
  slot: number
  side: boolean
  kind: string
  age: number // ms since the wake, at snapshot time
}

export interface BreakerState {
  id: string
  mode: "enforce" | "advise" | "inject" | "off"
}

export interface OfficeState {
  now: number
  host: string
  harnessOff: boolean
  desks: (DeskState | null)[] // length 8
  sides: (DeskState | null)[] // length 8, same slots
  rack: { slots: RackSlot[]; total: number; overflow: number }
  drawers: (DrawerState | null)[] // length 8
  drawerOverflow: number
  capsules: CapsuleState[]
  ticker: { rate: number; speed: number; denyMarks: number; label: string }
  stamp: { pressed: boolean; pending: number; issued: number; label: string }
  gauge: { share: number | null; angle: number; baseline: number; label: string }
  clock: { now: number; jobAngle: number | null; nextJob: string | null; label: string }
  fuses: { main: boolean; breakers: BreakerState[]; overflow: number; label: string }
  bell: boolean
  accent: Accent | null
  empty: boolean
  counts: { sessions: number; workers: number; questions: number; stuck: number; conflicts: number; racked: number }
  readout: string
  summary: string
}

type Session = LedgerSnapshot["sessions"][number]

// Ids from the ledger share their first characters (a time prefix), so the tail tells them apart.
const slug = (id: string) => id.replace(/[^a-z0-9]/gi, "").slice(-5).toLowerCase() || "-----"

/** Ticker speed, 0..1, on a log scale of rows per minute (O14). 1000 rows a minute is full speed. */
export function tickerSpeed(rate: number): number {
  return Math.min(1, Math.log10(1 + Math.max(0, rate)) / 3)
}

/** Needle angle in degrees for a steering share 0..1. */
export function needleAngle(share: number | null): number {
  if (share === null) return -GAUGE_SWEEP
  return -GAUGE_SWEEP + 2 * GAUGE_SWEEP * Math.min(1, Math.max(0, share))
}

const needsAlex = (s: Session) => s.ended_at === null && (s.waitingQuestion || s.stuck)

// O10 order: needs Alex first (a waiting question, then stuck), then running, then idle, then ended.
function rank(s: Session): number {
  if (s.ended_at !== null) return 0
  if (s.waitingQuestion) return 4
  if (s.stuck) return 3
  if (s.running) return 2
  return 1
}

const byPriority = (a: Session, b: Session) => rank(b) - rank(a) || a.last_activity - b.last_activity || a.started_at - b.started_at || a.id.localeCompare(b.id)

function deskLabel(s: Session, slot: number, side: boolean, parent: string | null): string {
  const where = side ? `Side desk ${slot + 1}, worker of ${parent ? slug(parent) : "no session"}` : `Desk ${slot + 1}`
  const facts = [s.tool, s.ended_at !== null ? "ended" : s.running ? "turn running" : "idle"]
  if (s.waitingQuestion) facts.push("waiting for your answer")
  if (s.stuck) facts.push("stuck")
  return `${where}: session ${slug(s.id)}, ${facts.join(", ")}${s.repo ? `, repo ${s.repo}` : ""}${s.goal ? `, goal: ${s.goal}` : ""}`
}

function seat(s: Session, slot: number, side: boolean, accent: Accent | null): DeskState {
  const ended = s.ended_at !== null
  return {
    slot,
    side,
    session: s.id,
    slug: slug(s.id),
    tool: s.tool,
    goal: s.goal,
    repo: s.repo,
    parent: s.parent_session_id,
    running: s.running,
    stuck: s.stuck,
    question: s.waitingQuestion,
    ended,
    lamp: s.running && !ended,
    flag: s.stuck && !ended,
    tray: s.waitingQuestion && !ended,
    dim: ended,
    lit: accent !== null && accent.kind !== "conflict" && accent.id === s.id,
    label: deskLabel(s, slot, side, s.parent_session_id),
  }
}

interface Seats {
  main: (string | null)[]
  side: (string | null)[]
}

function assign(snap: LedgerSnapshot, prev?: OfficeState): Seats & { racked: string[] } {
  const eligible = snap.sessions.filter((s) => s.ended_at === null || snap.now - s.ended_at < ENDED_DIM_MS)
  const byId = new Map(eligible.map((s) => [s.id, s]))
  const main: (string | null)[] = Array(MAX_DESKS).fill(null)
  const side: (string | null)[] = Array(MAX_DESKS).fill(null)

  // A desk stays with its session until it ends and frees (sticky slots).
  if (prev) {
    prev.desks.forEach((d, slot) => {
      if (d && byId.has(d.session)) main[slot] = d.session
    })
    prev.sides.forEach((d, slot) => {
      const worker = d ? byId.get(d.session) : undefined
      if (worker && main[slot] !== null && main[slot] === worker.parent_session_id) side[slot] = worker.id
    })
  }

  const seated = () => new Set([...main, ...side].filter((id): id is string => id !== null))
  const racked = new Set<string>()
  const isWorkerOfLive = (s: Session) => s.parent_session_id !== null && byId.has(s.parent_session_id)

  // The one reshuffle: a racked session that needs Alex takes the longest-idle desk that does not.
  const evict = (): number => {
    let best = -1
    let oldest = Infinity
    main.forEach((id, slot) => {
      const holder = id ? byId.get(id) : undefined
      if (!holder || needsAlex(holder)) return
      if (holder.last_activity < oldest) {
        oldest = holder.last_activity
        best = slot
      }
    })
    return best
  }

  const place = (s: Session): void => {
    const parentSlot = s.parent_session_id ? main.indexOf(s.parent_session_id) : -1
    if (parentSlot >= 0 && side[parentSlot] === null) {
      side[parentSlot] = s.id
      return
    }
    const free = main.indexOf(null)
    if (free >= 0) {
      main[free] = s.id
      return
    }
    if (needsAlex(s)) {
      const slot = evict()
      if (slot >= 0) {
        const out = main[slot]!
        main[slot] = s.id
        racked.add(out)
        const orphan = side[slot]
        if (orphan) {
          side[slot] = null
          racked.add(orphan)
        }
        return
      }
    }
    racked.add(s.id)
  }

  // Primary sessions first (so a worker finds its parent), then workers, then workers that lost their parent.
  const queue = [...eligible].filter((s) => !seated().has(s.id)).sort(byPriority)
  for (const s of queue.filter((s) => !isWorkerOfLive(s))) place(s)
  for (const s of queue.filter(isWorkerOfLive)) place(s)
  // A worker whose parent was racked or evicted above may still be unseated: give it a second look.
  for (const id of [...racked]) {
    const s = byId.get(id)
    if (s && !seated().has(id) && s.parent_session_id && main.includes(s.parent_session_id) && side[main.indexOf(s.parent_session_id)] === null) {
      racked.delete(id)
      place(s)
    }
  }
  for (const s of eligible) if (!seated().has(s.id)) racked.add(s.id)
  for (const id of seated()) racked.delete(id)

  const rackedList = [...racked].map((id) => byId.get(id)!).sort(byPriority).map((s) => s.id)
  return { main, side, racked: rackedList }
}

function pickAccent(snap: LedgerSnapshot): Accent | null {
  const live = snap.sessions.filter((s) => s.ended_at === null)
  const oldest = (list: Session[]) => [...list].sort((a, b) => a.last_activity - b.last_activity || a.id.localeCompare(b.id))[0]
  const question = oldest(live.filter((s) => s.waitingQuestion))
  if (question) return { kind: "question", id: question.id }
  const stuck = oldest(live.filter((s) => s.stuck))
  if (stuck) return { kind: "stuck", id: stuck.id }
  const conflict = snap.worktrees.find((w) => w.state !== "removed" && w.sync_state === "conflict")
  if (conflict) return { kind: "conflict", id: conflict.id }
  return null
}

function drawers(snap: LedgerSnapshot, accent: Accent | null, prev?: OfficeState): { list: (DrawerState | null)[]; overflow: number } {
  const slots: (string | null)[] = Array(MAX_DRAWERS).fill(null)
  const byId = new Map(snap.worktrees.map((w) => [w.id, w]))
  prev?.drawers.forEach((d, slot) => {
    const w = d ? byId.get(d.id) : undefined
    // A removed worktree keeps its slot for one snapshot, so the drawer slides shut. After that it frees.
    if (d && w && (w.state !== "removed" || !d.removed)) slots[slot] = d.id
  })
  const rank = (w: LedgerSnapshot["worktrees"][number]) => (w.sync_state === "conflict" ? 0 : w.state === "active" ? 1 : 2)
  const waiting = snap.worktrees.filter((w) => w.state !== "removed" && !slots.includes(w.id)).sort((a, b) => rank(a) - rank(b) || a.id.localeCompare(b.id))
  let overflow = 0
  for (const w of waiting) {
    const free = slots.indexOf(null)
    if (free < 0) overflow++
    else slots[free] = w.id
  }
  const list = slots.map((id, slot): DrawerState | null => {
    const w = id ? byId.get(id) : undefined
    if (!w) return null
    const removed = w.state === "removed"
    const conflict = !removed && w.sync_state === "conflict"
    return {
      slot,
      id: w.id,
      repo: w.repo,
      branch: w.branch,
      state: w.state,
      open: w.state === "active",
      removed,
      conflict,
      behind: !removed && w.sync_state === "behind",
      lit: accent?.kind === "conflict" && accent.id === w.id,
      label: `Drawer ${slot + 1}: worktree ${w.repo} ${w.branch}, ${w.state}${w.sync_state ? `, ${w.sync_state === "conflict" ? "conflict" : `sync ${w.sync_state}`}` : ""}${w.session_id ? `, owner session ${slug(w.session_id)}` : ", no owner"}`,
    }
  })
  return { list, overflow }
}

function hourAngle(ms: number): number {
  const d = new Date(ms)
  return (((d.getHours() % 12) + d.getMinutes() / 60) * 30) % 360
}

export function officeState(snap: LedgerSnapshot, prev?: OfficeState): OfficeState {
  const accent = pickAccent(snap)
  const seats = assign(snap, prev)
  const byId = new Map(snap.sessions.map((s) => [s.id, s]))
  const desks = seats.main.map((id, slot) => (id ? seat(byId.get(id)!, slot, false, accent) : null))
  const sides = seats.side.map((id, slot) => (id ? seat(byId.get(id)!, slot, true, accent) : null))

  const rackSessions = seats.racked.map((id) => byId.get(id)!)
  const rack = {
    slots: rackSessions.slice(0, MAX_RACK).map((s) => ({ session: s.id, lit: s.running && s.ended_at === null, label: `Rack slot: session ${slug(s.id)}, ${s.waitingQuestion ? "waiting for your answer, " : ""}${s.stuck ? "stuck, " : ""}${s.running ? "turn running" : s.ended_at !== null ? "ended" : "idle"}` })),
    total: rackSessions.length,
    overflow: Math.max(0, rackSessions.length - MAX_RACK),
  }

  const sessionSlot = new Map<string, { slot: number; side: boolean }>()
  desks.forEach((d) => d && sessionSlot.set(d.session, { slot: d.slot, side: false }))
  sides.forEach((d) => d && sessionSlot.set(d.session, { slot: d.slot, side: true }))
  const capsules: CapsuleState[] = snap.wakes
    .filter((w) => snap.now - w.time >= 0 && snap.now - w.time < WAKE_FLIGHT_MS && sessionSlot.has(w.session_id))
    .map((w) => ({ key: `${w.session_id}@${w.time}`, session: w.session_id, ...sessionSlot.get(w.session_id)!, kind: w.kind, age: snap.now - w.time }))
    .sort((a, b) => a.age - b.age)

  const dr = drawers(snap, accent, prev)

  const speed = tickerSpeed(snap.journalRate)
  const pending = snap.grants.filter((g) => g.used_at === null).length
  const angle = needleAngle(snap.steeringShare)
  const nextJobs = snap.jobs.filter((j): j is { name: string; next_at: number } => j.next_at !== null).sort((a, b) => a.next_at - b.next_at)
  const next = nextJobs[0]
  const breakers = snap.rules.slice(0, MAX_BREAKERS).map((r) => ({ id: r.id, mode: r.mode }))
  const questions = snap.sessions.filter((s) => s.ended_at === null && s.waitingQuestion).length
  const stuck = snap.sessions.filter((s) => s.ended_at === null && s.stuck).length
  const conflicts = snap.worktrees.filter((w) => w.state !== "removed" && w.sync_state === "conflict").length
  const live = snap.sessions.filter((s) => s.ended_at === null)
  const counts = { sessions: live.length, workers: live.filter((s) => s.parent_session_id !== null).length, questions, stuck, conflicts, racked: rackSessions.length }

  const readout = snap.harnessOff
    ? `harness off · ${counts.sessions} live`
    : counts.sessions === 0 && conflicts === 0
      ? "no sessions on this host"
      : [`${counts.sessions} live`, questions ? `${questions} waiting` : null, stuck ? `${stuck} stuck` : null, conflicts ? `${conflicts} conflict${conflicts > 1 ? "s" : ""}` : null].filter(Boolean).join(" · ")

  const lead = accent
    ? accent.kind === "question"
      ? `Needs you: session ${slug(accent.id)} waits for an answer.`
      : accent.kind === "stuck"
        ? `Needs you: session ${slug(accent.id)} is stuck.`
        : `Needs you: a worktree has a conflict (${snap.worktrees.find((w) => w.id === accent.id)?.branch ?? accent.id}).`
    : "Nothing needs you."
  const summary = `Harness office on ${snap.host}. ${lead} ${counts.sessions} live sessions, ${counts.workers} of them workers, ${counts.racked} on the rack. ${snap.harnessOff ? "Harness is off." : "Harness is on."}`

  return {
    now: snap.now,
    host: snap.host,
    harnessOff: snap.harnessOff,
    desks,
    sides,
    rack,
    drawers: dr.list,
    drawerOverflow: dr.overflow,
    capsules,
    ticker: {
      rate: snap.journalRate,
      speed,
      denyMarks: snap.denies,
      label: `Journal ticker: ${Math.round(snap.journalRate)} rows a minute, ${snap.denies} deny${snap.denies === 1 ? "" : "s"} in the last minute`,
    },
    stamp: {
      pressed: pending > 0,
      pending,
      issued: snap.grants.length,
      label: `Grant stamp: ${snap.grants.length} grant${snap.grants.length === 1 ? "" : "s"} in the last 30 minutes, ${pending} not used yet`,
    },
    gauge: {
      share: snap.steeringShare,
      angle,
      baseline: needleAngle(BASELINE_SHARE),
      label: snap.steeringShare === null ? "Steering gauge: no data" : `Steering gauge: ${Math.round(snap.steeringShare * 100)}% of prompts in the last 7 days are steering, baseline ${Math.round(BASELINE_SHARE * 100)}%`,
    },
    clock: {
      now: snap.now,
      jobAngle: next ? hourAngle(next.next_at) : null,
      nextJob: next ? next.name : null,
      label: next ? `Job clock: next job ${next.name} at ${new Date(next.next_at).toTimeString().slice(0, 5)}` : "Job clock: no job scheduled",
    },
    fuses: {
      main: !snap.harnessOff,
      breakers,
      overflow: Math.max(0, snap.rules.length - MAX_BREAKERS),
      label: `Fuse box: main switch ${snap.harnessOff ? "off" : "on"}, ${breakers.map((b) => `${b.id} ${b.mode}`).join(", ") || "no rules"}`,
    },
    bell: snap.bell,
    accent,
    empty: snap.sessions.length === 0,
    counts,
    readout,
    summary,
  }
}

/** The server's snapshot, as far as the office reads it (src/serve/snapshot.ts: Snapshot). */
export interface ServerSnapshot {
  host: string
  ledger: {
    now: number
    harnessOn: boolean
    sessions: { id: string; tool: string | null; parent_session_id: string | null; repo: string | null; goal: string | null; running: boolean; stuck: boolean; waiting: boolean; started_at: number; ended_at: number | null; last_event_at: number | null }[]
    questions: unknown[]
    worktrees: { id: string; repo: string | null; branch: string | null; state: string; sync_state: string | null; owner_session_id: string | null }[]
    rules: { id: string; mode: string }[]
    wakes: { time: number; session_id: string | null; reason: string | null }[]
    grants: { id: string; used_at: number | null; expires_at: number | null }[]
    jobs: { name: string; next_run_at: number | null }[]
    recent: { time: number; event: string; outcome: string | null }[]
    journalPerMin: number
    steeringShare7d: number | null
  }
}

const WORKTREE_STATES = ["active", "landed", "held", "removed"] as const
const SYNC_STATES = ["current", "behind", "conflict"] as const
const MODES = ["enforce", "advise", "inject", "off"] as const

/** Map the page's snapshot to the LedgerSnapshot the model reads. Pure. Grants that expired unused do not count as pending. */
export function ledgerFromServer(snap: ServerSnapshot): LedgerSnapshot {
  const l = snap.ledger
  const pick = <T extends string>(list: readonly T[], v: string | null, fallback: T): T => (list.find((x) => x === v) ?? fallback)
  return {
    now: l.now,
    host: snap.host,
    harnessOff: !l.harnessOn,
    sessions: l.sessions.map((s) => ({
      id: s.id,
      tool: s.tool === "claude" ? "claude" : "opencode",
      parent_session_id: s.parent_session_id,
      repo: s.repo,
      goal: s.goal,
      running: s.running,
      stuck: s.stuck,
      waitingQuestion: s.waiting,
      started_at: s.started_at,
      ended_at: s.ended_at,
      last_activity: s.last_event_at ?? s.started_at,
    })),
    worktrees: l.worktrees.map((w) => ({
      id: w.id,
      repo: w.repo ?? "repo",
      branch: w.branch ?? "detached",
      state: pick(WORKTREE_STATES, w.state, "held"),
      sync_state: w.sync_state === null ? null : pick(SYNC_STATES, w.sync_state, "current"),
      session_id: w.owner_session_id,
    })),
    wakes: l.wakes.filter((w): w is typeof w & { session_id: string } => w.session_id !== null).map((w) => ({ session_id: w.session_id, kind: w.reason ?? "wake", time: w.time })),
    journalRate: l.journalPerMin,
    denies: l.recent.filter((r) => r.outcome === "deny" && l.now - r.time < 60_000).length,
    grants: l.grants.filter((g) => g.used_at !== null || g.expires_at === null || g.expires_at > l.now).map((g) => ({ id: g.id, time: l.now, used_at: g.used_at })),
    steeringShare: l.steeringShare7d,
    jobs: l.jobs.map((j) => ({ name: j.name, next_at: j.next_run_at })),
    rules: l.rules.map((r) => ({ id: r.id, mode: pick(MODES, r.mode, "enforce") })),
    bell: l.questions.length > 0,
  }
}

/** The page entry: server snapshot in, office state out. */
export function officeStateFromServer(snap: ServerSnapshot, prev?: OfficeState): OfficeState {
  return officeState(ledgerFromServer(snap), prev)
}
