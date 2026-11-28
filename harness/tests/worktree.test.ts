import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { command } from "../src/ledger/authority.ts"
import { openLedger } from "../src/ledger/db.ts"
import { keepProcess, land, register, spawnGit, workstreamUpdate, worktreeNew } from "../src/worktree/lifecycle.ts"
import { renderLive, writeLive } from "../src/worktree/handoff.ts"
import { mergePr, NEEDS_TOKEN } from "../src/worktree/merge.ts"

let root: string
let main: string
let db: Database
const saved = { HOME: process.env.HOME, STATE: process.env.HARNESS_STATE_DIR }

const git = (cwd: string, ...args: string[]) => {
  const r = spawnGit(args, cwd)
  if (!r.ok) throw new Error(`git ${args.join(" ")}: ${r.err}`)
  return r.out
}
const events = (name: string) => db.query("select data_json from journal where event = ?").all(name) as { data_json: string }[]
const branches = () => git(main, "branch", "--format=%(refname:short)").split("\n")

// A repo whose origin is a bare repo, as on a real host.
beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "harness-worktree-"))
  process.env.HOME = join(root, "home")
  process.env.HARNESS_STATE_DIR = join(root, "state")
  for (const k of ["AUTHOR", "COMMITTER"]) {
    process.env[`GIT_${k}_NAME`] = "t"
    process.env[`GIT_${k}_EMAIL`] = "t@example.com"
  }
  mkdirSync(process.env.HOME, { recursive: true })
  const origin = join(root, "origin.git")
  main = join(root, "src", "proj")
  git(root, "init", "-q", "--bare", "-b", "main", origin)
  git(root, "clone", "-q", origin, main)
  writeFileSync(join(main, "README.md"), "one\n")
  git(main, "add", ".")
  git(main, "commit", "-q", "-m", "init")
  git(main, "push", "-q", "-u", "origin", "main")
  git(main, "remote", "set-head", "origin", "-a")
  db = openLedger()
})

afterEach(() => {
  db.close()
  for (const [k, v] of [["HOME", saved.HOME], ["HARNESS_STATE_DIR", saved.STATE]] as const) {
    if (v === undefined) delete process.env[k]
    else process.env[k] = v
  }
  rmSync(root, { recursive: true, force: true })
})

// Commits a file in the worktree and pushes it to origin/main as a fast-forward. Returns the pushed sha.
function pushFrom(path: string, file = "work.txt"): string {
  writeFileSync(join(path, file), "work\n")
  git(path, "add", ".")
  git(path, "commit", "-q", "-m", "work")
  git(path, "push", "-q", "origin", "HEAD:main")
  return git(path, "rev-parse", "HEAD")
}

describe("worktree_new and register (D7, D21, D37)", () => {
  test("creates the dir under ~/.worktrees/<repo>/<name>, the branch, the row, the workstream and the exclude", () => {
    const w = worktreeNew(db, { session: "s1", repoCwd: main, name: "feat-a" })
    expect(w.path).toBe(join(process.env.HOME!, ".worktrees", "proj", "feat-a"))
    expect(w.branch).toBe("feat-a")
    expect(existsSync(join(w.path, "README.md"))).toBe(true)
    expect(branches()).toContain("feat-a")

    const row = db.query("select * from worktrees where id = ?").get(w.id) as Record<string, unknown>
    expect(row).toMatchObject({ path: w.path, branch: "feat-a", state: "active", sync_state: null, session_id: "s1", repo: main })
    const ws = db.query("select * from workstreams where id = ?").get(row.workstream_id as string) as Record<string, unknown>
    expect(ws).toMatchObject({ owner_session_id: "s1", title: "feat-a" })
    expect(events("worktree.created")).toHaveLength(1)

    const exclude = readFileSync(join(main, ".git", "info", "exclude"), "utf8")
    expect(exclude.split("\n")).toContain(".harness/")
    expect(existsSync(join(w.path, ".harness", "HANDOFF.live.md"))).toBe(true)
    expect(git(w.path, "status", "--porcelain")).toBe("")
  })

  test("a second worktree adds .harness/ only once", () => {
    worktreeNew(db, { session: "s1", repoCwd: main, name: "a" })
    worktreeNew(db, { session: "s2", repoCwd: main, name: "b" })
    const lines = readFileSync(join(main, ".git", "info", "exclude"), "utf8").split("\n")
    expect(lines.filter((l) => l === ".harness/")).toHaveLength(1)
  })

  test("refuses a bad name", () => {
    expect(() => worktreeNew(db, { session: "s1", repoCwd: main, name: "../evil" })).toThrow(/bad worktree name/)
  })

  test("register() adds a hand-made worktree on first write, and only once", () => {
    const path = join(process.env.HOME!, ".worktrees", "proj", "hand")
    mkdirSync(join(path, ".."), { recursive: true })
    git(main, "worktree", "add", "-q", "-b", "hand", path, "HEAD")

    const first = register(db, { session: "s9", path })
    expect(first.registered).toBe(true)
    expect(db.query("select branch, state, repo from worktrees where id = ?").get(first.id)).toMatchObject({ branch: "hand", state: "active", repo: main })
    expect(register(db, { session: "s9", path })).toEqual({ id: first.id, registered: false })
    expect(() => register(db, { session: "s9", path: main })).toThrow(/not under/)
  })
})

