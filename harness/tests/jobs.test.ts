import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { startJobs } from "../src/jobs/jobs.ts"
import { openLedger } from "../src/ledger/db.ts"
import { append, upsertSession } from "../src/ledger/journal.ts"
import type { WakeMessage } from "../src/waker/deliver.ts"
import { checkConflicts } from "../src/waker/conflicts.ts"

let dir: string
let db: Database
let sent: WakeMessage[]
const fakeDeliver = async (m: WakeMessage) => {
  sent.push(m)
  return { ok: true, via: "fake" }
}

const git = (cwd: string, ...args: string[]) => {
  const r = Bun.spawnSync(["git", "-C", cwd, "-c", "user.email=t@t", "-c", "user.name=t", ...args])
  if (r.exitCode !== 0) throw new Error(`git ${args.join(" ")}: ${r.stderr}`)
  return r.stdout.toString().trim()
}

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-jobs-"))
  process.env.HARNESS_STATE_DIR = join(dir, "state")
  db = openLedger()
  sent = []
})

afterEach(() => {
  db.close()
  delete process.env.HARNESS_STATE_DIR
  delete process.env.HARNESS_JOB_CANARY
  rmSync(dir, { recursive: true, force: true })
})

describe("jobs", () => {
  test("runNow(prune) deletes journal rows older than 90 days and records last_result", async () => {
    const day = 24 * 3600_000
    append(db, { session_id: null, event: "old", time: Date.now() - 100 * day })
    append(db, { session_id: null, event: "new", time: Date.now() - day })
    const jobs = startJobs(db)
    try {
      const res = await jobs.runNow("prune")
      expect(res).toBe("ok: pruned 1 journal rows")
      expect(db.query("select count(*) as c from journal where event = 'old'").get()).toEqual({ c: 0 })
      expect(db.query("select count(*) as c from journal where event = 'new'").get()).toEqual({ c: 1 })
      const s = jobs.status().find((j) => j.name === "prune")!
      expect(s.schedule).toBe("0 3 * * *")
      expect(s.last_result).toBe(res)
      expect(s.last_run_at).toBeGreaterThan(0)
    } finally {
      jobs.stop()
    }
  })
})

describe("conflict watch (D79 to D82)", () => {
  let origin: string
  let main: string
  let n = 0

  function commit(repo: string, file: string, text: string) {
    writeFileSync(join(repo, file), text)
    git(repo, "add", file)
    git(repo, "commit", "-qm", `edit ${file}`)
  }

  function addWorktree(branch: string, sessionId: string | null, state = "active") {
    const path = join(dir, `wt-${branch}`)
    git(main, "worktree", "add", "-q", "-b", branch, path, "main")
    if (sessionId) upsertSession(db, { id: sessionId, tool: "opencode" })
    db.query("insert into worktrees(id, session_id, repo, path, branch, state) values(?, ?, 'r', ?, ?, ?)").run(`wt${++n}`, sessionId, path, branch, state)
    return path
  }

  // Another clone moves origin/main ahead.
  function advanceMain(file: string, text: string) {
    const other = join(dir, `other${++n}`)
    Bun.spawnSync(["git", "clone", "-q", origin, other])
    commit(other, file, text)
    git(other, "push", "-q", "origin", "HEAD:main")
  }

  beforeEach(() => {
    origin = join(dir, "origin.git")
    main = join(dir, "main")
    mkdirSync(main)
    Bun.spawnSync(["git", "init", "-q", "--bare", "-b", "main", origin])
    Bun.spawnSync(["git", "init", "-q", "-b", "main", main])
    git(main, "remote", "add", "origin", origin)
    commit(main, "shared.txt", "one\ntwo\nthree\n")
    commit(main, "other.txt", "x\n")
    git(main, "push", "-q", "-u", "origin", "main")
    git(main, "remote", "set-head", "origin", "main")
  })

  test("a worktree behind with no conflict is rebased", async () => {
    const wt = addWorktree("feat", "s1")
    commit(wt, "mine.txt", "mine\n")
    advanceMain("other.txt", "y\n")
    const res = await checkConflicts(db, { deliver: fakeDeliver })
    expect(res).toEqual([{ worktree: "wt1", sync_state: "current", files: [], rebased: true }])
    expect(git(wt, "rev-list", "--count", "HEAD..origin/main")).toBe("0")
    expect(git(wt, "log", "--format=%s", "-n", "2")).toContain("edit other.txt")
    expect(db.query("select count(*) as c from journal where event = 'worktree.rebased'").get()).toEqual({ c: 1 })
    expect((db.query("select sync_state from worktrees").get() as { sync_state: string }).sync_state).toBe("current")
    expect(sent).toHaveLength(0)
  })

  test("a dirty worktree behind main is marked behind and not rebased", async () => {
    const wt = addWorktree("feat", "s1")
    advanceMain("other.txt", "y\n")
    writeFileSync(join(wt, "shared.txt"), "dirty\n")
    const res = await checkConflicts(db, { deliver: fakeDeliver })
    expect(res[0]!.sync_state).toBe("behind")
    expect(res[0]!.rebased).toBeUndefined()
  })

  test("a conflicting worktree records the file and its owner gets one delivery", async () => {
    const wt = addWorktree("feat", "s1")
    commit(wt, "shared.txt", "one\nMINE\nthree\n")
    advanceMain("shared.txt", "one\nTHEIRS\nthree\n")
    const res = await checkConflicts(db, { deliver: fakeDeliver })
    expect(res[0]).toMatchObject({ sync_state: "conflict", files: ["shared.txt"] })
    const row = db.query("select sync_state, conflict_files, synced_at from worktrees").get() as { sync_state: string; conflict_files: string; synced_at: number }
    expect(row.sync_state).toBe("conflict")
    expect(JSON.parse(row.conflict_files)).toEqual(["shared.txt"])
    expect(row.synced_at).toBeGreaterThan(0)
    expect(sent).toHaveLength(1)
    expect(sent[0]!.session).toBe("s1")
    expect(sent[0]!.text).toContain("shared.txt")
    await checkConflicts(db, { deliver: fakeDeliver })
    expect(sent).toHaveLength(1)
  })

  test("a conflict with an ended owner journals conflict.orphaned", async () => {
    const wt = addWorktree("feat", "s1")
    db.query("update sessions set ended_at = 1 where id = 's1'").run()
    commit(wt, "shared.txt", "one\nMINE\nthree\n")
    advanceMain("shared.txt", "one\nTHEIRS\nthree\n")
    await checkConflicts(db, { deliver: fakeDeliver })
    expect(sent).toHaveLength(0)
    expect(db.query("select count(*) as c from journal where event = 'conflict.orphaned'").get()).toEqual({ c: 1 })
  })

  test("two worktrees editing the same line are both warned", async () => {
    const a = addWorktree("a", "sa")
    const b = addWorktree("b", "sb")
    commit(a, "shared.txt", "one\nAAA\nthree\n")
    commit(b, "shared.txt", "one\nBBB\nthree\n")
    await checkConflicts(db, { deliver: fakeDeliver })
    expect(sent.map((m) => m.session).sort()).toEqual(["sa", "sb"])
    expect(sent.every((m) => m.text.includes("shared.txt"))).toBe(true)
    await checkConflicts(db, { deliver: fakeDeliver })
    expect(sent).toHaveLength(2)
  })
})
