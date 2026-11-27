// Builds the page's data from the ledger. Read-only: nothing here writes a table.
// Event names it reads (journal.event): prompt, stop, stop.sendback, nudge, session.stuck, goal,
// question.asked, question.answered, grant, harness.wrong, egress.warning, watch.wake, harness.on,
// harness.off, harness.review. Where the ledger lane names one differently, change it in EVENTS.
import type { Database } from "bun:sqlite";
import { hostname } from "node:os";
import { verifyChain } from "../ledger/journal.ts";
import type { Resources } from "./resources.ts";

export const VIEW_IDS = ["inbox", "sessions", "worktrees", "bundles", "rules", "journal", "changes", "jobs"] as const;
export type ViewId = (typeof VIEW_IDS)[number];

/** The page's own journal identity (see actions.ts). It is not a work session and never shows as one. */
export const PAGE_SESSION = "harness-page";

export const EVENTS = {
  prompt: "prompt",
  stop: "stop",
  sendback: "stop.sendback",
  nudge: "nudge",
  stuck: "session.stuck",
  goal: "goal",
  asked: "question.asked",
  answered: "question.answered",
  wake: "watch.wake",
  on: "harness.on",
  off: "harness.off",
} as const;

const MIN = 60_000;
const ENDED_VISIBLE_MS = 60 * MIN;

export type SessionState = "waiting" | "stuck" | "running" | "idle" | "ended";

export interface SessionRow {
  id: string;
  slug: string;
  parent_session_id: string | null;
  tool: string | null;
  repo: string | null;
  cwd: string | null;
  model: string | null;
  interactive: boolean;
  started_at: number;
  ended_at: number | null;
  goal: string | null;
  turn: number;
  nudges: number;
  state: SessionState;
  waiting: boolean;
  stuck: boolean;
  running: boolean;
  last_event_at: number | null;
  workers: number;
  /** The newest tool row of this session: what it is doing, or did last. */
  last_tool: ToolCall | null;
  /** Branch of the worktree this session owns, if any. */
  worktree: string | null;
}

export interface ToolCall {
  name: string;
  arg: string | null;
  event: string;
  outcome: string | null;
  time: number;
}

export interface ProcessRow {
  id: number;
  session_id: string | null;
  session_slug: string | null;
  pid: number | null;
  command: string | null;
  port: number | null;
  keep: boolean;
  started_at: number | null;
  ended_at: number | null;
}

/** deny: outcome deny. advise: the rule spoke but did not block (advise, warn, inject, modify). sendback: a stop that went back. */
export type TailKind = "deny" | "advise" | "sendback";

export interface TailRow {
  seq: number;
  time: number;
  event: string;
  session_id: string | null;
  session_slug: string | null;
  rule_id: string | null;
  outcome: string | null;
  text: string;
  tool: string | null;
  kind: TailKind | null;
}

export interface Health {
  /** null until the chain was checked once. */
  chain_ok: boolean | null;
  chain_bad_seq: number | null;
  chain_checked_at: number | null;
  deny_1h: number;
  advise_1h: number;
  sendback_1h: number;
  /** Journal rows per minute, oldest first, the last 60 minutes. The last bucket is the current minute. */
  series: number[];
}

export interface Dash {
  processes: ProcessRow[];
  tail: TailRow[];
  health: Health;
}

export interface QuestionRow {
  id: string;
  seq: number;
  session_id: string;
  session_slug: string;
  tool: string | null;
  repo: string | null;
  goal: string | null;
  asked_at: number;
  text: string;
  options: string[];
}

export interface WorktreeRow {
  id: string;
  repo: string | null;
  path: string;
  branch: string | null;
  state: string;
  sync_state: string | null;
  conflict_files: string[];
  owner_session_id: string | null;
  owner_slug: string | null;
  synced_at: number | null;
  created_at: number | null;
}

export interface CommandRun {
  command: string;
  exit: number | null;
  tail: string | null;
}

export interface BundleRow {
  id: string;
  time: number;
  head_sha: string | null;
  verdict: string | null;
  advisory: number | null;
  summary: string | null;
  known_gaps: string | null;
  session_id: string | null;
  session_slug: string | null;
  repo: string | null;
  worker_model: string | null;
  did: string[];
  works: CommandRun[];
  verified: CommandRun[];
  gate: { outcome: string | null; reason: string | null } | null;
}

export interface SendbackRow {
  seq: number;
  time: number;
  session_id: string | null;
  session_slug: string | null;
  reason: string | null;
  wrong: boolean;
}

export interface RuleRow {
  id: string;
  event: string | null;
  module: string | null;
  mode: string;
  default_mode: string | null;
  ships_in: string | null;
  wrong_today: number;
  sendbacks_today: number;
  recent_sendbacks: SendbackRow[];
}

export interface JournalRow {
  seq: number;
  time: number;
  turn: number | null;
  event: string;
  session_id: string | null;
  session_slug: string | null;
  rule_id: string | null;
  outcome: string | null;
  reason: string | null;
  prompt_text: string | null;
  data: unknown;
}

export interface JournalPage {
  rows: JournalRow[];
  has_more: boolean;
  next_cursor: number | null;
}

