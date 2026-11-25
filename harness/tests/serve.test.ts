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
