import type { Database } from "bun:sqlite"
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { basename, dirname, join, resolve, sep } from "node:path"
import { append, upsertSession } from "../ledger/journal.ts"
import { ulid } from "../ledger/ulid.ts"
import { writeLive } from "./handoff.ts"

export type Git = (args: string[], cwd: string) => { ok: boolean; out: string; err: string }

export const spawnGit: Git = (args, cwd) => {
  const r = Bun.spawnSync(["git", ...args], {
    cwd,
    env: { ...process.env, GIT_TERMINAL_PROMPT: "0" },
    stdout: "pipe",
    stderr: "pipe",
  })
  return { ok: r.exitCode === 0, out: r.stdout.toString().trim(), err: r.stderr.toString().trim() }
}

const home = () => process.env.HOME ?? homedir()
export const worktreesRoot = () => join(home(), ".worktrees")

const touch = (db: Database, session: string) => upsertSession(db, { id: session, tool: "unknown" })

// The repo is keyed by its main checkout: from a linked worktree, the common git dir sits in the main one.
function mainCheckout(git: Git, cwd: string): string {
  const r = git(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)
  if (!r.ok || !r.out) throw new Error(`not a git repository: ${cwd}`)
  return basename(r.out) === ".git" ? dirname(r.out) : r.out
}

// The live file lives in .harness/. Excluding it keeps the worktree clean, so landing can remove it.
function ensureExclude(git: Git, main: string): void {
  const r = git(["rev-parse", "--path-format=absolute", "--git-path", "info/exclude"], main)
  if (!r.ok) return
  const file = r.out
  const text = existsSync(file) ? readFileSync(file, "utf8") : ""
  if (text.split(/\r?\n/).some((l) => l.trim() === ".harness/")) return
  mkdirSync(dirname(file), { recursive: true })
  appendFileSync(file, `${text === "" || text.endsWith("\n") ? "" : "\n"}.harness/\n`)
}

export function worktreeNew(
  db: Database,
  a: { session: string; repoCwd: string; name: string; workstreamId?: string },
  git: Git = spawnGit,
): { id: string; path: string; branch: string } {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(a.name) || a.name.includes("..") || a.name.endsWith(".lock")) {
    throw new Error(`bad worktree name "${a.name}": use letters, digits, ".", "_" and "-" only, no slash`)
  }
  const main = mainCheckout(git, a.repoCwd)
  const path = join(worktreesRoot(), basename(main), a.name)
  if (existsSync(path)) throw new Error(`worktree path already exists: ${path}`)
  if (a.workstreamId && !db.query("select 1 from workstreams where id = ?").get(a.workstreamId)) {
    throw new Error(`unknown workstream: ${a.workstreamId}`)
  }

  const base = git(["rev-parse", "--verify", "-q", "origin/HEAD"], main).ok ? "origin/HEAD" : "HEAD"
  mkdirSync(dirname(path), { recursive: true })
  const add = git(["worktree", "add", "--no-track", "-b", a.name, path, base], main)
  if (!add.ok) throw new Error(`git worktree add failed: ${add.err}`)
  ensureExclude(git, main)

  const id = ulid()
  const now = Date.now()
  db.transaction(() => {
    touch(db, a.session)
    let wsId = a.workstreamId
    if (!wsId) {
      wsId = ulid()
      db.query("insert into workstreams(id, owner_session_id, repo, title, state, updated_at) values(?, ?, ?, ?, 'active', ?)").run(
        wsId,
        a.session,
        main,
        a.name,
        now,
      )
    }
    db.query(
      "insert into worktrees(id, workstream_id, session_id, repo, path, branch, state, sync_state, created_at) values(?, ?, ?, ?, ?, ?, 'active', null, ?)",
    ).run(id, wsId, a.session, main, path, a.name, now)
    append(db, { session_id: a.session, event: "worktree.created", data: { id, path, branch: a.name, workstream_id: wsId, repo: main } })
  }).immediate()
  writeLive(db, main)
  return { id, path, branch: a.name }
}

// D37: a worktree made by hand under ~/.worktrees/ is recorded on its first write.
export function register(
  db: Database,
  a: { session: string; path: string },
  git: Git = spawnGit,
): { id: string; registered: boolean } {
  const path = resolve(a.path)
  if (!path.startsWith(worktreesRoot() + sep)) throw new Error(`not under ${worktreesRoot()}: ${path}`)
  const known = db.query("select id from worktrees where path = ?").get(path) as { id: string } | null
  if (known) return { id: known.id, registered: false }

  const br = git(["rev-parse", "--abbrev-ref", "HEAD"], path)
  if (!br.ok) throw new Error(`not a git worktree: ${path}`)
  const main = mainCheckout(git, path)
  ensureExclude(git, main)
  const id = ulid()
  db.transaction(() => {
    touch(db, a.session)
    db.query(
      "insert into worktrees(id, workstream_id, session_id, repo, path, branch, state, sync_state, created_at) values(?, null, ?, ?, ?, ?, 'active', null, ?)",
    ).run(id, a.session, main, path, br.out, Date.now())
    append(db, { session_id: a.session, event: "worktree.registered", data: { id, path, branch: br.out, repo: main } })
  }).immediate()
  writeLive(db, main)
  return { id, registered: true }
}

