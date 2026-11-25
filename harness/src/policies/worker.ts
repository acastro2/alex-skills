// Worker lifecycle (Phase 3, D17): a workers row when a general subagent is spawned,
// and a detached background verify when its call returns.
import { basename, join } from "node:path"
import { ulid } from "../ledger/ulid.ts"
import { pushGate } from "../proof/gate.ts"
import { git, hit, q1, type Env, type Out } from "./util.ts"
import { isGeneral } from "./spawn.ts"

export const TEST_GLOBS = ["tests/**", "**/*.test.*", "**/test_*.py"]

interface WorkerRow {
  id: string
  acceptance: string | null
}

// The lines under ACCEPTANCE: up to the first blank line or the next "SOME LABEL:" line.
// "- criterion → `cmd`" gives cmd; "- `cmd`" and a bare "cmd" also work.
export function parseAcceptance(prompt: string): string[] {
  const lines = prompt.split(/\r?\n/)
  const at = lines.findIndex((l) => /^ACCEPTANCE:/.test(l))
  if (at < 0) return []
  const out: string[] = []
  const first = lines[at].replace(/^ACCEPTANCE:/, "").trim()
  const take = (raw: string) => {
    let c = raw.replace(/^\s*(?:[-*]|\d+[.)])\s+/, "").trim()
    if (c.includes("→")) c = c.slice(c.lastIndexOf("→") + 1).trim()
    c = c.replace(/^\$\s+/, "")
    const m = /^`([^`]+)`$/.exec(c)
    if (m) c = m[1].trim()
    if (c) out.push(c)
  }
  if (first) take(first)
  for (const l of lines.slice(at + 1)) {
    if (!l.trim() || /^[A-Z][A-Z0-9 _-]{2,}:/.test(l)) break
    take(l)
  }
  return out
}

// Blob ids of the test files at HEAD: the baseline the verify step compares against.
function testHashes(cwd: string): Record<string, string> {
  const ls = git(["ls-tree", "-r", "HEAD"], cwd)
  if (!ls.ok) return {}
  const globs = TEST_GLOBS.map((g) => new Bun.Glob(g))
  const out: Record<string, string> = {}
  for (const line of ls.out.split("\n")) {
    const m = /^\d+ blob (\w+)\t(.+)$/.exec(line)
    if (m && globs.some((g) => g.match(m[2]))) out[m[2]] = m[1]
  }
  return out
}

// tool.before of an allowed general spawn. Never throws: a ledger problem must not block the spawn.
export function recordWorker(env: Env): void {
  const { db, ev } = env
  const i = ev.input ?? {}
  if (!isGeneral(i.agent)) return
  try {
    const cwd = String(i.cwd ?? ev.cwd)
    const head = git(["rev-parse", "HEAD"], cwd)
    const wt = q1<{ id: string }>(db, "select id from worktrees where removed_at is null and (? = path or ? like path || '/%') order by length(path) desc limit 1", cwd, cwd)
    db.query(
      `insert into workers(id, parent_session_id, worktree_id, model, base_sha, test_hashes, acceptance, ladder_round)
       values(?, ?, ?, ?, ?, ?, ?, 0)`,
    ).run(
      ulid(),
      ev.session,
      wt?.id ?? null,
      typeof i.model === "string" ? i.model : null,
      head.ok ? head.out : null,
      JSON.stringify(head.ok ? testHashes(cwd) : {}),
      JSON.stringify(parseAcceptance(String(i.prompt ?? ""))),
    )
  } catch {
    // no row: the tool.after step finds nothing to verify
  }
}

const bunBinary = () => process.env.HARNESS_BUN ?? (basename(process.execPath).startsWith("bun") ? process.execPath : (Bun.which("bun") ?? "bun"))

// tool.after of a general spawn: claim the worker row and start the verify in a detached process.
// Returns the context text for the parent, or null when this call has no worker row.
export function startVerify(env: Env): { context: string; workerId: string } | null {
  const { db, ev } = env
  const i = ev.input ?? {}
  if (!isGeneral(i.agent) || ev.failed) return null
  try {
    const pending = db
      .query("select id, acceptance from workers where parent_session_id = ? and last_activity is null order by id")
      .all(ev.session) as WorkerRow[]
    const mine = parseAcceptance(String(i.prompt ?? ""))
    const row = pending.find((w) => w.acceptance === JSON.stringify(mine)) ?? pending[0]
    if (!row) return null
    db.query("update workers set last_activity = ? where id = ?").run(ev.time, row.id)
    const cwd = String(i.cwd ?? ev.cwd)
    const p = Bun.spawn([bunBinary(), join(import.meta.dir, "..", "proof", "run-verify.ts"), row.id, cwd], {
      cwd: join(import.meta.dir, "..", ".."),
      stdio: ["ignore", "ignore", "ignore"],
      detached: true,
      env: process.env,
    })
    p.unref()
    return { workerId: row.id, context: `Harness: verifying this worker's result in the background (worker ${row.id}). The verdict arrives as a message.` }
  } catch {
    return null
  }
}

// tool.before of a shell command that pushes: the gate says what it would deny, the registry mode decides (D44).
export function guardPush(env: Env): Out | null {
  const command = String(env.ev.input?.command ?? "")
  if (!/\bgit\b/.test(command) || !/\bpush\b/.test(command)) return null
  try {
    const found = pushGate(env.db, { cwd: String(env.ev.input?.cwd ?? env.ev.cwd), command })
    return found ? hit(env, found.ruleId, found.message) : null
  } catch {
    return null
  }
}
