// Review 2026-11-27 (Blocker): a token row written behind the guard's back was usable and invisible (D70).
import { afterEach, beforeEach, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { command, holds } from "../src/ledger/authority.ts"
import { openLedger } from "../src/ledger/db.ts"
import { upsertSession } from "../src/ledger/journal.ts"
import { integrity } from "../src/ledger/integrity.ts"

let dir: string
let db: Database
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-integrity-"))
  process.env.HARNESS_STATE_DIR = dir
  db = openLedger()
})
afterEach(() => {
  db.close()
  delete process.env.HARNESS_STATE_DIR
  rmSync(dir, { recursive: true, force: true })
})

test("a forged token is not honoured and shows as unmatched; a real grant does not", () => {
  const now = Date.now()
  // A real grant goes through command(), which journals it.
  const real = command(db, { channel: "prompt", session: "s1", isRootSession: true, text: "MERGE-OK 7", now })
  expect(real.kind).toBe("grant")
  expect(holds(db, { kind: "merge", session: "s1", pr: 7, now })).not.toBeNull()
  upsertSession(db, { id: "s2", tool: "unknown" })
  // A forged one is a bare insert with a grant_seq that points at no grant row.
  db.query("insert into tokens(id, kind, session_id, grant_seq, request_id, pr, expires_at) values('FORGED', 'merge', 's2', 1, null, 9, ?)").run(now + 60_000)
  expect(holds(db, { kind: "merge", session: "s2", pr: 9, now })).toBeNull()
  const r = integrity(db)
  expect(r.unmatchedTokens).toEqual(["FORGED"])
  expect(r.ok).toBe(false)
})
