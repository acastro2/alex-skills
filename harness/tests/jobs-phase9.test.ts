import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { SEEDS, runCanary } from "../src/jobs/canary.ts"
import { runEvals } from "../src/jobs/evals.ts"
import { runMiner, type Judge, type ModelCall } from "../src/jobs/miner.ts"
import { checkShell } from "../src/shell/rules.ts"
import { getMeta } from "../src/ledger/db.ts"
import { openLedger } from "../src/ledger/db.ts"
import { append, upsertSession } from "../src/ledger/journal.ts"
import { seed } from "../src/ledger/registry.ts"

let dir: string
let db: Database

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-phase9-"))
  process.env.HARNESS_STATE_DIR = join(dir, "state")
  db = openLedger()
  seed(db)
  upsertSession(db, { id: "s1", tool: "opencode" })
})

afterEach(() => {
  db.close()
  delete process.env.HARNESS_STATE_DIR
  rmSync(dir, { recursive: true, force: true })
})

const events = (name: string) => db.query("select * from journal where event = ? order by seq").all(name) as any[]

describe("correction miner (D57)", () => {
  const proposal = {
    kind: "message",
    summary: "Say which URL is missing in the send-back message.",
    edits: [{ file: "harness/src/policies/stop.ts", find: "Add the direct link", replace: "Add the direct URL" }],
    eval: { event: { event: "stop", reply: "pushed it" }, expect: { outcome: "deny", ruleId: "stop-links" } },
  }

  test("three harness.wrong rows on one rule give one proposal with one eval in dry mode", async () => {
    for (let i = 1; i <= 3; i++) {
      const sb = append(db, { session_id: "s1", event: "stop.sendback", rule_id: "stop-links", outcome: "deny", reason: `no URL in the reply ${i}` })
      append(db, { session_id: "s1", event: "harness.wrong", rule_id: "stop-links", data: { sendback_seq: sb } })
    }
    const calls: ModelCall[] = []
    const printed: string[] = []
    let published = 0
    const never: Judge = async () => ({}) // wrong rows need no judgment
    const res = await runMiner(db, {
      dry: true,
      judge: never,
      run: async (c) => {
        calls.push(c)
        return { text: "```json\n" + JSON.stringify(proposal) + "\n```", cost: 0, model: "fake" }
      },
      print: (s) => printed.push(s),
      publish: () => {
        published++
        return "x"
      },
    })
    expect(res).toBe("ok: dry run, 1 proposals")
    expect(calls).toHaveLength(1)
    expect(calls[0].prompt).toContain("no URL in the reply 2")
    expect(published).toBe(0)
    expect(printed).toHaveLength(1)
    expect(printed[0]).toContain("stop-links [message]")
    expect(printed[0]).toContain(JSON.stringify(proposal.eval))
    expect(events("miner.pr")).toHaveLength(0)
  })
})

describe("red-team canary (D63)", () => {
  const MISSED = "git reset --hard"
  // A guard that denies everything except one seeded line.
  const missOne = (line: string) => (line === MISSED ? null : { ruleId: "recursive-delete" })

  test("a seeded bypass writes a failing test file and journals canary.bypass; bwrap blocked journals job.skipped", async () => {
    expect(SEEDS.some((s) => s.line === MISSED)).toBe(true)
    const out = join(dir, "canary")
    const res = await runCanary(db, { check: missOne, bwrapOk: () => false, dir: out })
    expect(res).toContain("1 bypasses")
    const files = readdirSync(out)
    expect(files).toHaveLength(1)
    expect(files[0]).toMatch(/^bypass-[0-9a-f]{8}\.test\.ts$/)
    expect(readFileSync(join(out, files[0]), "utf8")).toContain(JSON.stringify(MISSED))
    const bypass = events("canary.bypass")
    expect(bypass).toHaveLength(1)
    expect(JSON.parse(bypass[0].data_json).line).toBe(MISSED)
    expect(events("job.skipped").map((r) => r.reason)).toEqual(["bwrap blocked"])
  })

  test("a model-invented line counts as a bypass only when Jev says it is dangerous at 0.80 or more", async () => {
    const out = join(dir, "canary")
    const lines = ["dangerous-miss", "harmless-miss"]
    const res = await runCanary(db, {
      check: (l) => (lines.includes(l) ? null : { ruleId: "recursive-delete" }),
      bwrapOk: () => true,
      dir: out,
      run: async (c) => {
        expect(c.sandbox).toBe(true)
        return { text: JSON.stringify(lines), cost: 0, model: "fake" }
      },
      judge: async (_q, summary) => ({ danger: { value: summary.includes("dangerous") ? 0.9 : 0.1, source: "jev" } }),
    })
    expect(res).toContain("2 model lines")
    expect(events("canary.bypass").map((r) => JSON.parse(r.data_json).line)).toEqual(["dangerous-miss"])
    expect(events("job.skipped")).toHaveLength(0)
  })

  test("the real guard denies most of the seeded list", () => {
    const denied = SEEDS.filter((s) => checkShell(s.line, { cwd: "/home/canary/Developer/target", home: "/home/canary", repoRoot: "/home/canary/Developer/target", allowRoots: ["/tmp"], branch: "feat" })).length
    expect(denied).toBeGreaterThan(SEEDS.length / 2)
  })
})

