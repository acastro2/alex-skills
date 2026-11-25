// New-model evals (D66), hourly job (D69). When a new `claude-*` model shows up in `opencode models`, run the
// Phase 8 prune evals on it (capped at USD 5) and leave a summary for the morning brief.
import type { Database } from "bun:sqlite"
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join, resolve } from "node:path"
import { getMeta, setMeta } from "../ledger/db.ts"
import { append } from "../ledger/journal.ts"

export const CAP_USD = 5

// The Phase 8 scenario files and the rule each one tests. The runner takes (ruleId, scenario).
export const SCENARIO_RULES: Record<string, string> = {
  "coding-worker": "inject-coding",
  "merge-attempt": "merge-in-shell",
  links: "stop-links",
}

export interface ScenarioRef {
  ruleId: string
  scenario: { id: string; [k: string]: unknown }
}

// What src/eval/run.ts exports (Phase 8).
export type RunEvalFn = (ruleId: string, scenario: any, opts?: { model?: string; costCapUsd?: number }) => Promise<{
  ruleId: string
  scenario: string
  on: { score: number; cost: number; error?: string }
  off: { score: number; cost: number; error?: string }
  changes: boolean
}>

export interface EvalsDeps {
  list?: () => Promise<string[]>
  loadRunner?: () => Promise<RunEvalFn | null>
  scenarios?: () => ScenarioRef[]
  stateDir?: string
  capUsd?: number
  now?: () => number
}

// Same family and version, whatever the provider, context size, date stamp, or effort variant.
export function familyKey(id: string): string | null {
  const base = id.split("#")[0].split("/").pop()!.toLowerCase().replace(/\./g, "-")
  if (!base.startsWith("claude-")) return null
  return base.replace(/-\d{8}$/, "").replace(/-\d+[km]$/, "")
}

async function listModels(): Promise<string[]> {
  const p = Bun.spawn(["opencode", "models"], { stdout: "pipe", stderr: "pipe" })
  const [out, err] = await Promise.all([new Response(p.stdout).text(), new Response(p.stderr).text()])
  if ((await p.exited) !== 0) throw new Error(`opencode models: ${err.trim().split("\n").pop()}`)
  return out.split("\n").map((l) => l.trim()).filter(Boolean)
}

async function loadRunner(): Promise<RunEvalFn | null> {
  try {
    const m = await import("../eval/run.ts")
    return typeof m.runEval === "function" ? (m.runEval as RunEvalFn) : null
  } catch {
    return null
  }
}

function loadScenarios(): ScenarioRef[] {
  const dir = resolve(dirname(import.meta.path), "..", "..", "evals", "scenarios")
  const out: ScenarioRef[] = []
  try {
    for (const f of readdirSync(dir).sort()) {
      const sc = JSON.parse(readFileSync(join(dir, f), "utf8"))
      const ruleId = SCENARIO_RULES[sc.id]
      if (ruleId) out.push({ ruleId, scenario: sc })
    }
  } catch {}
  return out
}

const stateDir = () => process.env.HARNESS_STATE_DIR ?? join(process.env.HOME || homedir(), ".local", "state", "harness")

export async function runEvals(db: Database, d: EvalsDeps = {}): Promise<string> {
  const cap = d.capUsd ?? CAP_USD
  const ids = await (d.list ?? listModels)()
  const firstId = new Map<string, string>() // family key -> a listed id to run
  for (const id of ids) {
    const k = familyKey(id)
    if (k && !firstId.has(k)) firstId.set(k, id.split("#")[0])
  }

  const raw = getMeta(db, "known_models")
  if (raw === null) {
    setMeta(db, "known_models", JSON.stringify([...firstId.keys()].sort()))
    append(db, { session_id: null, event: "evals.run", reason: `seeded ${firstId.size} known claude models`, data: { seeded: [...firstId.keys()] } })
    return `ok: seeded ${firstId.size} known models`
  }
  const known = new Set<string>(JSON.parse(raw))
  const fresh = [...firstId.keys()].filter((k) => !known.has(k)).sort()
  if (!fresh.length) return "ok: no new claude model"

  const runEval = await (d.loadRunner ?? loadRunner)()
  if (!runEval) {
    append(db, { session_id: null, event: "job.skipped", reason: "eval runner missing", data: { job: "new-model-evals", models: fresh } })
    return "skipped: eval runner missing"
  }

  const scenarios = (d.scenarios ?? loadScenarios)()
  let spent = 0
  const done: string[] = []
  for (const key of fresh) {
    const model = firstId.get(key)!
    const lines: string[] = []
    let runs = 0
    let capped = false
    let modelCost = 0
    for (const s of scenarios) {
      if (spent >= cap) {
        capped = true
        break
      }
      try {
        const r = await runEval(s.ruleId, s.scenario, { model, costCapUsd: Math.max(0, cap - spent) })
        const cost = (Number(r.on?.cost) || 0) + (Number(r.off?.cost) || 0)
        spent += cost
        modelCost += cost
        runs++
        const err = r.on?.error ?? r.off?.error
        lines.push(`| ${s.ruleId} | ${s.scenario.id} | ${err ? `error: ${err.slice(0, 80)}` : r.changes ? "rule changes the outcome" : "no change"} | ${r.on?.score ?? "-"} | ${r.off?.score ?? "-"} | ${cost.toFixed(4)} |`)
      } catch (e) {
        runs++
        lines.push(`| ${s.ruleId} | ${s.scenario.id} | error: ${(e as Error).message.slice(0, 80)} | - | - | 0 |`)
      }
    }
    const when = new Date((d.now ?? Date.now)()).toISOString()
    const body = [
      `# New model: ${model}`,
      "",
      `First seen ${when}. Prune evals ran ${runs} of ${scenarios.length} scenarios${capped ? `; stopped at the USD ${cap} cap` : ""}. Cost USD ${modelCost.toFixed(4)}.`,
      "",
      "| rule | scenario | result | score on | score off | cost USD |",
      "| --- | --- | --- | --- | --- | --- |",
      ...lines,
      "",
    ].join("\n")
    const dir = join(d.stateDir ?? stateDir(), "brief")
    mkdirSync(dir, { recursive: true })
    writeFileSync(join(dir, `new-model-${key.replace(/[^A-Za-z0-9._-]/g, "-")}.md`), body)
    append(db, { session_id: null, event: "evals.run", reason: `${model}: ${runs} runs, USD ${modelCost.toFixed(4)}${capped ? ", capped" : ""}`, data: { model, key, runs, cost: modelCost, capped } })
    known.add(key)
    setMeta(db, "known_models", JSON.stringify([...known].sort()))
    done.push(model)
    if (spent >= cap) break
  }
  return `ok: evals for ${done.join(", ") || "none"}, USD ${spent.toFixed(2)}`
}
