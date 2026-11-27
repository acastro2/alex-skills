// `harness serve`: the page, a JSON API, server-sent events and actions. Binds 127.0.0.1 only.
import type { Database } from "bun:sqlite";
import { statSync } from "node:fs";
import { join } from "node:path";
import { ACTIONS, runAction, type ActionName } from "./actions.ts";
import { Auth, AuthError, FRESH_ACTIONS, SESSION_MS, sharedPasskeyPath } from "./auth.ts";
import { openDatabase } from "./db.ts";
import type { Resources } from "./resources.ts";
import { buildSnapshot, journalPage, maxSeq, sessionSlug, type Snapshot } from "./snapshot.ts";
import type { TlsFiles } from "./tls.ts";

const UI_DIR = join(import.meta.dir, "..", "..", "ui");
const APP_DIR = join(UI_DIR, "app");
const OFFICE_DIST = join(UI_DIR, "office", "dist", "office.js");
const OFFICE_CSS = join(UI_DIR, "office", "dist", "office.css");
const OFFICE_MODEL = join(import.meta.dir, "..", "ui", "office-model.ts");

const POLL_MS = 500;
const HEARTBEAT_MS = 5_000;
const SNAPSHOT_MAX_AGE_MS = 30_000;

const HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

export function hostnameOf(hostHeader: string | null): string | null {
  if (!hostHeader) return null;
  const m = hostHeader.match(/^(\[[^\]]+\]|[^:]+)(?::\d+)?$/);
  return m ? m[1].toLowerCase() : null;
}

const SECURITY_HEADERS: Record<string, string> = {
  "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Cross-Origin-Opener-Policy": "same-origin",
};

function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...SECURITY_HEADERS, ...headers },
  });
}

function asset(body: BodyInit, type: string): Response {
  return new Response(body, { headers: { "Content-Type": type, "Cache-Control": "no-cache", ...SECURITY_HEADERS } });
}

export interface AppOptions {
  db: Database;
  port?: number;
  clock?: () => number;
  /** The scheme the page is served on. Default http. */
  scheme?: "http" | "https";
  /** Read and write the shared passkey file (see auth.ts). Off by default so tests never touch the real file. */
  sharedPasskey?: string | boolean;
  /** The newest machine sample. Default: none, so `snapshot.resources` is null. */
  resources?: () => Resources | null;
}

export interface App {
  fetch(req: Request, server?: { timeout(req: Request, seconds: number): void }): Promise<Response>;
  auth: Auth;
  stop(): void;
}

