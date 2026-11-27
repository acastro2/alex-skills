// Page actions (D60, D61). The page holds no grant logic. Each action is checked for shape, then handed to the
// authority module as channel "page". If that module is not there, the action returns 503.
//
// What each action does once the authority module accepts it:
//   merge, apply  authority.command mints the grant token (`MERGE-OK <pr>`, `HARNESS-OK <sha8> <digest8>`).
//   off, on       authority.command flips the kill switch.
//   on <rule>, wrong  authority.command parses the line; the page then writes the journal row that records it.
//   rollback      authority.command accepts it, then apply.rollback restores the previous applied tree.
//   answer        NEVER goes through authority.command (O13): the text is stored as `question.answered`,
//                 so `MERGE-OK 1` typed into an answer is only text.
//   run-job       jobs.requestRun: a `job.requested` row the running jobs runner picks up.
import type { Database } from "bun:sqlite";
import { append, upsertSession } from "../ledger/journal.ts";
import { FRESH_ACTIONS } from "./auth.ts";
import { PAGE_SESSION } from "./snapshot.ts";

export const ACTIONS = ["answer", "wrong", "off", "on", "merge", "apply", "rollback", "run-job"] as const;
export type ActionName = (typeof ACTIONS)[number];

export interface ActionResult {
  status: number;
  body: Record<string, unknown>;
}

/** The real shape in src/ledger/authority.ts. */
export interface AuthorityChannel {
  channel: "page";
  session: string;
  isRootSession: boolean;
  text: string;
}
export type AuthorityCommand =
  | { kind: "none" }
  | { kind: "grant"; grant: "merge" | "harness"; tokenId: string }
  | { kind: "switch"; action: "off" | "on" | "wrong" | "on-rule" | "rollback"; arg?: string };
type AuthorityModule = { command?: (db: Database, ch: AuthorityChannel) => AuthorityCommand };

const AUTHORITY_URL = new URL("../ledger/authority.ts", import.meta.url);

export async function loadAuthority(): Promise<AuthorityModule | null> {
  if (!(await Bun.file(AUTHORITY_URL).exists())) return null;
  const mod = (await import(AUTHORITY_URL.href)) as AuthorityModule;
  return typeof mod.command === "function" ? mod : null;
}

/** A validated request: the line the authority module reads, and what to do after it accepts. */
export interface Plan {
  action: ActionName;
  /** Null for actions that never go through authority.command. */
  line: string | null;
  /** The session the grant binds to. Merge and apply bind to a session; the rest use the page's own. */
  session: string;
  args: Record<string, unknown>;
}

const bad = (message: string): ActionResult => ({ status: 400, body: { error: message } });
const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
const str = (v: unknown, max = 8000): string | null => (typeof v === "string" && v.trim() && v.length <= max ? v : null);
const int = (v: unknown): number | null => (typeof v === "number" && Number.isInteger(v) && v > 0 ? v : null);

export function buildPlan(db: Database, action: ActionName, rawArgs: unknown): Plan | ActionResult {
  const a = isObj(rawArgs) ? rawArgs : {};
  const plan = (line: string | null, args: Record<string, unknown>, session = PAGE_SESSION): Plan => ({ action, line, session, args });

  switch (action) {
    case "answer": {
      const session = str(a.session_id, 64);
      const seq = int(a.seq);
      const text = str(a.text);
      if (!session || !seq || !text) return bad("An answer needs session_id, seq and text.");
      const ask = db.query("SELECT 1 AS ok FROM journal WHERE seq = ? AND session_id = ? AND event = 'question.asked'").get(seq, session);
      if (!ask) return bad("That question is not in the journal.");
      const done = db.query("SELECT 1 AS ok FROM journal WHERE session_id = ? AND event = 'question.answered' AND seq > ?").get(session, seq);
      if (done) return { status: 409, body: { error: "That question was already answered." } };
      return plan(null, { session_id: session, seq, text });
    }
    case "wrong": {
      const seq = int(a.seq);
      if (!seq) return bad("`wrong` needs the seq of a send-back.");
      const row = db.query("SELECT rule_id, session_id FROM journal WHERE seq = ? AND event = 'stop.sendback'").get(seq) as { rule_id: string | null; session_id: string | null } | null;
      if (!row) return bad("That journal row is not a send-back.");
      return plan("harness wrong", { seq, rule_id: row.rule_id, session_id: row.session_id });
    }
    case "off":
      return plan("harness off", {});
    case "on": {
      const rule = a.rule === undefined ? null : str(a.rule, 80);
      if (a.rule !== undefined && !rule) return bad("`on` takes a rule id or nothing.");
      if (rule && !db.query("SELECT 1 AS ok FROM rules WHERE id = ?").get(rule)) return bad("Unknown rule.");
      return plan(rule ? `harness on ${rule}` : "harness on", rule ? { rule } : {});
    }
    case "merge": {
      const pr = int(a.pr);
      const session = str(a.session_id, 64);
      if (!pr || !session) return bad("`merge` needs a PR number and the session_id that will merge it.");
      if (!db.query("SELECT 1 AS ok FROM sessions WHERE id = ?").get(session)) return bad("Unknown session.");
      return plan(`MERGE-OK ${pr}`, { pr, session_id: session }, session);
    }
    case "apply": {
      const id = str(a.request_id, 64);
      const req = id ? (db.query("SELECT sha, digest, state FROM requests WHERE id = ?").get(id) as { sha: string; digest: string; state: string } | null) : null;
      if (!id || !req) return bad("Unknown harness request.");
      if (req.state !== "open") return bad("That request is not open.");
      // The passkey args digest binds the tap to the review shown, so the tap must name its full digest.
      if (a.digest !== req.digest) return bad("The digest does not match this request's review. Reload the page and read the review again.");
      return plan(`HARNESS-OK ${req.sha.slice(0, 8)} ${req.digest.slice(0, 8)}`, { request_id: id, digest: req.digest });
    }
    case "rollback": {
      const id = str(a.request_id, 64);
      const req = id ? (db.query("SELECT sha FROM requests WHERE id = ?").get(id) as { sha: string } | null) : null;
      if (!id || !req) return bad("Unknown harness request.");
      const applied = db.query("SELECT 1 AS ok FROM applies WHERE request_id = ? AND rolled_back_at IS NULL").get(id);
      if (!applied) return bad("That request has no apply to roll back.");
      return plan("harness rollback", { request_id: id, sha: req.sha });
    }
    case "run-job": {
      const name = str(a.name, 80);
      if (!name || !db.query("SELECT 1 AS ok FROM jobs WHERE name = ?").get(name)) return bad("Unknown job.");
      return plan(null, { name });
    }
  }
}

