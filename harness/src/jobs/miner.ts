// Correction miner (D57), weekly job (D69). Reads the last 7 days of the journal, finds the moments Alex
// pushed back on a rule, and opens ONE draft PR with a proposed change and one eval per rule. It never merges.
import type { Database } from "bun:sqlite"
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs"
import { homedir, tmpdir } from "node:os"
import { dirname, join, resolve } from "node:path"
import { judge as realJudge, type Answer, type Question } from "../judgment.ts"
import { append } from "../ledger/journal.ts"

// ---- model runner: the one seam every model job shares (miner, canary, evals) ----

export const PRIMARY_MODEL = "cursor/claude-haiku-5-5"
export const FALLBACK_MODEL = "opencode-go/deepseek-v4.1-flash#high"

export interface ModelCall {
  prompt: string
  sandbox?: boolean // run inside bwrap with no network and a hidden state dir
  cwd?: string
}
export interface ModelResult {
  text: string
  cost: number // USD, summed from the step_finish rows of `opencode run --format json`
  model: string
}
export type ModelRunner = (call: ModelCall) => Promise<ModelResult>

const home = () => process.env.HOME || homedir()

export function bwrapArgv(): string[] {
  // Read-only root, no state dir (so no ledger), but opencode's own state read-only and its data dir writable: without them
  // the Cursor provider fails ("Run setup failed") and opencode cannot open its log. The network stays ON: the model API is remote,
  // so `--unshare-net` makes every model call fail. The prompt forbids tools and the disk is read-only.
  const state = `${home()}/.local/state`
  const data = `${home()}/.local/share/opencode`
  return [
    "bwrap", "--chdir", "/tmp", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
    "--tmpfs", state, "--ro-bind-try", `${state}/opencode`, `${state}/opencode`, "--bind-try", data, data,
  ]
}

function opencodeBin(): string {
  return Bun.which("opencode") ?? join(home(), ".opencode", "bin", "opencode")
}

export function parseRunJson(stdout: string): { text: string; cost: number; error?: string } {
  const texts: string[] = []
  let cost = 0
  let error: string | undefined
  for (const line of stdout.split("\n")) {
    let m: any
    try {
      m = JSON.parse(line)
    } catch {
      continue
    }
    if (m?.type === "text" && typeof m.part?.text === "string") texts.push(m.part.text)
    else if (m?.type === "step_finish" && typeof m.part?.cost === "number") cost += m.part.cost
    else if (m?.type === "error") error = String(m.error?.data?.message ?? m.error?.message ?? m.error?.name ?? "error").slice(0, 300)
  }
  return { text: texts.join("\n").trim(), cost, error }
}

async function runOnce(model: string, call: ModelCall): Promise<ModelResult> {
  const cwd = call.cwd ?? mkdtempSync(join(tmpdir(), "harness-model-"))
  const argv = [...(call.sandbox ? bwrapArgv() : []), opencodeBin(), "run", "--format", "json", "--archived", "-m", model, call.prompt]
  const p = Bun.spawn(argv, { cwd, stdout: "pipe", stderr: "pipe" })
  const [out, err] = await Promise.all([new Response(p.stdout).text(), new Response(p.stderr).text()])
  const code = await p.exited
  const r = parseRunJson(out)
  if (code !== 0 || r.error || !r.text) throw new Error(`${model}: ${r.error ?? (err.trim().split("\n").pop() || `exit ${code}`)}`.slice(0, 300))
  return { text: r.text, cost: r.cost, model }
}

// Cursor first. Any failure of the primary (auth, quota, provider) goes to the fallback once.
export const opencodeRunner: ModelRunner = async (call) => {
  try {
    return await runOnce(PRIMARY_MODEL, call)
  } catch (e) {
    try {
      return await runOnce(FALLBACK_MODEL, call)
    } catch (e2) {
      throw new Error(`${(e as Error).message}; fallback: ${(e2 as Error).message}`)
    }
  }
}

