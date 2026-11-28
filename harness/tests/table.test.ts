// Architecture #3 (review 2026-11-27, decided with Alex): rules declare where they run in one table, and core
// dispatches from it, so adding a rule is one edit and the registry can no longer drift from the code.
// Stop checks live in the same table (on: stop).
import { expect, test } from "bun:test"
import { RULES } from "../src/ledger/registry.ts"
import { GUARDS, STOP_CHECKS, guardsFor, ruleEvents } from "../src/policies/table.ts"

test("tool.before guards per tool kind, in order, come from the table", () => {
  const names = (k: Parameters<typeof guardsFor>[0]) => guardsFor(k).map((g) => g.name)
  expect(names("shell")).toEqual(["shell", "page-port", "push", "worktree", "egress"])
  expect(names("edit")).toEqual(["path", "worktree"])
  expect(names("subagent")).toEqual(["spawn"])
  expect(names("harness")).toEqual(["mcp"])
  expect(names("browse")).toEqual(["page-port"])
  for (const k of ["fetch", "mcp", "external-write"] as const) expect(names(k)).toEqual(["egress"])
  expect(names("read")).toEqual([])
})

test("every rule a guard or stop check can emit is registered, and every registered guard or stop rule has a home", () => {
  const registered = new Map(RULES.map((r) => [r.id, r]))
  const guardRules = new Set(GUARDS.flatMap((g) => g.rules))
  const stopRules = new Set(STOP_CHECKS.flatMap((c) => c.rules))
  for (const id of guardRules) expect(registered.get(id)?.event, id).toBe("tool.before")
  for (const id of stopRules) expect(registered.get(id)?.event, id).toBe("stop")
  for (const r of RULES) {
    if (r.event === "stop" && r.default_mode !== "inject") expect(stopRules.has(r.id), r.id).toBe(true)
    if (r.event === "tool.before" && r.default_mode !== "inject") expect(guardRules.has(r.id), r.id).toBe(true)
  }
})

test("a rule's registered events are exactly where it runs (no drift)", () => {
  // stale-worker was registered as tool.after but also ran on prompt and from the waker.
  expect(ruleEvents("stale-worker")).toEqual(new Set(["prompt", "tool.after", "waker"]))
  expect(ruleEvents("recursive-delete")).toEqual(new Set(["tool.before"]))
  expect(ruleEvents("stop-proof")).toEqual(new Set(["stop"]))
  for (const r of RULES) expect(ruleEvents(r.id).has(r.event), r.id).toBe(true)
})