describe("land (D26, D40)", () => {
  test("clean worktree: removes it and its branch, and fast-forwards the clean main checkout", () => {
    const w = worktreeNew(db, { session: "s1", repoCwd: main, name: "feat" })
    const sha = pushFrom(w.path)

    expect(land(db, { worktreeId: w.id, pushedSha: sha })).toEqual({ state: "removed" })
    expect(existsSync(w.path)).toBe(false)
    expect(branches()).not.toContain("feat")
    expect(git(main, "rev-parse", "HEAD")).toBe(sha)
    expect(db.query("select state from worktrees where id = ?").get(w.id)).toEqual({ state: "removed" })
  })

  test("uncommitted file in the worktree: held, and the dir and branch stay", () => {
    const w = worktreeNew(db, { session: "s1", repoCwd: main, name: "feat" })
    const sha = pushFrom(w.path)
    writeFileSync(join(w.path, "wip.txt"), "unsaved\n")

    expect(land(db, { worktreeId: w.id, pushedSha: sha }).state).toBe("held")
    expect(existsSync(join(w.path, "wip.txt"))).toBe(true)
    expect(branches()).toContain("feat")
    expect(db.query("select state from worktrees where id = ?").get(w.id)).toEqual({ state: "held" })
  })

  test("dirty main checkout: skips the fast-forward and journals landing.ff-skipped", () => {
    const w = worktreeNew(db, { session: "s1", repoCwd: main, name: "feat" })
    const before = git(main, "rev-parse", "HEAD")
    const sha = pushFrom(w.path)
    writeFileSync(join(main, "README.md"), "alex is editing\n")

    const r = land(db, { worktreeId: w.id, pushedSha: sha })
    expect(r.ffSkipped).toMatch(/uncommitted/)
    expect(git(main, "rev-parse", "HEAD")).toBe(before)
    expect(readFileSync(join(main, "README.md"), "utf8")).toBe("alex is editing\n")
    const skipped = events("landing.ff-skipped")
    expect(skipped).toHaveLength(1)
    expect(JSON.parse(skipped[0].data_json).reason).toMatch(/uncommitted/)
  })

  test("marks the first open step of the linked workstream done", () => {
    const w = worktreeNew(db, { session: "s1", repoCwd: main, name: "feat" })
    const wsId = (db.query("select workstream_id from worktrees where id = ?").get(w.id) as { workstream_id: string }).workstream_id
    const ws = workstreamUpdate(db, { session: "s1", workstreamId: wsId, steps: { add: ["first", "second"] } })
    land(db, { worktreeId: w.id, pushedSha: pushFrom(w.path) })
    const states = db.query("select text, state from workstream_steps where workstream_id = ? order by position").all(ws.id)
    expect(states).toEqual([
      { text: "first", state: "done" },
      { text: "second", state: "todo" },
    ])
  })
})

