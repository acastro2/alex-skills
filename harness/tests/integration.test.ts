// Cross-lane behaviour wired into the core (spec: Phase 3, Phase 5, D17, D24, D37, D41-D47, D29).
// Each test enters through decide() or startJobs(), the same entry the adapters and `harness serve` use.
import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { closeCore, decide } from "../src/core.ts"
import { startJobs, requestRun } from "../src/jobs/jobs.ts"
import { openLedger } from "../src/ledger/db.ts"
import { seed, setMode } from "../src/ledger/registry.ts"
import { verify } from "../src/proof/verify.ts"
import { workstreamUpdate } from "../src/worktree/lifecycle.ts"
import type { HarnessEvent } from "../src/types.ts"

let dir: string
let db: Database
let home: string | undefined

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-int-"))
  process.env.HARNESS_STATE_DIR = join(dir, "state")
  process.env.HARNESS_JUDGE = "fallback"
  delete process.env.HARNESS_DISABLE
  home = process.env.HOME
  db = openLedger()
  seed(db) // decide() seeds too; tests flip modes before their first event
})

afterEach(() => {
  closeCore()
  db.close()
  if (home === undefined) delete process.env.HOME
  else process.env.HOME = home
  delete process.env.HARNESS_STATE_DIR
  delete process.env.HARNESS_JUDGE
  rmSync(dir, { recursive: true, force: true })
})

const ev = (over: Partial<HarnessEvent>): HarnessEvent => ({
  v: 1,
  event: "tool.before",
  tool: "claude",
  session: "s1",
  parentSession: null,
  cwd: dir,
  time: Date.now(),
  ...over,
})

const git = (cwd: string, ...args: string[]) => {
  const r = Bun.spawnSync(["git", "-C", cwd, "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", ...args], { stdout: "pipe", stderr: "pipe" })
  if (r.exitCode !== 0) throw new Error(`git ${args.join(" ")}: ${r.stderr}`)
  return r.stdout.toString().trim()
}

// A repo on main with one commit that holds a code file and a test file.
function repo(name = "repo"): string {
  const r = join(dir, name)
  mkdirSync(join(r, "tests"), { recursive: true })
  Bun.spawnSync(["git", "init", "-q", "-b", "main", r])
  writeFileSync(join(r, "a.ts"), "export const a = 1\n")
  writeFileSync(join(r, "tests", "a.test.ts"), "// test\n")
  git(r, "add", ".")
  git(r, "commit", "-qm", "init")
  return r
}

const rows = (sql: string, ...p: (string | number)[]) => db.query(sql).all(...p) as Record<string, any>[]
const waitFor = async (check: () => boolean, ms: number) => {
  const end = Date.now() + ms
  while (Date.now() < end) {
    if (check()) return true
    await Bun.sleep(100)
  }
  return check()
}

describe("MCP session binding", () => {
  test("Claude: a harness MCP call gets the hook's session in its input", async () => {
    const d = await decide(ev({ toolName: "mcp:harness:merge_pr", input: { repo: "o/r", pr: 3, session: "someone-else" } }))
    expect(d.outcome).toBe("modify")
    expect(d.input).toEqual({ repo: "o/r", pr: 3, session: "s1" })
  })

  test("OpenCode: a session that is not the caller's is denied, the caller's own passes", async () => {
    const bad = await decide(ev({ tool: "opencode", toolName: "mcp:harness:merge_pr", input: { repo: "o/r", pr: 3, session: "x" } }))
    expect(bad.outcome).toBe("deny")
    expect(bad.message).toBe('Pass session: "s1" to this harness tool.')
    const ok = await decide(ev({ tool: "opencode", toolName: "mcp:harness:merge_pr", input: { repo: "o/r", pr: 3, session: "s1" } }))
    expect(ok.outcome).toBe("allow")
  })
})

