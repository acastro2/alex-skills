// Fetch helpers, the passkey ceremonies and the one action call.
import { startAuthentication, startRegistration } from "@simplewebauthn/browser";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
  }
}

export const FRESH_ACTIONS = new Set(["merge", "apply", "off", "on", "rollback"]);

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { credentials: "same-origin", ...init });
  } catch {
    throw new ApiError(0, "The harness server did not answer.");
  }
  const text = await res.text();
  let body: Record<string, unknown> = {};
  try {
    body = text ? (JSON.parse(text) as Record<string, unknown>) : {};
  } catch {
    /* not JSON */
  }
  if (!res.ok) throw new ApiError(res.status, String(body.error ?? `Request failed (${res.status}).`), body.code as string | undefined);
  return body as T;
}

export const getJSON = <T>(path: string) => call<T>(path);
export const postJSON = <T>(path: string, body: unknown) =>
  call<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export interface SessionInfo {
  registered: boolean;
  authenticated: boolean;
  until: number | null;
  now: number;
  session_ms: number;
}

export const sessionInfo = () => getJSON<SessionInfo>("/api/session");

export const passkeysSupported = () => typeof window.PublicKeyCredential === "function";

export async function registerPasskey(): Promise<void> {
  const { challengeId, options } = await postJSON<{ challengeId: string; options: never }>("/api/auth/register/options", {});
  const response = await startRegistration({ optionsJSON: options });
  await postJSON("/api/auth/register/verify", { challengeId, response });
}

export async function signIn(): Promise<void> {
  const { challengeId, options } = await postJSON<{ challengeId: string; options: never }>("/api/auth/login/options", {});
  const response = await startAuthentication({ optionsJSON: options });
  await postJSON("/api/auth/login/verify", { challengeId, response });
}

export const signOut = () => postJSON("/api/auth/logout", {});

export interface ActionOk {
  ok: true;
  note?: string;
  [k: string]: unknown;
}

/** Run an action. merge, apply, off, on and rollback first get a fresh passkey assertion bound to these arguments. */
export async function act(action: string, args: Record<string, unknown>): Promise<ActionOk> {
  if (!FRESH_ACTIONS.has(action)) return postJSON<ActionOk>(`/api/action/${action}`, { args });
  const { challengeId, options } = await postJSON<{ challengeId: string; options: never }>("/api/auth/challenge", { action, args });
  let assertion;
  try {
    assertion = await startAuthentication({ optionsJSON: options });
  } catch (e) {
    throw new ApiError(0, (e as Error).name === "NotAllowedError" ? "The passkey tap was cancelled." : `The passkey tap failed: ${(e as Error).message}`);
  }
  return postJSON<ActionOk>(`/api/action/${action}`, { args, challengeId, assertion });
}