// Pulls the first JSON value out of a model reply (fenced or bare).
export function extractJson<T = unknown>(text: string): T | null {
  const fenced = /```(?:json)?\s*([\s\S]*?)```/.exec(text)
  const body = fenced ? fenced[1] : text
  const start = body.search(/[[{]/)
  if (start < 0) return null
  for (let end = body.length; end > start; end--) {
    const c = body[end - 1]
    if (c !== "}" && c !== "]") continue
    try {
      return JSON.parse(body.slice(start, end)) as T
    } catch {}
  }
  return null
}

// ---- collect corrections ----

export interface Correction {
  seq: number
  time: number
  text: string
  kind: "wrong" | "sendback-contradicted" | "prompt-correction"
  session: string | null
  rule_id: string
}

interface Row {
  seq: number
  session_id: string | null
  time: number
  event: string
  rule_id: string | null
  outcome: string | null
  reason: string | null
  prompt_text: string | null
  data_json: string | null
}

const WEEK = 7 * 24 * 3600_000
const HOUR = 3600_000
const THRESHOLD = 0.8
const SHORT_PROMPT = 80
const MAX_JUDGED = 200

const CORRECTS =
  "Does `prompt` correct the agent: say it was wrong, did not do what was asked, or tell it to stop what it was doing?"
const CONTRADICTS = "Does `prompt` contradict or reject what the harness `sendback` told the agent to do?"
const KEYWORDS = /^\s*(no\b|nope|wrong|stop\b)|that'?s not what i (asked|said|wanted)|\bi told you\b|\bnot what i asked\b/i

const corrects: Question = { q: CORRECTS, fallback: (s) => (KEYWORDS.test(safe(s).prompt) ? 1 : 0) }
const contradicts: Question = { q: CONTRADICTS, fallback: (s) => (KEYWORDS.test(safe(s).prompt) ? 1 : 0) }

function safe(s: string): { prompt: string } {
  try {
    return { prompt: String(JSON.parse(s).prompt ?? "") }
  } catch {
    return { prompt: "" }
  }
}

export type Judge = (qs: Record<string, Question>, summary: string) => Promise<Record<string, Answer>>

export async function collect(db: Database, now: number, judge: Judge): Promise<{ corrections: Correction[]; jevDown: boolean }> {
  const since = now - WEEK
  const rows = db
    .query(
      `select seq, session_id, time, event, rule_id, outcome, reason, prompt_text, data_json from journal
       where time >= ? and (event in ('harness.wrong', 'stop.sendback', 'prompt') or (outcome = 'deny' and rule_id is not null)) order by seq`,
    )
    .all(since) as Row[]
  const bySeq = new Map(rows.map((r) => [r.seq, r]))
  const out: Correction[] = []
  const used = new Set<number>() // sendbacks and prompts already counted
  let jevDown = false

  // 1. Alex marked a send-back wrong.
  for (const r of rows) {
    if (r.event !== "harness.wrong" || !r.rule_id) continue
    const data = r.data_json ? JSON.parse(r.data_json) : {}
    const sbSeq = Number(data.sendback_seq ?? data.seq)
    const sb = Number.isFinite(sbSeq) ? (bySeq.get(sbSeq) ?? (db.query("select * from journal where seq = ?").get(sbSeq) as Row | null)) : null
    if (sb) used.add(sb.seq)
    out.push({ seq: r.seq, time: r.time, text: sb?.reason ?? "Alex marked a send-back wrong", kind: "wrong", session: r.session_id, rule_id: r.rule_id })
  }

  // 2 and 3. Prompts: the first one after a send-back (contradiction), and short ones (correction).
  const lastDeny = new Map<string, Row>() // session -> latest row with a rule and a deny outcome
  const pendingSendback = new Map<string, Row>() // session -> send-back with no prompt yet
  const candidates: { prompt: Row; sendback: Row | null; blame: Row | null }[] = []
  for (const r of rows) {
    const s = r.session_id
    if (!s) continue
    if (r.event === "stop.sendback") {
      pendingSendback.set(s, r)
      if (r.rule_id) lastDeny.set(s, r)
    } else if (r.event !== "prompt") {
      if (r.rule_id && r.outcome === "deny") lastDeny.set(s, r) // a guard deny on a tool call
    } else {
      const text = (r.prompt_text ?? "").trim()
      const sb = pendingSendback.get(s)
      pendingSendback.delete(s)
      if (!text || text.startsWith("/")) continue
      const near = sb && r.time - sb.time <= HOUR ? sb : null
      const blame = near ?? ((x) => (x && r.time - x.time <= 10 * 60_000 ? x : null))(lastDeny.get(s))
      if (near || text.length <= SHORT_PROMPT) candidates.push({ prompt: r, sendback: near, blame })
    }
  }

  let judged = 0
  for (const c of candidates) {
    if (!c.blame?.rule_id || judged >= MAX_JUDGED) continue
    if (c.sendback && used.has(c.sendback.seq)) continue // already counted as a wrong
    judged++
    const text = c.prompt.prompt_text!.trim()
    const state = JSON.stringify({ prompt: text.slice(0, 400), ...(c.sendback ? { sendback: (c.sendback.reason ?? "").slice(0, 400) } : {}) })
    const key = c.sendback ? "contradicts" : "corrects"
    const a = (await judge({ [key]: c.sendback ? contradicts : corrects }, state))[key]
    if (a.source === "fallback") jevDown = true
    if (a.value < THRESHOLD) continue
    used.add(c.prompt.seq)
    out.push({ seq: c.prompt.seq, time: c.prompt.time, text, kind: c.sendback ? "sendback-contradicted" : "prompt-correction", session: c.prompt.session_id, rule_id: c.blame.rule_id })
  }
  return { corrections: out.sort((a, b) => a.seq - b.seq), jevDown }
}

// ---- proposals ----

export interface Edit {
  file: string // relative to the repo root, under harness/src/
  find: string
  replace: string
}
export interface Proposal {
  rule_id: string
  kind: "mode" | "message" | "match"
  summary: string
  edits: Edit[]
  eval: { event: Record<string, unknown>; expect: { outcome: string; ruleId?: string } }
}

const SRC_ROOT = resolve(dirname(import.meta.path), "..")

function sourceFor(rule: string, root: string): string {
  const hits: string[] = []
  const walk = (d: string) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = join(d, e.name)
      if (e.isDirectory()) walk(p)
      else if (e.name.endsWith(".ts") && readFileSync(p, "utf8").includes(`"${rule}"`)) hits.push(p)
    }
  }
  try {
    walk(root)
  } catch {}
  return hits
    .slice(0, 3)
    .map((p) => `--- harness/src/${p.slice(root.length + 1)}\n${readFileSync(p, "utf8").slice(0, 6000)}`)
    .join("\n\n")
}

