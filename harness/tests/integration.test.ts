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
  delete process.env.HARNESS_SCRATCH_ROOTS
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
  // Review 2026-11-27: verify works live, so the gate enforces by default (Phase 3: "A push with no bundle is denied").
  test("git push with no bundle is denied by default, and only journaled when set to advise", async () => {
    const r = repo()
    const push = () => decide(ev({ toolName: "shell", input: { command: "git push origin main", cwd: r }, cwd: r }))
    const d = await push()
    expect(d.outcome).toBe("deny")
    expect(d.ruleId).toBe("push-gate")

    setMode(db, "push-gate", "advise")
    expect((await push()).outcome).toBe("allow")
    expect(rows("select outcome from journal where rule_id = 'push-gate' and outcome = 'advise'")).toHaveLength(1)
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

  // Seen live 2026-11-25: OpenCode subagents return at launch, and the verify ran before the worker did anything.
  test("a background spawn defers the verify to the worker session's stop", async () => {
    const r = repo()
    const input = { ...spawnInput(r), prompt: `${spawnInput(r).prompt}\n\nHARNESS-CONTRACT v1` } // OpenCode denies a spawn without it
    await decide(ev({ tool: "opencode", toolName: "subagent", input, cwd: r }))
    const out = "The subagent is working in the background (sessionID: ses_child1). You will receive a message."
    const d = await decide(ev({ tool: "opencode", event: "tool.after", toolName: "subagent", input, output: out, cwd: r }))
    const [w] = rows("select id, worker_session_id, last_activity from workers")
    expect(w.worker_session_id).toBe("ses_child1")
    expect(w.last_activity).toBeNull()
    expect(d.context).toContain("Its verify runs when it finishes")
    await Bun.sleep(300)
    expect(rows("select 1 from journal where event = 'worker.verified'")).toHaveLength(0)

    const child = (over: Partial<HarnessEvent>) => ev({ tool: "opencode", session: "ses_child1", parentSession: "s1", cwd: r, ...over })
    await decide(child({ event: "stop", reply: "nothing yet" })) // no tool calls this round: no verify
    expect(rows("select last_activity from workers")[0].last_activity).toBeNull()
    await decide(child({ toolName: "shell", input: { command: "ls", cwd: r } }))
    await decide(child({ event: "stop", reply: "finished" }))
    expect(await waitFor(() => rows("select 1 from journal where event = 'worker.verified'").length > 0, 20_000)).toBe(true)
    expect(rows("select verdict from bundles where worker_id = ?", w.id)).toEqual([{ verdict: "green" }])
  }, 30_000)

  // Seen live: a READ-ONLY review spawn was denied 6 times for a missing ACCEPTANCE: block.
  test("a read-only worker needs no ACCEPTANCE: block or contract", async () => {
    const d = await decide(ev({ tool: "opencode", toolName: "subagent", input: { agent: "general", model: "cursor/claude-haiku-5-5", prompt: "READ-ONLY code review. Change nothing." } }))
    expect(d.outcome).toBe("allow")
    expect(rows("select 1 from workers")).toHaveLength(0) // nothing to verify, so no verdict message later
  })

  // Seen live: a follow-up to a running worker carries a sessionID and no model, and was denied.
  test("a follow-up to a running worker is not a spawn", async () => {
    const d = await decide(ev({ tool: "opencode", toolName: "subagent", input: { agent: "general", sessionID: "ses_child1", prompt: "one more note" } }))
    expect(d.outcome).toBe("allow")
    expect(rows("select 1 from workers")).toHaveLength(0)
  })
})

// Seen live: prose criteria under ACCEPTANCE: were stored as commands and would run as shell.
describe("parseAcceptance", () => {
  test("keeps commands, drops prose", async () => {
    const { parseAcceptance } = await import("../src/policies/worker.ts")
    const prompt = [
      "ACCEPTANCE:",
      "- `cd $W && python3 scripts/check.py` exits 0.",
      "- all pass.",
      "- tests → `bun test`",
      "cd ~/x && bun test tests/a.test.ts",
      "../tool/detect --json a.css (must print [])",
      "Plus: screenshots you READ at 2560x1440.",
      "Unified diffs of every edited file.",
    ].join("\n")
    expect(parseAcceptance(prompt)).toEqual([
      "cd $W && python3 scripts/check.py",
      "bun test",
      "cd ~/x && bun test tests/a.test.ts",
      "../tool/detect --json a.css",
    ])
  })
})