/** The request handler, with no socket. Tests use it directly; `startServer` puts it behind Bun.serve. */
export function createApp(opts: AppOptions): App {
  const { db } = opts;
  const clock = opts.clock ?? Date.now;
  const scheme = opts.scheme ?? "http";
  const auth = new Auth(db, clock, opts.sharedPasskey ? (typeof opts.sharedPasskey === "string" ? opts.sharedPasskey : sharedPasskeyPath()) : null);
  const encoder = new TextEncoder();

  // One poller for every open stream. It runs only while a stream is open.
  const clients = new Set<(frame: string) => void>();
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  let cached: { sig: string; at: number; frame: string; snapshot: Snapshot } | null = null;
  let lastSig = "";

  // The signature includes the sample time, so a new machine sample also sends a frame.
  const signature = () =>
    `${maxSeq(db)}:${(db.query("PRAGMA data_version").get() as { data_version: number }).data_version}:${opts.resources?.()?.at ?? 0}`;

  function withResources(snapshot: Snapshot): Snapshot {
    const r = opts.resources?.() ?? null;
    if (!r) return snapshot;
    const repos = new Map<string, string | null>();
    for (const row of db.query("SELECT id, repo FROM sessions").all() as { id: string; repo: string | null }[]) repos.set(row.id, row.repo);
    const fill = (p: Resources["top_cpu"][number]) => ({ ...p, slug: p.session ? sessionSlug(p.session, repos.get(p.session) ?? null) : null });
    return { ...snapshot, resources: { ...r, top_cpu: r.top_cpu.map(fill), top_rss: r.top_rss.map(fill) } };
  }

  function snapshotFrame(force = false): { frame: string; snapshot: Snapshot } {
    const sig = signature();
    if (!force && cached && cached.sig === sig && clock() - cached.at < SNAPSHOT_MAX_AGE_MS) return cached;
    const snapshot = withResources(buildSnapshot(db, clock()));
    cached = { sig, at: clock(), snapshot, frame: `id: ${snapshot.seq}\nevent: snapshot\ndata: ${JSON.stringify(snapshot)}\n\n` };
    return cached;
  }

  function startPolling() {
    if (pollTimer) return;
    lastSig = signature();
    pollTimer = setInterval(() => {
      try {
        const sig = signature();
        if (sig === lastSig) return;
        lastSig = sig;
        const { frame } = snapshotFrame(true);
        for (const send of clients) send(frame);
      } catch (e) {
        const frame = `event: ledger-error\ndata: ${JSON.stringify({ error: (e as Error).message })}\n\n`;
        for (const send of clients) send(frame);
      }
    }, POLL_MS);
    heartbeatTimer = setInterval(() => {
      for (const send of clients) send(`event: ping\ndata: ${clock()}\n\n`);
    }, HEARTBEAT_MS);
  }

  function stopPollingIfIdle() {
    if (clients.size > 0) return;
    if (pollTimer) clearInterval(pollTimer);
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    pollTimer = heartbeatTimer = null;
  }

  function events(req: Request, server?: { timeout(req: Request, seconds: number): void }): Response {
    server?.timeout(req, 0);
    let send: ((frame: string) => void) | null = null;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        send = (frame) => {
          try {
            controller.enqueue(encoder.encode(frame));
          } catch {
            if (send) clients.delete(send);
          }
        };
        clients.add(send);
        startPolling();
        try {
          send(`retry: 2000\n${snapshotFrame().frame}`);
        } catch (e) {
          send(`event: ledger-error\ndata: ${JSON.stringify({ error: (e as Error).message })}\n\n`);
        }
        req.signal.addEventListener("abort", () => {
          if (send) clients.delete(send);
          stopPollingIfIdle();
          try {
            controller.close();
          } catch {
            /* already closed */
          }
        });
      },
      cancel() {
        if (send) clients.delete(send);
        stopPollingIfIdle();
      },
    });
    return new Response(stream, {
      headers: { "Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-store", Connection: "keep-alive", "X-Accel-Buffering": "no", ...SECURITY_HEADERS },
    });
  }

  // The client bundle is built in-process with Bun.build and rebuilt when a source file changes.
  let bundle: { text: string; stamp: number } | null = null;
  async function clientBundle(): Promise<Response> {
    const stamp = sourceStamp(APP_DIR);
    if (!bundle || bundle.stamp !== stamp) {
      const out = await Bun.build({ entrypoints: [join(APP_DIR, "main.ts")], target: "browser", minify: false });
      if (!out.success) return new Response(`Client build failed:\n${out.logs.join("\n")}`, { status: 500 });
      bundle = { text: await out.outputs[0].text(), stamp };
    }
    return asset(bundle.text, "text/javascript; charset=utf-8");
  }

  let officeModel: { text: string; mtime: number } | null = null;
  async function officeModelBundle(): Promise<Response> {
    const f = Bun.file(OFFICE_MODEL);
    if (!(await f.exists())) return new Response("The office model is not built yet.", { status: 404 });
    if (!officeModel || officeModel.mtime !== f.lastModified) {
      const out = await Bun.build({ entrypoints: [OFFICE_MODEL], target: "browser" });
      if (!out.success) return new Response(`Office model build failed:\n${out.logs.join("\n")}`, { status: 500 });
      officeModel = { text: await out.outputs[0].text(), mtime: f.lastModified };
    }
    return asset(officeModel.text, "text/javascript; charset=utf-8");
  }

  async function file(path: string, type: string): Promise<Response> {
    const f = Bun.file(path);
    return (await f.exists()) ? asset(f, type) : new Response("Not found", { status: 404 });
  }

  const originOf = (req: Request): string | null => {
    const origin = req.headers.get("origin");
    const host = req.headers.get("host");
    return origin && host && origin === `${scheme}://${host}` ? origin : null;
  };

  async function readJson(req: Request): Promise<Record<string, unknown>> {
    if (!(req.headers.get("content-type") ?? "").startsWith("application/json")) throw new AuthError(415, "Send JSON.");
    try {
      const body = await req.json();
      return body && typeof body === "object" ? (body as Record<string, unknown>) : {};
    } catch {
      throw new AuthError(400, "The body is not valid JSON.");
    }
  }

  async function handle(req: Request, server?: { timeout(req: Request, seconds: number): void }): Promise<Response> {
    const url = new URL(req.url);
    const host = hostnameOf(req.headers.get("host"));
    if (!host || !HOSTS.has(host)) return new Response("Bad host", { status: 421 });

    const path = url.pathname;
    if (req.method === "GET") {
      if (path === "/") {
        // Passkeys need the RP ID `localhost`, which an IP address cannot be.
        if (host !== "localhost") return Response.redirect(`${scheme}://localhost:${url.port || (scheme === "https" ? "443" : "80")}/`, 302);
        return file(join(APP_DIR, "index.html"), "text/html; charset=utf-8");
      }
      if (path === "/app.js") return clientBundle();
      if (path === "/app.css") return file(join(APP_DIR, "app.css"), "text/css; charset=utf-8");
      if (path === "/theme.js") return file(join(APP_DIR, "theme.js"), "text/javascript; charset=utf-8");
      if (path === "/favicon.svg") return file(join(APP_DIR, "favicon.svg"), "image/svg+xml");
      if (path === "/office/office.js") return file(OFFICE_DIST, "text/javascript; charset=utf-8");
      if (path === "/office/office.css") return file(OFFICE_CSS, "text/css; charset=utf-8");
      if (path === "/office/model.js") return officeModelBundle();
    }

    if (!path.startsWith("/api/")) return new Response("Not found", { status: 404 });

    try {
      // Auth endpoints.
      if (path === "/api/session" && req.method === "GET") {
        const s = auth.session(req);
        return json({ registered: auth.hasCredential(), authenticated: Boolean(s), until: s?.until ?? null, now: clock(), session_ms: SESSION_MS });
      }
      if (req.method === "POST" && path.startsWith("/api/auth/")) {
        const origin = originOf(req);
        if (!origin) return json({ error: "Bad origin." }, 403);
        const body = await readJson(req);
        const done = (r: { token: string; until: number }) =>
          json({ ok: true, until: r.until }, 200, { "Set-Cookie": auth.cookieHeader(r.token, undefined, req) });
        switch (path) {
          case "/api/auth/register/options":
            return json(await auth.registrationOptions());
          case "/api/auth/register/verify":
            return done(await auth.verifyRegistration(origin, body.challengeId as string, body.response));
          case "/api/auth/login/options":
            return json(await auth.loginOptions());
          case "/api/auth/login/verify":
            return done(await auth.verifyLogin(origin, body.challengeId as string, body.response));
          case "/api/auth/logout":
            auth.endSession(req);
            return json({ ok: true }, 200, { "Set-Cookie": auth.cookieHeader("", 0, req) });
          case "/api/auth/challenge": {
            if (!auth.session(req)) return json({ error: "Sign in first." }, 401);
            const action = String(body.action ?? "");
            if (!FRESH_ACTIONS.has(action)) return json({ error: "That action needs no fresh tap." }, 400);
            return json(await auth.actionChallenge(action, body.args));
          }
        }
        return json({ error: "Not found" }, 404);
      }

      // Everything else needs the session.
      if (!auth.session(req)) return json({ error: "Sign in with your passkey.", code: "no-session" }, 401);

      if (path === "/api/snapshot" && req.method === "GET") return json(snapshotFrameSnapshot());
      if (path === "/api/events" && req.method === "GET") return events(req, server);
      if (path === "/api/journal" && req.method === "GET") {
        const q = url.searchParams;
        const num = (k: string) => (q.get(k) !== null && q.get(k) !== "" && Number.isFinite(Number(q.get(k))) ? Number(q.get(k)) : undefined);
        return json(
          journalPage(db, {
            session: q.get("session") || undefined,
            rule: q.get("rule") || undefined,
            event: q.get("event") || undefined,
            text: q.get("q") || undefined,
            since: num("since"),
            before: num("before"),
            after: num("after"),
            limit: num("limit"),
          }),
        );
      }

      const m = path.match(/^\/api\/action\/([a-z-]+)$/);
      if (m && req.method === "POST") {
        const origin = originOf(req);
        if (!origin) return json({ error: "Bad origin." }, 403);
        const action = m[1] as ActionName;
        if (!ACTIONS.includes(action)) return json({ error: "Unknown action." }, 404);
        const body = await readJson(req);
        if (FRESH_ACTIONS.has(action)) {
          await auth.verifyAction(origin, action, body.args, body.challengeId as string | undefined, body.assertion);
        }
        const result = await runAction(db, action, body.args);
        return json(result.body, result.status);
      }
    } catch (e) {
      if (e instanceof AuthError) return json({ error: e.message }, e.status);
      return json({ error: `The ledger cannot be read: ${(e as Error).message}` }, 500);
    }
    return json({ error: "Not found" }, 404);
  }

  function snapshotFrameSnapshot(): Snapshot {
    return snapshotFrame().snapshot;
  }

  return {
    fetch: handle,
    auth,
    stop() {
      for (const t of [pollTimer, heartbeatTimer]) if (t) clearInterval(t);
      pollTimer = heartbeatTimer = null;
      clients.clear();
    },
  };
}

