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

// The latest todo list this session wrote, from any row that carries data.todos.
export function latestTodos(db: Database, session: string): Todo[] {
  const r = q1<{ data_json: string }>(
    db,
    `select data_json from journal where session_id = ? and data_json like '%"todos"%' order by seq desc limit 1`,
    session,
  )
  if (!r) return []
  const todos = JSON.parse(r.data_json).todos
  return Array.isArray(todos) ? todos : []
}

export const isBrowseTool = (tool: unknown) => typeof tool === "string" && (tool.startsWith("mcp:browse:") || tool.startsWith("browse_"))