describe("main-checkout-write", () => {
  // Seen live: a scratch clone under /tmp produced most of the advise rows.
  test("a clone under the temp dir is not a main checkout", async () => {
    setMode(db, "main-checkout-write", "enforce")
    const r = repo() // repo() lives under tmpdir()
    const d = await decide(ev({ toolName: "edit", input: { path: join(r, "a.ts") }, cwd: r }))
    expect(d.outcome).toBe("allow")
  })

  test("a write in the main checkout is denied only when the rule is enforced; a linked worktree is free", async () => {
    process.env.HARNESS_SCRATCH_ROOTS = "/nonexistent-scratch" // this test's repos live under tmpdir()
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

// Found live 2026-11-28 ("is it actually doing proof of work?"): no worker got a real re-run.
describe("worker proof of work, as live", () => {
  const task = (cwd: string, accept: string[]) => ({
    prompt: `Add new.txt\nACCEPTANCE:\n${accept.map((c) => `- \`${c}\``).join("\n")}\n\n`,
    model: "cursor/claude-sonnet-5-5",
    agent: "general",
    cwd,
  })

  // OpenCode: the guard makes the parent paste the full contract, whose line "Do not edit it." read as a
  // read-only worker, so no worker row was written and nothing was ever re-verified.
  test("an OpenCode spawn carrying the full contract is recorded and verified when the worker stops", async () => {
    const { CONTRACT } = await import("../src/policies/spawn.ts")
    const r = repo()
    const input = { ...task(r, ["true"]), prompt: task(r, ["true"]).prompt + CONTRACT }
    await decide(ev({ tool: "opencode", toolName: "subagent", input, cwd: r }))
    expect(rows("select 1 from workers")).toHaveLength(1)
    await decide(ev({ tool: "opencode", event: "tool.after", toolName: "subagent", input, output: "Working in the background (sessionID: ses_live1).", cwd: r }))
    const child = (over: Partial<HarnessEvent>) => ev({ tool: "opencode", session: "ses_live1", parentSession: "s1", cwd: r, ...over })
    await decide(child({ toolName: "shell", input: { command: "ls", cwd: r } }))
    await decide(child({ event: "stop", reply: "done" }))
    expect(await waitFor(() => rows("select 1 from journal where event = 'worker.verified'").length > 0, 20_000)).toBe(true)
  }, 30_000)

  // Claude Code: a background Agent (no run_in_background flag, JSON launch reply) was verified at launch, in the
  // parent's dirty checkout, so every bundle was "partial: uncommitted changes" with 0 commands run.
  test("a Claude background worker is verified at SubagentStop, in the worktree it wrote, with its uncommitted work", async () => {
    const r = repo()
    writeFileSync(join(r, "dirty.txt"), "the parent's own unfinished work\n") // the main checkout is dirty
    const w = join(dir, "wt")
    git(r, "worktree", "add", "-q", "-b", "lane", w)
    const input = task(r, ["test -f new.txt", "true"])
    await decide(ev({ toolName: "subagent", input, cwd: r }))
    const launch = `{"isAsync":true,"status":"async_launched","agentId":"a1b2c3d4e5f60718"}\nagentId: a1b2c3d4e5f60718`
    await decide(ev({ event: "tool.after", toolName: "subagent", input, output: launch, cwd: r }))
    await Bun.sleep(300)
    expect(rows("select 1 from journal where event = 'worker.verified'")).toHaveLength(0) // not at launch

    // Inside a Claude subagent the hooks keep the parent's session_id and add agent_id.
    const sub = (over: Partial<HarnessEvent>) => ev({ cwd: r, ...over, agentId: "a1b2c3d4e5f60718" } as never)
    writeFileSync(join(w, "new.txt"), "work\n") // the worker leaves its work uncommitted
    await decide(sub({ toolName: "write", input: { path: join(w, "new.txt") }, output: "ok" }))
    await decide(sub({ event: "stop", reply: "STATUS: done" }))
    expect(await waitFor(() => rows("select 1 from journal where event = 'worker.verified'").length > 0, 20_000)).toBe(true)
    const [b] = rows("select verdict, verified_json from bundles where worker_id is not null")
    const v = JSON.parse(b.verified_json)
    expect(v.reruns.map((x: { command: string; exit: number }) => [x.command, x.exit])).toEqual([["test -f new.txt", 0], ["true", 0]])
    expect(b.verdict).toBe("green")
  }, 30_000)
})

// Ledger audit 2026-11-28: main-checkout-write and push-gate judged the session's cwd, not the folder a
// command works in, so `cd <worktree> && git …` was denied as a main-checkout write, and Claude's scratch
// and memory folders were denied too.
describe("main-checkout-write and push-gate follow cd and workdir", () => {
  test("a commit through `cd <worktree>` is not a main-checkout write; the same commit in main is", async () => {
    process.env.HARNESS_SCRATCH_ROOTS = "/nonexistent-scratch"
    setMode(db, "main-checkout-write", "enforce")
    const r = repo()
    const w = join(dir, "lane")
    git(r, "worktree", "add", "-q", "-b", "lane", w)
    const sh = (command: string, cwd = r) => decide(ev({ toolName: "shell", input: { command, cwd }, cwd: r }))
    expect((await sh(`cd ${w} && git commit -qam x`)).outcome).not.toBe("deny")
    expect((await sh(`git -C ${w} commit -qam x`)).outcome).not.toBe("deny")
    expect((await sh("git commit -qam x", w)).outcome).not.toBe("deny") // OpenCode workdir
    expect((await sh("git commit -qam x")).outcome).toBe("deny")
    expect((await sh(`cd ${r} && git commit -qam x`, w)).outcome).toBe("deny")
  })

  test("Claude's scratch and memory folders are never the main checkout", async () => {
    process.env.HARNESS_SCRATCH_ROOTS = "/nonexistent-scratch"
    setMode(db, "main-checkout-write", "enforce")
    const r = repo()
    const edit = (path: string) => decide(ev({ toolName: "write", input: { path }, cwd: r }))
    expect((await edit("/tmp/claude-502/-home-u-repo/sess/scratchpad/x.html")).outcome).not.toBe("deny")
    expect((await edit(join(process.env.HOME ?? "/home/u", ".claude/projects/-home-u-repo/memory/MEMORY.md"))).outcome).not.toBe("deny")
  })

  test("push-gate checks the HEAD of the folder `cd` moves to", async () => {
    setMode(db, "push-gate", "enforce")
    const r = repo()
    const w = join(dir, "lane2")
    git(r, "worktree", "add", "-q", "-b", "lane2", w)
    writeFileSync(join(w, "b.ts"), "export const b = 2\n")
    git(w, "add", ".")
    git(w, "commit", "-qm", "b")
    await verify(db, { session: "s1", cwd: w, commands: ["true"] } as never) // green bundle for the worktree HEAD only
    const d = await decide(ev({ toolName: "shell", input: { command: `cd ${w} && git push origin HEAD:main`, cwd: r }, cwd: r }))
    expect(d.ruleId).not.toBe("push-gate")
  })
})
