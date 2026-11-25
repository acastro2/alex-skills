// HTTPS for the page and the shared passkey file (so one 1Password passkey works on every host).
import { afterAll, beforeAll, expect, test } from "bun:test";
import { Database } from "bun:sqlite";
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadShared, saveShared } from "../src/serve/auth.ts";
import { seedLedger } from "../src/serve/seed.ts";
import { createApp, startServer, type Started } from "../src/serve/server.ts";
import { tlsFiles } from "../src/serve/tls.ts";

let dir: string;
let db: Database;
let server: Started;

beforeAll(async () => {
  dir = mkdtempSync(join(tmpdir(), "harness-tls-"));
  db = new Database(seedLedger(dir), { readwrite: true });
  const gen = Bun.spawnSync([
    "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
    "-keyout", join(dir, "localhost-key.pem"), "-out", join(dir, "localhost.pem"),
    "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
  ]);
  expect(gen.exitCode).toBe(0);
  server = await startServer({ db, port: 0, tls: { cert: join(dir, "localhost.pem"), key: join(dir, "localhost-key.pem") } });
});

afterAll(() => {
  server.stop();
  db.close();
  rmSync(dir, { recursive: true, force: true });
});

const insecure = { tls: { rejectUnauthorized: false } } as const;

test("tlsFiles reads HARNESS_TLS_DIR and is null when a file is missing", () => {
  const saved = process.env.HARNESS_TLS_DIR;
  try {
    process.env.HARNESS_TLS_DIR = dir;
    expect(tlsFiles()).toEqual({ cert: join(dir, "localhost.pem"), key: join(dir, "localhost-key.pem") });
    process.env.HARNESS_TLS_DIR = join(dir, "missing");
    expect(tlsFiles()).toBeNull();
  } finally {
    if (saved === undefined) delete process.env.HARNESS_TLS_DIR;
    else process.env.HARNESS_TLS_DIR = saved;
  }
});

test("with a cert, the page serves https on localhost and redirects an IP host to https", async () => {
  expect(server.url).toStartWith("https://localhost:");
  const ok = await fetch(`${server.url}/`, insecure);
  expect(ok.status).toBe(200);
  const redirect = await fetch(`https://127.0.0.1:${server.port}/`, { ...insecure, redirect: "manual" });
  expect(redirect.status).toBe(302);
  expect(redirect.headers.get("location")).toStartWith("https://localhost:");
});

test("on an https server, an http origin is refused and an https origin is accepted", async () => {
  const post = (origin: string) =>
    fetch(`${server.url}/api/auth/register/options`, { ...insecure, method: "POST", headers: { origin, "content-type": "application/json" }, body: "{}" });
  expect((await post(`http://localhost:${server.port}`)).status).toBe(403);
  expect((await post(`https://localhost:${server.port}`)).status).toBe(200);
});

test("without a cert, the origin is http", async () => {
  const app = createApp({ db: new Database(":memory:") });
  const res = await app.fetch(new Request("http://localhost/api/auth/logout", { method: "POST", headers: { host: "localhost", origin: "https://localhost", "content-type": "application/json" }, body: "{}" }));
  expect(res.status).toBe(403);
});

test("the shared passkey file round-trips: save writes mode 0600, load fills an empty page_auth", () => {
  const file = join(dir, "passkey.json");
  const row = db.query("INSERT INTO page_auth (credential_id, public_key, sign_count, session_until) VALUES ('cred-1', ?, 0, NULL)");
  row.run(new Uint8Array([1, 2, 3, 250]));
  saveShared(db, file);
  expect(statSync(file).mode & 0o777).toBe(0o600);
  const j = JSON.parse(readFileSync(file, "utf8"));
  expect(j.credential_id).toBe("cred-1");
  expect(j.public_key).toBe(Buffer.from([1, 2, 3, 250]).toString("base64url"));
  expect(typeof j.created_at).toBe("number");

  const other = new Database(seedLedger(mkdtempSync(join(dir, "o-"))), { readwrite: true });
  expect(other.query("SELECT COUNT(*) AS n FROM page_auth").get()).toEqual({ n: 0 });
  const app = createApp({ db: other, sharedPasskey: file });
  expect(app.auth.hasCredential()).toBe(true);
  const got = other.query("SELECT credential_id, public_key, sign_count FROM page_auth").get() as { credential_id: string; public_key: Uint8Array; sign_count: number };
  expect(got.credential_id).toBe("cred-1");
  expect(Array.from(got.public_key)).toEqual([1, 2, 3, 250]);
  expect(got.sign_count).toBe(0);
  app.stop();
  other.close();
});

test("loadShared does nothing when page_auth has a row, the file is missing, or the file is bad", () => {
  const empty = new Database(seedLedger(mkdtempSync(join(dir, "e-"))), { readwrite: true });
  expect(loadShared(empty, join(dir, "nope.json"))).toBe(false);
  const bad = join(dir, "bad.json");
  writeFileSync(bad, "{not json");
  expect(loadShared(empty, bad)).toBe(false);
  expect(existsSync(bad)).toBe(true);
  expect(loadShared(db, join(dir, "passkey.json"))).toBe(false); // db already has a credential
  empty.close();
});
