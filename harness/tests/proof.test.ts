import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { dirname, join } from "node:path"
import { openLedger } from "../src/ledger/db.ts"
import { bundleFor, prBody, recompute } from "../src/proof/bundle.ts"
import { pushGate } from "../src/proof/gate.ts"
import { verify } from "../src/proof/verify.ts"

let dir: string
let repo: string
let db: Database

function g(cwd: string, ...args: string[]): string {
  const p = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" })
  if (p.exitCode !== 0) throw new Error(`git ${args.join(" ")}: ${p.stderr.toString()}`)
  return p.stdout.toString().trim()
}

function commit(files: Record<string, string>, msg = "c"): string {
  for (const [f, text] of Object.entries(files)) {
    mkdirSync(dirname(join(repo, f)), { recursive: true })
    writeFileSync(join(repo, f), text)
  }
  g(repo, "add", "-A")
  g(repo, "commit", "-q", "-m", msg)
  return g(repo, "rev-parse", "HEAD")
}

const ver = (o: Partial<Parameters<typeof verify>[1]> & { commands: string[] }) => verify(db, { session: "s1", cwd: repo, ...o })

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-proof-"))
  process.env.HARNESS_STATE_DIR = join(dir, "state")
  db = openLedger()
  repo = join(dir, "repo")
  mkdirSync(repo)
  g(repo, "init", "-q", "-b", "main")
  g(repo, "config", "user.name", "t")
  g(repo, "config", "user.email", "t@t")
})

afterEach(() => {
  db.close()
  delete process.env.HARNESS_STATE_DIR
  rmSync(dir, { recursive: true, force: true })
})

describe("verify", () => {
  test("a passing command gives a green bundle and a git note", async () => {
    const head = commit({ "a.txt": "a" })
    const b = await ver({ commands: ["echo ok"] })
    expect(b.verdict).toBe("green")
    expect(b.headSha).toBe(head)
    expect(b.verified.reruns).toEqual([{ command: "echo ok", exit: 0, tail: "ok" }])
    expect(g(repo, "notes", "--ref=harness", "show", "HEAD")).toBe(`Verified: green ${b.id}`)
    expect(bundleFor(db, head)?.id).toBe(b.id)
    expect(g(repo, "worktree", "list").split("\n")).toHaveLength(1)
  })

  test("a failing command gives red", async () => {
    commit({ "a.txt": "a" })
    const b = await ver({ commands: ["echo boom; exit 3"] })
    expect(b.verdict).toBe("red")
    expect(b.verified.reruns[0]).toMatchObject({ exit: 3, tail: "boom" })
    expect(g(repo, "notes", "--ref=harness", "show", "HEAD")).toStartWith("Verified: red ")
  })

  test("an uncommitted file gives partial and runs nothing", async () => {
    commit({ "a.txt": "a" })
    writeFileSync(join(repo, "stray.txt"), "x")
    const b = await ver({ commands: ["touch ran-marker"] })
    expect(b.verdict).toBe("partial")
    expect(b.verified).toMatchObject({ clean: false, reason: "uncommitted changes", reruns: [] })
  })

  test("a test file the worker edited is restored from base in the re-run", async () => {
    const base = commit({ "code.txt": "right", "tests/t.sh": "grep -q right code.txt\n" })
    commit({ "tests/t.sh": "grep -q WRONGMARK code.txt\n" }, "worker weakens the test")
    const kept = await ver({ commands: ["sh tests/t.sh"] })
    expect(kept.verdict).toBe("red") // the worker's version fails
    const b = await ver({ commands: ["sh tests/t.sh"], baseSha: base, testGlobs: ["tests/**"] })
    expect(b.verdict).toBe("green") // only the base version passes
    expect(b.did.tests_changed).toEqual(["tests/t.sh"])
    expect(g(repo, "status", "--porcelain")).toBe("") // the repo itself stays untouched
  })

  test("a change to *.md files only is green: docs only, with no re-run", async () => {
    const base = commit({ "code.txt": "x" })
    commit({ "README.md": "docs" })
    const b = await ver({ commands: ["exit 1"], baseSha: base })
    expect(b.verdict).toBe("green")
    expect(b.verified).toMatchObject({ reason: "docs only", reruns: [] })
  })

  test("the repo's harness.verify script is always added", async () => {
    commit({ "package.json": JSON.stringify({ scripts: { "harness.verify": "exit 4" } }) })
    const b = await ver({ commands: ["true"] })
    expect(b.verdict).toBe("red")
    expect(b.verified.reruns.map((r) => r.exit)).toEqual([0, 4])
  })

  test("prBody has the head SHA, verdict, table, screenshots, bundle ID and gaps", async () => {
    const head = commit({ "a.txt": "a" })
    const b = await ver({ commands: ["echo ok"], uiProof: ["shot.png"], knownGaps: "none yet" })
    const body = prBody(b)
    for (const part of [`Head SHA: ${head}`, "Verdict: green", "| `echo ok` | 0 |", "Screenshots: shot.png", `Bundle: ${b.id}`, "Known gaps: none yet"])
      expect(body).toContain(part)
  })
})

describe("pushGate", () => {
  const push = (command: string) => pushGate(db, { cwd: repo, command })
  const denied = { ruleId: "push-gate", message: expect.stringContaining("Verify first") }

  beforeEach(() => {
    commit({ "a.txt": "a" })
    g(repo, "switch", "-q", "-c", "feature")
  })

  test("denies a push with no bundle", () => {
    commit({ "b.txt": "b" })
    expect(push("git push origin feature")).toMatchObject(denied)
  })

  test("a command that is not a push is none", () => {
    commit({ "b.txt": "b" })
    expect(push("git status")).toBeNull()
  })

  test("allows a push that changes only *.md files", () => {
    commit({ "README.md": "docs" })
    expect(push("git push origin feature")).toBeNull()
  })

  test("denies a red bundle to main and allows it to a feature branch", async () => {
    commit({ "b.txt": "b" })
    expect((await ver({ commands: ["exit 1"] })).verdict).toBe("red")
    expect(push("git push origin HEAD:main")).toMatchObject(denied)
    expect(push("git push origin feature:master")).toMatchObject(denied)
    expect(push("git push origin feature")).toBeNull()
    expect(push("git push")).toBeNull()
  })

  test("allows a green bundle to main", async () => {
    commit({ "b.txt": "b" })
    expect((await ver({ commands: ["true"] })).verdict).toBe("green")
    expect(push("git push origin main")).toBeNull()
  })
})

describe("recompute", () => {
  test("is true for a fresh bundle and false once a row is hand-edited", async () => {
    commit({ "a.txt": "a" })
    const b = await ver({ commands: ["exit 1"] })
    expect(recompute(db, b.id)).toBe(true)
    db.query("update bundles set verdict = 'green' where id = ?").run(b.id)
    expect(recompute(db, b.id)).toBe(false)
  })

  test("is false for a hand-edited detail field", async () => {
    commit({ "a.txt": "a" })
    const b = await ver({ commands: ["true"] })
    db.query("update bundles set known_gaps = 'nothing' where id = ?").run(b.id)
    expect(recompute(db, b.id)).toBe(false)
  })
})
