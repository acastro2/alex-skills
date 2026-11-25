import type { Database } from "bun:sqlite"
import { append, prune } from "../ledger/journal.ts"
import { checkConflicts } from "../waker/conflicts.ts"
import { wakerTick } from "../waker/waker.ts"

export interface JobDef {
  name: string
  schedule: string // cron expression
  run: () => Promise<string | void>
}

export interface JobStatus {
  name: string
  schedule: string | null
  last_run_at: number | null
  last_result: string | null
  running: boolean
}

const DAY = 24 * 3600_000

// D57, D63, D66: the parent configures the command later, e.g. HARNESS_JOB_CORRECTION_MINER="bun run ...".
function envJob(db: Database, name: string, schedule: string): JobDef {
  return {
    name,
    schedule,
    run: async () => {
      const cmd = process.env[`HARNESS_JOB_${name.toUpperCase().replace(/-/g, "_")}`]
      if (!cmd) {
        append(db, { session_id: null, event: "job.skipped", reason: "not configured", data: { job: name } })
        return "skipped: not configured"
      }
      const p = Bun.spawn(["sh", "-c", cmd], { stdout: "pipe", stderr: "pipe" })
      const [out, err] = await Promise.all([new Response(p.stdout).text(), new Response(p.stderr).text()])
      const code = await p.exited
      const last = (code === 0 ? out : err || out).trim().split("\n").pop()?.slice(0, 200) ?? ""
      if (code !== 0) throw new Error(`exit ${code}: ${last}`)
      return `ok: ${last}`
    },
  }
}

export function builtinJobs(db: Database): JobDef[] {
  return [
    {
      name: "prune",
      schedule: "0 3 * * *",
      run: async () => {
        const n = prune(db, 90 * DAY)
        db.exec("PRAGMA incremental_vacuum")
        return `ok: pruned ${n} journal rows`
      },
    },
    {
      name: "conflicts",
      schedule: "*/5 * * * *",
      run: async () => `ok: ${(await checkConflicts(db)).length} worktrees checked`,
    },
    {
      name: "waker",
      schedule: "*/2 * * * *",
      run: async () => {
        await wakerTick(db)
        return "ok"
      },
    },
    envJob(db, "correction-miner", "0 9 * * 1"),
    envJob(db, "canary", "0 10 * * 1"),
    envJob(db, "new-model-evals", "0 * * * *"),
  ]
}

// The MCP tool reads the table directly: the running `harness serve` owns the schedule and the run state.
export function status(db: Database): Omit<JobStatus, "running">[] {
  return db.query("select name, schedule, last_run_at, last_result from jobs order by name").all() as Omit<JobStatus, "running">[]
}

// The agent cannot run a job itself. It journals a request, and `harness serve` picks it up (startJobs polls).
export function requestRun(db: Database, name: string): { requested: string } {
  const known = new Set([...builtinJobs(db).map((j) => j.name), ...status(db).map((j) => j.name)])
  if (!known.has(name)) throw new Error(`unknown job: ${name} (known: ${[...known].sort().join(", ")})`)
  append(db, { session_id: null, event: "job.requested", data: { job: name } })
  return { requested: name }
}

export function startJobs(
  db: Database,
  opts: { jobs?: JobDef[]; pollMs?: number } = {},
): { stop(): void; status(): JobStatus[]; runNow(name: string): Promise<string> } {
  const defs = new Map<string, JobDef>()
  for (const j of [...builtinJobs(db), ...(opts.jobs ?? [])]) defs.set(j.name, j)
  const running = new Set<string>()

  const upsert = db.query(
    "insert into jobs(name, schedule) values(?, ?) on conflict(name) do update set schedule = excluded.schedule",
  )
  for (const j of defs.values()) upsert.run(j.name, j.schedule)

  async function runNow(name: string): Promise<string> {
    const j = defs.get(name)
    if (!j) throw new Error(`unknown job: ${name}`)
    if (running.has(name)) return "skipped: already running"
    running.add(name)
    let result: string
    try {
      result = (await j.run()) ?? "ok"
    } catch (e) {
      result = `error: ${(e as Error).message}`
    } finally {
      running.delete(name)
    }
    const seq = append(db, { session_id: null, event: "job.run", outcome: result.startsWith("error") ? "error" : "ok", reason: result, data: { job: name } })
    db.query("update jobs set last_run_at = ?, last_result = ?, last_seq = ? where name = ?").run(Date.now(), result, seq, name)
    return result
  }

  const crons = [...defs.values()].map((j) => Bun.cron(j.schedule, () => void runNow(j.name)))

  // A job.requested row newer than the job's last run means an agent asked for a run (job_run_now).
  const pending = db.query(
    `select 1 as x from journal j join jobs b on b.name = ?
     where j.event = 'job.requested' and json_extract(j.data_json, '$.job') = ? and j.time > coalesce(b.last_run_at, 0) limit 1`,
  )
  const poll = setInterval(() => {
    try {
      for (const name of defs.keys()) if (!running.has(name) && pending.get(name, name)) void runNow(name)
    } catch {
      // a locked or closed ledger: try again on the next tick
    }
  }, opts.pollMs ?? 10_000)

  return {
    stop: () => {
      crons.forEach((c) => c.stop())
      clearInterval(poll)
    },
    status: () => status(db).map((r) => ({ ...r, running: running.has(r.name) })),
    runNow,
  }
}
