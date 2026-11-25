import type { Database } from "bun:sqlite"
import { createHash } from "node:crypto"

export type Verdict = "green" | "red" | "partial"

export interface Rerun {
  command: string
  exit: number
  tail: string
}

export interface Verified {
  clean: boolean
  reruns: Rerun[]
  verdict: Verdict
  reason?: string
}

export interface Bundle {
  id: string
  sessionId: string | null
  workerId: string | null
  journalSeq: number | null
  headSha: string
  verdict: Verdict
  did: Record<string, any>
  works: Record<string, any>
  verified: Verified
  summary: string | null
  knownGaps: string | null
}

interface Row {
  id: string
  worker_id: string | null
  session_id: string | null
  journal_seq: number | null
  head_sha: string
  did_json: string
  works_json: string
  verified_json: string
  verdict: Verdict
  summary: string | null
  known_gaps: string | null
}

// The journal row holds this digest, and the journal is hash-chained, so a hand edit to any bundle field shows (D46).
export function digestOf(r: Omit<Row, "id" | "worker_id" | "session_id" | "journal_seq">): string {
  return createHash("sha256")
    .update(JSON.stringify([r.head_sha, r.verdict, r.did_json, r.works_json, r.verified_json, r.summary, r.known_gaps]))
    .digest("hex")
}

function toBundle(r: Row): Bundle {
  return {
    id: r.id,
    sessionId: r.session_id,
    workerId: r.worker_id,
    journalSeq: r.journal_seq,
    headSha: r.head_sha,
    verdict: r.verdict,
    did: JSON.parse(r.did_json),
    works: JSON.parse(r.works_json),
    verified: JSON.parse(r.verified_json),
    summary: r.summary,
    knownGaps: r.known_gaps,
  }
}

export function bundleFor(db: Database, headSha: string): Bundle | null {
  const r = db.query("select * from bundles where head_sha = ? order by rowid desc limit 1").get(headSha) as Row | null
  return r ? toBundle(r) : null
}

const cell = (s: string) => s.replace(/\|/g, "\\|").replace(/\n/g, " ")

// The 6 items of D48: head SHA, verdict, acceptance table, screenshots, bundle ID, known gaps.
export function prBody(b: Bundle): string {
  const reason = b.verified.reason ? ` (${b.verified.reason})` : ""
  const table = ["| Command | Exit |", "| --- | --- |", ...b.verified.reruns.map((r) => `| \`${cell(r.command)}\` | ${r.exit} |`)]
  const shots: string[] = b.works.ui_proof ?? []
  return [
    `Head SHA: ${b.headSha}`,
    `Verdict: ${b.verdict}${reason}`,
    `Acceptance:`,
    ...(b.verified.reruns.length ? table : ["none run"]),
    `Screenshots: ${shots.length ? shots.join(", ") : "none"}`,
    `Bundle: ${b.id}`,
    `Known gaps: ${b.knownGaps?.trim() || "none"}`,
  ].join("\n")
}

// Tamper check: the stored row must still match the digest the journal row recorded when verify wrote it.
export function recompute(db: Database, bundleId: string): boolean {
  const r = db.query("select * from bundles where id = ?").get(bundleId) as Row | null
  if (!r || r.journal_seq == null) return false
  const j = db.query("select event, data_json from journal where seq = ?").get(r.journal_seq) as {
    event: string
    data_json: string | null
  } | null
  if (!j || j.event !== "bundle" || !j.data_json) return false
  try {
    const d = JSON.parse(j.data_json)
    const verified = JSON.parse(r.verified_json) as Verified
    return d.bundleId === r.id && d.verdict === r.verdict && d.head_sha === r.head_sha && d.digest === digestOf(r) && verified.verdict === r.verdict
  } catch {
    return false
  }
}