export function proposalPrompt(rule: string, list: Correction[], source: string): string {
  const evidence = list.map((c) => `- (${c.kind}) ${c.text.slice(0, 300)}`).join("\n")
  return [
    `You maintain a rule engine called the harness. Rule "${rule}" was corrected by its owner ${list.length} times this week:`,
    evidence,
    "",
    "Relevant source:",
    source || "(no source file names this rule id)",
    "",
    "Propose ONE change: a rule mode change, a message rewrite, or a narrower match. Edit only files under harness/src/.",
    "Also give ONE eval case: a HarnessEvent as JSON and the expected outcome.",
    "Do not use tools and do not edit files. Reply with only this JSON:",
    `{"kind":"mode|message|match","summary":"one sentence","edits":[{"file":"harness/src/...","find":"exact text that occurs once","replace":"new text"}],"eval":{"event":{"event":"tool.before","toolName":"shell","input":{"command":"..."}},"expect":{"outcome":"allow|deny|modify|ask","ruleId":"optional"}}}`,
  ].join("\n")
}

export function parseProposal(rule: string, text: string): Proposal | null {
  const j = extractJson<any>(text)
  if (!j || typeof j !== "object" || !["mode", "message", "match"].includes(j.kind)) return null
  if (typeof j.summary !== "string" || !j.eval?.event || typeof j.eval.event !== "object" || typeof j.eval.event.event !== "string") return null
  if (typeof j.eval.expect?.outcome !== "string") return null
  const edits: Edit[] = Array.isArray(j.edits)
    ? j.edits.filter((e: any) => typeof e?.file === "string" && typeof e.find === "string" && typeof e.replace === "string")
    : []
  return { rule_id: rule, kind: j.kind, summary: j.summary.slice(0, 300), edits, eval: { event: j.eval.event, expect: j.eval.expect } }
}

const safeName = (s: string) => s.replace(/[^A-Za-z0-9_-]/g, "-")

export function evalTestSource(p: Proposal, date: string): string {
  const event = JSON.stringify({ v: 1, tool: "claude", session: "miner-eval", cwd: "/tmp", ...p.eval.event }, null, 2)
  const expect = JSON.stringify(p.eval.expect)
  return `// Eval case from the correction miner (D57), ${date}, rule ${p.rule_id}.
// Proposal: ${p.summary.replace(/\n/g, " ")}
import { afterEach, beforeEach, expect, test } from "bun:test"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { closeCore, decide } from "../../src/core.ts"

const event = ${event}
const expected: { outcome: string; ruleId?: string } = ${expect}

let dir: string
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-miner-"))
  process.env.HARNESS_STATE_DIR = dir
  delete process.env.HARNESS_DISABLE
})
afterEach(() => {
  closeCore()
  delete process.env.HARNESS_STATE_DIR
  rmSync(dir, { recursive: true, force: true })
})

test("miner eval ${p.rule_id} ${date}", async () => {
  const d = await decide({ ...event, time: Date.now() } as any)
  expect(d.outcome).toBe(expected.outcome)
  if (expected.ruleId) expect(d.ruleId).toBe(expected.ruleId)
})
`
}

