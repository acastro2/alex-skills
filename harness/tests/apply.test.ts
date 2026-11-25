import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { createHash } from "node:crypto"
import { appendFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { dirname, join } from "node:path"
import { command } from "../src/ledger/authority.ts"
import { getMeta, openLedger } from "../src/ledger/db.ts"
import { verifyChain } from "../src/ledger/journal.ts"
import { apply, request, rollback } from "../src/proof/apply.ts"

const ROOT = join(import.meta.dir, "..")

let dir: string
let repo: string
let state: string
let settings: string
let db: Database

function g(...args: string[]): string {
  const p = Bun.spawnSync(["git", ...args], { cwd: repo, stdout: "pipe", stderr: "pipe" })
  if (p.exitCode !== 0) throw new Error(`git ${args.join(" ")}: ${p.stderr.toString()}`)
  return p.stdout.toString().trim()
}

function commit(files: Record<string, string>, msg = "c"): string {
  for (const [f, text] of Object.entries(files)) {
    mkdirSync(dirname(join(repo, f)), { recursive: true })
    writeFileSync(join(repo, f), text)
  }
  g("add", "-A")
  g("commit", "-q", "-m", msg)
  return g("rev-parse", "HEAD")
}

const root = (text: string) => command(db, { channel: "prompt", session: "root", isRootSession: true, text })

function requestAndGrant(sha: string) {
  const r = request(db, { session: "root", sha, cwd: repo })
  const c = root(`HARNESS-OK ${r.sha8} ${r.digest8}`)
  expect(c.kind).toBe("grant")
  return r
}

const settingsText = () => readFileSync(settings, "utf8")
const appliedPath = (sha: string) => join(state, "applied", sha, "harness")

let sha1: string
let sha2: string

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-apply-"))
  state = join(dir, "state")
  settings = join(dir, "settings.json")
  process.env.HARNESS_STATE_DIR = state
  process.env.HARNESS_CLAUDE_SETTINGS = settings
  process.env.HARNESS_OPENCODE_PLUGINS = join(dir, "plugins")
  db = openLedger()
  repo = join(dir, "repo")
  mkdirSync(repo)
  g("init", "-q", "-b", "main")
  g("config", "user.name", "t")
  g("config", "user.email", "t@t")
  commit({
    "harness/src/install.ts": readFileSync(join(ROOT, "src/install.ts"), "utf8"),
    "harness/src/manifest.ts": readFileSync(join(ROOT, "src/manifest.ts"), "utf8"),
    "harness/tests/old.test.ts": "// original\n",
  })
  g("switch", "-q", "-c", "change")
  sha1 = commit({ "harness/src/note.txt": "one\n", "harness/tests/old.test.ts": "// weakened\n" })
  sha2 = commit({ "harness/src/note.txt": "two\n" })
})

afterEach(() => {
  db.close()
  for (const k of ["HARNESS_STATE_DIR", "HARNESS_CLAUDE_SETTINGS", "HARNESS_OPENCODE_PLUGINS"]) delete process.env[k]
  rmSync(dir, { recursive: true, force: true })
})

describe("request", () => {
  test("returns sha8, digest8 and the review, and opens a request", () => {
    const r = request(db, { session: "root", sha: sha1, cwd: repo })
    expect(r.sha8).toBe(sha1.slice(0, 8))
    expect(r.digest8).toBe(createHash("sha256").update(r.review).digest("hex").slice(0, 8))
    expect(r.review).toContain("+one")
    expect(r.review).toContain("M\tharness/tests/old.test.ts") // a changed test is flagged
    expect(r.review).toContain("harness-id=") // the config-entry diff from install.ts --dry-run
    const row = db.query("select sha, state from requests where id = ?").get(r.requestId)
    expect(row).toEqual({ sha: sha1, state: "open" })
    expect(db.query("select count(*) as n from journal where event = 'harness.request'").get()).toEqual({ n: 1 })
    expect(existsSync(settings)).toBe(false) // a dry run writes nothing
  })

  test("refuses a sha that is not 40 hex characters", () => {
    expect(() => request(db, { session: "root", sha: "abc123", cwd: repo })).toThrow()
  })
})