function pageSession(db: Database) {
  upsertSession(db, { id: PAGE_SESSION, tool: "page", interactive: true });
  db.query("UPDATE sessions SET ended_at = NULL WHERE id = ?").run(PAGE_SESSION);
}

export async function runAction(db: Database, action: ActionName, rawArgs: unknown): Promise<ActionResult> {
  const plan = buildPlan(db, action, rawArgs);
  if ("status" in plan) return plan;
  const now = Date.now();
  const a = plan.args;

  try {
    // Actions that never reach authority.command.
    if (plan.action === "answer") {
      const seq = append(db, {
        session_id: a.session_id as string,
        event: "question.answered",
        outcome: "ok",
        prompt_text: a.text as string,
        data: { ask_seq: a.seq, channel: "page" },
        time: now,
      });
      return { status: 200, body: { ok: true, seq } };
    }
    if (plan.action === "run-job") {
      pageSession(db);
      const { requestRun } = await import("../jobs/jobs.ts");
      try {
        requestRun(db, a.name as string);
      } catch (e) {
        return { status: 400, body: { error: (e as Error).message } };
      }
      return { status: 200, body: { ok: true, note: "Run requested. The job runner picks it up within 10 s." } };
    }

    const authority = await loadAuthority();
    if (!authority?.command) return { status: 503, body: { error: "authority not available" } };

    pageSession(db);
    const out = authority.command(db, { channel: "page", session: plan.session, isRootSession: true, text: plan.line as string });
    if (out.kind === "none") return { status: 403, body: { error: "The authority module did not accept this action." } };

    if (out.kind === "grant") return { status: 200, body: { ok: true, grant: out.grant, token_id: out.tokenId, note: "Approved for 30 minutes. It acts when the session asks for it." } };

    switch (out.action) {
      case "off":
      case "on":
        return { status: 200, body: { ok: true, harness: out.action } };
      case "wrong": {
        const seq = append(db, {
          session_id: (a.session_id as string | null) ?? PAGE_SESSION,
          event: "harness.wrong",
          rule_id: (a.rule_id as string | null) ?? null,
          outcome: "wrong",
          data: { seq: a.seq, channel: "page" },
          time: now,
        });
        return { status: 200, body: { ok: true, seq } };
      }
      case "on-rule": {
        const rule = out.arg as string;
        db.query("UPDATE rules SET mode = CASE WHEN default_mode = 'off' THEN 'enforce' ELSE default_mode END, updated_at = ? WHERE id = ?").run(now, rule);
        const seq = append(db, { session_id: PAGE_SESSION, event: "harness.rule", rule_id: rule, outcome: "on", data: { channel: "page" }, time: now });
        return { status: 200, body: { ok: true, seq } };
      }
      case "rollback": {
        // Alex tapped a fresh passkey for this: restore the previous applied tree now (D71).
        const { rollback } = await import("../proof/apply.ts");
        const r = rollback(db, { session: PAGE_SESSION, now });
        return r.ok
          ? { status: 200, body: { ok: true, sha: r.sha, note: `Rolled back to ${r.sha.slice(0, 8)}.` } }
          : { status: 409, body: { error: `Rollback failed: ${r.reason}` } };
      }
    }
    return { status: 500, body: { error: "Unhandled authority result." } };
  } catch (e) {
    return { status: 500, body: { error: `The action failed: ${(e as Error).message}` } };
  }
}

export { FRESH_ACTIONS };
