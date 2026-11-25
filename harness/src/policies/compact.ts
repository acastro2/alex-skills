// session.start after a compaction: put the session's state back from the ledger alone (D65).
// Todos, workstream and next steps, worktree, owned processes. Under 1500 chars.
import { mode } from "../ledger/registry.ts"
import { latestTodos, q1, shortArg, type Env } from "./util.ts"

const RULE = "compact-state"
const CAP = 1500

export const isCompact = (env: Env): boolean => env.ev.event === "session.start" && env.ev.input?.source === "compact"

const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s)

export function compactState(env: Env): { text: string; ruleId: string } | null {
  const { db, ev } = env
  if (!isCompact(env) || mode(db, RULE) === "off") return null
  const lines: string[] = []

  const todos = latestTodos(db, ev.session)
  if (todos.length) {
    lines.push("Todos:")
    for (const t of todos.slice(0, 12)) lines.push(`- [${t.status || "pending"}] ${clip(t.content, 120)}`)
  }

  const ws = q1<{ id: string; title: string | null; state: string | null }>(
    db,
    "select id, title, state from workstreams where owner_session_id = ? and coalesce(state, '') != 'done' order by updated_at desc, id desc limit 1",
    ev.session,
  )
  if (ws) {
    lines.push(`Workstream: ${clip(ws.title ?? ws.id, 100)} (${ws.state ?? "active"})`)
    const steps = db
      .query("select text from workstream_steps where workstream_id = ? and coalesce(state, '') != 'done' order by position, id limit 5")
      .all(ws.id) as { text: string }[]
    if (steps.length) lines.push(`Next steps: ${steps.map((s) => clip(s.text ?? "", 100)).join("; ")}`)
  }

  const wt = q1<{ path: string; branch: string | null }>(
    db,
    "select path, branch from worktrees where session_id = ? and removed_at is null order by created_at desc limit 1",
    ev.session,
  )
  if (wt) lines.push(`Worktree: ${wt.path}${wt.branch ? ` on ${wt.branch}` : ""}`)

  const procs = db
    .query("select pid, command, port from processes where session_id = ? and ended_at is null order by id limit 5")
    .all(ev.session) as { pid: number; command: string | null; port: number | null }[]
  if (procs.length) {
    lines.push("Running processes you own:")
    for (const p of procs) lines.push(`- pid ${p.pid}${p.port ? ` port ${p.port}` : ""}: ${shortArg(p.command ?? "", 80)}`)
  }

  if (!lines.length) return null
  const text = clip(`State restored after compaction (from the harness ledger):\n${lines.join("\n")}`, CAP)
  return { text, ruleId: RULE }
}
