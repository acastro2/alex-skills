// Shared pieces for the policy modules: the result shape, mode gating and small journal queries.
import type { Database } from "bun:sqlite"
import { mode } from "../ledger/registry.ts"
import { scrub } from "../ledger/journal.ts"
import type { Decision, HarnessEvent } from "../types.ts"

export interface Env {
  db: Database
  ev: HarnessEvent
  turn: number // this session's turn: prompts seen so far, counting this one for a prompt event
}

// A decision plus what the journal row should say. Unset fields default from the event and the decision.
export interface Out {
  decision: Decision
  event?: string
  ruleId?: string | null
  outcome?: string
  reason?: string
  data?: Record<string, unknown>
}

export const allow = (extra: Partial<Out> = {}): Out => ({ decision: { outcome: "allow" }, ...extra })

// Applies a rule's mode to a hit: off skips (null), advise allows and logs, enforce denies.
export function hit(env: Env, ruleId: string, message: string, data?: Record<string, unknown>): Out | null {
  const m = mode(env.db, ruleId)
  if (m === "off") return null
  if (m === "advise") return { decision: { outcome: "allow", ruleId }, ruleId, outcome: "advise", reason: message, data }
  return { decision: { outcome: "deny", message, ruleId }, ruleId, reason: message, data }
}

export function git(args: string[], cwd: string): { ok: boolean; out: string } {
  try {
    const r = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "ignore" })
    return { ok: r.exitCode === 0, out: r.stdout.toString().trim() }
  } catch {
    return { ok: false, out: "" }
  }
}

export function q1<T>(db: Database, sql: string, ...params: (string | number | null)[]): T | null {
  return db.query(sql).get(...params) as T | null
}

export const shortArg = (s: string, n = 80): string => scrub(s.replace(/\s+/g, " ")).slice(0, n)

export function firstLine(s: string): string {
  return (s.split(/\r?\n/).find((l) => l.trim()) ?? "").trim()
}

export interface Todo {
  content: string
  status: string
}

// What a tool row carries in data_json: the waker and the stop checks read these fields.
export function toolData(ev: HarnessEvent): Record<string, any> {
  const i = (ev.input ?? {}) as Record<string, any>
  const d: Record<string, any> = { tool: ev.toolName }
  if (ev.toolName === "shell") d.arg = shortArg(String(i.command ?? ""), 600)
  else if (typeof i.path === "string") {
    d.path = i.path
    d.arg = i.path
  } else d.arg = shortArg(JSON.stringify(i) ?? "", 160)
  if (Array.isArray(i.todos)) {
    d.todos = i.todos.map((t: any) => ({ content: String(t?.content ?? t?.text ?? "").slice(0, 200), status: String(t?.status ?? "") }))
  }
  if (ev.failed) d.failed = true
  return d
}

export interface ToolRow {
  seq: number
  data: Record<string, any>
}

// This session's tool rows for a turn (tool.after and the rows that replace it), oldest first.
export function toolRows(db: Database, session: string, turn: number): ToolRow[] {
  const rows = db
    .query(
      `select seq, data_json from journal
       where session_id = ? and turn = ? and event in ('tool.after', 'nudge', 'stuck', 'question.answered')
         and data_json is not null order by seq`,
    )
    .all(session, turn) as { seq: number; data_json: string }[]
  return rows.map((r) => ({ seq: r.seq, data: JSON.parse(r.data_json) })).filter((r) => r.data.tool)
}

// Claude Code keeps todos with TaskCreate/TaskUpdate. The journal keeps each call's input in data.arg
// (scrubbed, cut at 160 chars) but not the created task id, so ids are the creation order, 1-based.
function tasksAfter(db: Database, session: string, afterSeq: number): { seq: number; todos: Todo[] } | null {
  const rows = db
    .query(
      `select seq, data_json from journal
       where session_id = ? and seq > ? and event = 'tool.after'
         and (data_json like '%"taskcreate"%' or data_json like '%"taskupdate"%') order by seq`,
    )
    .all(session, afterSeq) as { seq: number; data_json: string }[]
  const tasks: { content: string; status: string; gone?: boolean }[] = []
  let last = 0
  for (const r of rows) {
    const d = JSON.parse(r.data_json)
    if (d.failed || (d.tool !== "taskcreate" && d.tool !== "taskupdate")) continue
    let input: Record<string, any> = {}
    try {
      input = JSON.parse(String(d.arg))
    } catch {
      const m = /"(subject|status|taskId)":"((?:[^"\\]|\\.)*)/.exec(String(d.arg)) // cut-off JSON: keep the first field
      if (m) input = { [m[1]!]: m[2] }
    }
    last = r.seq
    if (d.tool === "taskcreate") {
      tasks.push({ content: String(input.subject ?? input.description ?? "").slice(0, 200), status: "pending" })
      continue
    }
    const t = tasks[Number(input.taskId) - 1]
    if (!t) continue
    if (typeof input.subject === "string") t.content = input.subject.slice(0, 200)
    if (input.status === "deleted") t.gone = true
    else if (typeof input.status === "string") t.status = input.status
  }
  if (!last) return null
  return { seq: last, todos: tasks.filter((t) => !t.gone).map(({ content, status }) => ({ content, status })) }
}

// The latest todo list this session wrote: data.todos rows (TodoWrite) or the task rows (Claude Code), newest wins.
export function latestTodos(db: Database, session: string): Todo[] {
  const r = q1<{ seq: number; data_json: string }>(
    db,
    `select seq, data_json from journal where session_id = ? and data_json like '%"todos"%' order by seq desc limit 1`,
    session,
  )
  const written = r ? JSON.parse(r.data_json).todos : null
  const tasks = tasksAfter(db, session, 0)
  if (tasks && (!r || tasks.seq > r.seq)) return tasks.todos
  return Array.isArray(written) ? written : []
}

export const isBrowseTool = (tool: unknown) => typeof tool === "string" && (tool.startsWith("mcp:browse:") || tool.startsWith("browse_"))
