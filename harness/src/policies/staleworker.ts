// stale-worker: a background worker that went quiet and was never stopped.
// Claude Code keeps a background Agent alive while it waits on a shell that never ends; an OpenCode child
// session can idle the same way. The parent gets one nudge per worker per 30 min, from two places:
//   - the parent's own next prompt or tool.after (staleInjections), and
//   - the waker tick, when the parent is idle (src/waker/waker.ts).
// Liveness comes from the journal, not from the tool:
//   OpenCode: rows of the child session.
//   Claude:   hooks of a subagent carry the parent's session_id plus agent_id, so decide() tags each of those
//             rows with data.agent_id (agentData). SubagentStop reaches core as a `stop` with an agent id.
import type { Database } from "bun:sqlite"
import { append } from "../ledger/journal.ts"
import { mode } from "../ledger/registry.ts"
import type { HarnessEvent } from "../types.ts"
import type { Injection } from "./inject.ts"
import { endSessionProcesses, procInfo } from "./processes.ts"
import { firstLine, q1, shortArg, type Env } from "./util.ts"

export const RULE = "stale-worker"
export const THROTTLE_MS = 30 * 60_000 // one nudge per worker per 30 min
export const ABORT_AFTER_MS = 60 * 60_000 // OpenCode only: stale this long and the parent ended
const LOOKBACK_MS = 24 * 3600_000
const ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

// Set by the Claude adapter on events that fire inside a subagent. HarnessEvent has no field for it.
export interface AgentFields {
  agentId?: string
  agentType?: string
}
export const agentOf = (ev: HarnessEvent): string | undefined => (ev as HarnessEvent & AgentFields).agentId

export function staleMs(): number {
  const n = Number(process.env.HARNESS_STALE_WORKER_MIN)
  return (Number.isFinite(n) && n > 0 ? n : 15) * 60_000
}

const ulidTime = (id: string): number => [...id.slice(0, 10)].reduce((t, c) => t * 32 + Math.max(0, ULID_ALPHABET.indexOf(c)), 0)