export interface ChangeRow {
  id: string;
  created_at: number;
  sha: string;
  digest: string;
  state: string;
  status: "pending" | "applied" | "rolled_back" | "other";
  session_slug: string | null;
  review: string | null;
  apply: { id: string; applied_at: number | null; rolled_back_at: number | null; tree_hash: string | null } | null;
  /** A live, unused passkey grant for this request: the tap worked, the session has not run harness_apply yet. */
  granted: { until: number } | null;
  /** An open request whose sha is the current applied sha or an ancestor of it: a newer apply replaced it. */
  superseded: boolean;
}

export type JobResult = "ok" | "failed" | "never" | "unknown";

export interface JobRow {
  name: string;
  schedule: string | null;
  last_run_at: number | null;
  last_result: string | null;
  result: JobResult;
  next_run_at: number | null;
}

/** The raw facts the office model reads (`officeState(snap, prev)`). Other lane: harness/src/ui/office-model.ts. */
export interface LedgerSnapshot {
  now: number;
  seq: number;
  harnessOn: boolean;
  sessions: SessionRow[];
  questions: QuestionRow[];
  worktrees: WorktreeRow[];
  rules: Pick<RuleRow, "id" | "mode" | "default_mode">[];
  watches: { id: string; session_id: string | null; kind: string | null; target: string | null; last_state: string | null; polled_at: number | null }[];
  wakes: { seq: number; time: number; session_id: string | null; reason: string | null }[];
  grants: { id: string; kind: string | null; pr: number | null; session_id: string | null; used_at: number | null; expires_at: number | null }[];
  jobs: Pick<JobRow, "name" | "schedule" | "last_run_at" | "result" | "next_run_at">[];
  recent: { seq: number; time: number; event: string; outcome: string | null }[];
  journalPerMin: number;
  steeringShare7d: number | null;
}

/** A watched pull request that is not done. `state`, `review` and `checks` come from the waker's last poll. */
export interface PrWatchRow {
  id: string;
  target: string;
  /** The PR number in `target`, or null when the target has no `#n`. */
  pr: number | null;
  session_id: string | null;
  session_slug: string | null;
  /** A live, unused merge grant for this PR and session. */
  granted: { until: number } | null;
  state: string | null;
  review: string | null;
  mergeable: string | null;
  /** Names of the failed checks at the last poll. */
  failed: string[];
  polled_at: number | null;
}

export interface AttentionItem {
  view: ViewId;
  id: string;
  tone: "amber" | "red";
  what: string;
  detail: string;
  at: number | null;
}

export interface Snapshot {
  at: number;
  pr_watches: PrWatchRow[];
  seq: number;
  host: string;
  harness: { on: boolean; changed_at: number | null };
  counts: Record<ViewId, number>;
  alerts: Record<ViewId, number>;
  /** The one list of what needs Alex. The rail, tab title, dashboard and office read it; nothing re-derives it. */
  attention: AttentionItem[];
  ledger: LedgerSnapshot;
  views: {
    inbox: QuestionRow[];
    sessions: SessionRow[];
    worktrees: WorktreeRow[];
    bundles: BundleRow[];
    rules: RuleRow[];
    journal: JournalPage & { per_min: number };
    changes: ChangeRow[];
    jobs: JobRow[];
  };
  /** What the dashboard reads on top of the 8 views. */
  dash: Dash;
  /** Machine load. buildSnapshot sets null; the server fills it from the sampler. */
  resources: Resources | null;
}

type Params = (string | number | null)[];

function all<T>(db: Database, sql: string, ...params: Params): T[] {
  return db.query(sql).all(...params) as T[];
}
function one<T>(db: Database, sql: string, ...params: Params): T | null {
  return (db.query(sql).get(...params) as T | null) ?? null;
}

function parse<T>(text: string | null | undefined, fallback: T): T {
  if (!text) return fallback;
  try {
    return JSON.parse(text) as T;
  } catch {
    return fallback;
  }
}

const CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
export function ulidTime(id: string): number {
  let t = 0;
  for (const ch of id.slice(0, 10).toUpperCase()) {
    const v = CROCKFORD.indexOf(ch);
    if (v < 0) return 0;
    t = t * 32 + v;
  }
  return t;
}

export function sessionSlug(id: string | null, repo: string | null): string | null {
  if (!id) return null;
  const name = repo ? repo.replace(/\/+$/, "").split("/").pop() || repo : "session";
  return `${name}·${id.slice(-4).toLowerCase()}`;
}

