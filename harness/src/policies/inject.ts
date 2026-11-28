// Phase 7 injections: text that matters at one moment, sent once per session, each with its own rule id.
//   inject-ui      first edit or write of a UI file
//   inject-coding  first edit or write of a code file when `coding` was not loaded
//   inject-links   an outward change: git push, gh pr create or merge, an Atlassian create or edit
// Claude gets the edit rules on PreToolUse. OpenCode has no before-context channel, so it gets them on that call's tool.after.
import { mode } from "../ledger/registry.ts"
import { parse } from "../shell/parse.ts"
import { q1, type Env } from "./util.ts"

export interface Injection {
  ruleId: string
  text: string
  advise: boolean // the rule is in advise mode: journal it, send nothing
}

const UI_FILE = /\.(tsx|jsx|vue|svelte|css|html|astro)$/i
// shortcut: a list of code extensions. Config and data files (json, yaml, toml) and docs do not count.
const CODE_FILE = /\.(tsx?|jsx?|mjs|cjs|vue|svelte|astro|css|scss|html|py|go|rs|java|kt|rb|php|c|h|cc|cpp|cs|swift|sh|bash|zsh|sql|tf|hcl|lua)$/i

const UI_TEXT = "UI file: load the `coding` skill's web UI reference and check accessibility; take a browse screenshot after the change."
const CODING_TEXT = "Code change: load the `coding` skill first (AGENTS.md)."
const LINKS_TEXT = "Outward change: put its direct URL in your reply."

const ATLASSIAN = /^mcp:([^:]*atlassian[^:]*):(create|edit|update|addOrEdit|transition|executeWrite|executeDestructive)/i

const fired = (env: Env, ruleId: string): boolean =>
  !!q1(env.db, "select 1 as x from journal where session_id = ? and rule_id = ? limit 1", env.ev.session, ruleId)

// `coding` counts as loaded when a skill call named it, or its SKILL.md was read.
function codingLoaded(env: Env): boolean {
  return !!q1(
    env.db,
    `select 1 as x from journal where session_id = ? and data_json is not null
       and ((data_json like '%"tool":"skill"%' and data_json like '%coding%') or (data_json like '%"tool":"read"%' and data_json like '%coding/SKILL.md%')) limit 1`,
    env.ev.session,
  )
}

function isOutward(env: Env): boolean {
  const { ev } = env
  if (ev.toolName === "shell") {
    return parse(String(ev.input?.command ?? "")).commands.some(
      (c) =>
        (c[0] === "git" && c.includes("push")) ||
        (c[0] === "gh" && c.includes("pr") && (c.includes("create") || c.includes("merge"))),
    )
  }
  return ATLASSIAN.test(ev.toolName ?? "")
}

const PR_BATCH_TEXT =
  "One PR per job: push the next steps to the PR you already opened (one commit per step), and open a new PR only for a different job."

const isCreate = (c: string[]): boolean => c[0] === "gh" && c.includes("pr") && c.includes("create")

function isPrCreate(env: Env): boolean {
  return parse(String(env.ev.input?.command ?? "")).commands.some(isCreate)
}

// An earlier, successful `gh pr create` by this session. The current call is not in the journal yet.
function openedPrBefore(env: Env): boolean {
  const rows = env.db
    .query(
      `select data_json from journal where session_id = ? and event = 'tool.after'
         and data_json like '%"tool":"shell"%' and data_json like '%gh pr create%'`,
    )
    .all(env.ev.session) as { data_json: string }[]
  return rows.some((r) => {
    const d = JSON.parse(r.data_json)
    return d.tool === "shell" && !d.failed && parse(String(d.arg ?? "")).commands.some(isCreate)
  })
}

// Which injections this call earns. Each rule shows up once per session.
export function injections(env: Env): Injection[] {
  const { ev, db } = env
  if (!ev.session) return []
  const out: Injection[] = []
  const want = (ruleId: string, text: string) => {
    const m = mode(db, ruleId)
    if (m === "off" || fired(env, ruleId)) return
    out.push({ ruleId, text, advise: m === "advise" })
  }
  const edits = ev.toolName === "edit" || ev.toolName === "write"
  // Claude: before the edit. OpenCode: after it.
  const editNow = ev.tool === "claude" ? ev.event === "tool.before" : ev.event === "tool.after"
  if (edits && editNow && !ev.failed) {
    const path = String(ev.input?.path ?? "")
    if (UI_FILE.test(path)) want("inject-ui", UI_TEXT)
    if (CODE_FILE.test(path) && !codingLoaded(env)) want("inject-coding", CODING_TEXT)
  } else if (ev.event === "tool.after" && !ev.failed && isOutward(env)) {
    want("inject-links", LINKS_TEXT)
    // Not once per session: every extra `gh pr create` is told.
    if (ev.toolName === "shell" && isPrCreate(env) && openedPrBefore(env)) {
      const m = mode(db, "inject-pr-batch")
      if (m !== "off") out.push({ ruleId: "inject-pr-batch", text: PR_BATCH_TEXT, advise: m === "advise" })
    }
  }
  return out
}
