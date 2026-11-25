import type { Database } from "bun:sqlite"
import { createHash } from "node:crypto"
import { getMeta, setMeta } from "./db.ts"

const sha256 = (s: string) => createHash("sha256").update(s).digest("hex")

// Longest secret shapes first. Labelled forms keep their label so the row stays readable.
const SECRETS: [RegExp, string][] = [
  [/\bBearer\s+[A-Za-z0-9._~+/=-]{8,}/g, "Bearer [redacted]"],
  [/(password|token)=\S+/gi, "$1=[redacted]"],
  [/github_pat_[A-Za-z0-9_]{20,}/g, "[redacted]"],
  [/gh[pousr]_[A-Za-z0-9]{20,}/g, "[redacted]"],
  [/xox[bp]-[A-Za-z0-9-]{10,}/g, "[redacted]"],
  [/AKIA[0-9A-Z]{16}/g, "[redacted]"],
  [/sk-[A-Za-z0-9_-]{8,}/g, "[redacted]"],
  // Long hex or base64 run. Needs a digit, so plain long words and paths stay.
  [/(?=[A-Za-z0-9+/]*\d)[A-Za-z0-9+/]{32,}={0,2}/g, "[redacted]"],
]

export function scrub(text: string): string {
  return SECRETS.reduce((t, [re, to]) => t.replace(re, to), text)
}

export interface JournalRow {
  session_id: string | null
  turn?: number | null
  event: string
  rule_id?: string | null
  outcome?: string | null
  reason?: string | null
  prompt_text?: string | null
  args?: unknown
  output?: string | null
  data?: unknown
  time?: number
}

interface Stored {
  session_id: string | null
  turn: number | null
  time: number
  event: string
  rule_id: string | null
  outcome: string | null
  reason: string | null
  prompt_text: string | null
  args_hash: string | null
  output_hash: string | null
  data_json: string | null
}

// The chain covers every stored field except seq, in this fixed order.
function rowHash(prev: string, r: Stored): string {
  return sha256(
    prev +
      JSON.stringify([
        r.session_id,
        r.turn,
        r.time,
        r.event,
        r.rule_id,
        r.outcome,
        r.reason,
        r.prompt_text,
        r.args_hash,
        r.output_hash,
        r.data_json,
      ]),
  )
}

const anchor = (db: Database) => getMeta(db, "chain_anchor") ?? "genesis"

export function append(db: Database, row: JournalRow): number {
  const stored: Stored = {
    session_id: row.session_id,
    turn: row.turn ?? null,
    time: row.time ?? Date.now(),
    event: row.event,
    rule_id: row.rule_id ?? null,
    outcome: row.outcome ?? null,
    reason: row.reason ?? null,
    prompt_text: row.prompt_text == null ? null : scrub(row.prompt_text),
    args_hash: row.args === undefined ? null : sha256(typeof row.args === "string" ? row.args : JSON.stringify(row.args)),
    output_hash: row.output == null ? null : sha256(row.output),
    data_json: row.data === undefined ? null : JSON.stringify(row.data),
  }
  return db
    .transaction(() => {
      const last = db.query("select row_hash from journal order by seq desc limit 1").get() as { row_hash: string } | null
      const prev = last ? last.row_hash : anchor(db)
      const r = db
        .query(
          `insert into journal(session_id, turn, time, event, rule_id, outcome, reason, prompt_text,
             args_hash, output_hash, data_json, prev_hash, row_hash)
           values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .run(
          stored.session_id,
          stored.turn,
          stored.time,
          stored.event,
          stored.rule_id,
          stored.outcome,
          stored.reason,
          stored.prompt_text,
          stored.args_hash,
          stored.output_hash,
          stored.data_json,
          prev,
          rowHash(prev, stored),
        )
      return Number(r.lastInsertRowid)
    })
    .immediate()
}

export function verifyChain(db: Database): { ok: boolean; badSeq?: number } {
  let prev = anchor(db)
  for (const r of db.query("select * from journal order by seq").iterate() as Iterable<Stored & { seq: number; prev_hash: string; row_hash: string }>) {
    if (r.prev_hash !== prev || r.row_hash !== rowHash(prev, r)) return { ok: false, badSeq: r.seq }
    prev = r.row_hash
  }
  return { ok: true }
}

// Deletes the oldest rows whose time is more than olderThanMs before `now`. It stops at the
// first newer row, so what stays is one unbroken chain that starts at the new anchor.
export function prune(db: Database, olderThanMs: number, now: number = Date.now()): number {
  const cutoff = now - olderThanMs
  return db
    .transaction(() => {
      const keep = db.query("select min(seq) as seq from journal where time >= ?").get(cutoff) as { seq: number | null }
      const upTo = keep.seq ?? Number.MAX_SAFE_INTEGER
      const newest = db.query("select row_hash from journal where seq < ? order by seq desc limit 1").get(upTo) as {
        row_hash: string
      } | null
      if (!newest) return 0
      setMeta(db, "chain_anchor", newest.row_hash)
      return db.query("delete from journal where seq < ?").run(upTo).changes
    })
    .immediate()
}

export function upsertSession(
  db: Database,
  s: {
    id: string
    tool: string
    parent_session_id?: string | null
    repo?: string | null
    cwd?: string | null
    model?: string | null
    interactive?: boolean | null
  },
): void {
  db.query(
    `insert into sessions(id, parent_session_id, tool, repo, cwd, model, interactive, started_at)
     values(?, ?, ?, ?, ?, ?, ?, ?)
     on conflict(id) do update set
       parent_session_id = coalesce(excluded.parent_session_id, parent_session_id),
       tool = case when excluded.tool = 'unknown' then tool else excluded.tool end,
       repo = coalesce(excluded.repo, repo),
       cwd = coalesce(excluded.cwd, cwd),
       model = coalesce(excluded.model, model),
       interactive = coalesce(excluded.interactive, interactive)`,
  ).run(
    s.id,
    s.parent_session_id ?? null,
    s.tool,
    s.repo ?? null,
    s.cwd ?? null,
    s.model ?? null,
    s.interactive == null ? null : s.interactive ? 1 : 0,
    Date.now(),
  )
}