function startOfToday(now: number): number {
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

function firstLine(text: string | null, max = 140): string | null {
  if (!text) return null;
  const line = text.split("\n").find((l) => l.trim()) ?? "";
  const t = line.trim();
  return t.length > max ? `${t.slice(0, max - 1)}…` : t || null;
}

export function maxSeq(db: Database): number {
  return one<{ s: number | null }>(db, "SELECT MAX(seq) AS s FROM journal")?.s ?? 0;
}

function deriveSessions(db: Database, now: number): SessionRow[] {
  const rows = all<{
    id: string; parent_session_id: string | null; tool: string | null; repo: string | null; cwd: string | null;
    model: string | null; interactive: number | null; started_at: number; ended_at: number | null;
  }>(db, "SELECT * FROM sessions WHERE id <> ? AND (ended_at IS NULL OR ended_at > ?) ORDER BY started_at LIMIT 80", PAGE_SESSION, now - ENDED_VISIBLE_MS);

  const workerCount = new Map<string, number>();
  for (const w of all<{ parent_session_id: string; n: number }>(db, "SELECT parent_session_id, COUNT(*) AS n FROM workers GROUP BY parent_session_id")) {
    workerCount.set(w.parent_session_id, w.n);
  }

  return rows.map((s) => {
    const last = new Map<string, { seq: number; time: number }>();
    for (const r of all<{ event: string; seq: number; time: number }>(
      db,
      `SELECT event, MAX(seq) AS seq, MAX(time) AS time FROM journal WHERE session_id = ?
       AND event IN (?, ?, ?, ?, ?, ?, ?) GROUP BY event`,
      s.id, EVENTS.prompt, EVENTS.stop, EVENTS.sendback, EVENTS.stuck, EVENTS.asked, EVENTS.answered, EVENTS.goal,
    )) last.set(r.event, r);
    const seqOf = (e: string) => last.get(e)?.seq ?? 0;

    const turn = one<{ t: number | null }>(db, "SELECT MAX(turn) AS t FROM journal WHERE session_id = ?", s.id)?.t ?? 0;
    const nudges = one<{ n: number }>(db, "SELECT COUNT(*) AS n FROM journal WHERE session_id = ? AND event = ? AND turn = ?", s.id, EVENTS.nudge, turn)?.n ?? 0;
    const lastEvent = one<{ t: number | null }>(db, "SELECT MAX(time) AS t FROM journal WHERE session_id = ?", s.id)?.t ?? null;

    const ended = s.ended_at !== null;
    const waiting = !ended && seqOf(EVENTS.asked) > seqOf(EVENTS.answered);
    const stuck = !ended && seqOf(EVENTS.stuck) > seqOf(EVENTS.prompt);
    const running = !ended && Math.max(seqOf(EVENTS.prompt), seqOf(EVENTS.sendback)) > seqOf(EVENTS.stop);
    const state: SessionState = ended ? "ended" : waiting ? "waiting" : stuck ? "stuck" : running ? "running" : "idle";

    return {
      id: s.id,
      slug: sessionSlug(s.id, s.repo) as string,
      parent_session_id: s.parent_session_id,
      tool: s.tool,
      repo: s.repo,
      cwd: s.cwd,
      model: s.model,
      interactive: Boolean(s.interactive),
      started_at: s.started_at,
      ended_at: s.ended_at,
      goal: sessionGoal(db, s.id, last.get(EVENTS.goal)?.seq),
      turn,
      nudges,
      state,
      waiting,
      stuck,
      running,
      last_event_at: lastEvent,
      workers: workerCount.get(s.id) ?? 0,
      last_tool: lastTool(db, s.id),
      worktree: one<{ branch: string | null }>(db, "SELECT branch FROM worktrees WHERE session_id = ? AND removed_at IS NULL ORDER BY created_at DESC LIMIT 1", s.id)?.branch ?? null,
    };
  });
}

function lastTool(db: Database, sessionId: string): ToolCall | null {
  const r = one<{ event: string; time: number; outcome: string | null; data_json: string | null }>(
    db,
    "SELECT event, time, outcome, data_json FROM journal WHERE session_id = ? AND event IN ('tool.before', 'tool.after') ORDER BY seq DESC LIMIT 1",
    sessionId,
  );
  if (!r) return null;
  const d = parse<{ tool?: string; arg?: string }>(r.data_json, {});
  return { name: d.tool ?? "tool", arg: d.arg ? d.arg.slice(0, 200) : null, event: r.event, outcome: r.outcome, time: r.time };
}

function sessionGoal(db: Database, sessionId: string, goalSeq: number | undefined): string | null {
  if (goalSeq) {
    const g = one<{ data_json: string | null; prompt_text: string | null }>(db, "SELECT data_json, prompt_text FROM journal WHERE seq = ?", goalSeq);
    const fromData = parse<{ goal?: string }>(g?.data_json, {}).goal;
    const text = firstLine(fromData ?? g?.prompt_text ?? null);
    if (text) return text;
  }
  const worker = one<{ acceptance: string | null }>(db, "SELECT acceptance FROM workers WHERE worker_session_id = ?", sessionId);
  const objective = firstLine(parse<{ objective?: string }>(worker?.acceptance, {}).objective ?? null);
  if (objective) return objective;
  const p = one<{ prompt_text: string | null }>(db, "SELECT prompt_text FROM journal WHERE session_id = ? AND event = ? ORDER BY seq LIMIT 1", sessionId, EVENTS.prompt);
  return goalLine(p?.prompt_text ?? null);
}

// A worker prompt may start with the contract or a skill load. Prefer an OBJECTIVE: line, else the
// first line that says what the task is.
export function goalLine(text: string | null): string | null {
  if (!text) return null;
  const obj = /^\s*(?:#+\s*)?objective\s*[:\-]?\s*(.+)$/im.exec(text)?.[1];
  if (obj?.trim()) return firstLine(obj);
  const skip = /^(HARNESS-CONTRACT|- |\s*$|load the |no git |new request from |update from the parent|heads-up from the parent)/i;
  const line = text.split("\n").find((l) => !skip.test(l.trim()) && l.trim().length > 3);
  return firstLine(line ?? text);
}

function pendingQuestions(db: Database, sessions: SessionRow[]): QuestionRow[] {
  const out: QuestionRow[] = [];
  for (const s of sessions) {
    if (!s.waiting) continue;
    const ask = one<{ seq: number; time: number; prompt_text: string | null; reason: string | null; data_json: string | null }>(
      db,
      "SELECT seq, time, prompt_text, reason, data_json FROM journal WHERE session_id = ? AND event = ? ORDER BY seq DESC LIMIT 1",
      s.id, EVENTS.asked,
    );
    if (!ask) continue;
    // The core journals the tool input as `questions: [{question, options}]`; older rows and the seed use a flat shape.
    type Q = { question?: string; options?: (string | { label?: string })[] };
    const raw = parse<Q & { questions?: Q[] }>(ask.data_json, {});
    const data: Q = Array.isArray(raw.questions) && raw.questions.length ? raw.questions[0] : raw;
    const options = (data.options ?? []).map((o) => (typeof o === "string" ? o : o.label ?? "")).filter(Boolean);
    out.push({
      id: String(ask.seq),
      seq: ask.seq,
      session_id: s.id,
      session_slug: s.slug,
      tool: s.tool,
      repo: s.repo,
      goal: s.goal,
      asked_at: ask.time,
      text: data.question ?? ask.prompt_text ?? ask.reason ?? "",
      options,
    });
  }
  return out.sort((a, b) => a.asked_at - b.asked_at);
}

function worktreeRows(db: Database, now: number, slugs: Map<string, string | null>): WorktreeRow[] {
  const rows = all<{
    id: string; repo: string | null; path: string; branch: string | null; state: string; sync_state: string | null;
    conflict_files: string | null; session_id: string | null; synced_at: number | null; created_at: number | null; repo2: string | null;
  }>(
    db,
    `SELECT w.*, s.repo AS repo2 FROM worktrees w LEFT JOIN sessions s ON s.id = w.session_id
     WHERE w.removed_at IS NULL OR w.removed_at > ? ORDER BY w.created_at DESC LIMIT 60`,
    now - 10 * MIN,
  );
  return rows.map((w) => ({
    id: w.id,
    repo: w.repo,
    path: w.path,
    branch: w.branch,
    state: w.state,
    sync_state: w.sync_state,
    conflict_files: parse<string[]>(w.conflict_files, []),
    owner_session_id: w.session_id,
    owner_slug: w.session_id ? slugs.get(w.session_id) ?? sessionSlug(w.session_id, w.repo2) : null,
    synced_at: w.synced_at,
    created_at: w.created_at,
  }));
}

// did_json from verify.ts is {commits: [{sha, subject}|string], diff_stat: string}; the seed is a string list.
function didLines(v: unknown): string[] {
  if (Array.isArray(v)) return v.map(String)
  if (!v || typeof v !== "object") return []
  const d = v as { commits?: unknown[]; diff_stat?: unknown }
  const commits = (Array.isArray(d.commits) ? d.commits : []).map((c) =>
    c && typeof c === "object" ? [((c as any).sha ?? "").toString().slice(0, 8), (c as any).subject ?? ""].join(" ").trim() : String(c),
  )
  const stat = typeof d.diff_stat === "string" && d.diff_stat.trim() ? d.diff_stat.trim().split("\n").slice(-1) : []
  return [...commits, ...stat]
}

function bundleRows(db: Database): BundleRow[] {
  const rows = all<{
    id: string; worker_id: string | null; session_id: string | null; journal_seq: number | null; head_sha: string | null;
    did_json: string | null; works_json: string | null; verified_json: string | null; verdict: string | null;
    advisory: number | null; summary: string | null; known_gaps: string | null; repo: string | null; worker_model: string | null;
    gate_outcome: string | null; gate_reason: string | null;
  }>(
    db,
    `SELECT b.*, s.repo AS repo, w.model AS worker_model, j.outcome AS gate_outcome, j.reason AS gate_reason
     FROM bundles b LEFT JOIN sessions s ON s.id = b.session_id LEFT JOIN workers w ON w.id = b.worker_id
     LEFT JOIN journal j ON j.seq = b.journal_seq ORDER BY b.id DESC LIMIT 40`,
  );
  // verify.ts writes objects: works_json {claimed, ui_proof}, verified_json {clean, reruns, verdict}.
  // The seed writes plain arrays. Accept both.
  const list = (v: unknown, key: string): Record<string, unknown>[] => {
    const x = v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>)[key] : v;
    return Array.isArray(x) ? (x.filter((r) => r && typeof r === "object") as Record<string, unknown>[]) : [];
  };
  const runs = (text: string | null, key = "reruns"): CommandRun[] =>
    list(parse<unknown>(text, []), key).map((r) => ({
      command: String(r.command ?? r.cmd ?? ""),
      exit: typeof r.exit === "number" ? r.exit : null,
      tail: typeof r.tail === "string" ? r.tail : typeof r.output === "string" ? r.output : null,
    }));
  return rows.map((b) => ({
    id: b.id,
    time: ulidTime(b.id),
    head_sha: b.head_sha,
    verdict: b.verdict,
    advisory: b.advisory,
    summary: b.summary,
    known_gaps: b.known_gaps,
    session_id: b.session_id,
    session_slug: sessionSlug(b.session_id, b.repo),
    repo: b.repo,
    worker_model: b.worker_model,
    did: didLines(parse<unknown>(b.did_json, [])),
    works: runs(b.works_json, "claimed"),
    verified: runs(b.verified_json),
    gate: b.journal_seq ? { outcome: b.gate_outcome, reason: b.gate_reason } : null,
  }));
}

function ruleRows(db: Database, now: number, slugs: Map<string, string | null>): RuleRow[] {
  const today = startOfToday(now);
  const counts = new Map<string, number>();
  for (const r of all<{ rule_id: string; n: number }>(
    db,
    "SELECT rule_id, COUNT(*) AS n FROM journal WHERE event = ? AND time >= ? AND rule_id IS NOT NULL GROUP BY rule_id",
    EVENTS.sendback, today,
  )) counts.set(r.rule_id, r.n);

  const wrongSeqs = new Set<number>();
  const wrongByRule = new Map<string, number>();
  for (const c of all<{ rule_id: string | null; data_json: string | null }>(db, "SELECT rule_id, data_json FROM journal WHERE event = 'harness.wrong' AND time >= ?", today)) {
    const seq = parse<{ seq?: number }>(c.data_json, {}).seq;
    if (typeof seq === "number") wrongSeqs.add(seq);
    if (c.rule_id) wrongByRule.set(c.rule_id, (wrongByRule.get(c.rule_id) ?? 0) + 1);
  }

  return all<{ id: string; event: string | null; module: string | null; mode: string; default_mode: string | null; ships_in: string | null; wrong_today: number | null }>(
    db,
    "SELECT * FROM rules ORDER BY module, id",
  ).map((r) => ({
    id: r.id,
    event: r.event,
    module: r.module,
    mode: r.mode,
    default_mode: r.default_mode,
    ships_in: r.ships_in,
    wrong_today: wrongByRule.get(r.id) ?? 0,
    sendbacks_today: counts.get(r.id) ?? 0,
    recent_sendbacks: all<{ seq: number; time: number; session_id: string | null; reason: string | null }>(
      db,
      "SELECT seq, time, session_id, reason FROM journal WHERE event = ? AND rule_id = ? AND time >= ? ORDER BY seq DESC LIMIT 5",
      EVENTS.sendback, r.id, today,
    ).map((s) => ({
      seq: s.seq,
      time: s.time,
      session_id: s.session_id,
      session_slug: s.session_id ? slugs.get(s.session_id) ?? null : null,
      reason: s.reason,
      wrong: wrongSeqs.has(s.seq),
    })),
  }));
}

export interface JournalQuery {
  session?: string;
  rule?: string;
  event?: string;
  text?: string;
  since?: number;
  before?: number;
  after?: number;
  limit?: number;
}

const likeEscape = (s: string) => s.replace(/[\\%_]/g, (c) => `\\${c}`);

/** Paged read of the journal. Newest first by default; `after` switches to oldest first for replay. */
export function journalPage(db: Database, q: JournalQuery = {}): JournalPage {
  const limit = Math.min(Math.max(Math.floor(q.limit ?? 50), 1), 200);
  const where: string[] = [];
  const params: Params = [];
  if (q.session) { where.push("j.session_id = ?"); params.push(q.session); }
  if (q.rule) { where.push("j.rule_id = ?"); params.push(q.rule); }
  if (q.event) {
    if (q.event.includes("*")) { where.push("j.event LIKE ? ESCAPE '\\'"); params.push(likeEscape(q.event).replace(/\*/g, "%")); }
    else { where.push("j.event = ?"); params.push(q.event); }
  }
  if (q.text) {
    const t = `%${likeEscape(q.text)}%`;
    where.push("(j.reason LIKE ? ESCAPE '\\' OR j.prompt_text LIKE ? ESCAPE '\\' OR j.event LIKE ? ESCAPE '\\')");
    params.push(t, t, t);
  }
  if (q.since) { where.push("j.time >= ?"); params.push(q.since); }
  const ascending = q.after !== undefined;
  if (q.before !== undefined) { where.push("j.seq < ?"); params.push(q.before); }
  if (ascending) { where.push("j.seq > ?"); params.push(q.after as number); }

  const rows = all<{
    seq: number; time: number; turn: number | null; event: string; session_id: string | null; rule_id: string | null;
    outcome: string | null; reason: string | null; prompt_text: string | null; data_json: string | null; repo: string | null;
  }>(
    db,
    `SELECT j.seq, j.time, j.turn, j.event, j.session_id, j.rule_id, j.outcome, j.reason, j.prompt_text, j.data_json, s.repo AS repo
     FROM journal j LEFT JOIN sessions s ON s.id = j.session_id
     ${where.length ? `WHERE ${where.join(" AND ")}` : ""}
     ORDER BY j.seq ${ascending ? "ASC" : "DESC"} LIMIT ?`,
    ...params, limit + 1,
  );
  const has_more = rows.length > limit;
  const page = rows.slice(0, limit).map((r) => ({
    seq: r.seq,
    time: r.time,
    turn: r.turn,
    event: r.event,
    session_id: r.session_id,
    session_slug: sessionSlug(r.session_id, r.repo),
    rule_id: r.rule_id,
    outcome: r.outcome,
    reason: r.reason,
    prompt_text: r.prompt_text && r.prompt_text.length > 2000 ? `${r.prompt_text.slice(0, 2000)}…` : r.prompt_text,
    data: parse<unknown>(r.data_json, null),
  }));
  return { rows: page, has_more, next_cursor: has_more && page.length ? page[page.length - 1].seq : null };
}

// git is slow next to the snapshot loop, and the answer never changes for the same three strings.
const ancestorCache = new Map<string, boolean>();
function isAncestor(repo: string | null, sha: string, tip: string): boolean {
  if (sha === tip) return true;
  if (!repo) return false;
  const key = `${repo}|${sha}|${tip}`;
  let hit = ancestorCache.get(key);
  if (hit === undefined) {
    try {
      hit = Bun.spawnSync(["git", "merge-base", "--is-ancestor", sha, tip], { cwd: repo, stdout: "ignore", stderr: "ignore" }).exitCode === 0;
    } catch {
      hit = false;
    }
    ancestorCache.set(key, hit);
  }
  return hit;
}

function changeRows(db: Database, slugs: Map<string, string | null>, now: number): ChangeRow[] {
  const cur = one<{ value: string }>(db, "SELECT value FROM schema_meta WHERE key = 'current_apply'")?.value;
  const tip = cur ? one<{ sha: string }>(db, "SELECT sha FROM applies WHERE id = ? AND rolled_back_at IS NULL", cur)?.sha ?? null : null;
  const grants = new Map(
    all<{ request_id: string; until: number }>(
      db,
      `SELECT t.request_id, MAX(t.expires_at) AS until FROM tokens t
       JOIN journal j ON j.seq = t.grant_seq AND j.event = 'grant' AND json_extract(j.data_json, '$.token_id') = t.id
       WHERE t.kind = 'harness' AND t.request_id IS NOT NULL AND t.used_at IS NULL AND t.expires_at > ? GROUP BY t.request_id`,
      now,
    ).map((g) => [g.request_id, g.until]),
  );
  return all<{
    id: string; session_id: string | null; sha: string; digest: string; review_seq: number | null; state: string; created_at: number;
    review: string | null; apply_id: string | null; applied_at: number | null; rolled_back_at: number | null; tree_hash: string | null;
  }>(
    db,
    `SELECT r.*, j.prompt_text AS review, a.id AS apply_id, a.applied_at, a.rolled_back_at, a.tree_hash
     FROM requests r LEFT JOIN journal j ON j.seq = r.review_seq LEFT JOIN applies a ON a.request_id = r.id
     ORDER BY r.created_at DESC LIMIT 20`,
  ).map((r) => {
    const status: ChangeRow["status"] = r.rolled_back_at ? "rolled_back" : r.apply_id ? "applied" : r.state === "open" || r.state === "pending" ? "pending" : "other";
    return {
      id: r.id,
      created_at: r.created_at,
      sha: r.sha,
      digest: r.digest,
      state: r.state,
      status,
      session_slug: r.session_id ? slugs.get(r.session_id) ?? sessionSlug(r.session_id, null) : null,
      review: r.review,
      apply: r.apply_id ? { id: r.apply_id, applied_at: r.applied_at, rolled_back_at: r.rolled_back_at, tree_hash: r.tree_hash } : null,
      granted: status === "pending" && grants.has(r.id) ? { until: grants.get(r.id)! } : null,
      superseded:
        status === "pending" && tip !== null &&
        isAncestor(one<{ value: string }>(db, "SELECT value FROM schema_meta WHERE key = ?", `request_repo:${r.id}`)?.value ?? null, r.sha, tip),
    };
  });
}

function jobRows(db: Database, now: number): JobRow[] {
  return all<{ name: string; schedule: string | null; last_run_at: number | null; last_result: string | null }>(db, "SELECT * FROM jobs ORDER BY name").map((j) => {
    let next: number | null = null;
    try {
      if (j.schedule) next = (Bun as unknown as { cron: { parse(e: string, from: Date): Date | null } }).cron.parse(j.schedule, new Date(now))?.getTime() ?? null;
    } catch {
      next = null;
    }
    const r = j.last_result;
    const result: JobResult = r === null ? "never" : /^(fail|error)/i.test(r) ? "failed" : /^ok/i.test(r) ? "ok" : "unknown";
    return { name: j.name, schedule: j.schedule, last_run_at: j.last_run_at, last_result: r, result, next_run_at: next };
  });
}

// last_state is the waker's JSON ({state, review, mergeable, failed, done}); older rows hold a bare word like "open".
function prWatchRows(db: Database, now: number, slugs: Map<string, string | null>): PrWatchRow[] {
  const rows = all<{ id: string; session_id: string | null; target: string | null; last_state: string | null; polled_at: number | null }>(
    db,
    "SELECT id, session_id, target, last_state, polled_at FROM watches WHERE kind = 'pr' AND (expires_at IS NULL OR expires_at > ?) ORDER BY id DESC LIMIT 40",
    now,
  );
  const grants = new Map(
    all<{ pr: number; session_id: string; until: number }>(
      db,
      `SELECT t.pr, t.session_id, MAX(t.expires_at) AS until FROM tokens t
       JOIN journal j ON j.seq = t.grant_seq AND j.event = 'grant' AND json_extract(j.data_json, '$.token_id') = t.id
       WHERE t.kind = 'merge' AND t.pr IS NOT NULL AND t.session_id IS NOT NULL AND t.used_at IS NULL AND t.expires_at > ? GROUP BY t.pr, t.session_id`,
      now,
    ).map((g) => [`${g.pr}:${g.session_id}`, g.until]),
  );
  const out: PrWatchRow[] = [];
  for (const w of rows) {
    const s = parse<{ state?: string; review?: string; mergeable?: string; failed?: string[]; done?: boolean } | string | null>(w.last_state, w.last_state);
    const o = s && typeof s === "object" ? s : {};
    if (o.done) continue;
    const pr = /#(\d+)$/.exec(w.target ?? "")?.[1];
    out.push({
      id: w.id,
      target: w.target ?? "",
      pr: pr ? Number(pr) : null,
      session_id: w.session_id,
      session_slug: w.session_id ? slugs.get(w.session_id) ?? sessionSlug(w.session_id, null) : null,
      granted: pr && w.session_id && grants.has(`${pr}:${w.session_id}`) ? { until: grants.get(`${pr}:${w.session_id}`)! } : null,
      state: o.state ?? (typeof s === "string" ? s : null),
      review: o.review || null,
      mergeable: o.mergeable ?? null,
      failed: Array.isArray(o.failed) ? o.failed : [],
      polled_at: w.polled_at,
    });
  }
  return out;
}

function harnessState(db: Database): { on: boolean; changed_at: number | null } {
  const r = one<{ event: string; time: number }>(db, "SELECT event, time FROM journal WHERE event IN (?, ?) ORDER BY seq DESC LIMIT 1", EVENTS.on, EVENTS.off);
  return { on: r?.event !== EVENTS.off, changed_at: r?.time ?? null };
}

function processRows(db: Database, now: number, slugs: Map<string, string | null>): ProcessRow[] {
  return all<{ id: number; session_id: string | null; pid: number | null; command: string | null; port: number | null; keep: number | null; started_at: number | null; ended_at: number | null }>(
    db,
    `SELECT id, session_id, pid, command, port, keep, started_at, ended_at FROM processes
     WHERE ended_at IS NULL OR ended_at > ? ORDER BY ended_at IS NOT NULL, started_at DESC LIMIT 40`,
    now - 10 * MIN,
  ).map((p) => ({
    id: p.id,
    session_id: p.session_id,
    session_slug: p.session_id ? slugs.get(p.session_id) ?? sessionSlug(p.session_id, null) : null,
    pid: p.pid,
    command: p.command,
    port: p.port,
    keep: Boolean(p.keep),
    started_at: p.started_at,
    ended_at: p.ended_at,
  }));
}

const ADVISE = new Set(["advise", "warn", "inject", "modify"]);

export function tailKind(event: string, outcome: string | null): TailKind | null {
  if (event === EVENTS.sendback) return "sendback";
  if (outcome === "deny") return "deny";
  if (outcome && ADVISE.has(outcome)) return "advise";
  return null;
}

function tailRows(db: Database, limit: number): TailRow[] {
  return journalPage(db, { limit }).rows.map((r) => {
    const d = (r.data && typeof r.data === "object" ? r.data : {}) as { tool?: string; arg?: string };
    return {
      seq: r.seq,
      time: r.time,
      event: r.event,
      session_id: r.session_id,
      session_slug: r.session_slug,
      rule_id: r.rule_id,
      outcome: r.outcome,
      text: firstLine(r.reason ?? r.prompt_text ?? d.arg ?? null, 220) ?? "",
      tool: d.tool ?? null,
      kind: tailKind(r.event, r.outcome),
    };
  });
}

// verifyChain reads the whole journal. Check at most every 30 s, and less often when a check is slow.
const chainCache = new WeakMap<Database, { at: number; ms: number; ok: boolean; bad: number | null }>();

function chainState(db: Database, now: number): { ok: boolean; bad: number | null; at: number } {
  const c = chainCache.get(db);
  if (c && now - c.at < Math.max(30_000, c.ms * 20)) return { ok: c.ok, bad: c.bad, at: c.at };
  const t0 = Date.now();
  const r = verifyChain(db);
  const next = { at: now, ms: Date.now() - t0, ok: r.ok, bad: r.badSeq ?? null };
  chainCache.set(db, next);
  return { ok: next.ok, bad: next.bad, at: next.at };
}

function healthState(db: Database, now: number, seq: number): Health {
  const window = Math.max(seq - 50_000, 0);
  const c = one<{ deny: number | null; advise: number | null; sendback: number | null }>(
    db,
    `SELECT SUM(outcome = 'deny') AS deny, SUM(outcome IN ('advise', 'warn', 'inject', 'modify')) AS advise, SUM(event = ?) AS sendback
     FROM journal WHERE seq > ? AND time >= ?`,
    EVENTS.sendback, window, now - 60 * MIN,
  );
  const series = new Array<number>(60).fill(0);
  for (const b of all<{ ago: number; n: number }>(
    db,
    "SELECT CAST((? - time) / 60000 AS INTEGER) AS ago, COUNT(*) AS n FROM journal WHERE seq > ? AND time >= ? GROUP BY ago",
    now, window, now - 60 * MIN,
  )) series[59 - Math.min(Math.max(b.ago, 0), 59)] += b.n;
  const chain = chainState(db, now);
  return {
    chain_ok: chain.ok,
    chain_bad_seq: chain.bad,
    chain_checked_at: chain.at,
    deny_1h: c?.deny ?? 0,
    advise_1h: c?.advise ?? 0,
    sendback_1h: c?.sendback ?? 0,
    series,
  };
}

export function buildSnapshot(db: Database, now = Date.now()): Snapshot {
  const seq = maxSeq(db);
  const sessions = deriveSessions(db, now);
  const slugs = new Map<string, string | null>(sessions.map((s) => [s.id, s.slug]));
  for (const s of all<{ id: string; repo: string | null }>(db, "SELECT id, repo FROM sessions ORDER BY started_at DESC LIMIT 400")) {
    if (!slugs.has(s.id)) slugs.set(s.id, sessionSlug(s.id, s.repo));
  }
  const inbox = pendingQuestions(db, sessions);
  const worktrees = worktreeRows(db, now, slugs);
  const bundles = bundleRows(db);
  const rules = ruleRows(db, now, slugs);
  const journal = journalPage(db, { limit: 50 });
  const changes = changeRows(db, slugs, now);
  const jobs = jobRows(db, now);
  const harness = harnessState(db);

  const perMin = (one<{ n: number }>(db, "SELECT COUNT(*) AS n FROM journal WHERE seq > ? AND time >= ?", Math.max(seq - 5000, 0), now - 5 * MIN)?.n ?? 0) / 5;
  const hourWindow = 10_000;
  const hourCount = one<{ n: number }>(db, "SELECT COUNT(*) AS n FROM journal WHERE seq > ? AND time >= ?", Math.max(seq - hourWindow, 0), now - 60 * MIN)?.n ?? 0;

  const prompts = one<{ n: number; steer: number | null }>(
    db,
    "SELECT COUNT(*) AS n, SUM(CASE WHEN json_extract(data_json, '$.steering') = 1 THEN 1 ELSE 0 END) AS steer FROM journal WHERE event = ? AND time >= ?",
    EVENTS.prompt, now - 7 * 24 * 60 * MIN,
  );

  const live = sessions.filter((s) => s.state !== "ended");
  const attention: AttentionItem[] = [];
  for (const q of inbox) attention.push({ view: "inbox", id: String(q.seq), tone: "amber", what: "Question waiting", detail: `${q.session_slug}: ${q.text}`, at: q.asked_at });
  for (const x of live) if (x.stuck) attention.push({ view: "sessions", id: x.id, tone: "amber", what: "Stuck", detail: `${x.slug} after ${x.nudges} nudges`, at: x.last_event_at });
  for (const w of worktrees) if (w.sync_state === "conflict") attention.push({ view: "worktrees", id: w.id, tone: "red", what: "Conflict", detail: `${w.branch ?? w.path}: ${w.conflict_files.length} file${w.conflict_files.length === 1 ? "" : "s"}${w.owner_session_id ? "" : ", no owner"}`, at: w.synced_at });
  for (const b of bundles) if (b.verdict === "red") attention.push({ view: "bundles", id: b.id, tone: "red", what: "Red proof bundle", detail: `${b.head_sha?.slice(0, 8) ?? "no sha"}: ${b.summary ?? "no summary"}`, at: b.time });
  for (const c of changes) if (c.status === "pending" && !c.superseded && !c.granted) attention.push({ view: "changes", id: c.id, tone: "amber", what: "Harness change waiting", detail: `${c.sha.slice(0, 8)} asked by ${c.session_slug ?? "unknown"}`, at: c.created_at });
  for (const j of jobs) if (j.result === "failed") attention.push({ view: "jobs", id: j.name, tone: "red", what: "Job failed", detail: `${j.name}: ${j.last_result ?? ""}`, at: j.last_run_at });
  const alerts: Record<ViewId, number> = { inbox: 0, sessions: 0, worktrees: 0, bundles: 0, rules: 0, journal: 0, changes: 0, jobs: 0 };
  for (const a of attention) alerts[a.view]++;
  const counts: Record<ViewId, number> = {
    inbox: inbox.length,
    sessions: live.length,
    worktrees: worktrees.filter((w) => w.state !== "removed").length,
    bundles: bundles.length,
    rules: rules.length,
    journal: hourCount,
    changes: alerts.changes,
    jobs: jobs.length,
  };

  const ledger: LedgerSnapshot = {
    now,
    seq,
    harnessOn: harness.on,
    sessions,
    questions: inbox,
    worktrees,
    rules: rules.map((r) => ({ id: r.id, mode: r.mode, default_mode: r.default_mode })),
    watches: all(db, "SELECT id, session_id, kind, target, last_state, polled_at FROM watches WHERE expires_at IS NULL OR expires_at > ?", now),
    wakes: all<{ seq: number; time: number; session_id: string | null; reason: string | null }>(
      db, "SELECT seq, time, session_id, reason FROM journal WHERE event = ? AND time >= ? ORDER BY seq DESC LIMIT 20", EVENTS.wake, now - 5 * MIN,
    ),
    grants: all(db, "SELECT id, kind, pr, session_id, used_at, expires_at FROM tokens WHERE kind IN ('merge', 'harness') ORDER BY id DESC LIMIT 12"),
    jobs: jobs.map((j) => ({ name: j.name, schedule: j.schedule, last_run_at: j.last_run_at, result: j.result, next_run_at: j.next_run_at })),
    recent: all(db, "SELECT seq, time, event, outcome FROM journal ORDER BY seq DESC LIMIT 40"),
    journalPerMin: perMin,
    steeringShare7d: prompts && prompts.n > 0 ? (prompts.steer ?? 0) / prompts.n : null,
  };

  return {
    at: now,
    seq,
    host: hostname().split(".")[0],
    pr_watches: prWatchRows(db, now, slugs),
    harness,
    counts,
    alerts,
    attention,
    ledger,
    views: {
      inbox,
      sessions,
      worktrees,
      bundles,
      rules,
      journal: { ...journal, per_min: perMin },
      changes,
      jobs,
    },
    dash: {
      processes: processRows(db, now, slugs),
      tail: tailRows(db, 120),
      health: healthState(db, now, seq),
    },
    resources: null,
  };
}
