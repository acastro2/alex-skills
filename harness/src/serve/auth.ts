// Page auth (D61, O9): a WebAuthn passkey on localhost.
// Registration opens only while page_auth is empty. A login gives a 30-minute cookie session for read views,
// answers and `wrong`. merge, apply, off, on and rollback each need a fresh assertion, bound to that action
// and its arguments, used once.
import type { Database } from "bun:sqlite";
import { createHash, randomBytes } from "node:crypto";
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import {
  generateAuthenticationOptions,
  generateRegistrationOptions,
  verifyAuthenticationResponse,
  verifyRegistrationResponse,
} from "@simplewebauthn/server";

export const SESSION_MS = 30 * 60_000;
const CHALLENGE_MS = 2 * 60_000;
export const RP_ID = "localhost";
export const COOKIE = "harness_session";

/** Actions that need a fresh passkey assertion. Anything else needs only the session. */
export const FRESH_ACTIONS = new Set(["merge", "apply", "off", "on", "rollback"]);

type Challenge =
  | { kind: "register"; challenge: string; exp: number }
  | { kind: "login"; challenge: string; exp: number }
  | { kind: "action"; challenge: string; exp: number; action: string; digest: string };

/** The passkey file shared by every host, so ONE synced passkey (1Password) works on each. */
export function sharedPasskeyPath(): string {
  return process.env.HARNESS_PASSKEY_FILE || join(homedir(), ".config", "harness", "passkey.json");
}

export interface SharedPasskey {
  credential_id: string;
  public_key: string; // base64url
  created_at: number;
}

/** Write the shared passkey file, mode 0600. */
export function saveShared(db: Database, file = sharedPasskeyPath()): void {
  const row = db.query("SELECT credential_id, public_key FROM page_auth LIMIT 1").get() as { credential_id: string; public_key: Uint8Array } | null;
  if (!row) return;
  const body: SharedPasskey = { credential_id: row.credential_id, public_key: Buffer.from(row.public_key).toString("base64url"), created_at: Date.now() };
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, `${JSON.stringify(body, null, 2)}\n`, { mode: 0o600 });
  chmodSync(file, 0o600);
}

/** Insert the shared passkey into an empty page_auth. Returns true when it did. A bad file is ignored. */
export function loadShared(db: Database, file = sharedPasskeyPath()): boolean {
  if (!existsSync(file)) return false;
  if ((db.query("SELECT COUNT(*) AS n FROM page_auth").get() as { n: number }).n > 0) return false;
  try {
    const j = JSON.parse(readFileSync(file, "utf8")) as Partial<SharedPasskey>;
    if (typeof j.credential_id !== "string" || typeof j.public_key !== "string" || !j.credential_id || !j.public_key) return false;
    db.query("INSERT INTO page_auth (credential_id, public_key, sign_count, session_until) VALUES (?, ?, 0, NULL)").run(j.credential_id, Buffer.from(j.public_key, "base64url"));
    return true;
  } catch {
    return false;
  }
}

export function argsDigest(args: unknown): string {
  const canon = (v: unknown): unknown =>
    Array.isArray(v) ? v.map(canon) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v as object).sort(([a], [b]) => (a < b ? -1 : 1)).map(([k, x]) => [k, canon(x)])) : v;
  return createHash("sha256").update(JSON.stringify(canon(args ?? {}))).digest("hex");
}

const token = () => randomBytes(32).toString("base64url");

export class Auth {
  private sessions = new Map<string, number>();
  private challenges = new Map<string, Challenge>();

  constructor(
    private db: Database,
    private clock: () => number = Date.now,
    private sharedFile: string | null = null,
  ) {
    if (sharedFile) loadShared(db, sharedFile);
  }

  hasCredential(): boolean {
    return (this.db.query("SELECT COUNT(*) AS n FROM page_auth").get() as { n: number }).n > 0;
  }

  /** Start a session. Called after a verified login, and by tests that build the app in-process. */
  mintSession(): { token: string; until: number } {
    const t = token();
    const until = this.clock() + SESSION_MS;
    this.sessions.set(t, until);
    this.db.query("UPDATE page_auth SET session_until = ?").run(until);
    return { token: t, until };
  }

  session(req: Request): { token: string; until: number } | null {
    const raw = req.headers.get("cookie") ?? "";
    const m = raw.split(/;\s*/).find((c) => c.startsWith(`${COOKIE}=`));
    if (!m) return null;
    const t = m.slice(COOKIE.length + 1);
    const until = this.sessions.get(t);
    if (!until) return null;
    if (until <= this.clock()) {
      this.sessions.delete(t);
      return null;
    }
    return { token: t, until };
  }

  endSession(req: Request): void {
    const s = this.session(req);
    if (s) this.sessions.delete(s.token);
  }

  cookieHeader(t: string, maxAgeMs = SESSION_MS): string {
    return `${COOKIE}=${t}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${Math.floor(maxAgeMs / 1000)}`;
  }