function sourceStamp(dir: string): number {
  let newest = 0;
  for (const rel of new Bun.Glob("**/*.ts").scanSync({ cwd: dir })) newest = Math.max(newest, statSync(join(dir, rel)).mtimeMs);
  return newest;
}

export interface Started {
  url: string;
  port: number;
  stop(): void;
  app: App;
}

/** `tls` is opt-in: main.ts passes `tlsFiles()`, so tests on a host that has a cert stay on http. */
export async function startServer(
  opts: { db?: Database; port?: number; tls?: TlsFiles | null; sharedPasskey?: string | boolean; resources?: () => Resources | null } = {},
): Promise<Started> {
  const db = opts.db ?? (await openDatabase()).db;
  const wanted = opts.port ?? Number(process.env.HARNESS_PORT ?? 4317);
  const tls = opts.tls ?? null;
  const scheme = tls ? "https" : "http";
  const app = createApp({ db, scheme, sharedPasskey: opts.sharedPasskey, resources: opts.resources });
  const server = Bun.serve({
    hostname: "127.0.0.1",
    port: wanted,
    idleTimeout: 30,
    ...(tls ? { tls: { cert: Bun.file(tls.cert), key: Bun.file(tls.key) } } : {}),
    fetch: (req, srv) => app.fetch(req, srv),
  });
  return {
    url: `${scheme}://localhost:${server.port}`,
    port: server.port as number,
    app,
    stop() {
      app.stop();
      server.stop(true);
    },
  };
}
