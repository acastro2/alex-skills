// stop event: the Stop checks that ship in Phase 2 (spec: Stop checks table, D10, D27).
import { dirname } from "node:path"
import { existsSync } from "node:fs"
import { judge, type Question } from "../judgment.ts"
import { mode } from "../ledger/registry.ts"
import { scrub } from "../ledger/journal.ts"
import { cleanupCheck, handoffProtocolCheck } from "./cleanup.ts"
import { processCheck } from "./processes.ts"
import { overLimit } from "./resources.ts"
import { turnOf, type Call, type Turn } from "../turn.ts"
import { allow, git, hit, latestTodos, q1, type Env, type Out } from "./util.ts"

export const SENDBACK_CAP = 5
const THRESHOLD = 0.8
const UNSURE_LOW = 0.2
const JUDGE_TIMEOUT_MS = 2000 // the adapters time the core out at 2.5 s, so Jev gets less than the 3 s of D27

const UI_FILE = /\.(html|css|tsx|vue|svelte)$/i
const SCRATCH = /^\/tmp\/|^\/(private\/)?var\/folders\// // Linux and macOS temp folders
const PUSH_OR_CREATE = /\bgit\s+(-C\s+\S+\s+)?push\b|\bgh\s+(pr|issue)\s+create\b/
const MCP_CREATE = /^mcp:[^:]+:\w*(create|publish)\w*(issue|page|content|ticket|comment|pull|pr)\b|^mcp:[^:]+:\w*add\w*comment/i
const LIVE_CHECK = /\bgh\s+(pr|issue|run)\s+(view|list|checks|status)\b|\bgh\s+api\b/
const MCP_LIVE = /^mcp:(atlassian|slack|m365|github)/i

interface Check {
  id: string
  message: string
  data?: Record<string, unknown>
}

function existingDir(p: string): string | null {
  let d = dirname(p)
  while (d && d !== "/" && !existsSync(d)) d = dirname(d)
  return existsSync(d) ? d : null
}

function commitCheck(paths: string[]): Check | null {
  const dirty: string[] = []
  for (const p of paths) {
    const dir = existingDir(p)
    if (!dir) continue
    const st = git(["status", "--porcelain", "--", p], dir)
    if (st.ok && st.out) dirty.push(p)
  }
  if (!dirty.length) return null
  return {
    id: "stop-commit",
    message: `Uncommitted changes you made: ${dirty.slice(0, 5).join(", ")}. Commit them (and push if the work is verified).`,
    data: { paths: dirty.slice(0, 20) },
  }
}

