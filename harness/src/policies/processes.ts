// Background processes of a session (D20, D22): register them after a shell call, send the agent back
// when one runs unnamed at stop, and kill the unkept ones at session.end.
import type { Database } from "bun:sqlite"
import { createHash } from "node:crypto"
import { basename } from "node:path"
import { append, scrub } from "../ledger/journal.ts"
import { q1, shortArg, type Env } from "./util.ts"

const RECENT_MS = 120_000 // a registered process must have started this close to the tool call
export const KILL_GRACE_MS = 1500 // spec says 2 s; the adapters time the core out at 2.5 s, so SIGKILL must come earlier

const BG_CMD = /\b(nohup|setsid|disown)\b|(?<![&>|])&(?![&>])/
const BG_OUT = /running in background|started in background|moved to background/i
const LISTEN = [
  /listening (?:on|at)\b[^\n]*?(?::|\bport\s+)(\d{2,5})\b/gi,
  /Local:\s+https?:\/\/[^\s]+:(\d{2,5})/g,
  /started server on .*:(\d{2,5})/gi,
  /Serving HTTP on \S+ port (\d{2,5})/g,
]
const CMD_PORT = /(?:http\.server\s+|--port[= ]|--listen[= ]|\s-p\s*|(?:localhost|0\.0\.0\.0|127\.0\.0\.1|\*):)(\d{2,5})\b/g
const OUT_PID = [/\bpid[:=\s#]+(\d{2,7})\b/gi, /^\[\d+\]\s+(\d{2,7})\s*$/gm]
const LONE_PID = /^\s*(\d{2,7})\s*$/gm // only with `$!` in the command
const INTERPRETERS = /^(python[\d.]*|node|bun|deno|ruby|perl|php|java|sh|bash|zsh|npm|npx|pnpm|yarn|uv|uvx|env|sudo|setsid|nohup)$/

const hash = (s: string) => createHash("sha256").update(s).digest("hex").slice(0, 16)

export interface Proc {
  cmd: string
  startMs: number
}

// The live process behind a pid, or null: dead, zombie, or owned by someone else.
export function procInfo(pid: number): Proc | null {
  if (!Number.isInteger(pid) || pid <= 1) return null
  try {
    process.kill(pid, 0)
  } catch {
    return null
  }
  try {
    const r = Bun.spawnSync(["ps", "-ww", "-o", "stat=,etime=,args=", "-p", String(pid)], { stdout: "pipe", stderr: "ignore" })
    const m = /^\s*(\S+)\s+(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)\s+(.*)$/.exec(r.stdout.toString().split("\n")[0] ?? "")
    if (!m || m[1].startsWith("Z")) return null
    const secs = Number(m[2] ?? 0) * 86400 + Number(m[3] ?? 0) * 3600 + Number(m[4]) * 60 + Number(m[5])
    return { cmd: m[6].trim(), startMs: Date.now() - secs * 1000 }
  } catch {
    return null
  }
}

// Linux: ss. macOS: lsof. Either tool missing falls through to the other.
export function pidsOnPort(port: number): number[] {
  const tries: [string[], RegExp][] =
    process.platform === "linux"
      ? [[["ss", "-ltnpH", "sport", "=", `:${port}`], /pid=(\d+)/g], [["lsof", "-nP", `-iTCP:${port}`, "-sTCP:LISTEN", "-t"], /^(\d+)$/gm]]
      : [[["lsof", "-nP", `-iTCP:${port}`, "-sTCP:LISTEN", "-t"], /^(\d+)$/gm], [["ss", "-ltnpH", "sport", "=", `:${port}`], /pid=(\d+)/g]]
  for (const [cmd, re] of tries) {
    try {
      const r = Bun.spawnSync(cmd, { stdout: "pipe", stderr: "ignore" })
      const pids = [...r.stdout.toString().matchAll(re)].map((m) => Number(m[1]))
      if (pids.length) return [...new Set(pids)]
    } catch {}
  }
  return []
}

const all = (re: RegExp, text: string): number[] => [...text.matchAll(re)].map((m) => Number(m[1])).filter((n) => n > 1)

// tool.after of a shell call: record the background processes and listening servers it left behind.
export function registerShellProcesses(env: Env): void {
  const { db, ev } = env
  if (ev.toolName !== "shell" || ev.failed) return
  const input = (ev.input ?? {}) as Record<string, unknown>
  const command = String(input.command ?? "")
  const out = ev.output ?? ""
  const background = input.run_in_background === true || input.background === true || BG_CMD.test(command) || BG_OUT.test(out)

  const ports = new Set<number>(LISTEN.flatMap((re) => all(re, out)))
  const pids = new Map<number, number | null>() // pid -> port
  if (background) {
    for (const p of all(CMD_PORT, command)) ports.add(p)
    for (const re of OUT_PID) for (const pid of all(re, out)) pids.set(pid, null)
    if (command.includes("$!")) for (const pid of all(LONE_PID, out)) pids.set(pid, null)
  }
  for (const port of ports) for (const pid of pidsOnPort(port)) pids.set(pid, port)

  for (const [pid, port] of pids) {
    if (pid === process.pid || pid === process.ppid) continue
    const info = procInfo(pid)
    if (!info || info.startMs < ev.time - RECENT_MS) continue
    if (q1(db, "select 1 as x from processes where session_id = ? and pid = ? and ended_at is null", ev.session, pid)) continue
    db.query("insert into processes(session_id, pid, command, port, keep, started_at) values(?, ?, ?, ?, 0, ?)").run(
      ev.session,
      pid,
      scrub(info.cmd).slice(0, 300),
      port,
      info.startMs,
    )
    append(db, { session_id: ev.session, turn: env.turn, time: ev.time, event: "process.registered", data: { pid, port, cmdHash: hash(info.cmd) } })
  }
}

export interface ProcRow {
  id: number
  pid: number
  command: string | null
  port: number | null
  keep: number | null
}

// Is the live process still the one we registered? A reused pid has another command line.
function same(db: Database, session: string, row: ProcRow, cur: Proc): boolean {
  const rec = q1<{ h: string | null }>(
    db,
    "select json_extract(data_json, '$.cmdHash') as h from journal where session_id = ? and event = 'process.registered' and json_extract(data_json, '$.pid') = ? order by seq desc limit 1",
    session,
    row.pid,
  )
  if (rec?.h) return rec.h === hash(cur.cmd)
  // keep_process made the row, so there is no record: accept when the stored command and the live one overlap.
  const stored = row.command ?? ""
  return !!stored && (cur.cmd.includes(stored) || stored.includes(cur.cmd) || stored.includes(basename(cur.cmd.split(/\s+/)[0])))
}

// This session's unended processes. A dead one gets its ended_at here; a pid with another command is left alone.
function liveRows(db: Database, session: string, now: number): { row: ProcRow; mine: boolean }[] {
  const rows = db
    .query("select id, pid, command, port, keep from processes where session_id = ? and ended_at is null order by id")
    .all(session) as ProcRow[]
  const out: { row: ProcRow; mine: boolean }[] = []
  for (const row of rows) {
    const cur = procInfo(row.pid)
    if (!cur) db.query("update processes set ended_at = ? where id = ?").run(now, row.id)
    else out.push({ row, mine: same(db, session, row, cur) })
  }
  return out
}

// What a reply calls a process: the first word that is not an interpreter or a flag.
const nameOf = (command: string | null): string =>
  basename((command ?? "").split(/\s+/).find((t, i) => t && !t.startsWith("-") && !(i === 0 && INTERPRETERS.test(basename(t)))) ?? "")

const mentions = (reply: string, n: number) => new RegExp(`(?<!\\d)${n}(?!\\d)`).test(reply)

const describe = (r: ProcRow) => `Process ${shortArg(r.command ?? "unknown", 60)} (PID ${r.pid}${r.port ? `, port ${r.port}` : ""})`

// stop-processes: a process of this session is alive and the reply does not name it.
export function processCheck(env: Env, reply: string): { id: string; message: string; data: Record<string, unknown> } | null {
  const unnamed = liveRows(env.db, env.ev.session, env.ev.time)
    .filter((p) => p.mine)
    .map((p) => p.row)
    .filter((r) => {
      const name = nameOf(r.command)
      return !(mentions(reply, r.pid) || (r.port && mentions(reply, r.port)) || (name.length >= 3 && reply.includes(name)))
    })
  if (!unnamed.length) return null
  return {
    id: "stop-processes",
    message: unnamed
      .slice(0, 3)
      .map((r) => `${describe(r)} is still running. Kill it, or name it in your reply if Alex asked to keep it (\`keep_process\`).`)
      .join("\n"),
    data: { processes: unnamed.slice(0, 10).map((r) => ({ pid: r.pid, port: r.port, keep: !!r.keep })) },
  }
}

// session.end: SIGTERM each unkept process of the session, SIGKILL what is left after the grace time.
export async function endSessionProcesses(db: Database, session: string, time: number): Promise<number[]> {
  const todo = liveRows(db, session, time)
  const kill: ProcRow[] = []
  for (const { row, mine } of todo) {
    if (row.keep) continue
    if (!mine) {
      append(db, { session_id: session, time, event: "process.skipped", data: { pid: row.pid, reason: "pid now runs another command" } })
      continue
    }
    kill.push(row)
  }
  for (const r of kill) {
    try {
      process.kill(r.pid, "SIGTERM")
    } catch {}
  }
  const deadline = Date.now() + KILL_GRACE_MS
  while (kill.some((r) => procInfo(r.pid)) && Date.now() < deadline) await Bun.sleep(50)
  const killed: number[] = []
  for (const r of kill) {
    let signal = "SIGTERM"
    if (procInfo(r.pid)) {
      signal = "SIGKILL"
      try {
        process.kill(r.pid, "SIGKILL")
      } catch {}
    }
    db.query("update processes set ended_at = ? where id = ?").run(time, r.id)
    append(db, { session_id: session, time, event: "process.killed", data: { pid: r.pid, port: r.port, signal } })
    killed.push(r.pid)
  }
  return killed
}

// session.start: one line for the kept processes still running in this repo. Each is reported once.
export function keptProcessLine(db: Database, session: string, now: number): string | null {
  const repo = q1<{ repo: string | null }>(db, "select repo from sessions where id = ?", session)?.repo
  if (!repo) return null
  const rows = db
    .query(
      `select p.id, p.pid, p.command, p.port, p.keep from processes p join sessions s on s.id = p.session_id
       where s.repo = ? and p.keep = 1 and p.ended_at is null and p.reported_at is null order by p.id`,
    )
    .all(repo) as ProcRow[]
  const live = rows.filter((r) => {
    if (procInfo(r.pid)) return true
    db.query("update processes set ended_at = ? where id = ?").run(now, r.id)
    return false
  })
  if (!live.length) return null
  for (const r of live) db.query("update processes set reported_at = ? where id = ?").run(now, r.id)
  return `Kept processes still running in this repo: ${live.map(describe).join("; ")}. Kill them when Alex is done.`
}