describe("live handoff (D23, D38)", () => {
  test("renderLive lists two workstreams with their steps in order, and writeLive makes a read-only file", () => {
    const a = worktreeNew(db, { session: "s1", repoCwd: main, name: "alpha" })
    const b = worktreeNew(db, { session: "s2", repoCwd: main, name: "beta" })
    const one = workstreamUpdate(db, { session: "s1", steps: { add: ["write test", "write code", "open PR"] } })
    workstreamUpdate(db, { session: "s2", title: "Beta work", steps: { add: ["only step"] } })
    keepProcess(db, { session: "s1", pid: process.pid, command: "bun serve", port: 4000, keep: true })

    const ids = one.steps.map((s) => (s as { id: string }).id)
    workstreamUpdate(db, { session: "s1", steps: { reorder: [ids[2], ids[0]], done: [ids[0]] } })

    const md = renderLive(db, main)
    expect(md).toContain("alpha")
    expect(md).toContain("Beta work")
    expect(md).toContain("s1")
    expect(md).toContain("s2")
    expect(md.indexOf("open PR")).toBeLessThan(md.indexOf("write test"))
    expect(md.indexOf("write test")).toBeLessThan(md.indexOf("write code"))
    expect(md).toContain("[x] write test")
    expect(md).toContain("bun serve (port 4000, kept)")

    const files = writeLive(db, main)
    expect(files.sort()).toEqual([join(a.path, ".harness", "HANDOFF.live.md"), join(b.path, ".harness", "HANDOFF.live.md")].sort())
    expect(readFileSync(files[0], "utf8")).toBe(md)
    expect(statSync(files[0]).mode & 0o777).toBe(0o444)
    expect(() => writeLive(db, main)).not.toThrow() // overwrites a read-only file
  })

  test("a done workstream leaves the live view", () => {
    worktreeNew(db, { session: "s1", repoCwd: main, name: "alpha" })
    workstreamUpdate(db, { session: "s1", state: "done" })
    expect(renderLive(db, main)).toContain("No live workstreams.")
  })

  test("a session cannot change another session's workstream", () => {
    worktreeNew(db, { session: "s1", repoCwd: main, name: "alpha" })
    const id = (db.query("select id from workstreams").get() as { id: string }).id
    expect(() => workstreamUpdate(db, { session: "s2", workstreamId: id, title: "mine now" })).toThrow(/belongs to session s1/)
  })
})

describe("merge_pr (D26, D35)", () => {
  const fake = () => {
    const calls: string[][] = []
    return { calls, run: (args: string[]) => (calls.push(args), { code: 0, stdout: "merged", stderr: "" }) }
  }
  const grant = (text: string) => command(db, { channel: "prompt", session: "s1", isRootSession: true, text })

  test("without a token: returns the MERGE-OK message and runs no gh", () => {
    const g = fake()
    expect(mergePr(db, { session: "s1", repo: "o/r", pr: 7 }, g.run)).toEqual({ ok: false, message: NEEDS_TOKEN })
    expect(NEEDS_TOKEN).toBe("Merge needs Alex's token: he types `MERGE-OK <pr>` as the first line of a prompt.")
    expect(g.calls).toEqual([])
  })

  test("with a token: runs gh pr merge --rebase once, and a second call fails because the token is used", () => {
    const g = fake()
    grant("MERGE-OK 7")
    expect(mergePr(db, { session: "s1", repo: "o/r", pr: 7 }, g.run).ok).toBe(true)
    expect(g.calls).toEqual([["pr", "merge", "7", "--repo", "o/r", "--rebase"]])
    expect(events("merge.done")).toHaveLength(1)

    expect(mergePr(db, { session: "s1", repo: "o/r", pr: 7 }, g.run)).toEqual({ ok: false, message: NEEDS_TOKEN })
    expect(g.calls).toHaveLength(1)
  })

  test("a token for another PR does not merge this one", () => {
    const g = fake()
    grant("MERGE-OK 8")
    expect(mergePr(db, { session: "s1", repo: "o/r", pr: 7 }, g.run).ok).toBe(false)
    expect(g.calls).toEqual([])
  })

  test("a gh failure is journaled as merge.failed", () => {
    grant("MERGE-OK 7")
    const r = mergePr(db, { session: "s1", repo: "o/r", pr: 7 }, () => ({ code: 1, stdout: "", stderr: "not mergeable" }))
    expect(r.ok).toBe(false)
    expect(r.message).toContain("not mergeable")
    expect(events("merge.failed")).toHaveLength(1)
  })
})

