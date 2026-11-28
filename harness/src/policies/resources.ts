// Process sampling for stop-resources and the session-end sweep: one `ps` call, the agent's process tree,
// and the limits an agent's processes may not pass.
import type { Database } from "bun:sqlite"

export interface Sample {
  pid: number
  ppid: number
  rssKb: number
  cpu: number
  ageS: number
  comm: string
}

export interface Limits {
  idleMin: number
  rssMb: number
  cpuPct: number
}

const num = (name: string, dflt: number): number => {
  const n = Number(process.env[name])
  return process.env[name] !== undefined && process.env[name] !== "" && Number.isFinite(n) ? n : dflt
}

export const limits = (): Limits => ({
  idleMin: num("HARNESS_RESOURCE_IDLE_MIN", 10),
  rssMb: num("HARNESS_RESOURCE_RSS_MB", 500),
  cpuPct: num("HARNESS_RESOURCE_CPU_PCT", 50),
})

// [[dd-]hh:]mm:ss, what macOS prints for `etime`
function etimeSeconds(s: string): number {
  const m = /^(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)$/.exec(s.trim())
  return m ? Number(m[1] ?? 0) * 86400 + Number(m[2] ?? 0) * 3600 + Number(m[3]) * 60 + Number(m[4]) : 0
}

function ps(age: "etimes" | "etime"): Sample[] | null {
  try {
    const r = Bun.spawnSync(["ps", "-A", "-o", `pid=,ppid=,rss=,pcpu=,${age}=,comm=`], { stdout: "pipe", stderr: "ignore" })
    if (r.exitCode !== 0) return null
    const out: Sample[] = []
    for (const line of r.stdout.toString().split("\n")) {
      const m = /^\s*(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+(\S+)\s+(.+?)\s*$/.exec(line)
      if (m) out.push({ pid: Number(m[1]), ppid: Number(m[2]), rssKb: Number(m[3]), cpu: Number(m[4]), ageS: age === "etimes" ? Number(m[5]) : etimeSeconds(m[5]), comm: m[6] })
    }
    return out
  } catch {
    return null
  }
}

// Every process on the machine. Linux has etimes; macOS only etime.
export const sampleProcesses = (): Sample[] => ps("etimes") ?? ps("etime") ?? []

// Only these are agents. Anything else (systemd --user, launchd, init, a shell, tmux) is the parent of an orphan
// or of a hook run by hand, and its children are other people's work.
const AGENT = /^(claude|opencode)$/
const commOf = (all: Sample[], pid: number) => all.find((s) => s.pid === pid)?.comm.split("/").pop() ?? ""

// The agent process: HARNESS_AGENT_PID, else the hook's parent when it is claude or opencode. 0 means no agent.
// Incident 2026-11-28: an orphaned `bun test` had systemd --user as its parent, and the sweep killed the user
// session. The in-process OpenCode server hosts many sessions, so it is never the agent of one session.
export function agentPid(all: Sample[]): number {
  const n = Number(process.env.HARNESS_AGENT_PID)
  if (Number.isInteger(n) && n > 1) return n
  if (AGENT.test(commOf(all, process.pid))) return 0 // in-process (the OpenCode plugin)
  return process.ppid > 1 && AGENT.test(commOf(all, process.ppid)) ? process.ppid : 0
}

// Everything below root, root excluded.
export function descendants(all: Sample[], root: number): Set<number> {
  const kids = new Map<number, number[]>()
  for (const s of all) kids.set(s.ppid, [...(kids.get(s.ppid) ?? []), s.pid])
  const seen = new Set<number>()
  const todo = [root]
  for (let p = todo.pop(); p !== undefined; p = todo.pop()) for (const k of kids.get(p) ?? []) if (!seen.has(k)) (seen.add(k), todo.push(k))
  return seen
}

// The hook process and every ancestor of it: never a target, or the hook kills itself or its caller.
export function selfAndAncestors(all: Sample[]): Set<number> {
  const parent = new Map(all.map((s) => [s.pid, s.ppid]))
  const out = new Set<number>([process.pid, process.ppid])
  for (let p = parent.get(process.pid); p && p > 1 && !out.has(p); p = parent.get(p)) out.add(p)
  return out
}

// pids of every live keep_process row, and everything below them.
export function keptPids(db: Database, all: Sample[]): Set<number> {
  const rows = db.query("select pid from processes where keep = 1 and ended_at is null").all() as { pid: number }[]
  const out = new Set<number>()
  for (const r of rows) {
    out.add(r.pid)
    for (const d of descendants(all, r.pid)) out.add(d)
  }
  return out
}

export const ageText = (s: number): string => (s >= 3600 ? `${Math.floor(s / 3600)}h${Math.floor((s % 3600) / 60)}m` : s >= 60 ? `${Math.floor(s / 60)}m` : `${s}s`)

export interface Over {
  pid: number
  program: string
  rssMb: number
  cpu: number
  ageS: number
  line: string
}

// This session's live processes over a limit: unended, unkept rows of the processes table, then live
// descendants of the agent. Kept ones are left out.
export function overLimit(db: Database, session: string): Over[] {
  const all = sampleProcesses()
  if (!all.length) return []
  const by = new Map(all.map((s) => [s.pid, s]))
  const skip = new Set([...selfAndAncestors(all), ...keptPids(db, all)])
  const agent = agentPid(all)
  skip.add(agent)
  const rows = db.query("select pid from processes where session_id = ? and ended_at is null and coalesce(keep, 0) = 0 order by id").all(session) as { pid: number }[]
  const mine = [...new Set([...rows.map((r) => r.pid), ...(agent > 1 ? descendants(all, agent) : [])])]
  const lim = limits()
  const out: Over[] = []
  for (const pid of mine) {
    const s = by.get(pid)
    if (!s || skip.has(pid)) continue
    const rssMb = Math.round(s.rssKb / 1024)
    if (!(s.ageS >= lim.idleMin * 60 || rssMb > lim.rssMb || s.cpu > lim.cpuPct)) continue
    const program = s.comm.split("/").pop() ?? s.comm
    out.push({ pid, program, rssMb, cpu: s.cpu, ageS: s.ageS, line: `${pid} ${program} ${rssMb}MB ${s.cpu}% ${ageText(s.ageS)} → kill ${pid}` })
  }
  return out
}