describe("new-model evals (D66)", () => {
  const scenarios = Array.from({ length: 5 }, (_, i) => ({ ruleId: `rule-${i}`, scenario: { id: `sc-${i}` } }))
  const runner = (calls: string[]) => async (ruleId: string) => {
    calls.push(ruleId)
    return { ruleId, scenario: "x", on: { score: 1, cost: 1 }, off: { score: 0, cost: 1 }, changes: true }
  }

  test("a new claude id triggers one run, the USD 5 cap stops further scenarios, and the brief gets a summary", async () => {
    const state = join(dir, "state")
    const base = ["cursor/claude-haiku-5-5", "cursor/claude-haiku-5-5-1m", "github-copilot/claude-haiku-5.5", "openai/gpt-9"]
    // First sight seeds the known list and runs nothing.
    expect(await runEvals(db, { list: async () => base, loadRunner: async () => null, stateDir: state })).toBe("ok: seeded 1 known models")
    // A variant of a known model and a non-claude model are not new.
    expect(await runEvals(db, { list: async () => [...base, "cursor/claude-haiku-5-5#High", "openai/gpt-10"], loadRunner: async () => null, stateDir: state })).toBe("ok: no new claude model")

    const calls: string[] = []
    const list = async () => [...base, "cursor/claude-sonnet-6-0"]
    const res = await runEvals(db, { list, loadRunner: async () => runner(calls) as any, scenarios: () => scenarios, stateDir: state })
    expect(calls).toEqual(["rule-0", "rule-1", "rule-2"]) // 0 + 2 + 2 < 5 starts a run; 6 does not
    expect(res).toBe("ok: evals for cursor/claude-sonnet-6-0, USD 6.00")
    const brief = join(state, "brief", "new-model-claude-sonnet-6-0.md")
    expect(existsSync(brief)).toBe(true)
    expect(readFileSync(brief, "utf8")).toContain("stopped at the USD 5 cap")
    expect(JSON.parse(events("evals.run").at(-1).data_json)).toMatchObject({ key: "claude-sonnet-6-0", runs: 3, capped: true })
    expect(JSON.parse(getMeta(db, "known_models")!)).toContain("claude-sonnet-6-0")

    // Seen once: the next hour runs nothing.
    await runEvals(db, { list, loadRunner: async () => runner(calls) as any, scenarios: () => scenarios, stateDir: state })
    expect(calls).toHaveLength(3)
  })

  test("a new model with no eval runner journals job.skipped and stays new", async () => {
    const state = join(dir, "state")
    await runEvals(db, { list: async () => ["cursor/claude-haiku-5-5"], stateDir: state })
    const list = async () => ["cursor/claude-haiku-5-5", "cursor/claude-opus-6-0"]
    expect(await runEvals(db, { list, loadRunner: async () => null, stateDir: state })).toBe("skipped: eval runner missing")
    expect(events("job.skipped").map((r) => r.reason)).toEqual(["eval runner missing"])
    expect(JSON.parse(getMeta(db, "known_models")!)).not.toContain("claude-opus-6-0")
  })
})
