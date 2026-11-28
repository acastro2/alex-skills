import type { Database } from "bun:sqlite"
import { getMeta, setMeta } from "../ledger/db.ts"
import { append } from "../ledger/journal.ts"
import { mode } from "../ledger/registry.ts"
import { ulid } from "../ledger/ulid.ts"
import { endSessionProcesses } from "../policies/processes.ts"
import { ABORT_AFTER_MS, THROTTLE_MS, abortRequest, nudgedRecently, recordStale, staleText, staleWorkers } from "../policies/staleworker.ts"
import { land, spawnGit } from "../worktree/lifecycle.ts"
import { deliver as realDeliver, run, type Deliver, type Runner } from "./deliver.ts"

const WATCH_TTL_MS = 24 * 3600_000
const STALL_MS = 10 * 60_000
const NUDGE_CAP = 5

export function addWatch(
  db: Database,
  w: { session: string; kind: "pr" | "worker"; target: string; worker_id?: string; now?: number },
): string {
  const id = ulid()
  const now = w.now ?? Date.now()
  db.query("insert into watches(id, session_id, worker_id, kind, target, last_state, polled_at, expires_at) values(?, ?, ?, ?, ?, null, null, ?)").run(
    id,
    w.session,
    w.worker_id ?? null,
    w.kind,
    w.target,
    now + WATCH_TTL_MS,
  )
  return id
}

interface PrState {
  state: string
  review: string
  mergeable: string
  failed: string[] // failing check names
  head: string
  done?: boolean
}

interface Check {
  __typename?: string
  name?: string
  context?: string
  conclusion?: string
  state?: string
  detailsUrl?: string
  targetUrl?: string
}

const BAD = new Set(["FAILURE", "TIMED_OUT", "STARTUP_FAILURE", "ERROR"])
const BASELINE: PrState = { state: "OPEN", review: "", mergeable: "MERGEABLE", failed: [], head: "" }

function failedChecks(rollup: Check[] | undefined): Check[] {
  return (rollup ?? []).filter((c) => BAD.has(c.conclusion ?? c.state ?? ""))
}

const tail = (s: string, n: number) => s.split("\n").slice(-n).join("\n").trim()

async function prMessages(
  gh: Runner,
  repo: string,
  n: string,
  prev: PrState,
  cur: PrState,
  checks: Check[],
  next: string | null,
): Promise<{ kind: string; text: string }[]> {
  const out: { kind: string; text: string }[] = []
  if (cur.state === "MERGED" && prev.state !== "MERGED") {
    out.push({ kind: "pr.merged", text: `PR #${n} merged. Run the next planned step.${next ? ` Next: ${next}` : ""}` })
  } else if (cur.state === "CLOSED" && prev.state !== "CLOSED") {
    out.push({ kind: "pr.closed", text: `PR #${n} was closed without a merge.` })
  }
  if (cur.state !== "OPEN") return out
  if (cur.review === "APPROVED" && prev.review !== "APPROVED") {
    out.push({ kind: "pr.approved", text: `PR #${n} approved. Merge needs Alex's token.` })
  }
  if (cur.failed.length && cur.failed.join() !== prev.failed.join()) {
    const bad = failedChecks(checks)[0]!
    const runId = /\/runs\/(\d+)/.exec(bad.detailsUrl ?? bad.targetUrl ?? "")?.[1]
    let log = ""
    if (runId) log = tail((await gh(["gh", "run", "view", runId, "--repo", repo, "--log-failed"])).stdout, 80)
    out.push({ kind: "pr.check_failed", text: `PR #${n}: check failed: ${cur.failed.join(", ")}.${log ? `\n${log}` : ""}` })
  }
  if (cur.mergeable === "CONFLICTING" && prev.mergeable !== "CONFLICTING") {
    out.push({ kind: "pr.conflict", text: `PR #${n} has a conflict with its base. Rebase and re-run the acceptance commands.` })
  }
  return out
}

