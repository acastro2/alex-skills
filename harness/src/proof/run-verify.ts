// Background verify for one worker: `bun src/proof/run-verify.ts <workerId> [cwd]`.
// The core starts it detached when a general subagent returns (Phase 3). It re-runs the worker's
// acceptance commands, stores the bundle, and tells the parent session the verdict.
import type { Database } from "bun:sqlite"
import { openLedger } from "../ledger/db.ts"
import { append } from "../ledger/journal.ts"
import { seed } from "../ledger/registry.ts"
import { TEST_GLOBS } from "../policies/worker.ts"
import { deliver } from "../waker/deliver.ts"
import type { HostTool } from "../types.ts"
import { prBody, type Bundle } from "./bundle.ts"
import { verify } from "./verify.ts"

interface Worker {
  id: string
  parent_session_id: string
  worktree_id: string | null
  base_sha: string | null
  acceptance: string | null
}

// 6 lines for the parent: who, verdict, head, acceptance result, bundle, known gaps. All from prBody.
export function summaryOf(workerId: string, b: Bundle): string {
  const body = prBody(b).split("\n")
  const line = (p: string) => body.find((l) => l.startsWith(p)) ?? `${p} none`
  const failed = b.verified.reruns.filter((r) => r.exit !== 0)
  return [
    `Harness verified worker ${workerId}.`,
    line("Verdict:"),
    line("Head SHA:"),
    `Acceptance: ${b.verified.reruns.length} command(s), ${failed.length} failed${failed.length ? ` (${failed.map((r) => r.command).join("; ").slice(0, 120)})` : ""}`,
    line("Bundle:"),
    line("Known gaps:"),
  ].join("\n")
}

export async function runVerify(db: Database, workerId: string, cwdArg?: string): Promise<void> {
  const w = db.query("select id, parent_session_id, worktree_id, base_sha, acceptance from workers where id = ?").get(workerId) as Worker | null
  if (!w) throw new Error(`unknown worker: ${workerId}`)
  const parent = db.query("select tool, cwd from sessions where id = ?").get(w.parent_session_id) as { tool: string; cwd: string | null } | null
  const wt = w.worktree_id ? (db.query("select path from worktrees where id = ?").get(w.worktree_id) as { path: string } | null) : null
  const cwd = cwdArg || wt?.path || parent?.cwd || process.cwd()
  const tool: HostTool = parent?.tool === "opencode" ? "opencode" : "claude"

  let text: string
  let data: Record<string, unknown>
  let outcome: string
  try {
    const b = await verify(db, {
      session: w.parent_session_id,
      cwd,
      commands: JSON.parse(w.acceptance ?? "[]"),
      baseSha: w.base_sha ?? undefined,
      testGlobs: TEST_GLOBS,
      workerId: w.id,
      snapshot: true,
    })
    text = summaryOf(w.id, b)
    outcome = b.verdict
    data = { workerId: w.id, bundleId: b.id, verdict: b.verdict, head_sha: b.headSha }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    text = `Harness could not verify worker ${w.id}: ${msg.slice(0, 300)}`
    outcome = "error"
    data = { workerId: w.id, error: msg.slice(0, 500) }
  }
  await deliver(db, { session: w.parent_session_id, tool, text, kind: "worker.verified" })
  append(db, { session_id: w.parent_session_id, event: "worker.verified", outcome, reason: text.split("\n")[1] ?? text, data })
}

if (import.meta.main) {
  const [workerId, cwd] = process.argv.slice(2)
  if (!workerId) {
    console.error("usage: bun src/proof/run-verify.ts <workerId> [cwd]")
    process.exit(2)
  }
  const db = openLedger()
  try {
    seed(db)
    await runVerify(db, workerId, cwd)
  } catch (e) {
    console.error(e instanceof Error ? e.message : String(e))
    process.exitCode = 1
  } finally {
    db.close()
  }
}