const hhmm = (t: number) => {
  const d = new Date(t)
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`
}

const shortId = (id: string) => id.replace(/^(ses_|agent-)/, "").slice(0, 8)

export interface StaleWorker {
  id: string // workers.id
  parent: string
  session: string // the worker's session (OpenCode) or agent id (Claude)
  tool: "claude" | "opencode"
  parentEnded: boolean
  idleSince: number
  goal: string
  waiting: string // ", waiting on ..." or ""
}

// ---- tagging: decide() calls these around each event ----

export const lastProcId = (db: Database): number => q1<{ m: number | null }>(db, "select max(id) as m from processes")?.m ?? 0

// Extra journal data for an event: who ran it (Claude subagent), the processes its shell left behind,
// and whether a shell ran in the background.
export function agentData(db: Database, ev: HarnessEvent, procMark: number): Record<string, unknown> {
  const d: Record<string, unknown> = {}
  const agent = agentOf(ev)
  if (agent) d.agent_id = agent
  if (ev.event !== "tool.after") return d
  if (ev.toolName === "shell" && ev.input?.run_in_background === true) {
    d.bg = true
    const task = /backgroundTaskId:\s*(\S+)/.exec(ev.output ?? "")?.[1]
    if (task) d.bg_task = task
  }
  if (agent) {
    const pids = (db.query("select pid from processes where id > ? and session_id = ? order by id").all(procMark, ev.session) as { pid: number }[]).map((r) => r.pid)
    if (pids.length) d.pids = pids
  }
  return d
}

// tool.after of a background spawn: the data the spawn row carries so the worker can be found again.
export function workerStartData(env: Env, workerId: string): Record<string, unknown> {
  const { db, ev } = env
  const session = q1<{ s: string | null }>(db, "select worker_session_id as s from workers where id = ?", workerId)?.s
  if (!session) return {}
  const line = firstLine(String(ev.input?.prompt ?? "").replace(/^HARNESS-CONTRACT.*$/m, ""))
  return { workerSession: session, agent_id: session, goal: shortArg(line || "no goal given", 120) }
}

// ---- liveness ----

function goalOf(db: Database, parent: string, workerId: string, session: string): string {
  const spawn = q1<{ d: string | null }>(db, "select data_json as d from journal where session_id = ? and event = 'tool.after' and json_extract(data_json, '$.workerId') = ? limit 1", parent, workerId)
  const g = spawn?.d ? JSON.parse(spawn.d).goal : null
  if (typeof g === "string" && g) return g
  const p = q1<{ t: string | null }>(db, "select prompt_text as t from journal where session_id = ? and event = 'prompt' and prompt_text is not null order by seq limit 1", session)
  return shortArg(firstLine(p?.t ?? "") || "no goal recorded", 120)
}

// What the worker waits on: registered processes that still run, else a shell call that never returned,
// else the last shell it sent to the background.
function waitingOn(db: Database, parent: string, session: string, now: number, inFlight: string | null): string {
  const tagged = (db.query("select data_json from journal where session_id = ? and event = 'tool.after' and json_extract(data_json, '$.agent_id') = ? and json_extract(data_json, '$.pids') is not null").all(parent, session) as { data_json: string }[]).flatMap(
    (r) => JSON.parse(r.data_json).pids as number[],
  )
  type Proc = { pid: number; command: string | null; started_at: number | null }
  const open = db.query("select pid, command, started_at from processes where ended_at is null and session_id = ?")
  // Claude: the parent's process rows, narrowed to the pids this agent's own tool rows left behind.
  const viaParent = (open.all(parent) as Proc[]).filter((r) => tagged.includes(r.pid))
  const live = [...new Map([...viaParent, ...(open.all(session) as Proc[])].map((r) => [r.pid, r])).values()].filter((r) => {
    const cur = procInfo(r.pid)
    return cur && (r.started_at == null || Math.abs(cur.startMs - r.started_at) < 5000)
  })
  if (live.length) {
    const first = live[0]!
    const age = Math.max(0, Math.round((now - (first.started_at ?? now)) / 60_000))
    const more = live.length > 1 ? ` and ${live.length - 1} more` : ""
    return `, waiting on ${live.length} shell${live.length > 1 ? "s" : ""} (${shortArg(first.command ?? "unknown", 50)}, PID ${first.pid}, running ${age} min${more})`
  }
  const bg = q1<{ data_json: string }>(
    db,
    "select data_json from journal where event = 'tool.after' and (session_id = ? or (session_id = ? and json_extract(data_json, '$.agent_id') = ?)) and json_extract(data_json, '$.bg') = 1 order by seq desc limit 1",
    session,
    parent,
    session,
  )
  if (inFlight) return `, waiting on a shell call that has not returned (${inFlight})`
  if (!bg) return ""
  const d = JSON.parse(bg.data_json)
  return `, waiting on a background shell (${shortArg(String(d.arg ?? ""), 50)}${d.bg_task ? `, task ${d.bg_task}` : ""})`
}

// Workers with a session of their own that went quiet. `parent` limits it to one session's workers.
export function staleWorkers(db: Database, now: number, parent?: string): StaleWorker[] {
  const rows = db
    .query(
      `select w.id, w.parent_session_id as parent, w.worker_session_id as session, p.tool, p.ended_at as ended
       from workers w join sessions p on p.id = w.parent_session_id
       where w.worker_session_id is not null ${parent ? "and w.parent_session_id = ?" : ""}`,
    )
    .all(...(parent ? [parent] : [])) as { id: string; parent: string; session: string; tool: string; ended: number | null }[]
  const out: StaleWorker[] = []
  for (const w of rows) {
    const born = ulidTime(w.id)
    if (born < now - LOOKBACK_MS) continue
    const last = q1<{ event: string; time: number; data_json: string | null }>(
      db,
      // Only what the worker did counts. The harness's own rows (nudge, inject, wake.delivered) are not activity.
      `select event, time, data_json from journal
       where (session_id = ? or (session_id = ? and json_extract(data_json, '$.agent_id') = ?))
         and (event in ('prompt', 'stop', 'stop.sendback', 'session.start') or event like 'tool.%' or event like 'question.%')
       order by seq desc limit 1`,
      w.session,
      w.parent,
      w.session,
    )
    if (last?.event === "stop") continue // it finished, and nothing ran after
    const idleSince = last?.time ?? born
    if (now - idleSince < staleMs()) continue
    out.push({
      id: w.id,
      parent: w.parent,
      session: w.session,
      tool: w.tool === "opencode" ? "opencode" : "claude",
      parentEnded: w.ended != null,
      idleSince,
      goal: goalOf(db, w.parent, w.id, w.session),
      waiting: waitingOn(db, w.parent, w.session, now, last?.event === "tool.before" && JSON.parse(last.data_json ?? "{}").tool === "shell" ? shortArg(String(JSON.parse(last.data_json!).arg ?? ""), 50) : null),
    })
  }
  return out
}

// The verified ways to stop it. Claude Code: TaskStop takes task_id (agent id or shell id). OpenCode 2.4.1:
// POST /api/session/{sessionID}/interrupt, operation session.interrupt, resume=false parks queued input.
export const interruptPath = (session: string) => `/api/session/${encodeURIComponent(session)}/interrupt?resume=false`
export const abortRequest = (session: string): string[] => ["opencode", "api", "post", interruptPath(session)]

export function staleText(w: StaleWorker): string {
  const stop = w.tool === "opencode" ? `the shell command \`opencode api post "${interruptPath(w.session)}"\`` : `TaskStop with {"task_id": "${w.session}"}`
  return `Worker ${shortId(w.session)} (${w.goal}) has been idle since ${hhmm(w.idleSince)}${w.waiting}. Stop it with ${stop}, or say why it stays.`
}

