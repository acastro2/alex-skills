// prompt event: Alex's control commands (D35, D28) and routing hints (D56).
import { command } from "../ledger/authority.ts"
import { markWrong, mode, setMode, type Mode } from "../ledger/registry.ts"
import { q1, type Env, type Out } from "./util.ts"

// Keyword rules only. Order matters: first match wins. Each hint is under 200 chars.
const HINTS: [RegExp, string][] = [
  [
    /\b(what did we|what have we|did we (decide|discuss|talk|ship|fix|agree)|why did we|last (week|time|session)|previous session|earlier session|past (decisions?|sessions?)|who (said|sent)|when was (the|that) meeting)\b/i,
    "Hint: use the archeologist subagent.",
  ],
  [
    /\b(as me|in my voice|as alex|on my behalf)\b|\b(draft|write|compose)\b.{0,30}\b(email|reply|message|post)\b.{0,30}\bfor me\b/i,
    "Hint: load alex-voice.",
  ],
  [
    /\b(docs?|documentation|api reference|syntax|latest version)\b.{0,60}\b(react|next\.?js|prisma|tailwind|django|express|vite|bun|library|framework|sdk|api)\b|\b(react|next\.?js|prisma|tailwind|django|express|vite|library|framework|sdk)\b.{0,60}\b(docs?|documentation|api|syntax)\b/i,
    "Hint: use Context7.",
  ],
]

export function routingHint(text: string): string | null {
  const t = text.slice(0, 2000)
  for (const [re, hint] of HINTS) if (re.test(t)) return hint
  return null
}

export interface PromptResult {
  context: string[]
  out: Pick<Out, "event" | "ruleId" | "reason" | "data">
}

export function handlePrompt(env: Env): PromptResult {
  const { db, ev } = env
  const text = ev.prompt ?? ""
  const isRoot = !ev.parentSession
  const cmd = command(db, { channel: "prompt", session: ev.session, isRootSession: isRoot, text })
  const context: string[] = []
  const out: PromptResult["out"] = {}

  if (cmd.kind === "grant") {
    const line = text.split(/\r?\n/, 1)[0].trim()
    context.push(
      cmd.grant === "merge"
        ? `harness: merge grant for PR ${/(\d+)$/.exec(line)?.[1] ?? "?"} recorded, valid 30 min.`
        : "harness: apply grant recorded, valid 30 min.",
    )
    out.data = { command: "grant", kind: cmd.grant, token_id: cmd.tokenId }
  } else if (cmd.kind === "switch") {
    out.data = { command: cmd.action, arg: cmd.arg ?? null }
    if (cmd.action === "off") context.push("harness: off. Every rule allows; the journal still records.")
    else if (cmd.action === "on") context.push("harness: on.")
    else if (cmd.action === "on-rule") {
      try {
        setMode(db, cmd.arg!, "enforce")
        context.push(`harness: rule ${cmd.arg} is back on (enforce).`)
      } catch (e: any) {
        context.push(`harness: ${e.message}.`)
      }
    } else if (cmd.action === "wrong") {
      const sb = q1<{ seq: number; rule_id: string }>(
        db,
        "select seq, rule_id from journal where session_id = ? and event = 'stop.sendback' and rule_id is not null order by seq desc limit 1",
        ev.session,
      )
      if (!sb) context.push("harness: no send-back in this session to mark.")
      else {
        const n = markWrong(db, sb.seq)
        const m = mode(db, sb.rule_id) as Mode
        context.push(
          `harness: marked send-back ${sb.rule_id} wrong (${n} today).${m === "advise" ? ` Rule ${sb.rule_id} is now advise-only.` : ""}`,
        )
        out.ruleId = sb.rule_id
      }
    } else if (cmd.action === "rollback") {
      // The applier comes later. The request row is this event's one row.
      out.event = "rollback.requested"
      context.push("harness: rollback requested. It is recorded; the applier is not installed yet.")
    }
  } else if (isRoot && !text.startsWith("/")) {
    const hint = routingHint(text)
    if (hint) {
      const m = mode(db, "routing-hint")
      if (m !== "off") {
        out.ruleId = "routing-hint"
        out.reason = hint
        if (m === "advise") out.data = { advise: true }
        else context.push(hint)
      }
    }
  }
  return { context, out }
}
