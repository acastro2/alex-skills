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

  // Seen live 2026-11-25: after an apply, the next review diffed only against main's merge base, which hid
  // every commit since the installed sha. It must diff against what is installed now.
  test("after an apply, the next review diffs against the installed sha", () => {
    const r1 = requestAndGrant(sha1)
    expect(apply(db, { requestId: r1.requestId })).toMatchObject({ ok: true })
    const sha3 = commit({ "harness/src/note.txt": "three\n" })
    const r3 = request(db, { session: "root", sha: sha3, cwd: repo })
    expect(r3.review).toContain(`Base: ${sha1}`)
    expect(r3.review).toContain("-one")
    expect(r3.review).toContain("+three")
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

// Review 2026-11-27 (Blocker): the review was never journaled, so the page showed "No review text" and Alex
// approved a digest he could not check. The page tap must also carry the digest it approves.
describe("review binding", () => {
  test("the review text is journaled under review_seq and its sha256 is the request digest", () => {
    const r = request(db, { session: "root", sha: sha1, cwd: repo })
    const row = db
      .query("select j.prompt_text as review, q.digest from requests q join journal j on j.seq = q.review_seq where q.id = ?")
      .get(r.requestId) as { review: string | null; digest: string }
    expect(row.review).toBe(r.review)
    expect(createHash("sha256").update(row.review!).digest("hex")).toBe(row.digest)
  })

  test("a page apply tap must name the digest of the review shown; a wrong one is refused", async () => {
    const { runAction } = await import("../src/serve/actions.ts")
    const r = request(db, { session: "root", sha: sha1, cwd: repo })
    const digest = (db.query("select digest from requests where id = ?").get(r.requestId) as { digest: string }).digest
    expect((await runAction(db, "apply", { request_id: r.requestId, digest: "0".repeat(64) })).status).not.toBe(200)
    expect((await runAction(db, "apply", { request_id: r.requestId })).status).not.toBe(200)
    expect((await runAction(db, "apply", { request_id: r.requestId, digest })).status).toBe(200)
  })
})

// Ledger audit 2026-11-28: the MCP server and the hooks seed() on start and raised rule modes in the shared
// ledger, so push-gate and main-checkout-write enforced live with no apply (D71). Only apply may raise a mode.
describe("only apply changes a stored rule mode", () => {
  const stored = () => db.query("select mode, default_mode from rules where id = 'push-gate'").get()
  test("decide() and the MCP server leave an existing rules row alone; apply raises it", async () => {
    const { seed } = await import("../src/ledger/registry.ts")
    seed(db)
    db.query("update rules set mode = 'advise', default_mode = 'advise' where id = 'push-gate'").run()

    const { decide, closeCore } = await import("../src/core.ts")
    await decide({ v: 1, event: "prompt", tool: "claude", session: "s1", parentSession: null, cwd: repo, time: Date.now(), prompt: "hi" })
    closeCore()
    expect(stored()).toEqual({ mode: "advise", default_mode: "advise" })

    const mcp = Bun.spawn([process.execPath, join(ROOT, "src/mcp/agent.ts")], { stdin: "pipe", stdout: "pipe", stderr: "pipe", env: process.env })
    await Bun.sleep(1500)
    mcp.kill()
    await mcp.exited
    expect(stored()).toEqual({ mode: "advise", default_mode: "advise" })

    const r = requestAndGrant(sha1)
    expect(stored()).toEqual({ mode: "advise", default_mode: "advise" }) // a request changes nothing
    expect(apply(db, { requestId: r.requestId, cwd: repo })).toMatchObject({ ok: true })
    expect(stored()).toEqual({ mode: "enforce", default_mode: "enforce" })
  }, 30_000)
})

// Ledger audit 2026-11-28: 9 requests stayed open for days; a newer one never closed the old ones.
test("a newer request for the same repo supersedes the older open ones, journaled", () => {
  const r1 = request(db, { session: "root", sha: sha1, cwd: repo })
  const r2 = request(db, { session: "root", sha: sha2, cwd: repo })
  const st = (id: string) => (db.query("select state from requests where id = ?").get(id) as { state: string }).state
  expect(st(r1.requestId)).toBe("superseded")
  expect(st(r2.requestId)).toBe("open")
  const j = db.query("select data_json from journal where event = 'harness.superseded'").all() as { data_json: string }[]
  expect(j.map((x) => JSON.parse(x.data_json))).toEqual([expect.objectContaining({ request_id: r1.requestId, by: r2.requestId })])
})
