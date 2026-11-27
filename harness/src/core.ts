// decide(event) -> decision: the one interface between the tools and every policy (spec: Shape, Interface).
// Every event appends exactly one journal row with its decision. The kill switch allows all but still journals.
import type { Database } from "bun:sqlite"
import { isOff } from "./ledger/authority.ts"
import { openLedger } from "./ledger/db.ts"
import { append, upsertSession } from "./ledger/journal.ts"
import { seed } from "./ledger/registry.ts"
import { compactState } from "./policies/compact.ts"
import { guardEgress } from "./policies/egress.ts"
import { guardPath, guardShell, repoOf } from "./policies/guard.ts"
import { injections } from "./policies/inject.ts"
import { guardMcp } from "./policies/mcp.ts"
import { afterTool } from "./policies/nudge.ts"
import { guardPagePort } from "./policies/pageport.ts"
import { endSessionProcesses, keptProcessLine, registerShellProcesses } from "./policies/processes.ts"
import { handlePrompt } from "./policies/prompt.ts"
import { guardSpawn } from "./policies/spawn.ts"
import { agentData, agentOf, endWorkerProcesses, lastProcId, staleInjections, workerStartData } from "./policies/staleworker.ts"
import { stopChecks } from "./policies/stop.ts"
import { allow, isBrowseTool, q1, toolData, type Env, type Out } from "./policies/util.ts"
import { guardPush, recordWorker, startVerify, verifyFinishedWorker } from "./policies/worker.ts"
import { guardWorktree } from "./policies/worktree.ts"
import { takeInbox } from "./waker/deliver.ts"
import { resolve } from "node:path"
import { parse } from "./shell/parse.ts"
import { writeLive } from "./worktree/handoff.ts"
import { land, spawnGit } from "./worktree/lifecycle.ts"
import { ALLOW, type Decision, type HarnessEvent } from "./types.ts"

const LIVE_MS = 30 * 60_000
const isQuestion = (t?: string) => t === "question" || t === "askuserquestion"

let handle: { key: string; db: Database } | null = null

// One ledger handle per process. A different HARNESS_STATE_DIR (tests) opens a new one.
function ledger(): Database {
  const key = process.env.HARNESS_STATE_DIR ?? ""
  if (handle?.key === key) return handle.db
  closeCore()
  const db = openLedger()
  seed(db)
  handle = { key, db }
  return db
}

export function closeCore(): void {
  try {
    handle?.db.close()
  } catch {}
  handle = null
}

