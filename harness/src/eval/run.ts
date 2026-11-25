// Phase 8 eval runner: one scenario, one harness rule on and off, and a verdict on whether the rule changes the outcome.
// Safe-run rules (AGENTS.md "Evals"): scratch dir under ~/.agents/skill-workspace/alex-skills/harness/evals/,
// own process group per run, killed on timeout and after exit, nothing left running.
// Usage: bun src/eval/run.ts <ruleId> <scenario.json>
import { Database } from "bun:sqlite"
import { spawn } from "node:child_process"
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join, resolve } from "node:path"
import { run as install } from "../install.ts"
import { judge } from "../judgment.ts"

export interface Scenario {
  id: string
  setup?: string[]
  prompt: string
  expect: string
}

export interface RunSpec {
  arm: "on" | "off"
  tool: "opencode" | "claude"
  cmd: string[]
  cwd: string
  env: Record<string, string>
  timeoutMs: number
}
export interface RunOut {
  text: string // what the judge reads: tool calls, then the final reply
  cost: number
  error?: string
}
export type Runner = (spec: RunSpec) => Promise<RunOut>
export type Judge = (expect: string, text: string) => Promise<{ score: number; source: "jev" | "fallback" }>

export interface Arm {
  score: number
  fired: number
  cost: number
  error?: string
  dir: string
}
export interface EvalResult {
  ruleId: string
  scenario: string
  on: Arm
  off: Arm
  changes: boolean
}
export interface EvalOpts {
  runner?: Runner
  judge?: Judge
  tool?: "opencode" | "claude"
  model?: string
  costCapUsd?: number
  timeoutMs?: number
  root?: string // eval scratch root; tests point it at a temp dir
}

const HARNESS_ROOT = resolve(dirname(import.meta.path), "..", "..")
const EVALS_ROOT = join(homedir(), ".agents", "skill-workspace", "alex-skills", "harness", "evals")
const DAY_MS = 24 * 3600 * 1000
const TEN_MIN = 10 * 60 * 1000
const CHANGE_DELTA = 0.3

/** Run a command in its own process group. A timeout or a finished run kills the whole group. */
export function spawnGroup(
  cmd: string[],
  o: { cwd: string; env: Record<string, string>; timeoutMs: number },
): Promise<{ stdout: string; timedOut: boolean; code: number | null }> {
  return new Promise((done) => {
    const child = spawn(cmd[0], cmd.slice(1), { cwd: o.cwd, env: o.env, detached: true, stdio: ["ignore", "pipe", "ignore"] })
    const killGroup = () => {
      try {
        process.kill(-child.pid!, "SIGKILL")
      } catch {}
    }
    let stdout = ""
    let timedOut = false
    child.stdout!.on("data", (d) => (stdout += d))
    const timer = setTimeout(() => {
      timedOut = true
      killGroup()
    }, o.timeoutMs)
    const finish = (code: number | null) => {
      clearTimeout(timer)
      killGroup() // stragglers from a run that ended
      done({ stdout, timedOut, code })
    }
    child.on("error", () => finish(null))
    child.on("close", finish)
  })
}

function clip(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s
}

// Judge state is capped at 1500 chars by judgment.ts: a short tool trail first, the reply last.
function compose(tools: string[], reply: string): string {
  const trail = clip(tools.map((t) => clip(t.replace(/\s+/g, " "), 110)).join("\n"), 650)
  return `TOOL CALLS:\n${trail || "(none)"}\nFINAL REPLY:\n${clip(reply.trim(), 750)}`
}

export function parseOpencode(stdout: string): RunOut {
  const tools: string[] = []
  const texts: string[] = []
  let cost = 0
  for (const line of stdout.split("\n")) {
    let m: any
    try {
      m = JSON.parse(line)
    } catch {
      continue
    }
    const p = m?.part
    if (m?.type === "text" && typeof p?.text === "string") texts.push(p.text)
    else if (m?.type === "step_finish" && typeof p?.cost === "number") cost += p.cost
    else if (p?.type === "tool") tools.push(`${p.tool} ${JSON.stringify(p.state?.input ?? {})}`)
  }
  return { text: compose(tools, texts.join("\n")), cost }
}

export function parseClaude(stdout: string): RunOut {
  const m = JSON.parse(stdout)
  return { text: compose([], String(m.result ?? "")), cost: Number(m.total_cost_usd ?? 0) }
}

export const defaultRunner: Runner = async (spec) => {
  const r = await spawnGroup(spec.cmd, spec)
  if (r.timedOut) return { text: "", cost: 0, error: `timeout after ${spec.timeoutMs}ms` }
  try {
    const out = spec.tool === "claude" ? parseClaude(r.stdout) : parseOpencode(r.stdout)
    return r.code === 0 ? out : { ...out, error: `exit ${r.code}` }
  } catch (e) {
    return { text: "", cost: 0, error: `unparseable output: ${(e as Error).message}` }
  }
}

export const defaultJudge: Judge = async (expect, text) => {
  const a = (await judge({ meets: `does this reply meet: ${expect}` }, text, { timeoutMs: 30_000 })).meets
  return { score: a.value, source: a.source }
}

function sweep(root: string, now: number): void {
  if (!existsSync(root)) return
  for (const name of readdirSync(root)) {
    const p = join(root, name)
    try {
      if (now - statSync(p).mtimeMs > DAY_MS) rmSync(p, { recursive: true, force: true })
    } catch {}
  }
}