function sessionTool(db: Database, id: string): "claude" | "opencode" {
  const s = db.query("select tool from sessions where id = ?").get(id) as { tool: string } | null
  return s?.tool === "opencode" ? "opencode" : "claude"
}

// D7: a merged PR whose head branch is a registered active worktree of that repo lands the worktree.
// A failure is journaled and never stops the poll.
function landMerged(db: Database, repo: string, branch: string, sha: string): void {
  try {
    const rows = db.query("select id, repo, session_id from worktrees where state = 'active' and branch = ?").all(branch) as {
      id: string
      repo: string
      session_id: string | null
    }[]
    for (const w of rows) {
      const url = spawnGit(["remote", "get-url", "origin"], w.repo)
      if (!url.ok || !url.out.toLowerCase().includes(repo.toLowerCase())) continue
      try {
        land(db, { worktreeId: w.id, pushedSha: sha })
      } catch (e: any) {
        append(db, { session_id: w.session_id, event: "land.failed", reason: String(e?.message ?? e).slice(0, 500) })
      }
    }
  } catch {}
}

async function pollPrs(db: Database, gh: Runner, send: Deliver, now: number): Promise<void> {
  const rows = db
    .query("select id, session_id, target, last_state from watches where kind = 'pr' and expires_at > ?")
    .all(now) as { id: string; session_id: string | null; target: string; last_state: string | null }[]
  for (const w of rows) {
    const prev: PrState = w.last_state ? JSON.parse(w.last_state) : BASELINE
    if (prev.done) continue
    const m = /^(.+)#(\d+)$/.exec(w.target)
    if (!m) continue
    const [, repo, n] = m as unknown as [string, string, string]
    const r = await gh(["gh", "pr", "view", n, "--repo", repo, "--json", "state,reviewDecision,mergeable,statusCheckRollup,headRefOid,headRefName"])
    if (r.code !== 0) continue
    const j = JSON.parse(r.stdout) as { state: string; reviewDecision?: string; mergeable?: string; statusCheckRollup?: Check[]; headRefOid?: string; headRefName?: string }
    const checks = failedChecks(j.statusCheckRollup)
    const cur: PrState = {
      state: j.state,
      review: j.reviewDecision ?? "",
      mergeable: j.mergeable ?? "UNKNOWN",
      failed: checks.map((c) => c.name ?? c.context ?? "check").sort(),
      head: j.headRefOid ?? "",
    }
    if (cur.state !== "OPEN") cur.done = true
    if (cur.state === "MERGED" && prev.state !== "MERGED" && j.headRefName) landMerged(db, repo, j.headRefName, cur.head)
    let next: string | null = null
    if (cur.state === "MERGED" && w.session_id) {
      const step = db
        .query(
          `select s.text from workstream_steps s join workstreams ws on ws.id = s.workstream_id
           where ws.owner_session_id = ? and (s.state is null or s.state not in ('done', 'completed'))
           order by s.position limit 1`,
        )
        .get(w.session_id) as { text: string } | null
      next = step?.text ?? null
    }
    if (w.session_id) {
      for (const msg of await prMessages(gh, repo, n, prev, cur, j.statusCheckRollup ?? [], next)) {
        await send({ session: w.session_id, tool: sessionTool(db, w.session_id), ...msg })
      }
    }
    db.query("update watches set last_state = ?, polled_at = ? where id = ?").run(JSON.stringify(cur), now, w.id)
  }
}

const STALL_TEXT = "You have made no tool call for 10 minutes. Continue the work, or report what blocks you."

