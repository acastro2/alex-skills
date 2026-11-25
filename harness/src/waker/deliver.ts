import type { Database } from "bun:sqlite"
import { appendFileSync, mkdirSync, readFileSync, rmSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join } from "node:path"
import { append } from "../ledger/journal.ts"
import type { HostTool } from "../types.ts"

export interface WakeMessage {
  session: string
  tool: HostTool
  text: string
  kind?: string // pr.merged, stall, conflict, ...: goes into the journal row
}

export interface DeliverResult {
  ok: boolean
  via: string
}

export type Deliver = (msg: WakeMessage) => Promise<DeliverResult>

export interface Runner {
  (cmd: string[]): Promise<{ code: number; stdout: string; stderr: string }>
}

const stateDir = () => process.env.HARNESS_STATE_DIR ?? join(homedir(), ".local", "state", "harness")
const inboxFile = (session: string) => join(stateDir(), "inbox", `${session.replace(/[^A-Za-z0-9._-]/g, "_")}.txt`)

export const run: Runner = async (cmd) => {
  const p = Bun.spawn(cmd, { stdout: "pipe", stderr: "pipe" })
  const [stdout, stderr] = await Promise.all([new Response(p.stdout).text(), new Response(p.stderr).text()])
  return { code: await p.exited, stdout, stderr }
}

// The request deliver() sends to OpenCode. Endpoint from /openapi.json (opencode 2.4.1):
// POST /api/session/{sessionID}/synthetic, operation session.synthetic: "Durably admit synthetic
// session input and schedule execution unless resume is false". Body: { text, delivery?: steer|queue }.
export function opencodeRequest(session: string, text: string): string[] {
  return [
    "opencode",
    "api",
    "post",
    `/api/session/${encodeURIComponent(session)}/synthetic`,
    "--data",
    JSON.stringify({ text, delivery: "steer", metadata: { source: "harness-waker" } }),
  ]
}

// Claude Code has no API that wakes an idle interactive session. The adapter shows the inbox on the next
// prompt or session.start through takeInbox. No Rex notify command exists (checked `rex api list`), so no Rex step.
export function takeInbox(session: string): string | null {
  const f = inboxFile(session)
  let text: string
  try {
    text = readFileSync(f, "utf8")
  } catch {
    return null
  }
  rmSync(f, { force: true })
  return text.trim() ? text.trimEnd() : null
}

export async function deliver(db: Database, msg: WakeMessage, runner: Runner = run): Promise<DeliverResult> {
  let result: DeliverResult
  try {
    if (msg.tool === "opencode") {
      const r = await runner(opencodeRequest(msg.session, msg.text))
      result = { ok: r.code === 0, via: r.code === 0 ? "opencode:synthetic" : `opencode:synthetic failed: ${r.stderr.trim().slice(0, 200)}` }
    } else {
      const f = inboxFile(msg.session)
      mkdirSync(dirname(f), { recursive: true })
      appendFileSync(f, msg.text.endsWith("\n") ? msg.text : msg.text + "\n")
      result = { ok: true, via: "claude:inbox" }
    }
  } catch (e) {
    result = { ok: false, via: `error: ${(e as Error).message}` }
  }
  const known = db.query("select 1 from sessions where id = ?").get(msg.session)
  append(db, {
    session_id: known ? msg.session : null,
    event: result.ok ? "wake.delivered" : "wake.failed",
    data: { kind: msg.kind ?? "wake", text: msg.text, via: result.via },
  })
  return result
}
