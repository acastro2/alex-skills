// Worker lifecycle (Phase 3, D17): a workers row when a general subagent is spawned,
// and a detached background verify when its call returns.
import { basename, join } from "node:path"
import { ulid } from "../ledger/ulid.ts"
import { upsertSession } from "../ledger/journal.ts"
import { pushGate } from "../proof/gate.ts"
import { git, hit, q1, type Env, type Out } from "./util.ts"
import { isGeneral, isReadOnly } from "./spawn.ts"

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
  // A line is a command only when it says so: in backticks, after "→", or starting with a real program
  // or a path. Prose criteria ("all pass.", "Unified diffs of every edited file.") are not commands.
  const take = (raw: string) => {
    let c = raw.replace(/^\s*(?:[-*]|\d+[.)])\s+/, "").trim()
    if (c.includes("→")) c = c.slice(c.lastIndexOf("→") + 1).trim()
    c = c.replace(/^\$\s+/, "")
    const tick = /`([^`]+)`/.exec(c)
    if (tick) {
      out.push(tick[1].trim())
      return
    }
    c = c.replace(/\s+\([^()]*\)\s*$/, "").trim() // a trailing "(must print [])" note
    const prog = c.split(/\s+/)[0] ?? ""
    const looksLikeCommand = /^(?:\.{0,2}\/|~\/)/.test(prog) || (/^[a-z][\w.+-]*$/.test(prog) && Bun.which(prog) !== null) || ["cd", "test", "["].includes(prog)
    if (c && looksLikeCommand) out.push(c)
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
  if (!isGeneral(i.agent) || (typeof i.sessionID === "string" && i.sessionID) || isReadOnly(String(i.prompt ?? ""))) return
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
  if (!isGeneral(i.agent) || ev.failed || (typeof i.sessionID === "string" && i.sessionID)) return null
  try {
    const pending = db
      .query("select id, acceptance from workers where parent_session_id = ? and last_activity is null order by id")
      .all(ev.session) as WorkerRow[]
    const mine = parseAcceptance(String(i.prompt ?? ""))
    const row = pending.find((w) => w.acceptance === JSON.stringify(mine)) ?? pending[0]
    if (!row) return null
    // A background subagent (OpenCode always, Claude Code with run_in_background) returns at launch.
    // Track its session; the verify starts when that session stops (verifyFinishedWorker).
    const out = String(ev.output ?? "")
    const child = /sessionID:\s*(ses[\w-]+)/.exec(out)?.[1] ?? /agentId:\s*([\w-]+)/.exec(out)?.[1]
    if (child && (/in the background/i.test(out) || i.run_in_background === true)) {
      upsertSession(db, { id: child, tool: ev.tool, parent_session_id: ev.session, cwd: String(i.cwd ?? ev.cwd) })
      db.query("update workers set worker_session_id = ? where id = ?").run(child, row.id)
      return { workerId: row.id, context: `Harness: worker ${row.id} is tracked. Its verify runs when it finishes, and the verdict arrives as a message.` }
    }
    db.query("update workers set last_activity = ? where id = ?").run(ev.time, row.id)
    const cwd = String(i.cwd ?? ev.cwd)
    spawnVerify(row.id, cwd)
    return { workerId: row.id, context: `Harness: verifying this worker's result in the background (worker ${row.id}). The verdict arrives as a message.` }
  } catch {
    return null
  }
}

function spawnVerify(workerId: string, cwd: string): void {
    const p = Bun.spawn([bunBinary(), join(import.meta.dir, "..", "proof", "run-verify.ts"), workerId, cwd], {
      cwd: join(import.meta.dir, "..", ".."),
      stdio: ["ignore", "ignore", "ignore"],
      detached: true,
      env: process.env,
    })
    p.unref()
}

// stop of a tracked background worker: verify what it did this round. A round with no tool calls
// since the last verify (a plain reply) is skipped.
export function verifyFinishedWorker(env: Env): string | null {
  const { db, ev } = env
  try {
    const row = q1<{ id: string; last_activity: number | null; cwd: string | null }>(
      db,
      `select w.id, w.last_activity, coalesce(t.path, s.cwd) cwd from workers w
       left join worktrees t on t.id = w.worktree_id left join sessions s on s.id = w.worker_session_id
       where w.worker_session_id = ? order by w.id desc limit 1`,
      ev.session,
    )
    if (!row) return null
    const busy = q1<{ n: number }>(db, "select count(*) n from journal where session_id = ? and event like 'tool.%' and time > ?", ev.session, row.last_activity ?? 0)
    if (!busy?.n) return null
    db.query("update workers set last_activity = ? where id = ?").run(ev.time, row.id)
    spawnVerify(row.id, row.cwd ?? ev.cwd ?? process.cwd())
    return row.id
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
