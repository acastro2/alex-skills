import type { Database } from "bun:sqlite"
import { getMeta, setMeta } from "./db.ts"
import { append, upsertSession } from "./journal.ts"
import { ulid } from "./ulid.ts"

const GRANT_TTL_MS = 30 * 60 * 1000

export type Command =
  | { kind: "none" }
  | { kind: "grant"; grant: "merge" | "harness"; tokenId: string }
  | { kind: "switch"; action: "off" | "on" | "wrong" | "on-rule" | "rollback"; arg?: string }

export interface Channel {
  channel: "prompt" | "page" | "cli"
  session: string
  isRootSession: boolean
  text: string
  now?: number
}

const NONE: Command = { kind: "none" }
const MERGE_OK = /^MERGE-OK (\d+)$/
const HARNESS_OK = /^HARNESS-OK ([0-9a-f]{8}) ([0-9a-f]{8})$/
const SWITCH = /^harness (off|on|wrong|rollback)$/
const ON_RULE = /^harness on ([a-z][a-z0-9-]*)$/

export function isOff(db: Database): boolean {
  return getMeta(db, "harness_off") === "1"
}

function grant(
  db: Database,
  ch: Channel,
  line: string,
  now: number,
  g: { kind: "merge" | "harness"; pr?: number; requestId?: string },
): Command {
  return db
    .transaction((): Command => {
      upsertSession(db, { id: ch.session, tool: "unknown" })
      const tokenId = ulid(now)
      const seq = append(db, {
        session_id: ch.session,
        event: "grant",
        outcome: "allow",
        prompt_text: line,
        data: { kind: g.kind, token_id: tokenId, pr: g.pr ?? null, request_id: g.requestId ?? null, channel: ch.channel },
        time: now,
      })
      db.query(
        "insert into tokens(id, kind, session_id, grant_seq, request_id, pr, expires_at) values(?, ?, ?, ?, ?, ?, ?)",
      ).run(tokenId, g.kind, ch.session, seq, g.requestId ?? null, g.pr ?? null, now + GRANT_TTL_MS)
      return { kind: "grant", grant: g.kind, tokenId }
    })
    .immediate()
}

function setKillSwitch(db: Database, ch: Channel, off: boolean, now: number): void {
  db.transaction(() => {
    upsertSession(db, { id: ch.session, tool: "unknown" })
    setMeta(db, "harness_off", off ? "1" : "0")
    append(db, { session_id: ch.session, event: off ? "harness.off" : "harness.on", data: { channel: ch.channel }, time: now })
  }).immediate()
}

// Only the first line counts, and only in a root session or on the page. Everything else is none (D35).
export function command(db: Database, ch: Channel): Command {
  if (ch.channel === "prompt" && !ch.isRootSession) return NONE
  const now = ch.now ?? Date.now()
  const line = ch.text.split(/\r?\n/, 1)[0].trim()

  const merge = MERGE_OK.exec(line)
  if (merge) return grant(db, ch, line, now, { kind: "merge", pr: Number(merge[1]) })

  const harness = HARNESS_OK.exec(line)
  if (harness) {
    const req = db
      .query(
        "select id from requests where state = 'open' and substr(sha, 1, 8) = ? and substr(digest, 1, 8) = ? order by created_at desc, id desc limit 1",
      )
      .get(harness[1], harness[2]) as { id: string } | null
    return req ? grant(db, ch, line, now, { kind: "harness", requestId: req.id }) : NONE
  }

  const onRule = ON_RULE.exec(line)
  if (onRule) return { kind: "switch", action: "on-rule", arg: onRule[1] }

  const sw = SWITCH.exec(line)
  if (!sw) return NONE
  const action = sw[1] as "off" | "on" | "wrong" | "rollback"
  if (action === "off" || action === "on") setKillSwitch(db, ch, action === "off", now)
  return { kind: "switch", action }
}

// Merge tokens bind to the session that typed them and, when given, the PR. Harness tokens bind to the request.
// A token counts only when its grant_seq points at the journal 'grant' row that names it (D70). A row inserted
// behind the guard's back has no such journal row, so it is never honoured.
export function holds(
  db: Database,
  q: { kind: "merge" | "harness"; session: string; pr?: number; requestId?: string; now?: number },
): string | null {
  const row = db
    .query(
      `select t.id from tokens t
       join journal j on j.seq = t.grant_seq and j.event = 'grant' and json_extract(j.data_json, '$.token_id') = t.id
       where t.kind = ? and t.used_at is null and t.expires_at > ?
         and (? is null or t.pr = ?)
         and (case when ? is null then t.session_id = ? else t.request_id = ? end)
       order by t.id desc limit 1`,
    )
    .get(q.kind, q.now ?? Date.now(), q.pr ?? null, q.pr ?? null, q.requestId ?? null, q.session, q.requestId ?? null) as {
    id: string
  } | null
  return row ? row.id : null
}

// True once. A second call, or an expired token, returns false.
export function consume(db: Database, tokenId: string, now: number = Date.now()): boolean {
  return (
    db.query("update tokens set used_at = ? where id = ? and used_at is null and expires_at > ?").run(now, tokenId, now)
      .changes === 1
  )
}

// The full review text goes on the journal row that review_seq points at, so the page can show what the digest covers.
export function requestApply(db: Database, r: { session: string; sha: string; digest: string; review?: string }): string {
  return db
    .transaction(() => {
      upsertSession(db, { id: r.session, tool: "unknown" })
      const id = ulid()
      const now = Date.now()
      const seq = append(db, {
        session_id: r.session,
        event: "harness.request",
        prompt_text: r.review,
        verbatim: true,
        data: { request_id: id, sha: r.sha, digest: r.digest },
        time: now,
      })
      db.query("insert into requests(id, session_id, sha, digest, review_seq, state, created_at) values(?, ?, ?, ?, ?, 'open', ?)").run(
        id,
        r.session,
        r.sha,
        r.digest,
        seq,
        now,
      )
      return id
    })
    .immediate()
}
