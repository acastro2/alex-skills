import type { Database } from "bun:sqlite"
import { consume, holds } from "../ledger/authority.ts"
import { append, upsertSession } from "../ledger/journal.ts"

export type Gh = (args: string[]) => { code: number; stdout: string; stderr: string }

export const spawnGh: Gh = (args) => {
  const r = Bun.spawnSync(["gh", ...args], { stdout: "pipe", stderr: "pipe" })
  return { code: r.exitCode ?? 1, stdout: r.stdout.toString(), stderr: r.stderr.toString() }
}

export const NEEDS_TOKEN = "Merge needs Alex's token: he types `MERGE-OK <pr>` as the first line of a prompt."

// Always a rebase merge, never a merge commit (D26). The token is single use and bound to this session and PR.
export function mergePr(
  db: Database,
  a: { session: string; repo: string; pr: number },
  run: Gh = spawnGh,
): { ok: boolean; message: string } {
  if (!/^[\w.-]+\/[\w.-]+$/.test(a.repo)) return { ok: false, message: `bad repo "${a.repo}": use owner/name` }
  if (!Number.isInteger(a.pr) || a.pr <= 0) return { ok: false, message: `bad PR number: ${a.pr}` }

  upsertSession(db, { id: a.session, tool: "unknown" })
  const data = { repo: a.repo, pr: a.pr }
  const token = holds(db, { kind: "merge", session: a.session, pr: a.pr })
  if (!token || !consume(db, token)) {
    append(db, { session_id: a.session, event: "merge.denied", outcome: "deny", data })
    return { ok: false, message: NEEDS_TOKEN }
  }

  const r = run(["pr", "merge", String(a.pr), "--repo", a.repo, "--rebase"])
  if (r.code === 0) {
    append(db, { session_id: a.session, event: "merge.done", outcome: "allow", data: { ...data, token_id: token } })
    return { ok: true, message: `Merged ${a.repo}#${a.pr} by rebase.` }
  }
  const reason = (r.stderr || r.stdout).trim()
  append(db, { session_id: a.session, event: "merge.failed", outcome: "deny", reason, data: { ...data, token_id: token, code: r.code } })
  return { ok: false, message: `gh pr merge failed (exit ${r.code}): ${reason}. The token is spent; Alex must type MERGE-OK ${a.pr} again.` }
}
