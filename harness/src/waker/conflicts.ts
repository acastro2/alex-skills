import type { Database } from "bun:sqlite"
import { append } from "../ledger/journal.ts"
import { deliver as realDeliver, type Deliver, type Runner, run } from "./deliver.ts"

export interface ConflictResult {
  worktree: string
  sync_state: "current" | "behind" | "conflict"
  files: string[]
  rebased?: boolean
}

interface Worktree {
  id: string
  session_id: string | null
  repo: string | null
  path: string
  branch: string | null
  sync_state: string | null
  conflict_files: string | null
}

const MID_TURN_MS = 60_000

// Output of `merge-tree --write-tree --name-only`: tree id, then conflicted paths, then a blank line, then messages.
export function conflictedPaths(out: string): string[] {
  const lines = out.split("\n").slice(1)
  const end = lines.indexOf("")
  return [...new Set(lines.slice(0, end === -1 ? lines.length : end).filter(Boolean))]
}

async function baseRef(git: Runner, path: string): Promise<string | null> {
  const head = await git(["git", "-C", path, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
  if (head.code === 0 && head.stdout.trim()) return head.stdout.trim()
  for (const b of ["origin/main", "origin/master"]) {
    if ((await git(["git", "-C", path, "rev-parse", "--verify", "-q", b])).code === 0) return b
  }
  return null
}

function owner(db: Database, id: string | null): { id: string; tool: "claude" | "opencode" } | null {
  if (!id) return null
  const s = db.query("select id, tool, ended_at from sessions where id = ?").get(id) as {
    id: string
    tool: string
    ended_at: number | null
  } | null
  if (!s || s.ended_at != null) return null
  return { id: s.id, tool: s.tool === "opencode" ? "opencode" : "claude" }
}

const known = (db: Database, id: string | null) => (id && db.query("select 1 from sessions where id = ?").get(id) ? id : null)

export async function checkConflicts(
  db: Database,
  opts: { git?: Runner; deliver?: Deliver; now?: number } = {},
): Promise<ConflictResult[]> {
  const git = opts.git ?? run
  const send = opts.deliver ?? ((m) => realDeliver(db, m))
  const now = opts.now ?? Date.now()
  const rows = db.query("select id, session_id, repo, path, branch, sync_state, conflict_files from worktrees where state = 'active'").all() as Worktree[]
  const results: ConflictResult[] = []
  const live: Worktree[] = []

  for (const w of rows) {
    const fetched = await git(["git", "-C", w.path, "fetch", "-q", "origin"])
    const base = fetched.code === 0 ? await baseRef(git, w.path) : null
    if (!base) {
      append(db, { session_id: known(db, w.session_id), event: "worktree.sync_failed", data: { worktree: w.id, error: fetched.stderr.trim().slice(0, 200) || "no base ref" } })
      continue
    }
    live.push(w)
    const mt = await git(["git", "-C", w.path, "merge-tree", "--write-tree", "--name-only", base, "HEAD"])
    if (mt.code > 1) continue
    const behind = Number((await git(["git", "-C", w.path, "rev-list", "--count", `HEAD..${base}`])).stdout.trim()) || 0
    let state: ConflictResult["sync_state"] = mt.code === 1 ? "conflict" : behind > 0 ? "behind" : "current"
    const files = mt.code === 1 ? conflictedPaths(mt.stdout) : []
    const res: ConflictResult = { worktree: w.id, sync_state: state, files }
    const own = owner(db, w.session_id)

    if (state === "behind") {
      const clean = (await git(["git", "-C", w.path, "status", "--porcelain"])).stdout.trim() === ""
      const recent = w.session_id
        ? db.query("select 1 from journal where session_id = ? and time > ? limit 1").get(w.session_id, now - MID_TURN_MS)
        : null
      if (clean && !recent) {
        const rb = await git(["git", "-C", w.path, "rebase", base])
        if (rb.code === 0) {
          state = res.sync_state = "current"
          res.rebased = true
          append(db, { session_id: known(db, w.session_id), event: "worktree.rebased", data: { worktree: w.id, base, behind } })
        } else {
          await git(["git", "-C", w.path, "rebase", "--abort"])
          append(db, { session_id: known(db, w.session_id), event: "worktree.rebase_failed", data: { worktree: w.id, base, error: rb.stderr.trim().slice(0, 200) } })
        }
      }
    }

    const changed = state === "conflict" && (w.sync_state !== "conflict" || w.conflict_files !== JSON.stringify(files))
    db.query("update worktrees set sync_state = ?, conflict_files = ?, synced_at = ? where id = ?").run(
      state,
      files.length ? JSON.stringify(files) : null,
      now,
      w.id,
    )
    if (changed) {
      if (own) {
        const log = (await git(["git", "-C", w.path, "log", "--oneline", "-n", "10", `HEAD..${base}`])).stdout.trim()
        await send({
          session: own.id,
          tool: own.tool,
          kind: "conflict",
          text: `Your branch conflicts with ${base} in: ${files.join(", ")}.\nMain commits behind you:\n${log}\nRebase, resolve the conflicts, then run verify.`,
        })
      } else {
        append(db, { session_id: known(db, w.session_id), event: "conflict.orphaned", data: { worktree: w.id, files } })
      }
    }
    results.push(res)
  }

  // D82: two live branches in one repo that cannot merge cleanly.
  for (let i = 0; i < live.length; i++) {
    for (let j = i + 1; j < live.length; j++) {
      const a = live[i]!
      const b = live[j]!
      if (!a.repo || a.repo !== b.repo || !a.branch || !b.branch || a.branch === b.branch) continue
      const mt = await git(["git", "-C", a.path, "merge-tree", "--write-tree", "--name-only", a.branch, b.branch])
      if (mt.code !== 1) continue
      const files = conflictedPaths(mt.stdout)
      const key = [a.id, b.id].sort().join("+")
      const last = db
        .query("select data_json from journal where event = 'conflict.overlap' and json_extract(data_json, '$.pair') = ? order by seq desc limit 1")
        .get(key) as { data_json: string } | null
      if (last && JSON.stringify(JSON.parse(last.data_json).files) === JSON.stringify(files)) continue
      append(db, { session_id: null, event: "conflict.overlap", data: { pair: key, files } })
      for (const [me, other] of [[a, b], [b, a]] as const) {
        const own = owner(db, me.session_id)
        if (own)
          await send({
            session: own.id,
            tool: own.tool,
            kind: "overlap",
            text: `Your branch ${me.branch} overlaps with ${other.branch} in: ${files.join(", ")}. Agree on merge order with the other session or split the work.`,
          })
      }
    }
  }
  return results
}
