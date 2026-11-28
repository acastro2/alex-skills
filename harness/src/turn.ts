// Turn: what this session did this turn. One module answers it, so policies stop re-deriving it with their own
// journal reads and regex on bare data_json fields. Tool identity is a closed `Kind`, set here once from the
// normalized tool name (adapters/normalize.ts); policies never test host spellings.
import type { Database } from "bun:sqlite"

export type Kind = "shell" | "edit" | "read" | "subagent" | "question" | "todo" | "browse" | "fetch" | "harness" | "external-write" | "mcp" | "other"

const DIRECT = new Map<string, Kind>([
  ["shell", "shell"],
  ["edit", "edit"],
  ["write", "edit"],
  ["read", "read"],
  ["subagent", "subagent"],
  ["question", "question"],
  ["askuserquestion", "question"],
  ["todowrite", "todo"],
  ["taskcreate", "todo"],
  ["taskupdate", "todo"],
  ["webfetch", "fetch"],
])

// shortcut: a name pattern, not a list of tools. It reads the tool part of mcp:<server>:<tool> and treats a verb
// at the start or after "_" as a write. Upgrade to a per-server list when a read tool is wrongly flagged.
const EXTERNAL_WRITE = /(^|_)(create|edit|update|add|transition|send|post|publish|delete|upload|schedule|merge|register|upsert|write|executeWrite|executeDestructive)/i

export function toolKind(name: string | null | undefined): Kind {
  if (!name) return "other"
  const direct = DIRECT.get(name)
  if (direct) return direct
  if (!name.startsWith("mcp:")) return "other"
  if (name.startsWith("mcp:harness:")) return "harness"
  if (name.startsWith("mcp:browse:")) return "browse"
  const tool = name.split(":").slice(2).join(":")
  if (/fetch/i.test(tool)) return "fetch"
  return EXTERNAL_WRITE.test(tool) ? "external-write" : "mcp"
}

export interface Call {
  seq: number
  time: number
  event: string // tool.after, or the row that replaced it: nudge, stuck, question.answered
  kind: Kind
  tool: string
  arg: string
  path?: string
  failed: boolean
  data: Record<string, any> // the journal row's data_json
}

export interface Turn {
  prompt: string | null
  startedAt: number | null // time of the turn's first journal row
  calls: Call[]
  edited: string[] // paths of edit/write calls that did not fail, in order, unique
  shell: { command: string; failed: boolean }[]
  browsed: boolean // this SESSION used a browse tool (any turn): the browser is there for the agent to use
  triedHandoff: boolean // a tool this turn has "handoff" in its name
  kinds(): Set<Kind>
}

const CALL_EVENTS = "'tool.after', 'nudge', 'stuck', 'question.answered'"

// turn: a number, "all" (every turn of the session), or omitted for the latest turn. One journal query.
export function turnOf(db: Database, session: string, turn?: number | "all"): Turn {
  const inTurn = (a: string) => (turn === "all" ? "1" : typeof turn === "number" ? `${a}.turn = ?2` : `${a}.turn = (select max(turn) from journal where session_id = ?1)`)
  // The left join keeps one row when the turn is empty, so the session-wide `browsed` still comes back.
  const sql = `
    select j.seq, j.time, j.event, j.prompt_text, j.data_json,
           (select min(time) from journal m where m.session_id = ?1 and ${inTurn("m")}) as started,
           exists(select 1 from journal b where b.session_id = ?1 and b.data_json like '%"tool":"mcp:browse:%') as browsed
    from (select 1) left join journal j
      on j.session_id = ?1 and ${inTurn("j")}
     and (j.event = 'prompt' or (j.event in (${CALL_EVENTS}) and j.data_json is not null))
    order by j.seq`
  const rows = db.query(sql).all(...(typeof turn === "number" ? [session, turn] : [session])) as {
    seq: number | null
    time: number
    event: string
    prompt_text: string | null
    data_json: string | null
    started: number | null
    browsed: number
  }[]

  let prompt: string | null = null
  const calls: Call[] = []
  for (const r of rows) {
    if (r.seq === null) continue
    if (r.event === "prompt") {
      prompt = r.prompt_text
      continue
    }
    const data = JSON.parse(r.data_json!)
    if (!data.tool) continue
    const tool = String(data.tool)
    calls.push({
      seq: r.seq,
      time: r.time,
      event: r.event,
      kind: toolKind(tool),
      tool,
      arg: String(data.arg ?? ""),
      path: typeof data.path === "string" ? data.path : undefined,
      failed: !!data.failed,
      data,
    })
  }

  return {
    prompt,
    startedAt: rows[0]?.started ?? null,
    calls,
    edited: [...new Set(calls.filter((c) => c.kind === "edit" && !c.failed && c.path !== undefined).map((c) => c.path!))],
    shell: calls.filter((c) => c.kind === "shell").map((c) => ({ command: c.arg, failed: c.failed })),
    browsed: !!rows[0]?.browsed,
    triedHandoff: calls.some((c) => /handoff/i.test(c.tool)),
    kinds: () => new Set(calls.map((c) => c.kind)),
  }
}
