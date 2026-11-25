import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { command, consume, holds, isOff, requestApply } from "../src/ledger/authority.ts"
import { openLedger } from "../src/ledger/db.ts"

let dir: string
let db: Database
const T = 1_000_000

const prompt = (text: string, isRootSession = true, now = T) =>
  command(db, { channel: "prompt", session: "root", isRootSession, text, now })

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-authority-"))
  process.env.HARNESS_STATE_DIR = dir
  db = openLedger()
})

afterEach(() => {
  db.close()
  delete process.env.HARNESS_STATE_DIR
  rmSync(dir, { recursive: true, force: true })
})

describe("MERGE-OK", () => {
  test("first line in a root session grants once", () => {
    const r = prompt("MERGE-OK 42")
    expect(r.kind).toBe("grant")
    if (r.kind !== "grant") return
    expect(r.grant).toBe("merge")
    expect(holds(db, { kind: "merge", session: "root", pr: 42, now: T })).toBe(r.tokenId)
    expect(holds(db, { kind: "merge", session: "root", pr: 43, now: T })).toBeNull()
    expect(consume(db, r.tokenId, T)).toBe(true)
    expect(consume(db, r.tokenId, T)).toBe(false)
    expect(holds(db, { kind: "merge", session: "root", pr: 42, now: T })).toBeNull()
  })

  test("same text in a subagent session is none", () => {
    expect(prompt("MERGE-OK 42", false)).toEqual({ kind: "none" })
  })

  test("a substring is none", () => {
    expect(prompt("please type MERGE-OK 42")).toEqual({ kind: "none" })
  })

  test("on line 2 is none", () => {
    expect(prompt("hello\nMERGE-OK 42")).toEqual({ kind: "none" })
  })

  test("an expired token is not held", () => {
    const r = prompt("MERGE-OK 42")
    expect(r.kind).toBe("grant")
    expect(holds(db, { kind: "merge", session: "root", pr: 42, now: T + 31 * 60_000 })).toBeNull()
  })
})

describe("HARNESS-OK", () => {
  const sha = "abcdef0123456789abcdef0123456789abcdef01"
  const digest = "1a2b3c4d"

  test("wrong digest is none", () => {
    requestApply(db, { session: "root", sha, digest })
    expect(prompt("HARNESS-OK abcdef01 deadbeef")).toEqual({ kind: "none" })
  })

  test("right sha8 and digest8 of an open request grants, bound to that request", () => {
    const requestId = requestApply(db, { session: "root", sha, digest })
    const r = prompt("HARNESS-OK abcdef01 1a2b3c4d")
    expect(r.kind).toBe("grant")
    if (r.kind !== "grant") return
    expect(r.grant).toBe("harness")
    const tok = db.query("select request_id from tokens where id = ?").get(r.tokenId)
    expect(tok).toEqual({ request_id: requestId })
    expect(holds(db, { kind: "harness", session: "other", requestId, now: T })).toBe(r.tokenId)
  })

})

describe("kill switch", () => {
  test("harness off switches, harness on clears", () => {
    expect(isOff(db)).toBe(false)
    expect(prompt("harness off")).toEqual({ kind: "switch", action: "off" })
    expect(isOff(db)).toBe(true)
    expect(prompt("harness on")).toEqual({ kind: "switch", action: "on" })
    expect(isOff(db)).toBe(false)
  })
})