describe("push-gate", () => {
  test("git push with no bundle is allowed and journaled as advise by default, denied when enforced", async () => {
    const r = repo()
    const push = () => decide(ev({ toolName: "shell", input: { command: "git push origin main", cwd: r }, cwd: r }))
    expect((await push()).outcome).toBe("allow")
    expect(rows("select outcome, reason from journal where rule_id = 'push-gate'")).toEqual([
      { outcome: "advise", reason: expect.stringContaining("Verify first") },
    ])

    setMode(db, "push-gate", "enforce")
    const d = await push()
    expect(d.outcome).toBe("deny")
    expect(d.ruleId).toBe("push-gate")
  })
})

describe("worker lifecycle", () => {
  const spawnInput = (cwd: string) => ({
    prompt: "Fix a.ts\nACCEPTANCE:\n- a passes → `true`\n- `test -f a.ts`\n\nRETURN: proof",
    model: "cursor/claude-haiku-5-5",
    agent: "general",
    cwd,
  })

  test("a spawn inserts a workers row with the acceptance commands, base sha and test hashes", async () => {
    const r = repo()
    const d = await decide(ev({ toolName: "subagent", input: spawnInput(r), cwd: r }))
    expect(d.outcome).toBe("modify") // the contract is appended, the spawn is allowed
    const [w] = rows("select * from workers")
    expect(w.parent_session_id).toBe("s1")
    expect(w.base_sha).toBe(git(r, "rev-parse", "HEAD"))
    expect(JSON.parse(w.acceptance)).toEqual(["true", "test -f a.ts"])
    expect(Object.keys(JSON.parse(w.test_hashes))).toEqual(["tests/a.test.ts"])
    expect(w.model).toBe("cursor/claude-haiku-5-5")
  })

  test("tool.after returns the background context within 2 s, and worker.verified follows", async () => {
    const r = repo()
    await decide(ev({ toolName: "subagent", input: spawnInput(r), cwd: r }))
    const t0 = Date.now()
    const d = await decide(ev({ event: "tool.after", toolName: "subagent", input: spawnInput(r), output: "done", cwd: r }))
    expect(Date.now() - t0).toBeLessThan(2000)
    const [w] = rows("select id from workers")
    expect(d.outcome).toBe("modify")
    expect(d.context).toBe(`Harness: verifying this worker's result in the background (worker ${w.id}). The verdict arrives as a message.`)

    expect(await waitFor(() => rows("select 1 from journal where event = 'worker.verified'").length > 0, 20_000)).toBe(true)
    const [v] = rows("select session_id, outcome, data_json from journal where event = 'worker.verified'")
    expect(v.session_id).toBe("s1")
    expect(v.outcome).toBe("green")
    expect(JSON.parse(v.data_json).workerId).toBe(w.id)
    expect(rows("select verdict from bundles where worker_id = ?", w.id)).toEqual([{ verdict: "green" }])
  }, 30_000)
})

describe("main-checkout-write", () => {
  test("a write in the main checkout is denied only when the rule is enforced; a linked worktree is free", async () => {
    const r = repo()
    const file = join(r, "a.ts")
    const edit = (path: string) => decide(ev({ toolName: "edit", input: { path }, cwd: r }))
    const commit = () => decide(ev({ toolName: "shell", input: { command: "git commit -am x", cwd: r }, cwd: r }))

    setMode(db, "main-checkout-write", "advise")
    expect((await edit(file)).outcome).toBe("allow")
    expect((await commit()).outcome).toBe("allow")
    expect(rows("select outcome from journal where rule_id = 'main-checkout-write'")).toHaveLength(2)

    setMode(db, "main-checkout-write", "enforce")
    const d = await edit(file)
    expect(d.outcome).toBe("deny")
    expect(d.message).toBe("Work in a worktree: call `worktree_new`. It records the pointer for other agents.")
    expect((await commit()).outcome).toBe("deny")

    const wt = join(dir, "linked")
    git(r, "worktree", "add", "-q", "-b", "feat", wt)
    expect((await edit(join(wt, "a.ts"))).outcome).toBe("allow")
  })
})

