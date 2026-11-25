import { afterAll, describe, expect, test } from "bun:test"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { runEval, spawnGroup, type RunSpec, type Scenario } from "../src/eval/run.ts"

const root = mkdtempSync(join(tmpdir(), "eval-run-"))
afterAll(() => rmSync(root, { recursive: true, force: true }))

const sc: Scenario = { id: "t", setup: ["echo ready > ready.txt"], prompt: "p", expect: "e" }
const judgeBy = (scores: Record<string, number>) => async (_e: string, text: string) => ({ score: scores[text], source: "jev" as const })

function fake(texts: { on: string; off: string }, seen: RunSpec[] = []) {
  return async (spec: RunSpec) => {
    seen.push(spec)
    return { text: texts[spec.arm], cost: 0.01 }
  }
}

describe("runEval", () => {
  test("arms use separate state dirs and only the off arm disables the rule", async () => {
    const seen: RunSpec[] = []
    await runEval("merge-in-shell", sc, { root, runner: fake({ on: "a", off: "b" }, seen), judge: judgeBy({ a: 1, b: 1 }) })
    const on = seen.find((s) => s.arm === "on")!
    const off = seen.find((s) => s.arm === "off")!
    expect(on.env.HARNESS_STATE_DIR).not.toBe(off.env.HARNESS_STATE_DIR)
    expect(on.env.HARNESS_STATE_DIR.startsWith(on.cwd)).toBe(true)
    expect(on.env.HARNESS_DISABLE).toBeUndefined()
    expect(off.env.HARNESS_DISABLE).toBe("merge-in-shell")
    expect(on.cmd.slice(0, 3)).toEqual(["opencode", "run", "--standalone"])
  })

  test("changes is true when scores differ by 0.5", async () => {
    const r = await runEval("r", sc, { root, runner: fake({ on: "a", off: "b" }), judge: judgeBy({ a: 0.9, b: 0.4 }) })
    expect(r.on.score).toBe(0.9)
    expect(r.off.score).toBe(0.4)
    expect(r.changes).toBe(true)
  })

  test("changes is false when scores are equal", async () => {
    const r = await runEval("r", sc, { root, runner: fake({ on: "a", off: "b" }), judge: judgeBy({ a: 0.7, b: 0.7 }) })
    expect(r.changes).toBe(false)
  })

  test("a runner error marks the arm and the verdict is not a change", async () => {
    const runner = async (s: RunSpec) => (s.arm === "off" ? { text: "", cost: 0, error: "timeout after 1ms" } : { text: "a", cost: 0 })
    const r = await runEval("r", sc, { root, runner, judge: judgeBy({ a: 1 }) })
    expect(r.off.error).toContain("timeout")
    expect(r.changes).toBe(false)
  })
})

describe("spawnGroup", () => {
  test("a timeout kills the whole group, children included", async () => {
    const marker = `eval-run-test-${Date.now()}`
    const r = await spawnGroup(["sh", "-c", `sleep 60 & sleep 60 # ${marker}; wait`], { cwd: root, env: process.env as Record<string, string>, timeoutMs: 300 })
    expect(r.timedOut).toBe(true)
    await Bun.sleep(100)
    const left = Bun.spawnSync(["pgrep", "-f", marker])
    expect(left.exitCode).toBe(1)
  })
})