async function stallNudges(db: Database, send: Deliver, now: number): Promise<void> {
  if (mode(db, "nudge-stall") === "off") return
  const sessions = db.query("select id, tool, parent_session_id from sessions where ended_at is null").all() as {
    id: string
    tool: string
    parent_session_id: string | null
  }[]
  for (const s of sessions) {
    const last = db.query("select seq, turn, time, event from journal where session_id = ? order by seq desc limit 1").get(s.id) as {
      seq: number
      turn: number | null
      time: number
      event: string
    } | null
    if (!last || !last.event.startsWith("tool.") || last.time > now - STALL_MS) continue

    if (!s.parent_session_id) {
      // Root session: only with a todo pending and no question waiting for Alex (D77).
      const todo = db.query(`select data_json from journal where session_id = ? and data_json like '%"todos"%' order by seq desc limit 1`).get(s.id) as {
        data_json: string
      } | null
      const todos = (todo ? (JSON.parse(todo.data_json).todos ?? []) : []) as { status?: string }[]
      if (!todos.some((t) => t.status !== "completed" && t.status !== "cancelled")) continue
      const stop = db.query("select data_json from journal where session_id = ? and event = 'stop' order by seq desc limit 1").get(s.id) as {
        data_json: string | null
      } | null
      const reply = String((stop?.data_json ? JSON.parse(stop.data_json).reply : "") ?? "")
      if (reply.slice(-300).includes("?")) continue
    }

    const turnSql = last.turn == null ? "turn is null" : "turn = ?"
    const args = last.turn == null ? [s.id] : [s.id, last.turn]
    const count = (db.query(`select count(*) as c from journal where session_id = ? and event = 'nudge' and ${turnSql}`).get(...args) as { c: number }).c
    // One nudge per silence: a nudge newer than the last tool row means we already poked.
    if (db.query("select 1 from journal where session_id = ? and event in ('nudge', 'stuck') and seq > ? limit 1").get(s.id, last.seq)) continue

    if (count >= NUDGE_CAP) {
      append(db, { session_id: s.id, turn: last.turn, event: "stuck", data: { nudges: count } })
      continue
    }
    const r = await send({ session: s.id, tool: s.tool === "opencode" ? "opencode" : "claude", kind: "stall", text: STALL_TEXT })
    const rule = db.query("select 1 from rules where id = 'nudge-stall'").get() ? "nudge-stall" : null
    append(db, { session_id: s.id, turn: last.turn, event: "nudge", rule_id: rule, outcome: r.ok ? "delivered" : "failed", data: { kind: "stall", n: count + 1 } })
  }
}

const PARENT_IDLE_MS = 2 * 60_000

// The parent is idle when its last real event (not an agent's, not a harness row) is a stop, or it is silent.
function parentIdle(db: Database, parent: string, now: number): boolean {
  const last = db
    .query(
      `select event, time from journal where session_id = ? and json_extract(data_json, '$.agent_id') is null
         and (event in ('prompt', 'stop', 'stop.sendback', 'session.start') or event like 'tool.%') order by seq desc limit 1`,
    )
    .get(parent) as { event: string; time: number } | null
  return !last || last.event === "stop" || last.time < now - PARENT_IDLE_MS
}

// Stale background workers (stale-worker): nudge an idle parent, and abort an orphaned OpenCode child.
// Claude Code agents are never killed from outside; their shells die at the parent's session.end.
async function staleWorkerWake(db: Database, send: Deliver, runCmd: Runner, now: number): Promise<void> {
  const m = mode(db, "stale-worker")
  if (m === "off") return
  for (const w of staleWorkers(db, now)) {
    if (w.parentEnded) {
      if (w.tool !== "opencode" || m === "advise" || now - w.idleSince < ABORT_AFTER_MS) continue
      const tries = db.query("select outcome, time from journal where event = 'worker.aborted' and json_extract(data_json, '$.worker_id') = ?").all(w.id) as { outcome: string; time: number }[]
      if (tries.some((t) => t.outcome === "ok") || tries.length >= 3 || tries.some((t) => t.time > now - THROTTLE_MS)) continue
      const r = await runCmd(abortRequest(w.session))
      append(db, {
        session_id: w.parent,
        time: now,
        event: "worker.aborted",
        rule_id: "stale-worker",
        outcome: r.code === 0 ? "ok" : "failed",
        reason: r.code === 0 ? undefined : r.stderr.trim().slice(0, 200) || r.stdout.trim().slice(0, 200),
        data: { worker_id: w.id, worker_session: w.session, idle_since: w.idleSince, via: "opencode api" },
      })
      if (r.code === 0) {
        db.query("update sessions set ended_at = ? where id = ? and ended_at is null").run(now, w.session)
        await endSessionProcesses(db, w.session, now, false) // the waker is a daemon: its parent is not an agent
      }
      continue
    }
    if (nudgedRecently(db, w.id, now) || !parentIdle(db, w.parent, now)) continue
    if (m === "advise") {
      recordStale(db, w, now, "advise", "waker")
      continue
    }
    const r = await send({ session: w.parent, tool: sessionTool(db, w.parent), kind: "worker.stale", text: staleText(w) })
    recordStale(db, w, now, r.ok ? "delivered" : "failed", "waker")
  }
}

