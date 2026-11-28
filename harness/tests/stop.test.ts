import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { closeCore, decide } from "../src/core.ts"
import { openLedger } from "../src/ledger/db.ts"
import type { HarnessEvent } from "../src/types.ts"

let dir: string
let db: Database

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-stop-"))
  process.env.HARNESS_STATE_DIR = dir
  process.env.HARNESS_JUDGE = "fallback"
  delete process.env.HARNESS_DISABLE
  db = openLedger()
})

afterEach(() => {
  closeCore()
  db.close()
  delete process.env.HARNESS_STATE_DIR
  delete process.env.HARNESS_JUDGE
  rmSync(dir, { recursive: true, force: true })
})

const ev = (over: Partial<HarnessEvent>): HarnessEvent => ({
  v: 1,
  event: "tool.after",
  tool: "claude",
  session: "s1",
  parentSession: null,
  cwd: "/tmp",
  time: Date.now(),
  ...over,
})

const prompt = () => decide(ev({ event: "prompt", prompt: "go" }))
const shellAfter = (command: string) => decide(ev({ toolName: "shell", input: { command, cwd: "/tmp" }, output: "ok" }))
const stop = (reply: string, stopActive = false) => decide(ev({ event: "stop", reply, stopActive }))
const sendbacks = () => (db.query("select count(*) as c from journal where event = 'stop.sendback'").get() as { c: number }).c

function gitRepo(): string {
  const repo = mkdtempSync(join(tmpdir(), "harness-stop-repo-"))
  const run = (...a: string[]) => {
    const r = Bun.spawnSync(["git", ...a], { cwd: repo, stdout: "pipe", stderr: "pipe" })
    if (r.exitCode !== 0) throw new Error(r.stderr.toString())
  }
  run("init", "-q")
  run("config", "user.email", "t@t")
  run("config", "user.name", "t")
  run("config", "commit.gpgsign", "false")
  return repo
}

describe("stop-links", () => {
  test("sends back after git push when the reply has no URL, passes with one", async () => {
    await prompt()
    await shellAfter("git push origin feature")
    const bad = await stop("Pushed the branch.")
    expect(bad.outcome).toBe("deny")
    expect(bad.ruleId).toBe("stop-links")
    expect(bad.message).toContain("stop-links")

    const good = await stop("Pushed: https://github.com/o/r/pull/1")
    expect(good.outcome).toBe("allow")
  })
})

describe("stop-commit", () => {
  test("sends back for an uncommitted edited file and passes after the commit", async () => {
    const repo = gitRepo()
    try {
      const file = join(repo, "a.txt")
      writeFileSync(file, "one\n")
      await prompt()
      await decide(ev({ toolName: "write", input: { path: file, content: "one\n" }, output: "ok" }))
      const bad = await stop("Wrote the file.")
      expect(bad.outcome).toBe("deny")
      expect(bad.ruleId).toBe("stop-commit")

      Bun.spawnSync(["git", "add", "a.txt"], { cwd: repo })
      const c = Bun.spawnSync(["git", "commit", "-q", "-m", "one"], { cwd: repo, stderr: "pipe" })
      expect(c.exitCode).toBe(0)
      expect((await stop("Committed.")).outcome).toBe("allow")
    } finally {
      rmSync(repo, { recursive: true, force: true })
    }
  })

  // Seen live 2026-11-25: a worker whose contract forbids git writes was sent back to commit.
  test("a worker outside its own worktree is not asked to commit or to show a bundle", async () => {
    const repo = gitRepo()
    try {
      const file = join(repo, "a.txt")
      writeFileSync(file, "one\n")
      const w = (over: Partial<HarnessEvent>) => ev({ session: "w1", parentSession: "s1", ...over })
      await decide(w({ event: "prompt", prompt: "go" }))
      await decide(w({ toolName: "write", input: { path: file, content: "one\n" }, output: "ok" }))
      const d = await decide(w({ event: "stop", reply: "STATUS: done" }))
      expect(d.outcome).toBe("allow")
    } finally {
      rmSync(repo, { recursive: true, force: true })
    }
  })
})