interface WorktreeRow {
  id: string
  workstream_id: string | null
  session_id: string | null
  repo: string
  path: string
  branch: string
  state: string
}

export function land(
  db: Database,
  a: { worktreeId: string; pushedSha: string },
  git: Git = spawnGit,
): { state: "removed" | "held"; ffSkipped?: string; branchKept?: string } {
  const w = db.query("select * from worktrees where id = ?").get(a.worktreeId) as WorktreeRow | null
  if (!w) throw new Error(`unknown worktree: ${a.worktreeId}`)
  const main = w.repo
  const log = (event: string, data: Record<string, unknown>) =>
    append(db, { session_id: w.session_id, event, data: { worktree_id: w.id, sha: a.pushedSha, ...data } })

  db.transaction(() => {
    db.query("update worktrees set state = 'landed' where id = ?").run(w.id)
    if (w.workstream_id) {
      // shortcut: a step has no worktree link in the schema, so the first open step of the workstream is the one that landed.
      const step = db
        .query("select id from workstream_steps where workstream_id = ? and coalesce(state, '') != 'done' order by position, id limit 1")
        .get(w.workstream_id) as { id: string } | null
      if (step) db.query("update workstream_steps set state = 'done', done_at = ? where id = ?").run(Date.now(), step.id)
      db.query("update workstreams set updated_at = ? where id = ?").run(Date.now(), w.workstream_id)
    }
    log("worktree.landed", { branch: w.branch })
  }).immediate()

  const ffSkipped = fastForwardMain(git, main, (reason) => log("landing.ff-skipped", { reason }))

  let state: "removed" | "held" = "held"
  let branchKept: string | undefined
  if (!existsSync(w.path)) {
    git(["worktree", "prune"], main)
    state = "removed"
  } else {
    const dirty = git(["status", "--porcelain"], w.path)
    if (!dirty.ok || dirty.out !== "") {
      log("landing.held", { reason: dirty.ok ? "worktree has uncommitted changes" : dirty.err })
    } else {
      const rm = git(["worktree", "remove", w.path], main)
      if (rm.ok) {
        state = "removed"
        const del = git(["branch", "-d", w.branch], main)
        if (!del.ok) {
          branchKept = del.err
          log("landing.branch-kept", { branch: w.branch, reason: del.err })
        }
      } else {
        log("landing.held", { reason: rm.err })
      }
    }
  }
  db.query("update worktrees set state = ?, removed_at = ? where id = ?").run(state, state === "removed" ? Date.now() : null, w.id)
  log(state === "removed" ? "worktree.removed" : "worktree.held", { path: w.path })
  writeLive(db, main)
  return { state, ...(ffSkipped ? { ffSkipped } : {}), ...(branchKept ? { branchKept } : {}) }
}

// D26: the harness, not the agent, moves local main. Returns the skip reason, or undefined when it moved.
function fastForwardMain(git: Git, main: string, skip: (reason: string) => unknown): string | undefined {
  const bail = (reason: string) => (skip(reason), reason)
  const dirty = git(["status", "--porcelain"], main)
  if (!dirty.ok) return bail(`status failed: ${dirty.err}`)
  if (dirty.out !== "") return bail("main checkout has uncommitted changes")

  const head = git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], main)
  if (!head.ok) return bail("origin/HEAD is not set")
  const cur = git(["symbolic-ref", "--short", "HEAD"], main)
  if (!cur.ok || `origin/${cur.out}` !== head.out) return bail(`main checkout is not on ${head.out.replace("origin/", "")}`)

  const fetch = git(["fetch", "-q", "origin"], main)
  if (!fetch.ok) return bail(`fetch failed: ${fetch.err}`)
  const ff = git(["merge", "--ff-only", head.out], main)
  return ff.ok ? undefined : bail(`ff-only merge failed: ${ff.err}`)
}

export interface WorkstreamUpdate {
  session: string
  workstreamId?: string
  title?: string
  state?: string
  steps?: { add?: string[]; done?: string[]; reorder?: string[] }
}

