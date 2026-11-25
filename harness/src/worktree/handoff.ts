import type { Database } from "bun:sqlite"
import { chmodSync, existsSync, mkdirSync, writeFileSync } from "node:fs"
import { join } from "node:path"

interface WorkstreamRow {
  id: string
  owner_session_id: string | null
  title: string | null
  state: string | null
  updated_at: number | null
}

// The live view of one repo: every workstream that is not done (D23, D38).
// `repo` is the main checkout path, the same value the worktrees table keeps.
export function renderLive(db: Database, repo: string): string {
  const streams = db
    .query("select id, owner_session_id, title, state, updated_at from workstreams where repo = ? and coalesce(state, '') != 'done' order by updated_at, id")
    .all(repo) as WorkstreamRow[]

  const out = [`# Live handoff: ${repo}`, "", "Rendered by the harness. Read only. Change your entry with the `workstream_update` tool.", ""]
  if (streams.length === 0) out.push("No live workstreams.")

  for (const w of streams) {
    out.push(`## ${w.title ?? "untitled"} (${w.id})`)
    out.push(`- Owner: ${w.owner_session_id ?? "none"}`)
    out.push(`- State: ${w.state ?? "unknown"}`)
    if (w.updated_at) out.push(`- Updated: ${new Date(w.updated_at).toISOString()}`)

    const trees = db
      .query("select path, branch, state, sync_state from worktrees where workstream_id = ? and state != 'removed' order by created_at, id")
      .all(w.id) as { path: string; branch: string; state: string; sync_state: string | null }[]
    out.push("- Worktrees:")
    if (trees.length === 0) out.push("  - none")
    for (const t of trees) out.push(`  - \`${t.path}\` on \`${t.branch}\` (${t.state}${t.sync_state ? `, ${t.sync_state}` : ""})`)

    const steps = db
      .query("select id, text, state from workstream_steps where workstream_id = ? order by position, id")
      .all(w.id) as { id: string; text: string; state: string | null }[]
    out.push("- Next steps:")
    if (steps.length === 0) out.push("  - none")
    for (const s of steps) out.push(`  - [${s.state === "done" ? "x" : " "}] ${s.text} (${s.id})`)

    const procs = w.owner_session_id
      ? (db
          .query("select pid, command, port, keep from processes where session_id = ? and ended_at is null order by id")
          .all(w.owner_session_id) as { pid: number; command: string | null; port: number | null; keep: number | null }[])
      : []
    out.push("- Running processes:")
    if (procs.length === 0) out.push("  - none")
    for (const p of procs) {
      const extra = [p.port ? `port ${p.port}` : "", p.keep ? "kept" : ""].filter(Boolean).join(", ")
      out.push(`  - pid ${p.pid}: ${p.command ?? "unknown"}${extra ? ` (${extra})` : ""}`)
    }
    out.push("")
  }
  return out.join("\n").trimEnd() + "\n"
}

// Writes the rendering into every active worktree of the repo. The file is read only (0444),
// so an agent edits the ledger through the tool, not the file.
export function writeLive(db: Database, repo: string): string[] {
  const text = renderLive(db, repo)
  const trees = db.query("select path from worktrees where repo = ? and state = 'active'").all(repo) as { path: string }[]
  const written: string[] = []
  for (const t of trees) {
    if (!existsSync(t.path)) continue
    const dir = join(t.path, ".harness")
    const file = join(dir, "HANDOFF.live.md")
    mkdirSync(dir, { recursive: true })
    if (existsSync(file)) chmodSync(file, 0o644)
    writeFileSync(file, text)
    chmodSync(file, 0o444)
    written.push(file)
  }
  return written
}
