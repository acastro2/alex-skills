import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { closeCore, decide } from "../src/core.ts"
import { holds } from "../src/ledger/authority.ts"
import { openLedger } from "../src/ledger/db.ts"
import { verifyChain } from "../src/ledger/journal.ts"
import { seed, setMode } from "../src/ledger/registry.ts"
import type { HarnessEvent } from "../src/types.ts"

let dir: string
let db: Database

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-core-"))
  process.env.HARNESS_STATE_DIR = dir
  delete process.env.HARNESS_DISABLE
  db = openLedger()
  seed(db) // decide() seeds too; the test flips modes before its first event
})

afterEach(() => {
  closeCore()
  db.close()
  delete process.env.HARNESS_STATE_DIR
  delete process.env.HARNESS_DISABLE
  rmSync(dir, { recursive: true, force: true })
})

const ev = (over: Partial<HarnessEvent>): HarnessEvent => ({
  v: 1,
  event: "tool.before",
  tool: "claude",
  session: "s1",
  parentSession: null,
  cwd: "/tmp",
  time: Date.now(),
  ...over,
})

const sh = (command: string, over: Partial<HarnessEvent> = {}) =>
  ev({ toolName: "shell", input: { command, cwd: "/tmp" }, ...over })

const rows = () => db.query("select * from journal order by seq").all() as any[]

describe("kill switch", () => {
  test("allows rm -rf /home/x and journals the call", async () => {
    db.query("insert into schema_meta(key, value) values('harness_off', '1') on conflict(key) do update set value = '1'").run()
    const d = await decide(sh("rm -rf /home/x"))
    expect(d.outcome).toBe("allow")
    const r = rows().filter((x) => x.event === "tool.before")
    expect(r).toHaveLength(1)
    expect(r[0].outcome).toBe("allow")
  })
})

describe("recursive-delete", () => {
  const cmd = "rm -rf /home/u/Developer/x"

  test("denied when enforced", async () => {
    const d = await decide(sh(cmd))
    expect(d.outcome).toBe("deny")
    expect(d.ruleId).toBe("recursive-delete")
    const r = rows().find((x) => x.event === "tool.before")
    expect(r.rule_id).toBe("recursive-delete")
    expect(r.outcome).toBe("deny")
  })

  test("allowed with journal outcome advise when the rule is in advise mode", async () => {
    setMode(db, "recursive-delete", "advise")
    const d = await decide(sh(cmd))
    expect(d.outcome).toBe("allow")
    const r = rows().find((x) => x.event === "tool.before")
    expect(r.rule_id).toBe("recursive-delete")
    expect(r.outcome).toBe("advise")
    expect(r.reason).toContain("Recursive delete")
  })

  test("skipped when HARNESS_DISABLE names the rule", async () => {
    process.env.HARNESS_DISABLE = "recursive-delete"
    const d = await decide(sh(cmd))
    expect(d.outcome).toBe("allow")
    expect(rows().find((x) => x.event === "tool.before").outcome).toBe("allow")
  })
})

describe("prompt commands", () => {
  test("MERGE-OK 42 in a root session confirms and records a token", async () => {
    const d = await decide(ev({ event: "prompt", prompt: "MERGE-OK 42" }))
    expect(d.outcome).toBe("modify")
    expect(d.context).toContain("merge grant for PR 42 recorded, valid 30 min")
    expect(holds(db, { kind: "merge", session: "s1", pr: 42 })).not.toBeNull()
  })

  test("the same text in a subagent session grants nothing", async () => {
    const d = await decide(ev({ event: "prompt", session: "sub1", parentSession: "s1", prompt: "MERGE-OK 42" }))
    expect(d.outcome).toBe("allow")
    expect(holds(db, { kind: "merge", session: "sub1", pr: 42 })).toBeNull()
  })

  test("a history question gets the archeologist hint, other prompts get none", async () => {
    const a = await decide(ev({ event: "prompt", prompt: "what did we decide about the retry policy last week?" }))
    expect(a.context).toBe("Hint: use the archeologist subagent.")
    const b = await decide(ev({ event: "prompt", prompt: "rename the variable foo to bar" }))
    expect(b.outcome).toBe("allow")
  })
})

describe("spawn rules", () => {
  const spawn = (input: Record<string, unknown>, tool: "claude" | "opencode" = "claude") =>
    ev({ tool, toolName: "subagent", input: { agent: tool === "claude" ? "general-purpose" : "general", ...input } })

  test("Claude general spawn without model is denied", async () => {
    const d = await decide(spawn({ prompt: "ACCEPTANCE: bun test\ndo it" }))
    expect(d.outcome).toBe("deny")
    expect(d.ruleId).toBe("spawn-model")
  })

  test("with a model but no ACCEPTANCE it is denied", async () => {
    const d = await decide(spawn({ prompt: "do it", model: "cursor/claude-haiku-5-5" }))
    expect(d.outcome).toBe("deny")
    expect(d.ruleId).toBe("spawn-acceptance")
  })

  test("with both, Claude gets the contract appended", async () => {
    const d = await decide(spawn({ prompt: "do it\nACCEPTANCE: bun test", model: "m" }))
    expect(d.outcome).toBe("modify")
    expect(String((d.input as any).prompt)).toContain("HARNESS-CONTRACT v1")
    expect(String((d.input as any).prompt)).toStartWith("do it\nACCEPTANCE: bun test")
  })

  test("OpenCode with ACCEPTANCE but no marker is denied with the contract; with the marker it passes", async () => {
    const d = await decide(spawn({ prompt: "do it\nACCEPTANCE: bun test", model: "m" }, "opencode"))
    expect(d.outcome).toBe("deny")
    expect(d.message).toContain("HARNESS-CONTRACT v1")
    expect(d.message).toContain("Load the `coding` skill first")
    const ok = await decide(spawn({ prompt: "do it\nHARNESS-CONTRACT v1\nACCEPTANCE: bun test", model: "m" }, "opencode"))
    expect(ok.outcome).toBe("allow")
  })
})

describe("journal", () => {
  test("every decide call appends exactly one row and the chain stays ok", async () => {
    const events: HarnessEvent[] = [
      ev({ event: "session.start" }),
      ev({ event: "prompt", prompt: "hello" }),
      sh("ls"),
      sh("rm -rf /home/u/Developer/x"),
      ev({ event: "tool.after", toolName: "shell", input: { command: "ls" }, output: "a" }),
      ev({ toolName: "question", input: { questions: [{ question: "A or B?" }] } }),
      ev({ event: "tool.after", toolName: "question", input: {}, output: "A" }),
      ev({ event: "prompt", prompt: "MERGE-OK 7" }),
      ev({ event: "stop", reply: "done" }),
      ev({ event: "session.end" }),
    ]
    for (const e of events) {
      const before = (db.query("select count(*) as c from journal").get() as { c: number }).c
      const extra = e.event === "prompt" && e.prompt?.startsWith("MERGE-OK") ? 1 : 0 // authority writes its own grant row
      await decide(e)
      const after = (db.query("select count(*) as c from journal").get() as { c: number }).c
      expect(after - before).toBe(1 + extra)
    }
    expect(verifyChain(db).ok).toBe(true)
    const names = rows().map((r) => r.event)
    expect(names).toContain("question.asked")
    expect(names).toContain("question.answered")
    expect((db.query("select ended_at from sessions where id = 's1'").get() as any).ended_at).not.toBeNull()
  })
})