export function workstreamUpdate(db: Database, a: WorkstreamUpdate) {
  const id = db.transaction(() => {
    touch(db, a.session)
    const now = Date.now()
    let ws = a.workstreamId
    if (ws) {
      const row = db.query("select owner_session_id from workstreams where id = ?").get(ws) as { owner_session_id: string | null } | null
      if (!row) throw new Error(`unknown workstream: ${ws}`)
      if (row.owner_session_id !== a.session) throw new Error(`workstream ${ws} belongs to session ${row.owner_session_id}, not ${a.session}`)
    } else {
      const mine = db
        .query("select id from workstreams where owner_session_id = ? and coalesce(state, '') != 'done' order by updated_at desc, id desc limit 1")
        .get(a.session) as { id: string } | null
      if (mine) ws = mine.id
      else {
        const repo = (
          db.query("select repo from worktrees where session_id = ? and repo is not null order by created_at desc limit 1").get(a.session) ??
          db.query("select repo from sessions where id = ?").get(a.session)
        ) as { repo: string | null } | null
        ws = ulid()
        db.query("insert into workstreams(id, owner_session_id, repo, title, state, updated_at) values(?, ?, ?, ?, 'active', ?)").run(
          ws,
          a.session,
          repo?.repo ?? null,
          a.title ?? "untitled",
          now,
        )
      }
    }
    if (a.title !== undefined) db.query("update workstreams set title = ? where id = ?").run(a.title, ws)
    if (a.state !== undefined) db.query("update workstreams set state = ? where id = ?").run(a.state, ws)

    const own = new Set((db.query("select id from workstream_steps where workstream_id = ?").all(ws) as { id: string }[]).map((r) => r.id))
    const check = (ids: string[]) => {
      for (const s of ids) if (!own.has(s)) throw new Error(`step ${s} is not in workstream ${ws}`)
    }
    for (const text of a.steps?.add ?? []) {
      const next = (db.query("select coalesce(max(position), 0) + 1 as p from workstream_steps where workstream_id = ?").get(ws) as { p: number }).p
      const sid = ulid()
      db.query("insert into workstream_steps(id, workstream_id, position, text, state) values(?, ?, ?, ?, 'todo')").run(sid, ws, next, text)
      own.add(sid)
    }
    check(a.steps?.done ?? [])
    for (const s of a.steps?.done ?? []) db.query("update workstream_steps set state = 'done', done_at = ? where id = ?").run(now, s)
    if (a.steps?.reorder) {
      check(a.steps.reorder)
      const rest = (db.query("select id from workstream_steps where workstream_id = ? order by position, id").all(ws) as { id: string }[])
        .map((r) => r.id)
        .filter((s) => !a.steps!.reorder!.includes(s))
      ;[...new Set(a.steps.reorder), ...rest].forEach((s, i) => db.query("update workstream_steps set position = ? where id = ?").run(i + 1, s))
    }
    db.query("update workstreams set updated_at = ? where id = ?").run(now, ws)
    append(db, { session_id: a.session, event: "workstream.updated", data: { workstream_id: ws, title: a.title, state: a.state, steps: a.steps } })
    return ws!
  }).immediate()

  const row = db.query("select id, title, state, repo from workstreams where id = ?").get(id) as {
    id: string
    title: string | null
    state: string | null
    repo: string | null
  }
  if (row.repo) writeLive(db, row.repo)
  const steps = db.query("select id, position, text, state from workstream_steps where workstream_id = ? order by position, id").all(id)
  return { id: row.id, title: row.title, state: row.state, steps }
}

export function keepProcess(
  db: Database,
  a: { session: string; pid: number; command?: string; port?: number; keep: boolean },
): { id: number; keep: boolean } {
  // The core kills registered pids at session.end, so pid 0, 1 and negatives must never get in.
  if (!Number.isInteger(a.pid) || a.pid <= 1) throw new Error(`bad pid: ${a.pid}`)
  return db
    .transaction(() => {
      touch(db, a.session)
      const keep = a.keep ? 1 : 0
      const row = db.query("select id from processes where session_id = ? and pid = ? and ended_at is null order by id desc limit 1").get(a.session, a.pid) as {
        id: number
      } | null
      let id: number
      if (row) {
        id = row.id
        db.query("update processes set keep = ?, command = coalesce(?, command), port = coalesce(?, port) where id = ?").run(
          keep,
          a.command ?? null,
          a.port ?? null,
          id,
        )
      } else {
        id = Number(
          db
            .query("insert into processes(session_id, pid, command, port, keep, started_at) values(?, ?, ?, ?, ?, ?)")
            .run(a.session, a.pid, a.command ?? null, a.port ?? null, keep, Date.now()).lastInsertRowid,
        )
      }
      append(db, { session_id: a.session, event: "process.keep", data: { pid: a.pid, keep: a.keep, command: a.command, port: a.port } })
      return { id, keep: a.keep }
    })
    .immediate()
}