// ---- plan, PR body, publish ----

export interface Plan {
  date: string
  corrections: Correction[]
  proposals: Proposal[]
  skipped: { rule_id: string; reason: string }[]
}

const iso = (t: number) => new Date(t).toISOString().replace("T", " ").slice(0, 16) + "Z"
const cell = (s: string) => s.replace(/\|/g, "\\|").replace(/\s+/g, " ").slice(0, 200)

export function prBody(plan: Plan): string {
  const byRule = new Map<string, Correction[]>()
  for (const c of plan.corrections) byRule.set(c.rule_id, [...(byRule.get(c.rule_id) ?? []), c])
  const sections = plan.proposals.map((p) => {
    const rows = (byRule.get(p.rule_id) ?? []).map((c) => `| ${c.seq} | ${iso(c.time)} | ${c.kind} | ${cell(c.text)} |`).join("\n")
    const files = p.edits.map((e) => `\`${e.file}\``).join(", ") || "no source change"
    return [
      `## ${p.rule_id}`,
      "",
      `**Proposal (${p.kind}):** ${p.summary}`,
      "",
      `Files: ${files}. Eval: \`harness/tests/miner/${safeName(p.rule_id)}-${plan.date}.test.ts\`.`,
      "",
      "| seq | time | kind | text |",
      "| --- | --- | --- | --- |",
      rows,
    ].join("\n")
  })
  const skipped = plan.skipped.length ? ["", "## Not proposed", "", ...plan.skipped.map((s) => `- ${s.rule_id}: ${s.reason}`)] : []
  return [
    `The correction miner (D57) found ${plan.corrections.length} corrections in the last 7 days. This draft proposes one change per rule with at least 2 of them, and one eval each.`,
    "",
    "Why: Alex pushed back on these rules. A diff to review costs less than a session per fix. The miner never merges; merge needs `MERGE-OK`.",
    "",
    ...sections,
    ...skipped,
    "",
    "Proof: the eval tests are new and not yet run by the miner. Run `bun test tests/miner` in `harness/` before you trust a proposal.",
  ].join("\n")
}

export interface PublishDeps {
  repo: string
  remote?: string
  run?: (argv: string[], opts: { cwd: string; env?: Record<string, string> }) => { code: number; out: string }
}

function sh(argv: string[], o: { cwd: string; env?: Record<string, string> }) {
  const r = Bun.spawnSync(argv, { cwd: o.cwd, env: { ...(process.env as Record<string, string>), ...(o.env ?? {}) }, stdout: "pipe", stderr: "pipe" })
  return { code: r.exitCode ?? 1, out: r.stdout.toString() + r.stderr.toString() }
}

