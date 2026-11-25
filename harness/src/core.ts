// decide(event) -> decision: the one interface between the tools and every policy (spec: Shape, Interface).
// Every event appends exactly one journal row with its decision. The kill switch allows all but still journals.
import type { Database } from "bun:sqlite"
import { isOff } from "./ledger/authority.ts"
import { openLedger } from "./ledger/db.ts"
import { append, upsertSession } from "./ledger/journal.ts"
import { seed } from "./ledger/registry.ts"
import { guardPath, guardShell, repoOf } from "./policies/guard.ts"
import { guardMcp } from "./policies/mcp.ts"
import { afterTool } from "./policies/nudge.ts"
import { handlePrompt } from "./policies/prompt.ts"
import { guardSpawn } from "./policies/spawn.ts"
import { stopChecks } from "./policies/stop.ts"
import { allow, q1, toolData, type Env, type Out } from "./policies/util.ts"
import { guardPush, recordWorker, startVerify, verifyFinishedWorker } from "./policies/worker.ts"
import { guardWorktree } from "./policies/worktree.ts"
import { takeInbox } from "./waker/deliver.ts"
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
      const text = joinContext([takeInbox(ev.session), ...(off ? [] : liveNeighbours(db, ev))])
      return allow(text ? { decision: { outcome: "modify", context: text } } : {})
    }
    case "session.end":
      db.query("update sessions set ended_at = ? where id = ?").run(ev.time, ev.session)
      return allow()
    case "tool.before": {
      const name = ev.toolName
      const base = toolData(ev)
      if (isQuestion(name)) {
        const qs = (ev.input as any)?.questions ?? ev.input ?? {}
        return allow({ event: "question.asked", data: { ...base, questions: qs } })
      }
      let o: Out | null = null
      if (!off) {
        if (name === "shell") o = chain(() => guardShell(env), () => guardPush(env), () => guardWorktree(env))
        else if (name === "edit" || name === "write") o = chain(() => guardPath(env), () => guardWorktree(env))
        else if (name === "subagent") {
          o = guardSpawn(env)
          if (o?.decision.outcome !== "deny") recordWorker(env)
        } else if (name?.startsWith("mcp:harness:")) o = guardMcp(env)
      }
      return { ...(o ?? allow()), data: { ...base, ...(o?.data ?? {}) } }
    }
    case "tool.after": {
      if (off) return allow({ data: toolData(ev) })
      // The verify starts first: it is quick, and afterTool may wait on a judgment call.
      const worker = ev.toolName === "subagent" ? startVerify(env) : null
      const o = await afterTool(env)
      if (!worker) return o
      const context = joinContext([o.decision.context, worker.context])
      return { ...o, decision: { ...o.decision, outcome: "modify", context }, data: { ...(o.data ?? {}), workerId: worker.workerId } }
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

    let out: Out = await route(env, off)
    // The kill switch allows every call, and the journal says what the rules would have done.
    if (off && ev.event !== "prompt") out = { ...out, decision: ALLOW, reason: out.reason ?? "harness off" }
    const d = out.decision

    // A stop reply goes to the journal for the waker (data.reply, 4000 chars).
    const data = ev.event === "stop" ? { reply: (ev.reply ?? "").slice(0, 4000), ...(out.data ?? {}) } : out.data
    append(db, {
      session_id: ev.session,
      turn,
      time: ev.time,
      event: out.event ?? ev.event,
      rule_id: out.ruleId ?? d.ruleId ?? null,
      outcome: out.outcome ?? d.outcome,
      reason: out.reason ?? d.message ?? d.context,
      prompt_text: ev.event === "prompt" ? (ev.prompt ?? "") : undefined,
      args: ev.input,
      output: ev.output,
      data: data && Object.keys(data).length ? data : undefined,
    })
    return d
  } catch (e: any) {
    try {
      if (db) append(db, { session_id: ev.session || null, event: "core.error", reason: String(e?.message ?? e).slice(0, 500) })
    } catch {}
    throw e
  }
}