const LAND_CHECK_MS = 10 * 60_000

// A worktree whose HEAD already sits in origin/<default> (merged PR, push from elsewhere) lands.
// Fresh worktrees (branch never committed to) are skipped. Never throws.
function landMergedWorktrees(db: Database, now: number): void {
  try {
    const rows = db.query("select id, repo, path, session_id, branch from worktrees where state = 'active'").all() as {
      id: string
      repo: string
      path: string
      session_id: string | null
      branch: string | null
    }[]
    for (const w of rows) {
      try {
        const key = `land_check:${w.id}`
        const last = Number(getMeta(db, key) ?? 0)
        if (now - last < LAND_CHECK_MS) continue
        setMeta(db, key, String(now))
        const head = spawnGit(["rev-parse", "HEAD"], w.path)
        if (!head.ok) continue
        if (w.branch) {
          const log = spawnGit(["reflog", "show", "--format=%gs", w.branch], w.repo)
          if (!log.out.split("\n").some((l) => l && !l.startsWith("branch: Created"))) continue
        }
        if (spawnGit(["remote", "get-url", "origin"], w.repo).ok) spawnGit(["fetch", "-q", "origin"], w.repo)
        const sym = spawnGit(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], w.repo)
        const tip = sym.ok && sym.out ? sym.out : "origin/main"
        // Merged as is, or every commit is on main by patch (cherry-picked, re-split): nothing is missing from main.
        const merged = spawnGit(["merge-base", "--is-ancestor", head.out, tip], w.repo).ok
        const cherry = merged ? null : spawnGit(["cherry", tip, head.out], w.repo)
        const picked = !!cherry?.ok && !!cherry.out && !cherry.out.split("\n").some((l) => l.startsWith("+"))
        if (!merged && !picked) continue
        try {
          land(db, { worktreeId: w.id, pushedSha: head.out })
        } catch (e: any) {
          append(db, { session_id: w.session_id, event: "land.failed", reason: String(e?.message ?? e).slice(0, 500) })
        }
      } catch {}
    }
  } catch {}
}

export interface WakerOpts {
  every?: number
  deliver?: Deliver
  gh?: Runner
  run?: Runner // the opencode CLI (abort of a stale child); defaults to the real process runner
  now?: () => number
}

export async function wakerTick(db: Database, opts: WakerOpts = {}): Promise<void> {
  const gh = opts.gh ?? run
  const send = opts.deliver ?? ((m) => realDeliver(db, m))
  const now = (opts.now ?? Date.now)()
  await pollPrs(db, gh, send, now)
  await stallNudges(db, send, now)
  await staleWorkerWake(db, send, opts.run ?? run, now)
  landMergedWorktrees(db, now)
  db.query("delete from watches where expires_at <= ?").run(now)
}

export function startWaker(db: Database, opts: WakerOpts = {}): { stop(): void; tick(): Promise<void> } {
  let busy = false
  const tick = async () => {
    if (busy) return
    busy = true
    try {
      await wakerTick(db, opts)
    } finally {
      busy = false
    }
  }
  const timer = setInterval(() => void tick().catch(() => {}), opts.every ?? 120_000)
  return { stop: () => clearInterval(timer), tick }
}