// ---- throttle and journal ----

export function nudgedRecently(db: Database, workerId: string, now: number): boolean {
  return !!q1(db, "select 1 as x from journal where event = 'worker.stale' and time > ? and coalesce(outcome, '') != 'failed' and json_extract(data_json, '$.worker_id') = ? limit 1", now - THROTTLE_MS, workerId)
}

export function recordStale(db: Database, w: StaleWorker, now: number, outcome: string, via: string, turn?: number): void {
  append(db, {
    session_id: w.parent,
    turn,
    time: now,
    event: "worker.stale",
    rule_id: RULE,
    outcome,
    data: { worker_id: w.id, worker_session: w.session, idle_since: w.idleSince, via },
  })
}

// ---- the parent's own call ----

// prompt and tool.after reach the parent's context on both tools. A stop does not: Claude ignores context
// on an allowed stop, and OpenCode only sends the deny text. The waker covers a parent that is idle.
export function staleInjections(env: Env): Injection[] {
  const { db, ev } = env
  if (!ev.session || agentOf(ev) || (ev.event !== "prompt" && ev.event !== "tool.after")) return []
  const m = mode(db, RULE)
  if (m === "off") return []
  const out: Injection[] = []
  for (const w of staleWorkers(db, ev.time, ev.session)) {
    if (nudgedRecently(db, w.id, ev.time)) continue
    recordStale(db, w, ev.time, m === "advise" ? "advise" : "inject", "inject", env.turn)
    out.push({ ruleId: RULE, text: staleText(w), advise: m === "advise" })
  }
  return out
}

// session.end of a parent: the shells of its workers die with it. The parent's own processes were killed
// first; this covers processes registered under a worker session (OpenCode).
export async function endWorkerProcesses(db: Database, parent: string, time: number): Promise<number[]> {
  const sessions = (db.query("select worker_session_id as s from workers where parent_session_id = ? and worker_session_id is not null").all(parent) as { s: string }[]).map((r) => r.s)
  const killed: number[] = []
  for (const s of sessions) killed.push(...(await endSessionProcesses(db, s, time)))
  return killed
}