function linksCheck(calls: Call[], reply: string): Check | null {
  if (/https?:\/\//.test(reply)) return null
  const did = calls.filter((c) => !c.failed).some((c) => (c.kind === "shell" && PUSH_OR_CREATE.test(c.arg)) || MCP_CREATE.test(c.tool))
  return did ? { id: "stop-links", message: "This turn pushed or created something but the reply has no URL. Add the direct link to each change." } : null
}

const hasOpenTodo = (env: Env) => latestTodos(env.db, env.ev.session).some((t) => t.status === "pending" || t.status === "in_progress")

function uiProofCheck(calls: Call[]): Check | null {
  // A file in a temp folder is a scratch artifact (a report, a mock), not the product's UI (seen live 2026-11-27).
  const ui = calls.filter((c) => c.kind === "edit" && !c.failed && c.path !== undefined && UI_FILE.test(c.path) && !SCRATCH.test(c.path))
  if (!ui.length) return null
  const last = ui[ui.length - 1]
  const shot = calls.some((c) => c.seq > last.seq && c.kind === "browse" && /screenshot/i.test(c.tool))
  return shot ? null : { id: "stop-ui-proof", message: `UI files changed (${last.path}) with no browse screenshot after the last edit. Take one and show it.` }
}

const DONE_CLAIM = /\b(done|fixed|works|working|complete|implemented)\b/i
const GIT_COMMIT = /\bgit\s+(?:-C\s+\S+\s+)?commit\b/

// D47: a "done" claim after a code edit needs a green bundle from this turn.
function proofCheck(env: Env, edited: string[], reply: string): Check | null {
  if (!edited.some((p) => !/\.md$/i.test(p))) return null
  if (!DONE_CLAIM.test(reply)) return null
  const green = q1(
    env.db,
    `select 1 as x from journal where session_id = ? and event = 'bundle' and outcome = 'green'
       and seq > coalesce((select min(seq) from journal where session_id = ? and turn = ?), 0) limit 1`,
    env.ev.session,
    env.ev.session,
    env.turn,
  )
  return green ? null : { id: "stop-proof", message: "You said it is done, but this turn has no green proof bundle. Call the `verify` tool with the commands that prove it." }
}

// D6, D38: a commit after the workstream entry was last touched means the handoff is stale.
function handoffCheck(env: Env, calls: Call[]): Check | null {
  const ws = q1<{ t: number | null }>(
    env.db,
    "select max(updated_at) as t from workstreams where owner_session_id = ? and coalesce(state, '') != 'done'",
    env.ev.session,
  )
  if (ws?.t == null) return null
  const stale = calls.some((c) => c.kind === "shell" && !c.failed && GIT_COMMIT.test(c.arg) && c.time > ws.t!)
  return stale ? { id: "stop-handoff", message: "Update your workstream entry with `workstream_update`: state and next steps." } : null
}

// stop-resources: this session's live processes over the idle, memory or CPU limit, one kill line each.
function resourcesCheck(env: Env): Check | null {
  const over = overLimit(env.db, env.ev.session)
  if (!over.length) return null
  return {
    id: "stop-resources",
    message: `Processes over the limits. Kill them, or keep one with \`keep_process\` if Alex asked:\n${over.slice(0, 10).map((o) => o.line).join("\n")}`,
    data: { resources: over.slice(0, 10).map((o) => ({ pid: o.pid, program: o.program, rssMb: o.rssMb, cpu: o.cpu, ageS: o.ageS })) },
  }
}

// ---- judgment checks: fallbacks are strict, so Jev being down never adds send-backs ----

const tail = (s: string, n: number) => s.slice(-n)
const field = (s: string, _name: string) => s.split(/\nLive checks: /)[0].replace(/^Reply: /, "")

const ASKS = /\?|\b(let me know|do you want|should i|your call|please confirm|waiting on you|which (one|option))\b/i
const FOOTER = /\b(next|done|finished|complete[d]?|running|left|remaining|blocked|not run)\b/i
const STALE =
  /\balready (merged|sent)\b|\b(still|is|are) (open|waiting|pending)\b|\bawaiting (review|approval|merge)\b|\b(pr|review|ticket)\b[^.\n]{0,40}\b(open|waiting|pending)\b/i
const CANT = /\b(i can(?:no|')t|cannot|can't|unable to|you(?:'ll| will)? (?:need|have) to|please (?:open|click|log|do)|manually)\b/i
const BROWSER = /\b(browser|web ?page|website|portal|dashboard|tab|click|ui)\b/i
const HUMAN_ONLY = /\b(log ?in|sign[- ]?in|2fa|passkey|captcha|payment|password)\b/i

// The closing plan of a reply: the text after the last "Next:", else from the first "Then I". Null when there is none.
function planOf(reply: string): string | null {
  const t = tail(reply, 900)
  const next = [...t.matchAll(/\bnext\s*:/gi)].pop()
  if (next) return t.slice(next.index! + next[0].length).trim()
  const then = /\bthen,? i\b/i.exec(t)
  return then ? t.slice(then.index).trim() : null
}

// Strict fallback: only "I <own-work verb>" with no question in the plan. Alex's steps ("you merge", MERGE-OK) never match.
const OWN_STEP =
  /\b(?:i|i'll|i will)\s+(?:then\s+)?(?:update|fix|write|add|open|run|validate|implement|create|commit|push|edit|change|build|refactor|rewrite|test|re-?run|approve|log|document|check|review)\b/i

const QUESTIONS: Record<string, Question> = {
  piecemeal: {
    q: "Does the closing plan of the `reply` (after \"Next:\" or \"Then I\") contain work the agent can run itself (code, tests, PR updates, validation, writing a log, approving in a tool), rather than only steps that belong to Alex (merge or MERGE-OK, prod apply, passkey or 2FA, a decision or a question)?",
    fallback: (s) => {
      const plan = planOf(field(s, "Reply"))
      return plan && !plan.includes("?") && OWN_STEP.test(plan) ? 1 : 0
    },
  },
  asks: { q: "Does the `reply` ask the user a question or wait on them?", fallback: (s) => (ASKS.test(field(s, "Reply")) ? 1 : 0) },
  footer: {
    q: "Does the `reply` end by saying what is done, what is running, and the next step?",
    fallback: (s) => (FOOTER.test(tail(field(s, "Reply"), 600)) ? 1 : 0),
  },
  stale: {
    q: "Does the `reply` claim a PR, review or ticket is still open or waiting, without the turn having checked it live (see `Live checks`)?",
    fallback: (s) => (STALE.test(field(s, "Reply")) && /^Live checks: none/m.test(s) ? 1 : 0),
  },
  cant: {
    q: "Does the `reply` say it cannot do something, or ask the user to do it manually, for a task that could be done in a browser?",
    fallback: (s) => {
      const r = field(s, "Reply")
      return CANT.test(r) && BROWSER.test(r) && !HUMAN_ONLY.test(r) ? 1 : 0
    },
  },
}

const usesBrowse = (turn: Turn): boolean => process.env.HARNESS_BROWSE === "1" || turn.browsed

// What a stop check sees. `data` is the journal data of this stop; the judgment entry adds what Jev said.
export interface StopCtx {
  env: Env
  turn: Turn
  reply: string
  checkedLive: boolean
  worker: boolean
  ownWt: string[] // worktrees a worker owns (empty for a root session)
  data: Record<string, unknown>
}

export interface StopCheck {
  name: string
  rules: string[] // the rule ids this check can emit
  run(c: StopCtx): Check[] | Promise<Check[]>
}

const on = (env: Env, id: string) => mode(env.db, id) !== "off"

// A check with one rule: it runs (and may cost a git call) only while its rule is not off.
const single = (id: string, f: (c: StopCtx) => Check | null, when: (c: StopCtx) => boolean = () => true): StopCheck => ({
  name: id,
  rules: [id],
  run: (c) => {
    if (!on(c.env, id) || !when(c)) return []
    const r = f(c)
    return r ? [r] : []
  },
})

// One Jev call carries every judgment this stop needs.
async function judgments(c: StopCtx): Promise<Check[]> {
  const { env, turn: t, reply, checkedLive, data } = c
  const fired: Check[] = []
  const add = (x: Check | null) => x && on(env, x.id) && fired.push(x)
  const want: string[] = []
  const needContinue = on(env, "stop-continue") && hasOpenTodo(env)
  if (needContinue) want.push("asks")
  if (on(env, "stop-state") && reply.length > 400) want.push("footer")
  if (on(env, "stop-stale-state") && !checkedLive) want.push("stale")
  // A step that is a passkey, login, 2FA, captcha or payment is Alex's by the rule itself, and a turn that already
  // tried handoff did what the rule asks (seen live 2026-11-25: five false send-backs on passkey taps).
  const alexOnly = /\b(passkey|pass key|sign[ -]?in|log[ -]?in|2fa|two-factor|captcha|payment|touch id)\b/i.test(reply)
  if (on(env, "stop-false-cant") && usesBrowse(t) && !alexOnly && !t.triedHandoff) want.push("cant")
  if (on(env, "stop-piecemeal") && planOf(reply)) want.push("piecemeal")
  if (!want.length) return fired
  const summary = scrub(
    [
      `Reply: ${tail(reply, 900)}`,
      `Live checks: ${checkedLive ? "yes" : "none"}`,
      `Tools this turn: ${[...new Set(t.calls.map((c) => c.tool))].slice(0, 12).join(", ") || "none"}`,
    ].join("\n"),
  ).slice(0, 1500)
  const ans = await judge(Object.fromEntries(want.map((k) => [k, QUESTIONS[k]])), summary, { timeoutMs: JUDGE_TIMEOUT_MS })
  if (want.some((k) => ans[k].source === "fallback")) data.jev = "jev-unavailable"
  data.judged = Object.fromEntries(want.map((k) => [k, ans[k].value]))
  const v = (k: string) => ans[k]?.value
  if (want.includes("piecemeal") && v("piecemeal") >= THRESHOLD) {
    const steps = (planOf(reply) ?? "").replace(/\s+/g, " ").slice(0, 300)
    add({ id: "stop-piecemeal", message: `Do these now, they are yours: ${steps}. Only Alex's steps may end a turn.` })
  }
  if (want.includes("asks") && v("asks") <= UNSURE_LOW) {
    add({ id: "stop-continue", message: "The todo list still has open items and your reply asks nothing. Continue with the next item, or ask Alex what you need." })
  }
  if (want.includes("footer") && v("footer") <= UNSURE_LOW) {
    add({ id: "stop-state", message: "End the reply with what is done, what is running, and the next step." })
  }
  if (want.includes("stale") && v("stale") >= THRESHOLD) {
    add({ id: "stop-stale-state", message: "You say something is still open or waiting, but you did not check it this turn. Check it live (gh pr view, the ticket, the inbox), then restate." })
  }
  if (want.includes("cant") && v("cant") >= THRESHOLD) {
    add({ id: "stop-false-cant", message: "You say you cannot do this, or ask Alex to do it. Use browser control (`browse`). Only login, 2FA, passkey, captcha or payment go to Alex, through `handoff`." })
  }
  return fired
}

export const STOP_CHECKS: StopCheck[] = [
  // A worker outside its own worktree may not commit (its contract); the parent commits, and the harness
  // verifies the worker on its own. So these two checks apply to a worker only inside a worktree it owns.
  single("stop-commit", (c) => {
    const inOwn = (p: string) => c.ownWt.some((w) => p === w || p.startsWith(`${w}/`))
    return commitCheck(c.worker ? c.turn.edited.filter(inOwn) : c.turn.edited)
  }),
  single("stop-links", (c) => linksCheck(c.turn.calls, c.reply)),
  single("stop-ui-proof", (c) => uiProofCheck(c.turn.calls)),
  single("stop-proof", (c) => proofCheck(c.env, c.turn.edited, c.reply), (c) => !c.worker || c.ownWt.length > 0),
  single("stop-handoff", (c) => handoffCheck(c.env, c.turn.calls)),
  single("stop-resources", (c) => resourcesCheck(c.env)),
  single("stop-processes", (c) => processCheck(c.env, c.reply)),
  single("stop-cleanup", (c) => cleanupCheck(c.env)),
  single("stop-handoff-protocol", (c) => handoffProtocolCheck(c.env, c.turn)),
  { name: "judgments", rules: ["stop-piecemeal", "stop-continue", "stop-state", "stop-stale-state", "stop-false-cant"], run: judgments },
]

export async function stopChecks(env: Env): Promise<Out> {
  const { db, ev, turn } = env
  const reply = ev.reply ?? ""
  const t = turnOf(db, ev.session, turn)
  const data: Record<string, unknown> = { reply: reply.slice(0, 4000) }
  const checkedLive = t.calls.some((c) => (c.kind === "shell" && LIVE_CHECK.test(c.arg)) || MCP_LIVE.test(c.tool))
  const worker = !!ev.parentSession
  const ownWt = worker
    ? (db.query("select path from worktrees where session_id = ? and removed_at is null").all(ev.session) as { path: string }[]).map((w) => w.path)
    : []
  const ctx: StopCtx = { env, turn: t, reply, checkedLive, worker, ownWt, data }

  const fired: Check[] = []
  for (const c of STOP_CHECKS) fired.push(...(await c.run(ctx)))
  if (!fired.length) return allow({ data })

  // stopActive: the agent was already sent back once. Do not repeat a check that fired last time.
  let todo = fired
  if (ev.stopActive) {
    const last = q1<{ data_json: string | null }>(
      db,
      "select data_json from journal where session_id = ? and turn = ? and event = 'stop.sendback' order by seq desc limit 1",
      ev.session,
      turn,
    )
    const prev: string[] = last?.data_json ? (JSON.parse(last.data_json).checks ?? []) : []
    todo = fired.filter((c) => !prev.includes(c.id))
    if (!todo.length) return allow({ data: { ...data, repeated: fired.map((c) => c.id) }, reason: `already sent back for: ${fired.map((c) => c.id).join(", ")}` })
  }

  // OpenCode has no stop_hook_active: the journal says which rules already sent this agent back this turn.
  // A rule sends back once per turn; the repeat is journaled as advise and the stop goes through.
  const done = new Set<string>()
  for (const r of db
    .query("select rule_id, data_json from journal where session_id = ? and turn = ? and event = 'stop.sendback'")
    .all(ev.session, turn) as { rule_id: string | null; data_json: string | null }[]) {
    if (r.rule_id) done.add(r.rule_id)
    try {
      for (const id of JSON.parse(r.data_json ?? "{}").checks ?? []) done.add(id)
    } catch {}
  }
  const again = todo.filter((c) => done.has(c.id))
  if (again.length) {
    todo = todo.filter((c) => !done.has(c.id))
    data.sentBack = again.map((c) => c.id)
    if (!todo.length) {
      return allow({
        ruleId: again[0].id,
        outcome: "advise",
        reason: `already sent back this turn: ${again.map((c) => `${c.id}: ${c.message}`).join(" | ")}`,
        data: { ...data, advised: again.map((c) => c.id) },
      })
    }
  }

  const sent = (q1<{ c: number }>(db, "select count(*) as c from sendbacks where session_id = ? and turn = ?", ev.session, turn) ?? { c: 0 }).c
  const ids = todo.map((c) => c.id)
  if (sent >= SENDBACK_CAP) {
    return allow({ data: { ...data, capped: ids }, reason: `cap reached: ${ids.join(", ")}` })
  }

  // Enforce hits send back; advise hits are only logged.
  const enforced: Check[] = []
  const advised: Check[] = []
  for (const c of todo) {
    const h = hit(env, c.id, c.message)
    if (h?.decision.outcome === "deny") enforced.push(c)
    else if (h) advised.push(c)
  }
  const checksData = { ...data, checks: enforced.map((c) => c.id), ...Object.assign({}, ...enforced.map((c) => c.data ?? {})) }
  if (!enforced.length) {
    return allow({ ruleId: advised[0].id, outcome: "advise", reason: advised.map((c) => `${c.id}: ${c.message}`).join(" | "), data: { ...data, advised: advised.map((c) => c.id) } })
  }
  const message = enforced.map((c) => `[${c.id}] ${c.message}`).join("\n")
  return {
    decision: { outcome: "deny", message, ruleId: enforced[0].id },
    event: "stop.sendback",
    ruleId: enforced[0].id,
    outcome: "deny",
    reason: message,
    data: checksData,
  }
}
