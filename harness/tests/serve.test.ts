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
  cookie = `harness_session_${new URL(server.url).port}=${server.app.auth.mintSession().token}`; // named per port
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

test("the snapshot carries pr_watches: open PR watches only, with the session slug", async () => {
  const snap = await (await get("/api/snapshot")).json();
  const w = snap.pr_watches as { target: string; pr: number | null; session_slug: string | null; state: string | null }[];
  expect(w.map((r) => r.target)).toEqual(["mac-bootstrap#58"]);
  expect(w[0].pr).toBe(58);
  expect(w[0].session_slug).toBeTruthy();
  expect(w[0].state).toBe("open");
});

test("a harness change with a live unused grant has granted set; an applied one is never offered", async () => {
  type C = { id: string; status: string; granted: { until: number } | null };
  const before = (await (await get("/api/snapshot")).json()).views.changes as C[];
  const pending = before.find((c) => c.status === "pending")!;
  const applied = before.find((c) => c.status === "applied")!;
  expect(pending.granted).toBeNull();

  // A second connection, as the real MCP process does: the server's cache sees it through PRAGMA data_version.
  const writer = new Database(join(dir, "ledger.db"), { readwrite: true });
  // A grant counts only through its journal row (D70), so make it the real way.
  const { command } = await import("../src/ledger/authority.ts");
  const p = pending as C & { sha: string; digest: string };
  const g = command(writer, { channel: "page", session: "page", isRootSession: true, text: `HARNESS-OK ${p.sha.slice(0, 8)} ${p.digest.slice(0, 8)}` });
  expect(g.kind).toBe("grant");
  const until = (writer.query("SELECT expires_at FROM tokens WHERE id = ?").get((g as { tokenId: string }).tokenId) as { expires_at: number }).expires_at;
  writer.query("INSERT INTO tokens (id, kind, session_id, request_id, expires_at) VALUES (?,?,?,?,?)").run("01TESTGRANTSPENT", "harness", null, applied.id, until);
  const after = (await (await get("/api/snapshot")).json()).views.changes as C[];
  expect(after.find((c) => c.id === pending.id)!.granted).toEqual({ until });
  expect(after.find((c) => c.id === applied.id)!.granted).toBeNull();
  writer.query("DELETE FROM tokens WHERE id IN (?, '01TESTGRANTSPENT')").run((g as { tokenId: string }).tokenId);
  writer.close();
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

test("a snapshot carries `resources` with its series when a provider is set, and null when not", async () => {
  const { createApp } = await import("../src/serve/server.ts");
  const point = { t: 60_000, cpu: 10, mem: 40, swap: 0, load1: 1, psi_mem: 0 };
  const res = {
    at: 123,
    os: "linux" as const,
    source: "proc" as const,
    cpu: { total: 12, cores: [10, 14], count: 2 },
    load: { one: 1, five: 1, fifteen: 1 },
    memory: null,
    disks: [],
    io: null,
    pressure: null,
    top_cpu: [{ pid: 1, cpu: 1, rss_mb: 1, etime: "00:01", comm: "x", args: "x", session: null, slug: null }],
    top_rss: [],
    series: [point],
    tone: "ok" as const,
    reasons: [],
  };
  const withRes = createApp({ db, resources: () => res });
  const without = createApp({ db });
  try {
    const headers = (app: typeof withRes) => ({ host: "localhost", cookie: `harness_session=${app.auth.mintSession().token}` });
    const a = await (await withRes.fetch(new Request("http://localhost/api/snapshot", { headers: headers(withRes) }))).json();
    expect(a.resources.at).toBe(123);
    expect(a.resources.series).toEqual([point]);
    const b = await (await without.fetch(new Request("http://localhost/api/snapshot", { headers: headers(without) }))).json();
    expect(b.resources).toBeNull();
  } finally {
    withRes.stop();
    without.stop();
  }
});

// Seen live 2026-11-27: cookies ignore the port, so the Mac page (4316) and the VM page (4317) shared one cookie.
test("the session cookie is named per port, so two pages on localhost do not share it", async () => {
  const { openLedger } = await import("../src/ledger/db.ts");
  const { Auth } = await import("../src/serve/auth.ts");
  const d = mkdtempSync(join(tmpdir(), "harness-port-"));
  try {
    const db = openLedger(join(d, "ledger.db"));
    const auth = new Auth(db, () => 1_000_000);
    const { token } = auth.mintSession();
    const mac = new Request("https://localhost:4316/");
    expect(auth.cookieHeader(token, undefined, mac)).toStartWith(`harness_session_4316=${token};`);
    const at = (port: number, name: string) => new Request(`https://localhost:${port}/`, { headers: { cookie: `${name}=${token}` } });
    expect(auth.session(at(4316, "harness_session_4316"))).not.toBeNull();
    expect(auth.session(at(4317, "harness_session_4316"))).toBeNull(); // the other page's cookie is not this page's
    db.close();
  } finally {
    rmSync(d, { recursive: true, force: true });
  }
});

// Architecture #2 (review 2026-11-27): one attention list in the snapshot decides "needs Alex"; the badge,
// tab title, dashboard and office figure only read it. A grant counts only with its journal row (D70).
test("the snapshot's attention list holds what needs Alex, and a granted or forged-grant change behaves right", async () => {
  const { command } = await import("../src/ledger/authority.ts");
  type C = { id: string; sha: string; digest: string; status: string; superseded: boolean; granted: { until: number } | null };
  type A = { view: string; id: string; tone: string; what: string };
  const snap1 = await (await get("/api/snapshot")).json();
  const pending = (snap1.views.changes as C[]).find((c) => c.status === "pending" && !c.superseded)!;
  const att1 = snap1.attention as A[];
  expect(att1.some((a) => a.view === "changes" && a.id === pending.id && a.tone === "amber")).toBe(true);
  expect(snap1.counts.changes).toBe(att1.filter((a) => a.view === "changes").length);
  for (const a of att1) expect(typeof a.what).toBe("string");

  // A forged token (bare insert, no journal grant row) neither grants nor clears the change.
  const writer = new Database(join(dir, "ledger.db"), { readwrite: true });
  writer.query("INSERT INTO tokens (id, kind, session_id, request_id, expires_at) VALUES (?,?,?,?,?)").run("01FORGEDPAGE", "harness", null, pending.id, Date.now() + 60_000);
  const snap2 = await (await get("/api/snapshot")).json();
  expect((snap2.views.changes as C[]).find((c) => c.id === pending.id)!.granted).toBeNull();
  expect((snap2.attention as A[]).some((a) => a.id === pending.id)).toBe(true);

  // A real grant clears it from attention and shows as granted.
  const r = command(writer, { channel: "page", session: "page", isRootSession: true, text: `HARNESS-OK ${pending.sha.slice(0, 8)} ${pending.digest.slice(0, 8)}` });
  expect(r.kind).toBe("grant");
  const snap3 = await (await get("/api/snapshot")).json();
  expect((snap3.views.changes as C[]).find((c) => c.id === pending.id)!.granted).not.toBeNull();
  expect((snap3.attention as A[]).some((a) => a.id === pending.id)).toBe(false);
  expect(snap3.counts.changes).toBe((snap3.attention as A[]).filter((a) => a.view === "changes").length);
  writer.query("DELETE FROM tokens WHERE id = '01FORGEDPAGE'").run();
  writer.close();
});
