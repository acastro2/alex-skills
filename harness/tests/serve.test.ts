// Acceptance criteria for `harness serve` (docs/specs/harness-office.md, O7 and O9; D61).
import { afterAll, beforeAll, expect, test } from "bun:test";
import { Database } from "bun:sqlite";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { appendJournal, seedLedger } from "../src/serve/seed.ts";
import { startServer, type Started } from "../src/serve/server.ts";

let dir: string;
let db: Database;
let server: Started;
let cookie: string;

beforeAll(async () => {
  dir = mkdtempSync(join(tmpdir(), "harness-serve-"));
  const path = seedLedger(dir);
  db = new Database(path, { readwrite: true });
  server = await startServer({ db, port: 0 });
  cookie = `harness_session=${server.app.auth.mintSession().token}`;
});

afterAll(() => {
  server.stop();
  db.close();
  rmSync(dir, { recursive: true, force: true });
});

const get = (path: string, headers: Record<string, string> = {}) => fetch(`${server.url}${path}`, { headers: { cookie, ...headers } });

test("GET /api/snapshot from a seeded ledger returns the data of all 8 views", async () => {
  const res = await get("/api/snapshot");
  expect(res.status).toBe(200);
  const snap = await res.json();

  expect(Object.keys(snap.views).sort()).toEqual(["bundles", "changes", "inbox", "jobs", "journal", "rules", "sessions", "worktrees"]);
  expect(snap.views.inbox).toHaveLength(1);
  expect(snap.views.inbox[0].options).toHaveLength(3);
  expect(snap.views.sessions).toHaveLength(6);
  expect(snap.views.sessions.filter((s: { state: string }) => s.state === "stuck")).toHaveLength(1);
  expect(snap.views.sessions.filter((s: { state: string }) => s.state === "waiting")).toHaveLength(1);
  expect(snap.views.worktrees.find((w: { sync_state: string }) => w.sync_state === "conflict").conflict_files.length).toBeGreaterThan(0);
  expect(snap.views.bundles.map((b: { verdict: string }) => b.verdict)).toContain("red");
  expect(snap.views.bundles.map((b: { verdict: string }) => b.verdict)).toContain("green");
  expect(snap.views.rules.length).toBe(9);
  expect(snap.views.journal.rows.length).toBeGreaterThan(0);
  expect(snap.views.changes.map((c: { status: string }) => c.status).sort()).toEqual(["applied", "pending"]);
  expect(snap.views.jobs).toHaveLength(3);
  expect(snap.counts.inbox).toBe(1);
  expect(snap.ledger.questions).toHaveLength(1);
});

test("the snapshot carries what the dashboard reads: processes, journal tail, health series, last tool and worktree", async () => {
  const snap = await (await get("/api/snapshot")).json();

  expect(snap.dash.processes.length).toBeGreaterThan(0);
  expect(snap.dash.processes.some((p: { ended_at: number | null }) => p.ended_at === null)).toBe(true);
  expect(snap.dash.tail.length).toBeGreaterThan(0);
  expect(snap.dash.tail[0].seq).toBeGreaterThan(snap.dash.tail[1].seq);
  expect(snap.dash.tail.some((r: { kind: string | null }) => r.kind === "deny")).toBe(true);
  expect(snap.dash.tail.some((r: { kind: string | null }) => r.kind === "sendback")).toBe(true);
  expect(snap.dash.health.series).toHaveLength(60);
  expect(snap.dash.health.series.every((n: unknown) => typeof n === "number")).toBe(true);
  expect(snap.dash.health.chain_ok).toBe(true);
  expect(snap.dash.health.deny_1h).toBeGreaterThan(0);

  const sessions = snap.views.sessions as { slug: string; last_tool: { name: string } | null; worktree: string | null }[];
  expect(sessions.some((s) => s.last_tool?.name)).toBe(true);
  expect(sessions.some((s) => s.worktree === "feat/harness-ledger")).toBe(true);
});

test("a request with Host evil.example is rejected", async () => {
  const res = await fetch(`${server.url}/api/snapshot`, { headers: { cookie, host: "evil.example" } });
  expect(res.status).toBe(421);
  const index = await fetch(`${server.url}/`, { headers: { host: "evil.example" } });
  expect(index.status).toBe(421);
});

test("POST /api/action/off without a fresh assertion is 401", async () => {
  const res = await fetch(`${server.url}/api/action/off`, {
    method: "POST",
    headers: { cookie, "content-type": "application/json", origin: server.url },
    body: JSON.stringify({ args: {} }),
  });
  expect(res.status).toBe(401);
});