describe("lazy worktree registration (D37)", () => {
  test("the first write in a hand-made worktree under ~/.worktrees records it, once", async () => {
    process.env.HOME = join(dir, "home")
    const r = repo()
    const wt = join(process.env.HOME, ".worktrees", "repo", "feat")
    mkdirSync(join(wt, ".."), { recursive: true })
    git(r, "worktree", "add", "-q", "-b", "feat", wt)
    const write = () => decide(ev({ toolName: "write", input: { path: join(wt, "new.ts"), content: "x" }, cwd: wt }))
    expect((await write()).outcome).toBe("allow")
    expect((await write()).outcome).toBe("allow")
    expect(rows("select path, branch, state from worktrees")).toEqual([{ path: wt, branch: "feat", state: "active" }])
  })
})

describe("stop-proof (D47)", () => {
  test("a done claim after a code edit is sent back until a green bundle exists this turn", async () => {
    const r = repo()
    await decide(ev({ event: "prompt", prompt: "change a.ts", cwd: r }))
    writeFileSync(join(r, "a.ts"), "export const a = 2\n")
    git(r, "commit", "-qam", "change a")
    await decide(ev({ event: "tool.after", toolName: "edit", input: { path: join(r, "a.ts") }, output: "ok", cwd: r }))

    const quiet = await decide(ev({ event: "stop", reply: "Changed a.ts.", cwd: r }))
    expect(quiet.outcome).toBe("allow")

    const bad = await decide(ev({ event: "stop", reply: "It is done and works.", cwd: r }))
    expect(bad.outcome).toBe("deny")
    expect(bad.ruleId).toBe("stop-proof")
    expect(bad.message).toContain("You said it is done, but this turn has no green proof bundle. Call the `verify` tool with the commands that prove it.")

    const b = await verify(db, { session: "s1", cwd: r, commands: ["true"] })
    expect(b.verdict).toBe("green")
    const good = await decide(ev({ event: "stop", reply: "It is done and works.", cwd: r }))
    expect(good.outcome).toBe("allow")
  })
})

describe("stop-handoff (D6, D38)", () => {
  test("a commit after the workstream entry was updated sends the owner back until it updates", async () => {
    const r = repo()
    await decide(ev({ event: "prompt", prompt: "work", cwd: r }))
    db.query("insert into workstreams(id, owner_session_id, repo, title, state, updated_at) values('w1', 's1', null, 't', 'active', ?)").run(Date.now() - 60_000)
    await decide(ev({ event: "tool.after", toolName: "shell", input: { command: "git commit -m x", cwd: r }, output: "ok", cwd: r, time: Date.now() - 1000 }))

    const bad = await decide(ev({ event: "stop", reply: "Committed.", cwd: r }))
    expect(bad.outcome).toBe("deny")
    expect(bad.ruleId).toBe("stop-handoff")
    expect(bad.message).toContain("Update your workstream entry with `workstream_update`: state and next steps.")

    workstreamUpdate(db, { session: "s1", state: "active" })
    const good = await decide(ev({ event: "stop", reply: "Committed.", cwd: r }))
    expect(good.outcome).toBe("allow")
  })
})

describe("jobs_status and job_run_now", () => {
  test("requestRun is picked up by a running startJobs and runs the job once", async () => {
    let ran = 0
    const jobs = startJobs(db, { jobs: [{ name: "probe", schedule: "0 0 1 1 *", run: async () => (++ran, "ok: probe") }], pollMs: 100 })
    try {
      expect(requestRun(db, "probe")).toEqual({ requested: "probe" })
      expect(await waitFor(() => ran === 1, 15_000)).toBe(true)
      await Bun.sleep(400)
      expect(ran).toBe(1)
      expect(jobs.status().find((j) => j.name === "probe")?.last_result).toBe("ok: probe")
      expect(() => requestRun(db, "nope")).toThrow("unknown job: nope")
    } finally {
      jobs.stop()
    }
  }, 20_000)
})