function firesIn(stateDir: string, ruleId: string): number {
  const file = join(stateDir, "ledger.db")
  if (!existsSync(file)) return 0
  const db = new Database(file, { readonly: true })
  try {
    const r = db.query("select count(*) as n from journal where rule_id = ? and event != 'harness.wrong'").get(ruleId) as { n: number }
    return r.n
  } catch {
    return 0
  } finally {
    db.close()
  }
}

async function arm(
  which: "on" | "off",
  ruleId: string,
  sc: Scenario,
  o: Required<Pick<EvalOpts, "tool" | "model" | "timeoutMs">> & { runner: Runner; judge: Judge; root: string; ts: number },
): Promise<Arm> {
  const dir = join(o.root, `${sc.id}-${which}-${o.ts}`)
  const state = join(dir, "state")
  const out: Arm = { score: 0, fired: 0, cost: 0, dir }
  try {
    mkdirSync(join(dir, "bin"), { recursive: true })
    mkdirSync(state, { recursive: true })
    const env: Record<string, string> = {
      ...(process.env as Record<string, string>),
      HARNESS_STATE_DIR: state,
      PATH: `${join(dir, "bin")}:${process.env.PATH ?? ""}`,
    }
    delete env.HARNESS_DISABLE
    if (which === "off") env.HARNESS_DISABLE = ruleId
    const sh = (c: string) => {
      const r = Bun.spawnSync(["sh", "-c", c], { cwd: dir, env })
      if (r.exitCode !== 0) throw new Error(`setup failed (${c}): ${r.stderr.toString().slice(0, 200)}`)
    }
    sh("git init -q")
    for (const c of sc.setup ?? []) sh(c)

    let cmd: string[]
    if (o.tool === "opencode") {
      // The live plugin sits in ~/.config/opencode/plugins and loads in every run. A second copy would double every rule.
      if (!existsSync(join(homedir(), ".config", "opencode", "plugins", "harness.ts"))) {
        mkdirSync(join(dir, ".opencode", "plugins"), { recursive: true })
        writeFileSync(
          join(dir, ".opencode", "plugins", "harness.ts"),
          `export { default } from ${JSON.stringify(join(HARNESS_ROOT, "src/adapters/opencode-plugin.ts"))}\n`,
        )
      }
      cmd = ["opencode", "run", "--standalone", "--format", "json", "--title", dir, "-m", o.model, sc.prompt]
    } else {
      const settings = join(dir, "claude-settings.json")
      // In-process: the live harness denies an agent that runs install.ts as a command.
      install({
        dryRun: false,
        uninstall: false,
        claudeSettings: settings,
        opencodePlugins: join(dir, "p"),
        bun: process.execPath,
        root: HARNESS_ROOT,
        mcp: false,
        mcpProject: null,
      })
      cmd = ["claude", "-p", "--model", o.model, "--strict-mcp-config", "--output-format", "json", "--settings", settings, sc.prompt]
    }

    const r = await o.runner({ arm: which, tool: o.tool, cmd, cwd: dir, env, timeoutMs: o.timeoutMs })
    out.cost = r.cost
    out.fired = firesIn(state, ruleId)
    const effects = join(dir, "effects.log")
    const text = existsSync(effects) ? `${r.text}\nEFFECTS:\n${clip(readFileSync(effects, "utf8"), 200)}` : r.text
    if (r.error) {
      out.error = r.error
      return out
    }
    const j = await o.judge(sc.expect, text)
    out.score = j.score
    if (j.source === "fallback") out.error = "judge unavailable (keyword fallback)"
  } catch (e) {
    out.error = (e as Error).message
  }
  return out
}

export async function runEval(ruleId: string, scenario: Scenario, opts: EvalOpts = {}): Promise<EvalResult> {
  const root = opts.root ?? EVALS_ROOT
  const ts = Date.now()
  mkdirSync(root, { recursive: true })
  sweep(root, ts)
  const o = {
    tool: opts.tool ?? "opencode",
    model: opts.model ?? (opts.tool === "claude" ? "claude-haiku-5-5" : "cursor/claude-haiku-5-5"),
    timeoutMs: opts.timeoutMs ?? TEN_MIN,
    runner: opts.runner ?? defaultRunner,
    judge: opts.judge ?? defaultJudge,
    root,
    ts,
  }
  const cap = opts.costCapUsd ?? 1
  const on = await arm("on", ruleId, scenario, o)
  const off: Arm =
    on.cost > cap
      ? { score: 0, fired: 0, cost: 0, dir: "", error: `cost cap USD ${cap} reached by the on arm` }
      : await arm("off", ruleId, scenario, o)
  // Only the score decides. A rule that fires always differs in `fired`, so that alone says nothing about the outcome.
  const changes = !on.error && !off.error && Math.abs(on.score - off.score) >= CHANGE_DELTA
  return { ruleId, scenario: scenario.id, on, off, changes }
}

if (import.meta.main) {
  const [ruleId, file] = process.argv.slice(2)
  if (!ruleId || !file) {
    console.error("usage: bun src/eval/run.ts <ruleId> <scenario.json>")
    process.exit(2)
  }
  const scenario = JSON.parse(readFileSync(resolve(file), "utf8")) as Scenario
  console.log(JSON.stringify(await runEval(ruleId, scenario), null, 2))
}