  private put(c: Challenge): string {
    const id = token();
    this.challenges.set(id, c);
    for (const [k, v] of this.challenges) if (v.exp < this.clock()) this.challenges.delete(k);
    return id;
  }

  private take(id: string | undefined, kind: Challenge["kind"]): Challenge | null {
    if (!id) return null;
    const c = this.challenges.get(id);
    this.challenges.delete(id);
    return c && c.kind === kind && c.exp >= this.clock() ? c : null;
  }

  async registrationOptions() {
    if (this.hasCredential()) throw new AuthError(409, "A passkey is already registered on this host.");
    const options = await generateRegistrationOptions({
      rpName: "harness",
      rpID: RP_ID,
      userName: "alex",
      userID: new TextEncoder().encode("alex"),
      attestationType: "none",
      authenticatorSelection: { residentKey: "preferred", userVerification: "required" },
    });
    return { challengeId: this.put({ kind: "register", challenge: options.challenge, exp: this.clock() + CHALLENGE_MS }), options };
  }

  async verifyRegistration(origin: string, challengeId: string | undefined, response: unknown) {
    if (this.hasCredential()) throw new AuthError(409, "A passkey is already registered on this host.");
    const c = this.take(challengeId, "register");
    if (!c) throw new AuthError(400, "The challenge expired. Try again.");
    const v = await verifyRegistrationResponse({
      response: response as never,
      expectedChallenge: c.challenge,
      expectedOrigin: origin,
      expectedRPID: RP_ID,
      requireUserVerification: true,
    }).catch(() => null);
    if (!v?.verified) throw new AuthError(400, "The passkey could not be verified.");
    const cred = v.registrationInfo.credential;
    this.db.query("INSERT INTO page_auth (credential_id, public_key, sign_count, session_until) VALUES (?, ?, ?, NULL)").run(cred.id, cred.publicKey, 0);
    if (this.sharedFile) saveShared(this.db, this.sharedFile);
    return this.mintSession();
  }

  async loginOptions() {
    const cred = this.db.query("SELECT credential_id FROM page_auth LIMIT 1").get() as { credential_id: string } | null;
    if (!cred) throw new AuthError(409, "No passkey is registered yet.");
    const options = await generateAuthenticationOptions({ rpID: RP_ID, userVerification: "required", allowCredentials: [{ id: cred.credential_id }] });
    return { challengeId: this.put({ kind: "login", challenge: options.challenge, exp: this.clock() + CHALLENGE_MS }), options };
  }

  async verifyLogin(origin: string, challengeId: string | undefined, response: unknown) {
    const c = this.take(challengeId, "login");
    if (!c) throw new AuthError(400, "The challenge expired. Try again.");
    await this.verifyAssertion(origin, c.challenge, response);
    return this.mintSession();
  }

  /** A challenge for one action with these exact arguments. */
  async actionChallenge(action: string, args: unknown) {
    const cred = this.db.query("SELECT credential_id FROM page_auth LIMIT 1").get() as { credential_id: string } | null;
    if (!cred) throw new AuthError(409, "No passkey is registered yet.");
    const options = await generateAuthenticationOptions({ rpID: RP_ID, userVerification: "required", allowCredentials: [{ id: cred.credential_id }] });
    const challengeId = this.put({ kind: "action", challenge: options.challenge, exp: this.clock() + CHALLENGE_MS, action, digest: argsDigest(args) });
    return { challengeId, options };
  }

  /** Verify the fresh assertion for this action. Throws AuthError(401) when it is missing, wrong, expired or reused. */
  async verifyAction(origin: string, action: string, args: unknown, challengeId: string | undefined, assertion: unknown): Promise<void> {
    const c = this.take(challengeId, "action") as Extract<Challenge, { kind: "action" }> | null;
    if (!c || !assertion) throw new AuthError(401, "This action needs a fresh passkey tap.");
    if (c.action !== action || c.digest !== argsDigest(args)) throw new AuthError(401, "The passkey tap was for a different action.");
    await this.verifyAssertion(origin, c.challenge, assertion);
  }

  private async verifyAssertion(origin: string, challenge: string, response: unknown): Promise<void> {
    const id = (response as { id?: string } | null)?.id;
    const cred = id
      ? (this.db.query("SELECT credential_id, public_key FROM page_auth WHERE credential_id = ?").get(id) as { credential_id: string; public_key: Uint8Array } | null)
      : null;
    if (!cred) throw new AuthError(401, "Unknown passkey.");
    const v = await verifyAuthenticationResponse({
      response: response as never,
      expectedChallenge: challenge,
      expectedOrigin: origin,
      expectedRPID: RP_ID,
      requireUserVerification: true,
      // A synced passkey (1Password) reports counter 0 on every host, and a counting one can differ per host.
      // The shared file lets any host accept the credential, so the counter is never a check: pass 0.
      // Replay is blocked by the one-time challenge.
      credential: { id: cred.credential_id, publicKey: new Uint8Array(cred.public_key), counter: 0 },
    }).catch(() => null);
    if (!v?.verified) throw new AuthError(401, "The passkey tap did not verify.");
  }
}

export class AuthError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
