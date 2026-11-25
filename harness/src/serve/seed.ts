// Development and test fixture for the page. The schema and the hash chain come from the ledger lane
// (openLedger, append); this file only inserts realistic rows.
import type { Database } from "bun:sqlite";
import { join } from "node:path";
import { openLedger } from "../ledger/db.ts";
import { append } from "../ledger/journal.ts";

const CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";

export function ulid(ms: number, n: number): string {
  let t = "";
  let x = Math.floor(ms);
  for (let i = 0; i < 10; i++) {
    t = CROCKFORD[x % 32] + t;
    x = Math.floor(x / 32);
  }
  let r = "";
  let y = n * 2654435761 + 12345;
  for (let i = 0; i < 16; i++) {
    r += CROCKFORD[Math.abs(y) % 32];
    y = Math.floor(y / 32) + n * 7 + i;
  }
  return t + r;
}

export interface JournalInput {
  session_id: string | null;
  turn?: number;
  time: number;
  event: string;
  rule_id?: string | null;
  outcome?: string | null;
  reason?: string | null;
  prompt_text?: string | null;
  data?: unknown;
}

export function appendJournal(db: Database, r: JournalInput): number {
  return append(db, { ...r, turn: r.turn ?? 1 });
}

const MIN = 60_000;

/** Realistic rows: 6 sessions, a waiting question, a stuck worker, worktrees with a conflict, bundles green and red, rules, journal. */
export function seedLedger(stateDir: string, now = Date.now()): string {
  const path = join(stateDir, "ledger.db");
  const db = openLedger(path);

  const S = (n: number) => ulid(now - 3 * 60 * MIN + n, n);
  const sessions = [
    { id: S(1), parent: null, tool: "opencode", repo: "alex-skills", cwd: "~/.agents/skills", model: "claude-opus-4-7", started: now - 142 * MIN, ended: null },
    { id: S(2), parent: null, tool: "claude-code", repo: "mac-bootstrap", cwd: "~/src/mac-bootstrap", model: "claude-sonnet-5-5", started: now - 96 * MIN, ended: null },
    { id: S(3), parent: S(1), tool: "opencode", repo: "alex-skills", cwd: "~/.worktrees/harness-ledger", model: "cursor/claude-haiku-5-5", started: now - 61 * MIN, ended: null },
    { id: S(4), parent: null, tool: "claude-code", repo: "platform-infra", cwd: "~/src/platform-infra", model: "claude-opus-4-7", started: now - 33 * MIN, ended: null },
    { id: S(5), parent: S(1), tool: "opencode", repo: "alex-skills", cwd: "~/.worktrees/harness-serve", model: "cursor/claude-sonnet-5-5", started: now - 24 * MIN, ended: null },
    { id: S(6), parent: null, tool: "opencode", repo: "blog", cwd: "~/src/blog", model: "claude-sonnet-5-5", started: now - 75 * MIN, ended: now - 3 * MIN },
  ];
  const ins = db.query("INSERT INTO sessions (id, parent_session_id, tool, repo, cwd, model, interactive, started_at, ended_at) VALUES (?,?,?,?,?,?,?,?,?)");
  for (const s of sessions) ins.run(s.id, s.parent, s.tool, s.repo, s.cwd, s.model, s.parent ? 0 : 1, s.started, s.ended);
  const [s1, s2, s3, s4, s5, s6] = sessions.map((s) => s.id);

  const rules: [string, string, string, string, string, string, number][] = [
    ["recursive-delete", "tool.before", "destructive", "enforce", "enforce", "phase 1", 0],
    ["merge-in-shell", "tool.before", "destructive", "enforce", "enforce", "phase 1", 0],
    ["destructive-git", "tool.before", "destructive", "enforce", "enforce", "phase 1", 0],
    ["harness-self", "tool.before", "authority", "enforce", "enforce", "phase 1", 0],
    ["stop-needs-proof", "stop", "stop-checks", "enforce", "enforce", "phase 2", 1],
    ["stop-open-processes", "stop", "stop-checks", "advise", "enforce", "phase 3", 0],
    ["drift-nudge", "tool.after", "judgment", "inject", "inject", "phase 5", 0],
    ["egress-guard", "tool.before", "egress", "advise", "advise", "phase 9", 0],
    ["worker-test-edit", "tool.before", "workers", "off", "enforce", "phase 4", 0],
  ];
  const insRule = db.query("INSERT INTO rules (id, event, module, mode, default_mode, ships_in, wrong_today, updated_at) VALUES (?,?,?,?,?,?,?,?)");
  for (const r of rules) insRule.run(...r, now - 40 * MIN);

  // Journal stream, oldest first.
  const j = (session: string | null, minAgo: number, event: string, extra: Partial<JournalInput> = {}) =>
    appendJournal(db, { session_id: session, time: now - minAgo * MIN, event, ...extra });

  for (const s of sessions) j(s.id, (now - s.started) / MIN, "session.start", { outcome: "ok" });
  j(s1, 141, "prompt", { turn: 1, prompt_text: "Build the harness serve page: working views and the shell around the office. Spec is docs/specs/harness-office.md." });
  j(s1, 141, "goal", { turn: 1, data: { goal: "Build harness serve and the 8 working views" } });
  j(s2, 95, "prompt", { turn: 1, prompt_text: "Pin Bun on the VM and the Mac in mac-bootstrap, then verify the install on both." });
  j(s4, 32, "prompt", { turn: 1, prompt_text: "Plan the OpenTofu change for the new log bucket, no apply." });
  j(s6, 74, "prompt", { turn: 1, prompt_text: "Draft the post on steering prompts." });
  j(s6, 4, "stop", { turn: 4, outcome: "allow" });
  j(s3, 60, "prompt", { turn: 1, prompt_text: "Write the ledger db module. Acceptance: bun test tests/ledger.test.ts exits 0." });
  j(s5, 23, "prompt", { turn: 1, prompt_text: "Write the harness serve routes and the 8 views." });

  const tools = ["Read", "Grep", "Edit", "Shell", "Write"];
  const args: Record<string, string[]> = {
    Read: ["harness/src/serve/snapshot.ts", "harness/ui/app/app.css", "docs/specs/harness-office.md", "harness/src/ledger/journal.ts"],
    Grep: ["verifyChain", "sync_state", "originOf", "outcome = 'deny'"],
    Edit: ["harness/ui/app/views/dashboard.ts", "harness/src/serve/seed.ts", "mac-bootstrap/bun-pin.sh", "tofu/log_bucket.tf"],
    Shell: ["bun test tests/serve.test.ts", "git diff --stat", "tofu plan -out=tfplan", "bun run typecheck"],
    Write: ["harness/ui/app/views/dashboard.ts", "docs/notes/pin-bun.md", "harness/tests/ledger.test.ts"],
  };
  // 160 tool rows over the last hour, a little denser toward now, so the sparkline has a shape.
  for (let i = 0; i < 160; i++) {
    const sid = [s1, s2, s3, s4, s5][i % 5];
    const tool = tools[(i >> 1) % tools.length];
    const deny = i % 17 === 5;
    const advise = !deny && i % 23 === 9;
    j(sid, 58 - Math.pow(i / 159, 0.8) * 54, i % 2 ? "tool.after" : "tool.before", {
      turn: 1 + Math.floor(i / 55),
      outcome: deny ? "deny" : advise ? "advise" : "allow",
      reason: deny ? "recursive-delete: path outside the allowlist" : advise ? "egress-guard: argument over 2000 characters" : null,
      rule_id: deny ? "recursive-delete" : advise ? "egress-guard" : null,
      data: { tool, arg: args[tool][(i >> 1) % args[tool].length] },
    });
  }
  const sb1 = j(s5, 30, "stop.sendback", { turn: 1, rule_id: "stop-needs-proof", outcome: "deny", reason: "No test output shown for the claim 'tests pass'." });
  const sb2 = j(s1, 52, "stop.sendback", { turn: 1, rule_id: "stop-needs-proof", outcome: "deny", reason: "The reply names a server on port 4317 but the process is not in the ledger." });
  j(s1, 50, "correction", { turn: 2, outcome: "wrong", reason: "send-back was right: server was running" });
  j(s1, 49, "harness.wrong", { turn: 2, rule_id: "stop-needs-proof", outcome: "wrong", data: { seq: sb2 } });
  for (let i = 1; i <= 5; i++) j(s3, 30 - i * 3, "nudge", { turn: 3, rule_id: "drift-nudge", outcome: "inject", reason: `Drift from goal, nudge ${i} of 5` });
  j(s3, 12, "session.stuck", { turn: 3, outcome: "stuck", reason: "5 nudges in one turn with no progress" });
  j(s4, 14, "egress.warning", { turn: 1, rule_id: "egress-guard", outcome: "warn", reason: "Argument over 2000 characters sent to exa_web_search_exa" });
  j(s1, 20, "grant", { turn: 3, outcome: "grant", reason: "MERGE-OK 214 typed by Alex", data: { kind: "merge", pr: 214 } });
  j(s1, 19, "watch.wake", { turn: 3, outcome: "ok", reason: "PR 214 merged", data: { kind: "pr", pr: 214 } });
  j(s5, 8, "watch.wake", { turn: 1, outcome: "ok", reason: "CI red on alex-skills#219", data: { kind: "ci" } });
  for (let i = 0; i < 6; i++) j(s1, 45 - i * 6, "prompt", { turn: 2 + i, prompt_text: ["merged", "link?", "what now?", "continue", "ok go", "show me the diff"][i], data: { steering: i < 4 ? 1 : 0 } });
  j(s4, 9, "stop", { turn: 1, outcome: "allow" });
  const q = j(s2, 6, "question.asked", {
    turn: 3,
    prompt_text: "The VM has no Bun in its PATH after login. Which way do you want me to pin it?",
    data: { question: "The VM has no Bun in its PATH after login. Which way do you want me to pin it?", options: ["Add ~/.bun/bin to the login shell profile", "Install Bun under /usr/local with mise", "Stop and let me look at the VM first"] },
  });
  void q;

  // Processes the harness knows about: two kept on purpose, three live, one that just ended.
  const proc = db.query("INSERT INTO processes (session_id, pid, command, port, keep, started_at, ended_at, reported_at) VALUES (?,?,?,?,?,?,?,?)");
  proc.run(s1, 49120, "caddy run --config Caddyfile", 8443, 1, now - 130 * MIN, null, now - 20 * 1000);
  proc.run(s5, 48211, "bun src/serve/main.ts", 4318, 1, now - 23 * MIN, null, now - 20 * 1000);
  proc.run(s2, 51877, "vite --port 5173", 5173, 0, now - 18 * MIN, null, now - 20 * 1000);
  proc.run(s3, 50233, "bun test --watch tests/ledger.test.ts", null, 0, now - 40 * MIN, null, now - 20 * 1000);
  proc.run(s4, 52010, "tofu plan -out=tfplan", null, 0, now - 7 * MIN, null, now - 20 * 1000);
  proc.run(s5, 47001, "bun build ui/app/main.ts --outdir /tmp/ui", null, 0, now - 9 * MIN, now - 4 * MIN, now - 4 * MIN);

  // Worktrees, workstreams, workers.
  const ws = ulid(now - 150 * MIN, 91);
  db.query("INSERT INTO workstreams (id, owner_session_id, repo, title, state, updated_at) VALUES (?,?,?,?,?,?)").run(ws, s1, "alex-skills", "Harness: ledger, authority, serve", "active", now - 5 * MIN);
  const wt = (n: number, session: string | null, repo: string, path: string, branch: string, state: string, sync: string, files: string[] | null, ago: number) => {
    const id = ulid(now - ago * MIN, 200 + n);
    db.query("INSERT INTO worktrees (id, workstream_id, session_id, repo, path, branch, state, sync_state, conflict_files, synced_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)").run(id, ws, session, repo, path, branch, state, sync, files ? JSON.stringify(files) : null, now - 2 * MIN, now - ago * MIN);
    return id;
  };
  const w3 = wt(1, s3, "alex-skills", "~/.worktrees/harness-ledger", "feat/harness-ledger", "active", "conflict", ["harness/src/ledger/db.ts", "harness/package.json", "docs/specs/harness-ledger.erd.json"], 61);
  const w5 = wt(2, s5, "alex-skills", "~/.worktrees/harness-serve", "feat/harness-serve", "active", "behind", null, 24);
  wt(3, s2, "mac-bootstrap", "~/.worktrees/bun-pin", "chore/bun-pin", "active", "current", null, 95);
  wt(4, s1, "alex-skills", "~/.worktrees/harness-core", "feat/harness-core", "landed", "current", null, 140);
  wt(5, null, "platform-infra", "~/.worktrees/log-bucket", "feat/log-bucket", "held", "behind", null, 300);

  const wk = (n: number, parent: string, worker: string, wtree: string, model: string, ago: number) => {
    const id = ulid(now - ago * MIN, 300 + n);
    db.query("INSERT INTO workers (id, parent_session_id, worker_session_id, worktree_id, model, base_sha, acceptance, ladder_round, last_activity) VALUES (?,?,?,?,?,?,?,?,?)").run(id, parent, worker, wtree, model, "9c1e4b7", JSON.stringify({ objective: n === 1 ? "Write the ledger db module" : "Write the harness serve routes and the 8 views", commands: ["bun test tests/ledger.test.ts"] }), n, now - (n === 1 ? 13 : 1) * MIN);
    return id;
  };
  const k3 = wk(1, s1, s3, w3, "cursor/claude-haiku-5-5", 61);
  const k5 = wk(2, s1, s5, w5, "cursor/claude-sonnet-5-5", 24);

  const bundle = (n: number, worker: string, session: string, head: string, verdict: string, advisory: number, summary: string, did: string[], works: unknown[], verified: unknown[], gaps: string | null, ago: number) => {
    const seq = j(session, ago, "bundle", { outcome: verdict, reason: verdict === "green" ? "push gate: pass" : "push gate: blocked, re-run failed" });
    db.query("INSERT INTO bundles (id, worker_id, session_id, journal_seq, head_sha, did_json, works_json, verified_json, verdict, advisory, summary, known_gaps) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)").run(ulid(now - ago * MIN, 400 + n), worker, session, seq, head, JSON.stringify(did), JSON.stringify(works), JSON.stringify(verified), verdict, advisory, summary, gaps);
  };
  bundle(1, k3, s3, "4be91f0a7c", "green", 0.91, "Ledger db module opens the file, runs migrations, appends journal rows.", ["harness/src/ledger/db.ts +212", "tests/ledger.test.ts +88"], [{ command: "bun test tests/ledger.test.ts", exit: 0, tail: "14 pass, 0 fail" }], [{ command: "bun test tests/ledger.test.ts", exit: 0, tail: "14 pass, 0 fail" }, { command: "bun run typecheck", exit: 0, tail: "no errors" }], null, 38);
  bundle(2, k3, s3, "77d20c9e13", "red", 0.34, "Journal hash chain added; re-run of the chain test fails.", ["harness/src/ledger/journal.ts +140"], [{ command: "bun test tests/journal.test.ts", exit: 0, tail: "9 pass" }], [{ command: "bun test tests/journal.test.ts", exit: 1, tail: "1 fail: prev_hash does not match row 3" }], "Worker reported 9 pass; the harness re-run shows 1 fail. Chain test not edited.", 20);
  bundle(3, k5, s5, "a03f55b2d8", "green", 0.88, "Snapshot builder and routes return all 8 views.", ["harness/src/serve/snapshot.ts +310"], [{ command: "bun test tests/serve.test.ts", exit: 0, tail: "4 pass" }], [{ command: "bun test tests/serve.test.ts", exit: 0, tail: "4 pass" }], "Passkey flow checked in a browser only.", 9);
  bundle(4, k5, s5, "d1c8e77f02", "green", 0.79, "Rules view and journal paging.", ["harness/ui/app/views/rules.ts +120"], [{ command: "bun build ui/app/main.ts", exit: 0, tail: "bundled" }], [{ command: "bun build ui/app/main.ts", exit: 0, tail: "bundled" }], null, 3);

  // Requests, tokens, applies.
  const rv = j(s1, 25, "harness.review", { outcome: "rendered", prompt_text: "Review of 3 files changed:\n  M harness/src/core.ts   (+14 -2)\n  A harness/src/serve/snapshot.ts\n  M harness/src/ledger/authority.ts  (changed case: merge needs a token)\nAuthority suite: 31 pass. Changed case: authority.test.ts 'page grant needs a fresh assertion'." });
  db.query("INSERT INTO requests (id, session_id, sha, digest, review_seq, state, created_at) VALUES (?,?,?,?,?,?,?)").run(ulid(now - 25 * MIN, 500), s1, "e4f9a1c2b7d3", "5a7d90b1", rv, "open", now - 25 * MIN);
  const rv2 = j(s1, 110, "harness.review", { outcome: "rendered", prompt_text: "Review of 1 file changed:\n  M harness/src/shell/parse.ts (+6 -1)\nAuthority suite: 28 pass." });
  const rq2 = ulid(now - 110 * MIN, 501);
  db.query("INSERT INTO requests (id, session_id, sha, digest, review_seq, state, created_at) VALUES (?,?,?,?,?,?,?)").run(rq2, s1, "1b2c3d4e5f60", "c0ffee01", rv2, "applied", now - 110 * MIN);
  const tk = ulid(now - 108 * MIN, 502);
  db.query("INSERT INTO tokens (id, kind, session_id, grant_seq, request_id, pr, expires_at, used_at) VALUES (?,?,?,?,?,?,?,?)").run(tk, "harness", s1, null, rq2, null, now - 78 * MIN, now - 106 * MIN);
  db.query("INSERT INTO applies (id, request_id, token_id, sha, tree_hash, schema_version, applied_at, rolled_back_at) VALUES (?,?,?,?,?,?,?,?)").run(ulid(now - 106 * MIN, 503), rq2, tk, "1b2c3d4e5f60", "tree-8a1f", 1, now - 106 * MIN, null);
  db.query("INSERT INTO tokens (id, kind, session_id, grant_seq, request_id, pr, expires_at, used_at) VALUES (?,?,?,?,?,?,?,?)").run(ulid(now - 20 * MIN, 504), "merge", s1, null, null, 214, now + 10 * MIN, now - 19 * MIN);

  // Watches and jobs.
  db.query("INSERT INTO watches (id, session_id, worker_id, kind, target, last_state, polled_at, expires_at) VALUES (?,?,?,?,?,?,?,?)").run(ulid(now - 30 * MIN, 600), s5, k5, "ci", "alex-skills#219", "red", now - 2 * MIN, now + 20 * 60 * MIN);
  db.query("INSERT INTO watches (id, session_id, worker_id, kind, target, last_state, polled_at, expires_at) VALUES (?,?,?,?,?,?,?,?)").run(ulid(now - 90 * MIN, 601), s2, null, "pr", "mac-bootstrap#58", "open", now - 2 * MIN, now + 20 * 60 * MIN);
  const jobs: [string, string, number | null, string | null][] = [
    ["correction-miner", "0 3 * * *", now - 17 * 60 * MIN, "ok: 4 corrections mined"],
    ["red-team-canary", "0 4 * * 1", now - 3 * 24 * 60 * MIN, "failed: bwrap exited 1"],
    ["new-model-evals", "0 5 1 * *", null, null],
  ];
  for (const jb of jobs) db.query("INSERT INTO jobs (name, schedule, last_run_at, last_result, last_seq) VALUES (?,?,?,?,?)").run(jb[0], jb[1], jb[2], jb[3], null);

  // The last three minutes, in time order, so the newest end of the tail reads like a live log.
  const recent: [string, number, string, string | null, string | null, string | null, { tool: string; arg: string } | null][] = [
    [s5, 2.9, "tool.before", "allow", null, null, { tool: "Edit", arg: "harness/ui/app/views/dashboard.ts" }],
    [s5, 2.8, "tool.after", "allow", null, null, { tool: "Edit", arg: "harness/ui/app/views/dashboard.ts" }],
    [s1, 2.6, "tool.before", "allow", null, null, { tool: "Shell", arg: "git diff --stat" }],
    [s1, 2.5, "tool.after", "allow", null, null, { tool: "Shell", arg: "git diff --stat" }],
    [s3, 2.3, "nudge", "inject", "drift-nudge", "Drift from goal, nudge 5 of 5", null],
    [s4, 2.1, "tool.before", "deny", "recursive-delete", "recursive-delete: path outside the allowlist", { tool: "Shell", arg: "rm -rf .terraform/modules" }],
    [s2, 1.9, "tool.before", "allow", null, null, { tool: "Read", arg: "mac-bootstrap/bun-pin.sh" }],
    [s2, 1.8, "tool.after", "allow", null, null, { tool: "Read", arg: "mac-bootstrap/bun-pin.sh" }],
    [s5, 1.5, "tool.before", "allow", null, null, { tool: "Shell", arg: "bun test tests/serve.test.ts" }],
    [s5, 1.2, "tool.after", "allow", null, null, { tool: "Shell", arg: "bun test tests/serve.test.ts" }],
    [s1, 0.9, "tool.before", "allow", null, null, { tool: "Grep", arg: "verifyChain" }],
    [s1, 0.8, "tool.after", "allow", null, null, { tool: "Grep", arg: "verifyChain" }],
    [s4, 0.6, "tool.before", "advise", "egress-guard", "egress-guard: argument over 2000 characters", { tool: "exa_web_search_exa", arg: "opentofu s3 log bucket lifecycle rules" }],
    [s5, 0.4, "tool.before", "allow", null, null, { tool: "Edit", arg: "harness/ui/app/app.css" }],
    [s3, 0.2, "tool.before", "allow", null, null, { tool: "Read", arg: "harness/src/ledger/db.ts" }],
  ];
  for (const [sid, ago, event, outcome, rule, reason, data] of recent) j(sid, ago, event, { turn: 3, outcome, rule_id: rule, reason, data });

  void [sb1, s6];
  db.close();
  return path;
}

if (import.meta.main) {
  const dir = process.argv[2] ?? process.env.HARNESS_STATE_DIR;
  if (!dir) {
    console.error("usage: bun src/serve/seed.ts <state-dir>");
    process.exit(2);
  }
  console.log(seedLedger(dir));
}