test("SSE sends a fresh snapshot after a journal row is appended", async () => {
  const res = await get("/api/events");
  expect(res.headers.get("content-type")).toContain("text/event-stream");
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // One read stays pending across timeouts, so a chunk that arrives late is never dropped.
  let pending: Promise<ReadableStreamReadResult<Uint8Array>> | null = null;
  const nextSnapshot = async (timeoutMs: number) => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const m = buffer.match(/event: snapshot\ndata: (.*)\n\n/);
      if (m) {
        buffer = buffer.slice((m.index ?? 0) + m[0].length);
        return JSON.parse(m[1]);
      }
      pending ??= reader.read();
      const chunk = await Promise.race([pending, new Promise<null>((r) => setTimeout(() => r(null), 200))]);
      if (chunk) {
        pending = null;
        if (!chunk.done) buffer += decoder.decode(chunk.value);
      }
    }
    return null;
  };

  const first = await nextSnapshot(2000);
  expect(first).not.toBeNull();

  const writer = new Database(join(dir, "ledger.db"), { readwrite: true });
  appendJournal(writer, { session_id: null, time: Date.now(), event: "prompt", prompt_text: "appended while the stream is open" });
  writer.close();

  const second = await nextSnapshot(3000);
  await reader.cancel();
  expect(second).not.toBeNull();
  expect(second.seq).toBeGreaterThan(first.seq);
});

// Seen live 2026-11-25: the dashboard read the seed's shapes, and the first real bundle broke the whole page.
test("the snapshot reads rows written by the real modules: a verify bundle and a question", async () => {
  const { openLedger } = await import("../src/ledger/db.ts");
  const { verify } = await import("../src/proof/verify.ts");
  const { decide, closeCore } = await import("../src/core.ts");
  const { buildSnapshot } = await import("../src/serve/snapshot.ts");
  const d = mkdtempSync(join(tmpdir(), "harness-real-"));
  const prev = process.env.HARNESS_STATE_DIR;
  process.env.HARNESS_STATE_DIR = join(d, "state");
  try {
    const repo = join(d, "repo");
    const g = (...a: string[]) => Bun.spawnSync(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t", ...a]);
    Bun.spawnSync(["git", "init", "-q", "-b", "main", repo]);
    await Bun.write(join(repo, "a.txt"), "x\n");
    g("add", "."); g("commit", "-qm", "init");
    await Bun.write(join(repo, "a.txt"), "y\n");
    g("commit", "-qam", "change a");
    const db = openLedger();
    const base = g("rev-parse", "HEAD~1").stdout.toString().trim();
    await verify(db, { session: "s1", cwd: repo, commands: ["true"], baseSha: base });
    await decide({ v: 1, event: "tool.before", tool: "claude", session: "s1", parentSession: null, cwd: repo, time: Date.now(), toolName: "askuserquestion", input: { questions: [{ question: "Pick one?", options: [{ label: "A" }, { label: "B" }] }] } });
    const snap = buildSnapshot(db) as any;
    const b = snap.views.bundles?.[0] ?? snap.bundles?.[0];
    expect(b.verdict).toBe("green");
    expect(b.did.some((l: string) => l.includes("change a"))).toBe(true);
    expect(b.verified[0]).toMatchObject({ command: "true", exit: 0 });
    closeCore();
    db.close();
  } finally {
    if (prev === undefined) delete process.env.HARNESS_STATE_DIR; else process.env.HARNESS_STATE_DIR = prev;
    rmSync(d, { recursive: true, force: true });
  }
});

// Seen live 2026-11-25: full paths as session names, and "HARNESS-CONTRACT v1" as a worker's goal.
test("session names use the repo's last path part, and a worker goal skips the contract", async () => {
  const { sessionSlug, goalLine } = await import("../src/serve/snapshot.ts");
  expect(sessionSlug("ses_abcdWXYZ", "/home/u/Developer/org/builder-hub")).toBe("builder-hub·wxyz");
  expect(goalLine("HARNESS-CONTRACT v1\n- Load the `coding` skill first.\nFix the parser bug")).toBe("Fix the parser bug");
  expect(goalLine("Load the coding skill.\n\nOBJECTIVE: the harness MCP server\nmore")).toBe("the harness MCP server");
});

// Alex asked for a stickier session: it must survive a restart and slide while it is used.
test("a page session survives a restart, slides on use, and stops at the 7-day cap", async () => {
  const { openLedger } = await import("../src/ledger/db.ts");
  const { Auth, SESSION_MS, SESSION_MAX_MS } = await import("../src/serve/auth.ts");
  const d = mkdtempSync(join(tmpdir(), "harness-sess-"));
  try {
    const db = openLedger(join(d, "ledger.db"));
    let t = 1_000_000;
    const clock = () => t;
    const { token } = new Auth(db, clock).mintSession();
    const req = () => new Request("https://localhost/", { headers: { cookie: `harness_session=${token}` } });
    const restarted = new Auth(db, clock); // a new process: no in-memory sessions
    t += SESSION_MS - 60_000;
    const s = restarted.session(req());
    expect(s).not.toBeNull();
    expect(s!.until).toBe(t + SESSION_MS); // slid forward
    t += SESSION_MS - 60_000;
    expect(new Auth(db, clock).session(req())).not.toBeNull(); // still alive after another near-full idle
    t = 1_000_000 + SESSION_MAX_MS + 1;
    expect(new Auth(db, clock).session(req())).toBeNull();
    db.close();
  } finally {
    rmSync(d, { recursive: true, force: true });
  }
});
