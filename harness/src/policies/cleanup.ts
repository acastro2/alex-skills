// Stop checks for disk and handoff hygiene (D22, D23): scratch size, leftover worktrees, HANDOFF.md protocol.
import { existsSync, readFileSync, realpathSync } from "node:fs"
import { tmpdir } from "node:os"
import { dirname, join, relative } from "node:path"
import { git, q1, toolRows, type Env } from "./util.ts"

interface Found {
  id: string
  message: string
  data?: Record<string, unknown>
}

const scratchLimitMb = () => Number(process.env.HARNESS_SCRATCH_LIMIT_MB) || 500

// Top-level entries under tmpdir() that this session's tool rows wrote to (rows carry data.path).
function scratchDirs(env: Env): string[] {
  // Longest root first, one match per path: OpenCode's tmpdir is /tmp/opencode, so under the plain /tmp root
  // a file in it made the whole shared /tmp/opencode count as one session's scratch (seen live: 505 MB).
  const roots = [...new Set([tmpdir(), process.env.TMPDIR?.replace(/\/+$/, ""), "/tmp"].filter(Boolean) as string[])].sort((a, b) => b.length - a.length)
  const rows = env.db
    .query("select data_json from journal where session_id = ? and event = 'tool.after' and data_json like '%\"path\"%'")
    .all(env.ev.session) as { data_json: string }[]
  const tops = new Set<string>()
  for (const r of rows) {
    const p = JSON.parse(r.data_json).path
    if (typeof p !== "string") continue
    // Claude Code's temp folder /tmp/claude-<uid>/<project>/<session>/ is shared by every session: the
    // session folder is the scratch unit, never claude-<uid> itself (seen live 2026-11-27: 586 MB, mine 1 MB).
    const cc = p.match(/^(\/tmp\/claude-\d+\/[^/]+)\//)?.[1]
    const root = cc ?? roots.find((r) => p.startsWith(`${r}/`))
    const first = root ? p.slice(root.length + 1).split("/")[0] : ""
    if (root && first) tops.add(join(root, first))
  }
  return [...tops].filter((d) => existsSync(d) && !roots.includes(d) && !/^\/tmp\/claude-\d+(\/[^/]+)?$/.test(d))
}

const sizeMb = (dir: string): number => {
  const r = Bun.spawnSync(["du", "-sk", dir], { stdout: "pipe", stderr: "ignore" })
  return (Number(r.stdout.toString().split(/\s+/)[0]) || 0) / 1024
}

export function cleanupCheck(env: Env): Found | null {
  const limit = scratchLimitMb()
  const big = scratchDirs(env)
    .map((d) => ({ d, mb: sizeMb(d) }))
    .filter((x) => x.mb > 0)
  const total = big.reduce((n, x) => n + x.mb, 0)
  const left = (env.db.query("select path from worktrees where session_id = ? and state = 'removed'").all(env.ev.session) as { path: string }[])
    .map((w) => w.path)
    .filter((p) => existsSync(p))

  const parts: string[] = []
  if (total > limit) {
    const top = big.sort((a, b) => b.mb - a.mb).slice(0, 3)
    parts.push(`Your scratch files take ${Math.round(total)} MB (limit ${limit} MB): ${top.map((x) => `${x.d} (${Math.round(x.mb)} MB)`).join(", ")}. Delete what you no longer need.`)
  }
  if (left.length) {
    parts.push(`Worktree ${left.slice(0, 3).join(", ")} was removed from the ledger but is still on disk. Check it holds no unsaved work, then clean it up.`)
  }
  return parts.length ? { id: "stop-cleanup", message: parts.join("\n"), data: { scratchMb: Math.round(total), leftWorktrees: left.slice(0, 5) } } : null
}

const MESSAGE = "HANDOFF.md holds lasting context only (150 lines max); live state goes through `workstream_update`."
const PID_LINE = /\bpid\b\W{0,3}\d+/i
const STATE_LINE = /^\s*[-*]?\s*\**state\**\s*:/i
const isoDay = (t: number) => new Date(t).toISOString().slice(0, 10)

// Lines this turn added to the file: the working-tree diff, plus commits made since the turn began.
function addedLines(top: string, rel: string, sinceMs: number): Set<string> {
  const diff = git(["diff", "-U0", "HEAD", "--", rel], top).out
  const log = git(["log", `--since=${Math.floor(sinceMs / 1000)}`, "-p", "-U0", "--format=", "--", rel], top).out
  const added = new Set<string>()
  for (const l of `${diff}\n${log}`.split("\n")) if (l.startsWith("+") && !l.startsWith("+++")) added.add(l.slice(1).trim())
  return added
}

// A line is live state when it lists a process with a PID, or a State: line dated today under a workstream that has a ledger row.
function liveStateLines(env: Env, text: string, added: Set<string>): string[] {
  const streams = (env.db.query("select id, title from workstreams").all() as { id: string; title: string | null }[]).flatMap((w) => [
    w.id.toLowerCase(),
    ...(w.title && w.title.length >= 3 && w.title !== "untitled" ? [w.title.toLowerCase()] : []),
  ])
  const days = [isoDay(env.ev.time), new Date(env.ev.time - new Date().getTimezoneOffset() * 60_000).toISOString().slice(0, 10)]
  const hits: string[] = []
  let heading = ""
  for (const line of text.split("\n")) {
    const h = /^#{1,6}\s+(.*)$/.exec(line)
    if (h) {
      heading = h[1].toLowerCase()
      continue
    }
    if (!added.has(line.trim())) continue
    if (/running processes/.test(heading) && PID_LINE.test(line)) hits.push(line.trim())
    else if (STATE_LINE.test(line) && days.some((d) => line.includes(d)) && streams.some((s) => heading.includes(s))) hits.push(line.trim())
  }
  return hits
}

export function handoffProtocolCheck(env: Env): Found | null {
  const rows = toolRows(env.db, env.ev.session, env.turn)
  const paths = [...new Set(rows.filter((r) => (r.data.tool === "edit" || r.data.tool === "write") && !r.data.failed && typeof r.data.path === "string").map((r) => r.data.path as string))]
  const since = q1<{ t: number | null }>(env.db, "select min(time) as t from journal where session_id = ? and turn = ?", env.ev.session, env.turn)?.t ?? env.ev.time

  for (const path of paths) {
    if (!/(^|\/)HANDOFF\.md$/.test(path) || !existsSync(path)) continue
    const dir = dirname(path)
    const top = git(["rev-parse", "--show-toplevel"], dir)
    if (!top.ok) continue
    const rel = relative(top.out, realpathSync(path))
    if (rel !== "HANDOFF.md" && rel !== "docs/HANDOFF.md") continue
    if (!git(["ls-files", "--error-unmatch", "--", rel], top.out).ok) continue // not committed: not the protocol's business

    const text = readFileSync(path, "utf8")
    const lines = text.replace(/\n$/, "").split("\n").length
    if (lines > 150) return { id: "stop-handoff-protocol", message: MESSAGE, data: { path, lines } }
    const live = liveStateLines(env, text, addedLines(top.out, rel, since))
    if (live.length) return { id: "stop-handoff-protocol", message: MESSAGE, data: { path, liveState: live.slice(0, 5) } }
  }
  return null
}
