import type { Database } from "bun:sqlite"
import { getMeta, setMeta } from "./db.ts"
import { isOff } from "./authority.ts"
import { append } from "./journal.ts"

export type Mode = "enforce" | "advise" | "inject" | "off"

export interface Rule {
  id: string
  event: string
  module: string
  default_mode: Mode
  ships_in: string // phase number from the spec
}

const rule = (id: string, event: string, module: string, ships_in: string, default_mode: Mode = "enforce"): Rule => ({
  id,
  event,
  module,
  default_mode,
  ships_in,
})

export const RULES: Rule[] = [
  rule("recursive-delete", "tool.before", "destructive", "1"),
  rule("merge-in-shell", "tool.before", "destructive", "1"),
  rule("destructive-git", "tool.before", "destructive", "1"),
  rule("push-gate", "tool.before", "worker", "3", "advise"), // log-only until verify works (D44)
  rule("ledger-write", "tool.before", "authority", "1"),
  rule("harness-self", "tool.before", "authority", "1"),
  rule("harness-config-write", "tool.before", "authority", "1"),
  rule("main-checkout-write", "tool.before", "worktree", "5"),
  rule("stop-commit", "stop", "stop", "2"),
  rule("stop-links", "stop", "stop", "2"),
  rule("stop-continue", "stop", "stop", "2"),
  rule("stop-ui-proof", "stop", "stop", "2"),
  rule("stop-state", "stop", "stop", "2"),
  rule("stop-handoff", "stop", "stop", "5"),
  rule("stop-proof", "stop", "stop", "3"),
  rule("stop-processes", "stop", "stop", "5"),
  rule("stop-cleanup", "stop", "stop", "5"),
  rule("stop-handoff-protocol", "stop", "stop", "5"),
  rule("stop-stale-state", "stop", "stop", "2"),
  rule("stop-false-cant", "stop", "stop", "2"),
  rule("spawn-model", "tool.before", "worker", "3"),
  rule("spawn-acceptance", "tool.before", "worker", "3"),
  rule("egress", "tool.before", "egress", "9", "advise"), // advisory only (D62)
  rule("routing-hint", "prompt", "judgment", "2", "inject"),
  rule("nudge-drift", "tool.after", "worker", "3", "inject"),
  rule("nudge-wrapup", "tool.after", "worker", "3", "inject"),
  rule("nudge-stall", "stop", "waker", "3", "inject"),
]

const WRONG_LIMIT = 3

function known(id: string): Rule {
  const r = RULES.find((x) => x.id === id)
  if (!r) throw new Error(`unknown rule: ${id}`)
  return r
}

export function seed(db: Database): void {
  const now = Date.now()
  const ins = db.query(
    "insert or ignore into rules(id, event, module, mode, default_mode, ships_in, wrong_today, updated_at) values(?, ?, ?, ?, ?, ?, 0, ?)",
  )
  db.transaction(() => {
    for (const r of RULES) ins.run(r.id, r.event, r.module, r.default_mode, r.default_mode, r.ships_in, now)
  }).immediate()
}

export function mode(db: Database, id: string): Mode {
  const r = known(id)
  const disabled = (process.env.HARNESS_DISABLE ?? "").split(",").map((s) => s.trim())
  if (disabled.includes(id) || isOff(db)) return "off"
  const row = db.query("select mode from rules where id = ?").get(id) as { mode: Mode } | null
  return row ? row.mode : r.default_mode
}

export function setMode(db: Database, id: string, to: Mode): void {
  known(id)
  // A rule that comes back on starts a fresh count, or one more wrong would flip it again (D28).
  const changed = db
    .query("update rules set mode = ?, wrong_today = case when ? = 'enforce' then 0 else wrong_today end, updated_at = ? where id = ?")
    .run(to, to, Date.now(), id).changes
  if (changed !== 1) throw new Error(`rule not seeded: ${id}`)
}

// Marks a send-back as false. Returns today's wrong count for its rule. The third one flips the rule to advise (D28).
export function markWrong(db: Database, sendbackSeq: number, now: number = Date.now()): number {
  return db
    .transaction(() => {
      const sb = db.query("select session_id, rule_id from journal where seq = ?").get(sendbackSeq) as {
        session_id: string | null
        rule_id: string | null
      } | null
      if (!sb?.rule_id) throw new Error(`no rule-tagged journal row at seq ${sendbackSeq}`)

      const day = new Date(now).toISOString().slice(0, 10)
      if (getMeta(db, "wrong_day") !== day) {
        db.query("update rules set wrong_today = 0").run()
        setMeta(db, "wrong_day", day)
      }
      append(db, {
        session_id: sb.session_id,
        event: "harness.wrong",
        rule_id: sb.rule_id,
        data: { sendback_seq: sendbackSeq },
        time: now,
      })
      db.query("update rules set wrong_today = wrong_today + 1, updated_at = ? where id = ?").run(now, sb.rule_id)
      const row = db.query("select wrong_today, mode from rules where id = ?").get(sb.rule_id) as {
        wrong_today: number
        mode: Mode
      }
      if (row.wrong_today >= WRONG_LIMIT && row.mode !== "off") {
        db.query("update rules set mode = 'advise' where id = ?").run(sb.rule_id)
      }
      return row.wrong_today
    })
    .immediate()
}