describe("stop-continue", () => {
  const todos = [
    { content: "step one", status: "completed" },
    { content: "step two", status: "pending" },
  ]

  test("a pending todo and a reply with no question is sent back", async () => {
    await prompt()
    await decide(ev({ toolName: "todowrite", input: { todos }, output: "ok" }))
    const d = await stop("Finished step one.")
    expect(d.outcome).toBe("deny")
    expect(d.ruleId).toBe("stop-continue")
  })

  test("a reply that asks Alex something passes", async () => {
    await prompt()
    await decide(ev({ toolName: "todowrite", input: { todos }, output: "ok" }))
    expect((await stop("Finished step one. Should I do step two now?")).outcome).toBe("allow")
  })
})

describe("cap and repeat", () => {
  // Decided 2026-11-28 (ledger audit): one send-back per rule per turn replaces the old 5-repeat allowance.
  test("a repeated rule is sent back once, then journaled as advise and the stop goes through", async () => {
    await prompt()
    await shellAfter("git push origin feature")
    expect((await stop("Pushed.")).outcome).toBe("deny")
    const again = await stop("Pushed.")
    expect(again.outcome).toBe("allow")
    expect(sendbacks()).toBe(1)
  })

  test("stopActive with the check that fired last time does not send back twice", async () => {
    await prompt()
    await shellAfter("git push origin feature")
    expect((await stop("Pushed.")).outcome).toBe("deny")
    expect((await stop("Pushed again.", true)).outcome).toBe("allow")
    expect(sendbacks()).toBe(1)
  })
})

// Seen live 2026-11-25: stop-false-cant sent the agent back five times for passkey taps, which are Alex's.
describe("stop-false-cant", () => {
  const judged = () => {
    const r = db.query("select data_json from journal where event in ('stop','stop.sendback') order by seq desc limit 1").get() as { data_json: string }
    return JSON.parse(r.data_json).judged ?? {}
  }
  test("a passkey or sign-in step, or a turn that tried handoff, is not judged", async () => {
    await prompt()
    await decide(ev({ toolName: "mcp:browse:screenshot", input: { tab: "t" }, output: "ok" }))
    await stop("Click Sign in with passkey in the open tab, then say in.")
    expect("cant" in judged()).toBe(false)

    await prompt()
    await decide(ev({ toolName: "mcp:browse:handoff", input: { tab: "t" }, output: "client exited" }))
    await stop("The card failed, so do the step by hand.")
    expect("cant" in judged()).toBe(false)

    await prompt()
    await decide(ev({ toolName: "mcp:browse:screenshot", input: { tab: "t" }, output: "ok" }))
    await stop("Please open the settings page and change the theme yourself.")
    expect("cant" in judged()).toBe(true)
  })
})

// Seen live 2026-11-27: a scratch HTML report in the temp folder was treated as product UI.
describe("stop-ui-proof", () => {
  const write = (path: string) => decide(ev({ toolName: "write", input: { path }, output: "ok" }))
  test("a UI file in the repo needs a screenshot; a scratch file in a temp folder does not", async () => {
    await prompt()
    await write("/tmp/claude-502/proj/sess/scratchpad/report.html")
    expect((await stop("Report written.")).ruleId).not.toBe("stop-ui-proof")

    await prompt()
    await write("/home/u/repo/ui/app/app.css")
    expect((await stop("Styles changed.")).ruleId).toBe("stop-ui-proof")
  })
})

