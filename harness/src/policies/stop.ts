// stop event: the Stop checks that ship in Phase 2 (spec: Stop checks table, D10, D27).
import { dirname } from "node:path"
import { existsSync } from "node:fs"
import { judge, type Question } from "../judgment.ts"
import { mode } from "../ledger/registry.ts"
import { scrub } from "../ledger/journal.ts"
import { allow, git, hit, isBrowseTool, latestTodos, q1, toolRows, type Env, type Out, type ToolRow } from "./util.ts"

export const SENDBACK_CAP = 5
const THRESHOLD = 0.8
const UNSURE_LOW = 0.2
const JUDGE_TIMEOUT_MS = 2000 // the adapters time the core out at 2.5 s, so Jev gets less than the 3 s of D27

const UI_FILE = /\.(html|css|tsx|vue|svelte)$/i
const PUSH_OR_CREATE = /\bgit\s+(-C\s+\S+\s+)?push\b|\bgh\s+(pr|issue)\s+create\b/
const MCP_CREATE = /^mcp:[^:]+:\w*(create|publish)\w*(issue|page|content|ticket|comment|pull|pr)\b|^mcp:[^:]+:\w*add\w*comment/i
const LIVE_CHECK = /\bgh\s+(pr|issue|run)\s+(view|list|checks|status)\b|\bgh\s+api\b/
const MCP_LIVE = /^mcp:(atlassian|slack|m365|github)/i

interface Check {
  id: string
  message: string
  data?: Record<string, unknown>
}

const isEdit = (d: Record<string, any>) => (d.tool === "edit" || d.tool === "write") && typeof d.path === "string" && !d.failed

function editedPaths(rows: ToolRow[]): string[] {
  return [...new Set(rows.filter((r) => isEdit(r.data)).map((r) => r.data.path as string))]
}

function existingDir(p: string): string | null {
  let d = dirname(p)
  while (d && d !== "/" && !existsSync(d)) d = dirname(d)
  return existsSync(d) ? d : null
}

function commitCheck(rows: ToolRow[]): Check | null {
  const dirty: string[] = []
  for (const p of editedPaths(rows)) {
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

function linksCheck(rows: ToolRow[], reply: string): Check | null {
  if (/https?:\/\//.test(reply)) return null
  const did = rows.filter((r) => !r.data.failed).some((r) => {
    const t = String(r.data.tool ?? "")
    return (t === "shell" && PUSH_OR_CREATE.test(String(r.data.arg ?? ""))) || MCP_CREATE.test(t)
  })
  return did ? { id: "stop-links", message: "This turn pushed or created something but the reply has no URL. Add the direct link to each change." } : null
}

const hasOpenTodo = (env: Env) => latestTodos(env.db, env.ev.session).some((t) => t.status === "pending" || t.status === "in_progress")

function uiProofCheck(rows: ToolRow[]): Check | null {
  const ui = rows.filter((r) => isEdit(r.data) && UI_FILE.test(r.data.path))
  if (!ui.length) return null
  const last = ui[ui.length - 1].seq
  const shot = rows.some((r) => r.seq > last && isBrowseTool(r.data.tool) && /screenshot/i.test(String(r.data.tool)))
  return shot
    ? null
    : { id: "stop-ui-proof", message: `UI files changed (${ui[ui.length - 1].data.path}) with no browse screenshot after the last edit. Take one and show it.` }
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

const QUESTIONS: Record<string, Question> = {
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

function usesBrowse(env: Env): boolean {
  if (process.env.HARNESS_BROWSE === "1") return true
  const r = q1(env.db, `select 1 as x from journal where session_id = ? and data_json like '%"tool":"mcp:browse:%' limit 1`, env.ev.session)
  return !!r
}

export async function stopChecks(env: Env): Promise<Out> {
  const { db, ev, turn } = env
  const reply = ev.reply ?? ""
  const rows = toolRows(db, ev.session, turn)
  const data: Record<string, unknown> = { reply: reply.slice(0, 4000) }
  const live = (r: ToolRow) => (r.data.tool === "shell" && LIVE_CHECK.test(String(r.data.arg ?? ""))) || MCP_LIVE.test(String(r.data.tool ?? ""))
  const checkedLive = rows.some(live)

  const on = (id: string) => mode(db, id) !== "off"
  const fired: Check[] = []
  const add = (c: Check | null) => c && on(c.id) && fired.push(c)

  if (on("stop-commit")) add(commitCheck(rows))
  if (on("stop-links")) add(linksCheck(rows, reply))
  if (on("stop-ui-proof")) add(uiProofCheck(rows))

  // One Jev call carries every judgment this stop needs.
  const want: string[] = []
  const needContinue = on("stop-continue") && hasOpenTodo(env)
  if (needContinue) want.push("asks")
  if (on("stop-state") && reply.length > 400) want.push("footer")
  if (on("stop-stale-state") && !checkedLive) want.push("stale")
  if (on("stop-false-cant") && usesBrowse(env)) want.push("cant")
  if (want.length) {
    const summary = scrub(
      [
        `Reply: ${tail(reply, 900)}`,
        `Live checks: ${checkedLive ? "yes" : "none"}`,
        `Tools this turn: ${[...new Set(rows.map((r) => r.data.tool))].slice(0, 12).join(", ") || "none"}`,
      ].join("\n"),
    ).slice(0, 1500)
    const ans = await judge(Object.fromEntries(want.map((k) => [k, QUESTIONS[k]])), summary, { timeoutMs: JUDGE_TIMEOUT_MS })
    if (want.some((k) => ans[k].source === "fallback")) data.jev = "jev-unavailable"
    data.judged = Object.fromEntries(want.map((k) => [k, ans[k].value]))
    const v = (k: string) => ans[k]?.value
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
  }
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
