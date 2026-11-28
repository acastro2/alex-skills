// Alex 2026-11-28: approvals must work from the terminal too, not only the page. A human types the digest on
// the terminal (/dev/tty); an agent's shell has no terminal, and the shell guard denies the command for agents.
import { afterEach, beforeEach, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { openLedger } from "../src/ledger/db.ts"
import { requestApply } from "../src/ledger/authority.ts"
import { checkShell, type ShellCtx } from "../src/shell/rules.ts"

const ROOT = join(import.meta.dir, "..")
const CLI = join(ROOT, "src", "cli.ts")
const SHA = "519dea9c70297022979f38f677bf0dcf5ad160e8"
const DIGEST = "d3cb4adc" + "0".repeat(56)

let dir: string
let db: Database
let requestId: string
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-cli-"))
  process.env.HARNESS_STATE_DIR = dir
  db = openLedger()
  requestId = requestApply(db, { session: "root", sha: SHA, digest: DIGEST, review: "HARNESS REVIEW test" })
})
afterEach(() => {
  db.close()
  delete process.env.HARNESS_STATE_DIR
  rmSync(dir, { recursive: true, force: true })
})

const env = () => ({ ...process.env, HARNESS_STATE_DIR: dir, HARNESS_TOUCHID: "skip" }) // no Touch ID on the VM
const grants = () => db.query("select count(*) n from tokens where request_id = ? and used_at is null").get(requestId) as { n: number }

// Run with a real pseudo-terminal, the way Alex types in his own terminal. `script` gives the child a tty.
const withTty = (args: string, typed: string) =>
  Bun.spawnSync(["script", "-qec", `${process.execPath} ${CLI} ${args}`, "/dev/null"], { stdin: Buffer.from(typed), env: env(), stdout: "pipe", stderr: "pipe" })

test("`requests` lists the open request with the line to type", () => {
  const p = Bun.spawnSync([process.execPath, CLI, "requests"], { env: env(), stdout: "pipe", stderr: "pipe" })
  expect(p.exitCode).toBe(0)
  expect(p.stdout.toString()).toContain("519dea9c")
  expect(p.stdout.toString()).toContain("d3cb4adc")
})

test("approve with no terminal (an agent's shell) is refused and grants nothing", () => {
  const p = Bun.spawnSync([process.execPath, CLI, "approve", "519dea9c"], { stdin: Buffer.from("d3cb4adc\n"), env: { ...env(), HARNESS_TTY: "/nonexistent/tty" }, stdout: "pipe", stderr: "pipe" })
  expect(p.exitCode).not.toBe(0)
  expect(p.stderr.toString()).toMatch(/terminal/i)
  expect(grants().n).toBe(0)
})

test("approve on a terminal with the right digest grants, journaled as channel cli; a wrong digest grants nothing", () => {
  const wrong = withTty("approve 519dea9c", "ffffffff\n")
  expect(wrong.exitCode).not.toBe(0)
  expect(grants().n).toBe(0)
  const ok = withTty("approve 519dea9c", "d3cb4adc\n")
  expect(ok.exitCode).toBe(0)
  expect(grants().n).toBe(1)
  const g = db.query("select json_extract(data_json, '$.channel') ch from journal where event = 'grant' order by seq desc limit 1").get() as { ch: string }
  expect(g.ch).toBe("cli")
})

test("merge-ok on a terminal grants a merge token for that PR and session", () => {
  db.query("insert into sessions(id, tool, started_at) values('s9', 'claude', 0)").run()
  const ok = withTty("merge-ok 42 --session s9", "42\n")
  expect(ok.exitCode).toBe(0)
  expect(db.query("select count(*) n from tokens where kind = 'merge' and pr = 42 and session_id = 's9'").get()).toEqual({ n: 1 })
})

test("the shell guard denies the approve and merge-ok commands for agents", () => {
  const ctx: ShellCtx = { cwd: "/home/u", home: "/home/u", repoRoot: null, allowRoots: ["/tmp"], isTrackedOrIgnored: () => false, branch: "main" }
  for (const line of ["harness approve 519dea9c", "harness merge-ok 42 --session s9", `bun ${CLI} approve 519dea9c`, "bun src/cli.ts merge-ok 5"])
    expect(checkShell(line, ctx)?.ruleId).toBe("harness-self")
  expect(checkShell("harness requests", ctx)).toBeNull() // reading is fine
})