// Ledger audit 2026-11-28: stop-cleanup sent the same agent back up to 4 times in one turn (153 send-backs
// in 48 h). A rule sends back at most once a turn; after that it is journaled and the stop goes through.
describe("send-back cap", () => {
  test("the same stop rule sends back once per turn, then lets the stop through", async () => {
    process.env.HARNESS_SCRATCH_LIMIT_MB = "1"
    const { mkdtempSync, writeFileSync } = await import("node:fs")
    const scratch = mkdtempSync(join(tmpdir(), "harness-cap-"))
    try {
      writeFileSync(join(scratch, "big.bin"), Buffer.alloc(2 * 1024 * 1024, 1))
      const oc = (over: Partial<HarnessEvent>) => decide(ev({ tool: "opencode", ...over }))
      await oc({ event: "prompt", prompt: "go" })
      await oc({ toolName: "write", input: { path: join(scratch, "big.bin") }, output: "ok" })
      expect((await oc({ event: "stop", reply: "Wrote scratch." })).ruleId).toBe("stop-cleanup")
      const second = await decide(ev({ tool: "opencode", event: "stop", reply: "That folder is shared; not mine to delete." })) // OpenCode has no stop_hook_active
      expect(second.outcome).not.toBe("deny")
      expect(sendbacks()).toBe(1)
      await oc({ event: "prompt", prompt: "again" }) // a new turn may send back again
      expect((await oc({ event: "stop", reply: "Wrote scratch again." })).ruleId).toBe("stop-cleanup")
    } finally {
      rmSync(scratch, { recursive: true, force: true })
      delete process.env.HARNESS_SCRATCH_LIMIT_MB
    }
  })
})

// A slow hook that fails open was invisible: nothing recorded how long decide() took.
test("every journaled decision records how long decide() took, in ms", async () => {
  await prompt()
  await shellAfter("ls")
  const rows = db.query("select event, json_extract(data_json, '$.ms') ms from journal where event in ('prompt', 'tool.after')").all() as { event: string; ms: number | null }[]
  expect(rows.length).toBeGreaterThanOrEqual(2)
  for (const r of rows) {
    expect(typeof r.ms).toBe("number")
    expect(r.ms!).toBeGreaterThanOrEqual(0)
  }
})

// Alex 2026-11-28 ("meal piece steps instead of complete ones"): a reply that ends with a Next: plan of the
// agent's OWN work is sent back; only Alex's steps (merge, prod apply, passkey, a decision) may end a turn.
describe("stop-piecemeal", () => {
  const enforce = async () => (await import("../src/ledger/registry.ts")).setMode(db, "stop-piecemeal", "enforce")
  test("a Next: plan of the agent's own steps is sent back once when enforced", async () => {
    await prompt()
    await enforce()
    const d = await stop("MOP #826 is open.\n\nNext: I update the runbook, then I validate hypercare and write the log.")
    expect(d.ruleId).toBe("stop-piecemeal")
    expect(d.message).toMatch(/do (these|them) now/i)
  })
  test("a Next: step that is only Alex's ends the turn", async () => {
    await prompt()
    await enforce()
    const d = await stop("Everything is built and verified.\n\nNext: you merge #826 (MERGE-OK 826).")
    expect(d.ruleId).not.toBe("stop-piecemeal")
  })
  test("it starts in advise: journaled, not sent back", async () => {
    await prompt()
    const d = await stop("Done with step one.\n\nNext: I fix the tests and open the PR.")
    expect(d.ruleId).not.toBe("stop-piecemeal")
    expect(db.query("select count(*) n from journal where rule_id = 'stop-piecemeal' and outcome = 'advise'").get()).toEqual({ n: 1 })
  })
})

// Alex 2026-11-28 (burn -n: 51 leftover agent processes, 1.7 GB): agents must watch CPU, memory and leftover
// processes, not only disk. stop-resources lists this session's processes over the limits with kill lines.
describe("stop-resources", () => {
  test("a registered process past the idle limit is named with its kill line when enforced", async () => {
    process.env.HARNESS_RESOURCE_IDLE_MIN = "0"
    const { setMode } = await import("../src/ledger/registry.ts")
    const p = Bun.spawn(["sleep", "300"], { stdio: ["ignore", "ignore", "ignore"] })
    try {
      await prompt()
      setMode(db, "stop-resources", "enforce")
      await decide(ev({ toolName: "shell", input: { command: "sleep 300 & echo PID: $!", cwd: "/tmp" }, output: `PID: ${p.pid}` }))
      const d = await stop("Finished.")
      expect(d.ruleId).toBe("stop-resources")
      expect(d.message).toContain(`kill ${p.pid}`)
    } finally {
      p.kill("SIGKILL")
      delete process.env.HARNESS_RESOURCE_IDLE_MIN
    }
  })
})