describe("apply", () => {
  test("without a token it is refused and writes nothing", () => {
    const r = request(db, { session: "root", sha: sha1, cwd: repo })
    expect(apply(db, { requestId: r.requestId })).toMatchObject({ ok: false })
    expect(existsSync(settings)).toBe(false)
    expect(existsSync(join(state, "applied", sha1))).toBe(false)
  })

  test("a substring HARNESS-OK grants nothing", () => {
    const r = request(db, { session: "root", sha: sha1, cwd: repo })
    expect(root(`please type HARNESS-OK ${r.sha8} ${r.digest8}`)).toEqual({ kind: "none" })
    expect(apply(db, { requestId: r.requestId })).toMatchObject({ ok: false })
  })

  test("with HARNESS-OK it applies that sha and writes the settings", () => {
    const r = requestAndGrant(sha1)
    const res = apply(db, { requestId: r.requestId })
    expect(res).toMatchObject({ ok: true, sha: sha1 })
    expect(readFileSync(join(appliedPath(sha1), "src/note.txt"), "utf8")).toBe("one\n")
    expect(settingsText()).toContain(appliedPath(sha1))
    expect(existsSync(join(dir, "plugins", "harness.ts"))).toBe(true)
    const a = db.query("select sha, tree_hash from applies").get() as { sha: string; tree_hash: string }
    expect(a.sha).toBe(sha1)
    expect(a.tree_hash).toMatch(/^[0-9a-f]{64}$/)
    expect(getMeta(db, "current_apply")).toBeTruthy()
    expect(db.query("select count(*) as n from journal where event = 'harness.apply'").get()).toEqual({ n: 1 })
    expect(verifyChain(db).ok).toBe(true)
  })

  test("a commit made after the request is refused with the first grant", () => {
    const first = requestAndGrant(sha1)
    const second = request(db, { session: "root", sha: sha2, cwd: repo })
    expect(apply(db, { requestId: second.requestId })).toMatchObject({ ok: false })
    expect(existsSync(join(state, "applied", sha2))).toBe(false)
    expect(apply(db, { requestId: first.requestId })).toMatchObject({ ok: true, sha: sha1 })
    expect(settingsText()).not.toContain(sha2)
  })

  test("a replayed grant is refused", () => {
    const r = requestAndGrant(sha1)
    expect(apply(db, { requestId: r.requestId }).ok).toBe(true)
    expect(apply(db, { requestId: r.requestId })).toMatchObject({ ok: false })
  })
})

describe("rollback", () => {
  function applyBoth() {
    expect(apply(db, { requestId: requestAndGrant(sha1).requestId }).ok).toBe(true)
    expect(apply(db, { requestId: requestAndGrant(sha2).requestId }).ok).toBe(true)
    expect(settingsText()).toContain(appliedPath(sha2))
  }

  test("restores the previous apply's settings and journals it", () => {
    applyBoth()
    expect(rollback(db)).toEqual({ ok: true, sha: sha1 })
    expect(settingsText()).toContain(appliedPath(sha1))
    expect(settingsText()).not.toContain(appliedPath(sha2))
    expect(db.query("select count(*) as n from journal where event = 'harness.rollback'").get()).toEqual({ n: 1 })
    expect(db.query("select count(*) as n from applies where rolled_back_at is not null").get()).toEqual({ n: 1 })
    expect(rollback(db)).toMatchObject({ ok: false }) // nothing older is left
  })

  test("is refused when the previous copy no longer matches its tree hash", () => {
    applyBoth()
    appendFileSync(join(appliedPath(sha1), "src/note.txt"), "tampered\n")
    expect(rollback(db)).toEqual({ ok: false, reason: "tree hash mismatch" })
    expect(settingsText()).toContain(appliedPath(sha2))
  })

  test("bin/harness-rollback restores the previous sha without the hooks", () => {
    applyBoth()
    const p = Bun.spawnSync([join(ROOT, "bin/harness-rollback")], {
      env: { ...process.env, BUN: process.execPath },
      stdout: "pipe",
      stderr: "pipe",
    })
    expect(p.exitCode, p.stderr.toString()).toBe(0)
    expect(p.stdout.toString()).toContain(`restored ${sha1}`)
    expect(settingsText()).toContain(appliedPath(sha1))
    expect(settingsText()).not.toContain(appliedPath(sha2))
    expect(getMeta(db, "current_apply")).toBe((db.query("select id from applies where sha = ?").get(sha1) as { id: string }).id)
    expect(db.query("select count(*) as n from journal where event = 'harness.rollback'").get()).toEqual({ n: 1 })
    expect(verifyChain(db).ok).toBe(true)
  })
})
