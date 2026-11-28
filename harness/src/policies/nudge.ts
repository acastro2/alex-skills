// tool.after: the PR watch hook, drift nudge (D75), wrap-up (D76) and the question journal.
import { mode } from "../ledger/registry.ts"
import { judge } from "../judgment.ts"
import { addWatch } from "../waker/waker.ts"
import { toolKind, turnOf } from "../turn.ts"
import { allow, firstLine, latestTodos, q1, shortArg, toolData, type Env, type Out } from "./util.ts"

const DRIFT_EVERY = 20
const NUDGE_CAP = 5
const WRAPUP_MS = 30 * 60_000
const DRIFT_ON = 0.2 // on-task probability at or below this = off task at 0.80 or above
export const BUDGET_RE = /^BUDGET:\s*(\d+)\s*min/im

const PR_URL = /https:\/\/github\.com\/([\w.-]+\/[\w.-]+)\/pull\/(\d+)/

// The session's goal: a worker's first prompt line, else the todo in progress, else the first open todo.
export function goalOf(env: Env): string | null {
  const { db, ev } = env
  if (ev.parentSession) {
    const p = q1<{ prompt_text: string }>(
      db,
      "select prompt_text from journal where session_id = ? and event = 'prompt' and prompt_text is not null order by seq desc limit 1",
      ev.session,
    )
    const line = p ? firstLine(p.prompt_text.replace(/^HARNESS-CONTRACT.*$/m, "")) : ""
    if (line) return line.slice(0, 200)
  }
  const open = latestTodos(db, ev.session).filter((t) => t.status !== "completed" && t.status !== "cancelled")
  const t = open.find((x) => x.status === "in_progress") ?? open[0]
  return t?.content ? t.content.slice(0, 200) : null
}

function budgetMs(env: Env): number {
  const p = q1<{ prompt_text: string }>(
    env.db,
    "select prompt_text from journal where session_id = ? and event = 'prompt' and prompt_text is not null order by seq limit 1",
    env.ev.session,
  )
  const m = p ? BUDGET_RE.exec(p.prompt_text) : null
  return m ? Number(m[1]) * 60_000 : WRAPUP_MS
}

export async function afterTool(env: Env): Promise<Out> {
  const { db, ev, turn } = env
  const base = toolData(ev)
  const kind = toolKind(ev.toolName)

  // gh pr create: watch the new PR so the waker can wake this session.
  if (kind === "shell" && !ev.failed && /\bgh\s+pr\s+create\b/.test(String(ev.input?.command ?? ""))) {
    const m = PR_URL.exec(ev.output ?? "")
    if (m) {
      const target = `${m[1]}#${m[2]}`
      addWatch(db, { session: ev.session, kind: "pr", target })
      base.watch = target
    }
  }

  // A question tool call that got its answer.
  if (kind === "question") {
    const last = q1<{ event: string }>(
      db,
      "select event from journal where session_id = ? and event in ('question.asked', 'question.answered') order by seq desc limit 1",
      ev.session,
    )
    if (last?.event === "question.asked") return allow({ event: "question.answered", data: base })
  }

  // Wrap-up for workers, once.
  if (ev.parentSession && mode(db, "nudge-wrapup") !== "off") {
    const started = q1<{ started_at: number }>(db, "select started_at from sessions where id = ?", ev.session)
    const done = q1(db, "select 1 as x from journal where session_id = ? and rule_id = 'nudge-wrapup' limit 1", ev.session)
    if (started && !done && ev.time - started.started_at >= budgetMs(env)) {
      const text = "Time budget reached: finish the current step, commit, and report what is done and what is left."
      return nudge(env, "nudge-wrapup", text, base)
    }
  }

  // Drift: every 20th tool call in the turn.
  const dm = mode(db, "nudge-drift")
  if (dm === "off") return allow({ data: base })
  const rows = turnOf(db, ev.session, turn).calls
  if ((rows.length + 1) % DRIFT_EVERY !== 0) return allow({ data: base })
  const goal = goalOf(env)
  if (!goal) return allow({ data: base })

  const nudged = (q1<{ c: number }>(db, "select count(*) as c from nudges where session_id = ? and turn = ?", ev.session, turn) ?? { c: 0 }).c
  if (nudged >= NUDGE_CAP) {
    if (q1(db, "select 1 as x from journal where session_id = ? and turn = ? and event = 'stuck' limit 1", ev.session, turn)) {
      return allow({ data: base })
    }
    return allow({ event: "stuck", ruleId: "nudge-drift", reason: `${nudged} nudges this turn, none helped`, data: { ...base, nudges: nudged } })
  }

  const recent = [...rows.slice(-(DRIFT_EVERY - 1)).map((r) => r.data), base]
  const summary = `Goal: ${goal}\nLast ${recent.length} tool calls:\n${recent.map((d) => `${d.tool}: ${shortArg(String(d.arg ?? ""), 80)}`).join("\n")}`
  const ans = await judge(
    { ontask: { q: "Is this recent activity on task for the goal?", fallback: () => 1 } },
    summary,
    { timeoutMs: 2000 },
  )
  const a = ans.ontask
  const data = { ...base, ...(a.source === "fallback" ? { jev: "jev-unavailable" } : {}), ontask: a.value }
  if (a.source === "jev" && a.value <= DRIFT_ON) {
    const text = `You are drifting from ${goal}. Wrap up: finish ${nextStep(env, goal)}, run the acceptance commands, report.`
    return nudge(env, "nudge-drift", text, data)
  }
  return allow({ data })
}

const nextStep = (env: Env, goal: string): string => {
  const open = latestTodos(env.db, env.ev.session).filter((t) => t.status !== "completed" && t.status !== "cancelled")
  return open[0]?.content?.slice(0, 120) ?? goal
}

function nudge(env: Env, ruleId: string, text: string, data: Record<string, unknown>): Out {
  // advise logs the nudge but does not inject it.
  const inject = mode(env.db, ruleId) !== "advise"
  return {
    decision: inject ? { outcome: "modify", context: text, ruleId } : { outcome: "allow", ruleId },
    event: "nudge",
    ruleId,
    outcome: inject ? "inject" : "advise",
    reason: text,
    data,
  }
}