function applyEdits(wt: string, edits: Edit[]): boolean {
  const staged: [string, string][] = []
  for (const e of edits) {
    if (!/^harness\/src\//.test(e.file) || e.file.includes("..")) return false
    let text = staged.find(([f]) => f === e.file)?.[1]
    try {
      text ??= readFileSync(join(wt, e.file), "utf8")
    } catch {
      return false
    }
    if (text.split(e.find).length !== 2 || !e.find) return false // must match exactly once
    const next = text.replace(e.find, () => e.replace)
    const i = staged.findIndex(([f]) => f === e.file)
    if (i >= 0) staged[i] = [e.file, next]
    else staged.push([e.file, next])
  }
  for (const [f, t] of staged) writeFileSync(join(wt, f), t)
  return true
}

// Branch in a temp worktree of origin/main, commit, push as acastro2, open a DRAFT PR. Returns the URL.
export function publish(plan: Plan, d: PublishDeps): string {
  const run = d.run ?? sh
  const remote = d.remote ?? "origin"
  const branch = `harness/miner-${plan.date}`
  const tmp = mkdtempSync(join(tmpdir(), "harness-miner-wt-"))
  const wt = join(tmp, "wt")
  const must = (argv: string[], o: { cwd: string; env?: Record<string, string> }) => {
    const r = run(argv, o)
    if (r.code !== 0) throw new Error(`${argv.slice(0, 3).join(" ")}: ${r.out.trim().split("\n").pop()}`)
    return r.out.trim()
  }
  let added = false
  try {
    must(["git", "fetch", remote, "main"], { cwd: d.repo })
    must(["git", "worktree", "add", "-b", branch, wt, `${remote}/main`], { cwd: d.repo })
    added = true
    const kept: Proposal[] = []
    const skipped = [...plan.skipped]
    for (const p of plan.proposals) {
      if (p.edits.length && !applyEdits(wt, p.edits)) {
        skipped.push({ rule_id: p.rule_id, reason: `proposal "${p.summary}" did not apply (path outside harness/src/ or find text not unique)` })
        continue
      }
      const file = join(wt, "harness", "tests", "miner", `${safeName(p.rule_id)}-${plan.date}.test.ts`)
      mkdirSync(dirname(file), { recursive: true })
      writeFileSync(file, evalTestSource(p, plan.date))
      kept.push(p)
    }
    if (!kept.length) throw new Error("no proposal applied")
    const final = { ...plan, proposals: kept, skipped }
    must(["git", "add", "harness"], { cwd: wt })
    must(["git", "commit", "-qm", `feat(harness): miner proposals ${plan.date}`], { cwd: wt })
    const env = { GH_TOKEN: must(["gh", "auth", "token", "--user", "acastro2"], { cwd: d.repo }) }
    must(["git", "push", "-u", remote, branch], { cwd: wt, env })
    const bodyFile = join(tmp, "body.md")
    writeFileSync(bodyFile, prBody(final))
    return must(
      ["gh", "pr", "create", "--draft", "--repo", "acastro2/alex-skills", "--base", "main", "--head", branch, "--title", `feat(harness): miner proposals ${plan.date}`, "--body-file", bodyFile],
      { cwd: wt, env },
    )
      .split("\n")
      .pop()!
  } finally {
    if (added) run(["git", "worktree", "remove", "--force", wt], { cwd: d.repo })
    rmSync(tmp, { recursive: true, force: true })
  }
}

// ---- the job ----

export interface MinerOpts {
  run?: ModelRunner
  judge?: Judge
  now?: number
  dry?: boolean
  print?: (s: string) => void
  publish?: (plan: Plan) => string
  repo?: string
}

export function renderPlan(plan: Plan): string {
  const lines = [`miner plan ${plan.date}: ${plan.corrections.length} corrections, ${plan.proposals.length} proposals`]
  for (const p of plan.proposals) {
    lines.push(`- ${p.rule_id} [${p.kind}] ${p.summary}`)
    lines.push(`  edits: ${p.edits.map((e) => e.file).join(", ") || "none"}`)
    lines.push(`  eval: ${JSON.stringify(p.eval)}`)
  }
  for (const s of plan.skipped) lines.push(`- skipped ${s.rule_id}: ${s.reason}`)
  return lines.join("\n")
}

export async function runMiner(db: Database, o: MinerOpts = {}): Promise<string> {
  const now = o.now ?? Date.now()
  const dry = o.dry ?? process.env.HARNESS_MINER_DRY === "1"
  const run = o.run ?? opencodeRunner
  const { corrections, jevDown } = await collect(db, now, o.judge ?? realJudge)
  if (jevDown) append(db, { session_id: null, event: "job.note", reason: "jev-unavailable", data: { job: "correction-miner" } })
  if (!corrections.length) return "no corrections"

  const byRule = new Map<string, Correction[]>()
  for (const c of corrections) byRule.set(c.rule_id, [...(byRule.get(c.rule_id) ?? []), c])
  const plan: Plan = { date: new Date(now).toISOString().slice(0, 10), corrections, proposals: [], skipped: [] }
  for (const [rule, list] of byRule) {
    if (list.length < 2) continue
    try {
      const r = await run({ prompt: proposalPrompt(rule, list, sourceFor(rule, SRC_ROOT)) })
      const p = parseProposal(rule, r.text)
      if (p) plan.proposals.push(p)
      else plan.skipped.push({ rule_id: rule, reason: "the model reply was not a valid proposal" })
    } catch (e) {
      plan.skipped.push({ rule_id: rule, reason: `model call failed: ${(e as Error).message.slice(0, 200)}` })
    }
  }
  if (!plan.proposals.length) return `no proposals (${corrections.length} corrections, ${byRule.size} rules, ${plan.skipped.length} skipped)`

  if (dry) {
    ;(o.print ?? console.log)(renderPlan(plan))
    return `ok: dry run, ${plan.proposals.length} proposals`
  }
  const repo = o.repo ?? process.env.HARNESS_MINER_REPO ?? join(home(), ".agents", "skills")
  const url = (o.publish ?? ((p: Plan) => publish(p, { repo })))(plan)
  append(db, { session_id: null, event: "miner.pr", reason: url, data: { url, rules: plan.proposals.map((p) => p.rule_id), corrections: corrections.length } })
  return `ok: ${url}`
}