// Review 2026-11-27 (Blocker): land() had no production caller, so worktrees never landed (D7, D22, D40).
describe("land is wired into the hook path", () => {
  test("a push to main from a worktree, seen by decide(), lands the worktree", async () => {
    const { decide, closeCore } = await import("../src/core.ts")
    const w = worktreeNew(db, { session: "s1", repoCwd: main, name: "wired" })
    const sha = pushFrom(w.path)
    const ev = (over: Record<string, unknown>) =>
      ({ v: 1, tool: "claude", session: "s1", parentSession: null, cwd: w.path, time: Date.now(), ...over }) as never
    await decide(ev({ event: "prompt", prompt: "ship it" }))
    await decide(ev({ event: "tool.after", toolName: "shell", input: { command: "git push -q origin HEAD:main", cwd: w.path }, output: "ok" }))
    closeCore()
    expect(db.query("select state from worktrees where id = ?").get(w.id)).toEqual({ state: "removed" })
    expect(git(main, "rev-parse", "HEAD")).toBe(sha)
  })
})

// Ledger audit 2026-11-28: 20 worktrees active, 3 ever landed. A worktree whose branch reached main another
// way (a merged PR, a push from elsewhere) must land on the waker's tick; an unmerged one stays.
describe("waker lands merged worktrees", () => {
  test("merged into origin/main: landed; not merged: still active", async () => {
    const { wakerTick } = await import("../src/waker/waker.ts")
    const merged = worktreeNew(db, { session: "s1", repoCwd: main, name: "merged" })
    pushFrom(merged.path) // reaches origin/main without land()
    const open = worktreeNew(db, { session: "s1", repoCwd: main, name: "open" })
    writeFileSync(join(open.path, "wip.txt"), "wip\n")
    git(open.path, "add", ".")
    git(open.path, "commit", "-q", "-m", "wip")
    const gh = async () => ({ code: 1, stdout: "", stderr: "" })
    await wakerTick(db, { gh, deliver: async () => {} } as never)
    const state = (id: string) => (db.query("select state from worktrees where id = ?").get(id) as { state: string }).state
    expect(state(merged.id)).toBe("removed")
    expect(state(open.id)).toBe("active")
  })
})

// Live 2026-11-28: four lane branches whose commits reached main as cherry-picks (re-split, with later edits on
// top) stayed active for a day and flooded every session with conflict and overlap warnings. A worktree whose
// branch has nothing missing from main (git cherry: no "+" commit) is done: the waker lands it.
test("the waker lands a worktree whose every commit is on main by patch", async () => {
  const { wakerTick } = await import("../src/waker/waker.ts")
  const w = worktreeNew(db, { session: "s1", repoCwd: main, name: "picked" })
  writeFileSync(join(w.path, "a.txt"), "a\n")
  git(w.path, "add", ".")
  git(w.path, "commit", "-q", "-m", "a")
  const a = git(w.path, "rev-parse", "HEAD")
  writeFileSync(join(w.path, "b.txt"), "b\n")
  git(w.path, "add", ".")
  git(w.path, "commit", "-q", "-m", "b")
  const b = git(w.path, "rev-parse", "HEAD")
  // main takes both by cherry-pick, with an unrelated commit between them, then edits on top
  git(main, "cherry-pick", a)
  writeFileSync(join(main, "c.txt"), "c\n")
  git(main, "add", ".")
  git(main, "commit", "-q", "-m", "c")
  git(main, "cherry-pick", b)
  git(main, "push", "-q", "origin", "main")
  const open = worktreeNew(db, { session: "s1", repoCwd: main, name: "unpicked" })
  writeFileSync(join(open.path, "d.txt"), "d\n")
  git(open.path, "add", ".")
  git(open.path, "commit", "-q", "-m", "d")
  await wakerTick(db, { gh: async () => ({ code: 1, stdout: "", stderr: "" }), deliver: async () => {} } as never)
  const state = (id: string) => (db.query("select state from worktrees where id = ?").get(id) as { state: string }).state
  expect(state(w.id)).toBe("removed")
  expect(state(open.id)).toBe("active")
})
