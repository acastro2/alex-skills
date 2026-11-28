import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { command } from "../src/ledger/authority.ts"
import { openLedger } from "../src/ledger/db.ts"
import { append, prune, scrub, upsertSession, verifyChain } from "../src/ledger/journal.ts"
import { markWrong, mode, seed } from "../src/ledger/registry.ts"

let dir: string
let db: Database

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-ledger-"))
  process.env.HARNESS_STATE_DIR = dir
  delete process.env.HARNESS_DISABLE
  db = openLedger()
  upsertSession(db, { id: "s1", tool: "claude" })
})

afterEach(() => {
  db.close()
  delete process.env.HARNESS_STATE_DIR
  delete process.env.HARNESS_DISABLE
  rmSync(dir, { recursive: true, force: true })
})

const names = (type: string) =>
  (db.query("select name from sqlite_master where type = ? and name not like 'sqlite_%'").all(type) as { name: string }[])
    .map((r) => r.name)
    .sort()

describe("migrations", () => {
  test("create all 17 tables and 4 views", () => {
    expect(names("table")).toEqual(
      [
        "applies", "bundles", "journal", "jobs", "page_auth", "processes", "requests", "rules", "schema_meta",
        "sessions", "snapshots", "tokens", "watches", "workers", "workstream_steps", "workstreams", "worktrees",
      ].sort(),
    )
    expect(names("view")).toEqual(["corrections", "egress", "nudges", "sendbacks"])
  })
})

describe("journal chain", () => {
  const fill = () => {
    for (let i = 1; i <= 5; i++) append(db, { session_id: "s1", event: "tool.before", reason: `r${i}`, time: i * 1000 })
  }

  test("verifies after appends", () => {
    fill()
    expect(verifyChain(db)).toEqual({ ok: true })
  })

  test("editing one row's reason breaks the chain at that seq", () => {
    fill()
    db.query("update journal set reason = 'tampered' where seq = 3").run()
    expect(verifyChain(db)).toEqual({ ok: false, badSeq: 3 })
  })

  test("prune keeps the chain verifiable from the anchor, and links to pruned rows become NULL", () => {
    const seq = command(db, { channel: "prompt", session: "s1", isRootSession: true, text: "MERGE-OK 7", now: 500 })
    expect(seq.kind).toBe("grant")
    fill()
    const before = db.query("select grant_seq from tokens").get() as { grant_seq: number | null }
    expect(before.grant_seq).not.toBeNull()

    // rows at 500, 1000, 2000 are older than 2500 ms at now = 5000 (cutoff 2500)
    expect(prune(db, 2500, 5000)).toBe(3)
    expect(verifyChain(db)).toEqual({ ok: true })
    expect((db.query("select count(*) as n from journal").get() as { n: number }).n).toBe(3)
    expect(db.query("select grant_seq from tokens").get()).toEqual({ grant_seq: null })

    // a new row chains onto what is left
    append(db, { session_id: "s1", event: "tool.before", time: 6000 })
    expect(verifyChain(db)).toEqual({ ok: true })
  })
})

describe("scrub", () => {
  test("redacts api keys and password=", () => {
    const out = scrub("use sk-abc123def456ghi789jkl012 and password=hunter2 please")
    expect(out).not.toContain("sk-abc123")
    expect(out).not.toContain("hunter2")
    expect(out).toContain("[redacted]")
  })

})

describe("registry", () => {
  beforeEach(() => seed(db))

  test("mode honors HARNESS_DISABLE", () => {
    expect(mode(db, "stop-commit")).toBe("enforce")
    process.env.HARNESS_DISABLE = "stop-links, stop-commit"
    expect(mode(db, "stop-commit")).toBe("off")
    expect(mode(db, "stop-state")).toBe("enforce")
  })

  test("mode honors the kill switch for every rule", () => {
    command(db, { channel: "page", session: "s1", isRootSession: false, text: "harness off" })
    expect(mode(db, "recursive-delete")).toBe("off")
    expect(mode(db, "egress")).toBe("off")
  })

  test("3 harness wrong in a day flips the rule to advise", () => {
    const sendback = (n: number) =>
      append(db, { session_id: "s1", event: "stop.sendback", rule_id: "stop-commit", outcome: "deny", turn: n })
    markWrong(db, sendback(1))
    markWrong(db, sendback(2))
    expect(mode(db, "stop-commit")).toBe("enforce")
    expect(markWrong(db, sendback(3))).toBe(3)
    expect(mode(db, "stop-commit")).toBe("advise")
  })
})

// Review 2026-11-27: push-gate and main-checkout-write now enforce by default (D7, Phase 3). A ledger seeded
// with the old advise default moves to enforce; a mode Alex changed himself is kept.
import { seed as seedRules, mode as ruleMode, raiseDefaults } from "../src/ledger/registry.ts"
test("a raised default upgrades rules Alex never changed, and keeps the ones he did", () => {
  const d = mkdtempSync(join(tmpdir(), "harness-seed-"))
  const db = openLedger(join(d, "ledger.db"))
  try {
    seedRules(db) // openLedger does not seed
    db.query("update rules set mode = 'advise', default_mode = 'advise' where id in ('push-gate', 'main-checkout-write')").run()
    db.query("update rules set mode = 'off' where id = 'main-checkout-write'").run() // Alex turned it off
    raiseDefaults(db) // only apply raises a default now (D71, ledger audit 2026-11-28)
    expect(ruleMode(db, "push-gate")).toBe("enforce")
    expect(ruleMode(db, "main-checkout-write")).toBe("off")
  } finally {
    db.close()
    rmSync(d, { recursive: true, force: true })
  }
})