// D7, D22, D40: a successful push to the default branch from inside an active worktree lands it.
// Returns the git push's target dir when the command pushes to main, else null.
function pushToMain(command: string, cwd: string): string | null {
  let defaultBranch: string | null = null
  for (const a of parse(command).commands) {
    if (a[0] !== "git") continue
    let dir = cwd
    let i = 1
    for (; i < a.length; i++) {
      if (a[i] === "-C" && a[i + 1] !== undefined) dir = resolve(dir, a[++i]!)
      else if (a[i] === "-c" || a[i] === "--git-dir" || a[i] === "--work-tree") i++
      else if (!a[i]!.startsWith("-")) break
    }
    if (a[i] !== "push") continue
    const pos: string[] = []
    for (i++; i < a.length; i++) {
      const w = a[i]!
      if (w === "--repo" || w === "-o" || w === "--push-option" || w === "--receive-pack" || w === "--exec") i++
      else if (!w.startsWith("-")) pos.push(w)
    }
    defaultBranch ??= gitOut(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], dir)?.replace(/^origin\//, "") ?? null
    const mains = new Set(["main", "master", ...(defaultBranch ? [defaultBranch] : [])])
    const hit = pos.slice(1).some((r) => mains.has(r.replace(/^\+/, "").split(":").pop()!.replace(/^refs\/heads\//, "")))
    if (hit) return dir
  }
  return null
}

const gitOut = (args: string[], cwd: string): string | null => {
  const r = spawnGit(args, cwd)
  return r.ok && r.out ? r.out : null
}

function landOnPush(env: Env): void {
  const { db, ev } = env
  if (ev.toolName !== "shell" || ev.failed) return
  const command = String((ev.input as any)?.command ?? "")
  if (!/\bpush\b/.test(command)) return
  try {
    const dir = pushToMain(command, ev.cwd)
    if (!dir) return
    const w = q1<{ id: string; path: string }>(
      db,
      "select id, path from worktrees where state = 'active' and (path = ? or substr(?, 1, length(path) + 1) = path || '/') order by length(path) desc limit 1",
      dir,
      dir,
    )
    if (!w) return
    const sha = gitOut(["rev-parse", "HEAD"], w.path)
    if (!sha) throw new Error(`no HEAD in ${w.path}`)
    land(db, { worktreeId: w.id, pushedSha: sha })
  } catch (e: any) {
    try {
      append(db, { session_id: ev.session, event: "land.failed", reason: String(e?.message ?? e).slice(0, 500) })
    } catch {}
  }
}

function ensureSession(db: Database, ev: HarnessEvent): void {
  const row = q1<{ tool: string }>(db, "select tool from sessions where id = ?", ev.session)
  if (row && row.tool !== "unknown") return
  if (ev.parentSession && !q1(db, "select 1 as x from sessions where id = ?", ev.parentSession)) {
    upsertSession(db, { id: ev.parentSession, tool: ev.tool })
  }
  upsertSession(db, { id: ev.session, tool: ev.tool, parent_session_id: ev.parentSession ?? null, cwd: ev.cwd, repo: repoOf(ev.cwd) })
}

function liveNeighbours(db: Database, ev: HarnessEvent): string[] {
  const repo = q1<{ repo: string | null }>(db, "select repo from sessions where id = ?", ev.session)?.repo
  if (!repo) return []
  const rows = db
    .query(
      `select s.id, s.tool from sessions s
       where s.repo = ? and s.id != ? and s.ended_at is null
         and coalesce(s.parent_session_id, '') != ?
         and s.id != coalesce((select parent_session_id from sessions where id = ?), '')
         and coalesce((select max(time) from journal where session_id = s.id), 0) > ?`,
    )
    .all(repo, ev.session, ev.session, ev.session, ev.time - LIVE_MS) as { id: string; tool: string }[]
  return rows.map((r) => `Session ${r.id} (${r.tool}) is also working in ${repo}. Use a worktree to change code.`)
}

// D38: render the live handoff of a repo with active worktrees; say so when another live session works there.
function liveHandoffLine(db: Database, ev: HarnessEvent): string | null {
  const s = q1<{ repo: string | null; cwd: string | null }>(db, "select repo, cwd from sessions where id = ?", ev.session)
  const main = q1<{ repo: string }>(
    db,
    "select repo from worktrees where state = 'active' and (repo = ? or path = ? or substr(?, 1, length(path) + 1) = path || '/') limit 1",
    s?.repo ?? "",
    s?.repo ?? "",
    s?.cwd ?? "",
  )?.repo
  if (!main) return null
  writeLive(db, main)
  const other = q1(
    db,
    `select s.id from sessions s
     where s.ended_at is null and s.id != ? and coalesce(s.parent_session_id, '') != ?
       and s.id != coalesce((select parent_session_id from sessions where id = ?), '')
       and (s.repo = ? or s.id in (select session_id from worktrees where repo = ? and state = 'active')
            or s.id in (select owner_session_id from workstreams where repo = ? and coalesce(state, '') != 'done'))
       and coalesce((select max(time) from journal where session_id = s.id), 0) > ?
     limit 1`,
    ev.session,
    ev.session,
    ev.session,
    main,
    main,
    main,
    ev.time - LIVE_MS,
  )
  return other ? `Other sessions work in ${main}. Read .harness/HANDOFF.live.md (in each worktree) to see who does what, and update your own entry with \`workstream_update\`.` : null
}

const joinContext = (parts: (string | null | undefined)[]): string | undefined => {
  const t = parts.filter(Boolean).join("\n")
  return t || undefined
}

// Runs the policies for one tool call in order. The first deny ends the chain and wins; else the first
// hit that names a rule leads. Every policy's data goes to the journal row.
function chain(...policies: (() => Out | null)[]): Out | null {
  const outs: Out[] = []
  for (const p of policies) {
    const o = p()
    if (!o) continue
    outs.push(o)
    if (o.decision.outcome === "deny") break
  }
  if (!outs.length) return null
  const lead = outs.find((o) => o.decision.outcome === "deny") ?? outs.find((o) => o.ruleId) ?? outs[0]
  const data = Object.assign({}, ...outs.map((o) => o.data ?? {}))
  return { ...lead, data: Object.keys(data).length ? data : undefined }
}

async function route(env: Env, off: boolean): Promise<Out> {
  const { db, ev } = env
  switch (ev.event) {
    case "prompt": {
      const { context, out } = handlePrompt(env)
      const text = joinContext([takeInbox(ev.session), ...context])
      const pending = q1<{ event: string }>(
        db,
        "select event from journal where session_id = ? and event in ('question.asked', 'question.answered') order by seq desc limit 1",
        ev.session,
      )
      const answered = pending?.event === "question.asked" && !out.event
      return {
        decision: text ? { outcome: "modify", context: text, ruleId: out.ruleId ?? undefined } : ALLOW,
        ...out,
        event: answered ? "question.answered" : out.event,
        outcome: text && out.ruleId === "routing-hint" ? "inject" : undefined,
        data: { ...(out.data ?? {}), ...(answered ? { via: "prompt" } : {}) },
      }
    }
    case "session.start": {
      const restored = off ? null : compactState(env)
      const text = joinContext([
        takeInbox(ev.session),
        ...(off ? [] : liveNeighbours(db, ev)),
        off ? null : liveHandoffLine(db, ev),
        off ? null : keptProcessLine(db, ev.session, ev.time),
        restored?.text,
      ])
      if (!text) return allow()
      const ruleId = restored?.ruleId
      return allow({
        decision: { outcome: "modify", context: text, ruleId },
        ...(restored ? { ruleId, outcome: "inject", data: { source: "compact", chars: restored.text.length } } : {}),
      })
    }
    case "session.end": {
      db.query("update sessions set ended_at = ? where id = ?").run(ev.time, ev.session)
      // D20: the unkept processes die with the session. The kill switch leaves them alone.
      // Its background workers die with it: their shells too (stale-worker). Claude never kills an agent from outside.
      const killed = off ? [] : [...(await endSessionProcesses(db, ev.session, ev.time)), ...(await endWorkerProcesses(db, ev.session, ev.time))]
      return allow(killed.length ? { data: { killed } } : {})
    }
    case "tool.before": {
      const name = ev.toolName
      const base = toolData(ev)
      if (isQuestion(name)) {
        const qs = (ev.input as any)?.questions ?? ev.input ?? {}
        return allow({ event: "question.asked", data: { ...base, questions: qs } })
      }
      let o: Out | null = null
      if (!off) {
        if (name === "shell") {
          o = chain(() => guardShell(env), () => guardPagePort(env), () => guardPush(env), () => guardWorktree(env), () => guardEgress(env))
        }
        else if (name === "edit" || name === "write") o = chain(() => guardPath(env), () => guardWorktree(env))
        else if (name === "subagent") {
          o = guardSpawn(env)
          if (o?.decision.outcome !== "deny") recordWorker(env)
        } else if (name?.startsWith("mcp:harness:")) o = guardMcp(env)
        else if (isBrowseTool(name)) o = guardPagePort(env)
        else if (name === "webfetch" || name?.startsWith("mcp:")) o = guardEgress(env)
      }
      return { ...(o ?? allow()), data: { ...base, ...(o?.data ?? {}) } }
    }
    case "tool.after": {
      if (off) return allow({ data: toolData(ev) })
      // The verify starts first: it is quick, and afterTool may wait on a judgment call.
      const worker = ev.toolName === "subagent" ? startVerify(env) : null
      const o = await afterTool(env)
      try {
        registerShellProcesses(env)
      } catch {} // a failed lookup must never block the tool call
      landOnPush(env)
      if (!worker) return o
      const context = joinContext([o.decision.context, worker.context])
      return { ...o, decision: { ...o.decision, outcome: "modify", context }, data: { ...(o.data ?? {}), workerId: worker.workerId, ...workerStartData(env, worker.workerId) } }
    }
    case "stop":
      if (off) return allow({ data: { reply: (ev.reply ?? "").slice(0, 4000) } })
      verifyFinishedWorker(env)
      return stopChecks(env)
  }
}

export async function decide(ev: HarnessEvent): Promise<Decision> {
  let db: Database | undefined
  try {
    db = ledger()
    ensureSession(db, ev)
    const prior = q1<{ t: number | null }>(db, "select max(turn) as t from journal where session_id = ?", ev.session)?.t ?? 0
    const turn = prior + (ev.event === "prompt" ? 1 : 0)
    const off = isOff(db)
    const env: Env = { db, ev, turn }

    const procMark = agentOf(ev) && ev.event === "tool.after" ? lastProcId(db) : 0
    let out: Out = await route(env, off)
    // The kill switch allows every call, and the journal says what the rules would have done.
    if (off && ev.event !== "prompt") out = { ...out, decision: ALLOW, reason: out.reason ?? "harness off" }
    const base = out.decision

    // Phase 7 injections ride on the call's decision. Each gets its own journal row, so "once per session" can be checked.
    const inj = base.outcome === "deny" || base.outcome === "ask" ? [] : [...injections(env), ...staleInjections(env)]
    const sent = inj.filter((i) => !i.advise).map((i) => i.text)
    // The outcome stays as it was: an allow that carries context is an allow with a note.
    const d: Decision = sent.length ? { ...base, context: joinContext([base.context, ...sent]) } : base

    // A stop reply goes to the journal for the waker (data.reply, 4000 chars).
    const stopData = ev.event === "stop" ? { reply: (ev.reply ?? "").slice(0, 4000), ...(out.data ?? {}) } : out.data
    const tag = agentData(db, ev, procMark)
    const data = Object.keys(tag).length ? { ...(stopData ?? {}), ...tag } : stopData
    append(db, {
      session_id: ev.session,
      turn,
      time: ev.time,
      event: out.event ?? ev.event,
      rule_id: out.ruleId ?? base.ruleId ?? null,
      outcome: out.outcome ?? base.outcome,
      reason: out.reason ?? base.message ?? base.context,
      prompt_text: ev.event === "prompt" ? (ev.prompt ?? "") : undefined,
      args: ev.input,
      output: ev.output,
      data: data && Object.keys(data).length ? data : undefined,
    })
    for (const i of inj) {
      append(db, {
        session_id: ev.session,
        turn,
        time: ev.time,
        event: "inject",
        rule_id: i.ruleId,
        outcome: i.advise ? "advise" : "inject",
        reason: i.text,
      })
    }
    return d
  } catch (e: any) {
    try {
      if (db) append(db, { session_id: ev.session || null, event: "core.error", reason: String(e?.message ?? e).slice(0, 500) })
    } catch {}
    throw e
  }
}
