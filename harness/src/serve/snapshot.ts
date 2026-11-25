// Builds the page's data from the ledger. Read-only: nothing here writes a table.
// Event names it reads (journal.event): prompt, stop, stop.sendback, nudge, session.stuck, goal,
// question.asked, question.answered, grant, harness.wrong, egress.warning, watch.wake, harness.on,
// harness.off, harness.review. Where the ledger lane names one differently, change it in EVENTS.
import type { Database } from "bun:sqlite";
import { hostname } from "node:os";

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

export interface Snapshot {
  at: number;
  seq: number;
  host: string;
  harness: { on: boolean; changed_at: number | null };
  counts: Record<ViewId, number>;
  alerts: Record<ViewId, number>;
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
  return `${repo ?? "session"}·${id.slice(-4).toLowerCase()}`;
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
    };
  });
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
  return firstLine(p?.prompt_text ?? null);
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
    const data = parse<{ question?: string; options?: (string | { label?: string })[] }>(ask.data_json, {});
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
  const runs = (text: string | null): CommandRun[] =>
    parse<Record<string, unknown>[]>(text, []).map((r) => ({
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
    did: parse<unknown[]>(b.did_json, []).map(String),
    works: runs(b.works_json),
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

function changeRows(db: Database, slugs: Map<string, string | null>): ChangeRow[] {
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

function harnessState(db: Database): { on: boolean; changed_at: number | null } {
  const r = one<{ event: string; time: number }>(db, "SELECT event, time FROM journal WHERE event IN (?, ?) ORDER BY seq DESC LIMIT 1", EVENTS.on, EVENTS.off);
  return { on: r?.event !== EVENTS.off, changed_at: r?.time ?? null };
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
  const changes = changeRows(db, slugs);
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
  const counts: Record<ViewId, number> = {
    inbox: inbox.length,
    sessions: live.length,
    worktrees: worktrees.filter((w) => w.state !== "removed").length,
    bundles: bundles.length,
    rules: rules.length,
    journal: hourCount,
    changes: changes.filter((c) => c.status === "pending").length,
    jobs: jobs.length,
  };
  const alerts: Record<ViewId, number> = {
    inbox: inbox.length,
    sessions: live.filter((s) => s.stuck).length,
    worktrees: worktrees.filter((w) => w.sync_state === "conflict").length,
    bundles: bundles.filter((b) => b.verdict === "red").length,
    rules: 0,
    journal: 0,
    changes: counts.changes,
    jobs: jobs.filter((j) => j.result === "failed").length,
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
    harness,
    counts,
    alerts,
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
  };
}
