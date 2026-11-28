// Terminal approvals (Alex 2026-11-28). `requests` is read-only. `approve` and `merge-ok` are the human gate:
// the answer is read from the controlling terminal only (never stdin), then Touch ID on macOS, then command().
// An agent's shell has no terminal, and the shell guard (harness-self) denies these verbs for agents.
import type { Database } from "bun:sqlite"
import { closeSync, existsSync, openSync, readSync, statSync, writeSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"
import { openLedger } from "./ledger/db.ts"
import { command } from "./ledger/authority.ts"
import { upsertSession } from "./ledger/journal.ts"

const CLI_SESSION = "harness-cli"
const NO_TTY = "approve needs a terminal: run it yourself, not through an agent"

class Exit extends Error {
  constructor(
    readonly code: number,
    msg: string,
  ) {
    super(msg)
  }
}

interface OpenRequest {
  id: string
  session_id: string | null
  sha: string
  digest: string
  review_seq: number | null
  created_at: number
}

const openRequests = (db: Database) =>
  db.query("select id, session_id, sha, digest, review_seq, created_at from requests where state = 'open' order by created_at, id").all() as OpenRequest[]

function age(ms: number): string {
  const s = Math.max(0, Math.round((Date.now() - ms) / 1000))
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h`
  return `${Math.floor(s / 86400)}d`
}

function requests(db: Database): string {
  const rows = openRequests(db)
  if (!rows.length) return "No open harness requests.\n"
  const out = rows.map((r) => `${r.sha.slice(0, 8)}  ${r.digest.slice(0, 8)}  asked by ${r.session_id ?? "unknown"}  ${age(r.created_at)} ago\n    to approve, run in your terminal: harness approve ${r.sha.slice(0, 8)}`)
  return out.join("\n") + "\n"
}

// ---- the human gate ----

interface Tty {
  ask(prompt: string): string
  say(text: string): void
  close(): void
}

function openTty(): Tty {
  let fd: number
  try {
    fd = openSync(process.env.HARNESS_TTY || "/dev/tty", "r+")
  } catch {
    throw new Exit(2, NO_TTY)
  }
  const say = (text: string) => void writeSync(fd, text)
  return {
    say,
    close: () => closeSync(fd),
    ask(prompt) {
      say(prompt)
      const buf = Buffer.alloc(1)
      const bytes: number[] = []
      for (;;) {
        let n = 0
        try {
          n = readSync(fd, buf, 0, 1, null)
        } catch (e) {
          if ((e as NodeJS.ErrnoException).code === "EAGAIN") continue
          throw new Exit(2, NO_TTY)
        }
        if (n === 0 || buf[0] === 10) break
        if (buf[0] !== 13) bytes.push(buf[0])
      }
      return Buffer.from(bytes).toString("utf8").trim()
    },
  }
}

function touchId(tty: Tty, reason: string): void {
  if (process.env.HARNESS_TOUCHID === "skip") return
  if (process.platform !== "darwin") {
    tty.say("No Touch ID on this OS: skipped.\n")
    return
  }
  const src = join(import.meta.dir, "..", "bin", "touchid.swift")
  const bin = join(process.env.HARNESS_STATE_DIR ?? join(homedir(), ".local", "state", "harness"), "bin", "touchid")
  let argv = ["swift", src, reason]
  // Compile once; a stale binary (older than the source) is rebuilt. Without swiftc, run the script with `swift`.
  if (!existsSync(bin) || statSync(bin).mtimeMs < statSync(src).mtimeMs) {
    Bun.spawnSync(["mkdir", "-p", join(bin, "..")])
    Bun.spawnSync(["swiftc", "-O", src, "-o", bin], { stdout: "ignore", stderr: "ignore" })
  }
  if (existsSync(bin)) argv = [bin, reason]
  tty.say("Touch ID: confirm on the sensor.\n")
  const p = Bun.spawnSync(argv, { stdin: "ignore", stdout: "ignore", stderr: "pipe" })
  if (p.exitCode !== 0) throw new Exit(1, "Touch ID failed. Nothing granted.")
}

// Order matters: terminal, typed confirmation, Touch ID. Nothing is granted before all three pass.
function gate(summary: string, expected: string, label: string, reason: string): void {
  const tty = openTty()
  try {
    tty.say(summary)
    const typed = tty.ask(`Type ${label} to approve: `)
    if (typed !== expected) throw new Exit(1, `That is not ${label}. Nothing granted.`)
    touchId(tty, reason)
  } finally {
    tty.close()
  }
}

// ---- commands ----

function approve(db: Database, prefix: string | undefined): string {
  if (!prefix || !/^[0-9a-f]{8,40}$/i.test(prefix)) throw new Exit(1, "usage: harness approve <sha8>")
  const matches = openRequests(db).filter((r) => r.sha.startsWith(prefix.toLowerCase()))
  if (matches.length === 0) throw new Exit(1, `No open request with sha ${prefix}. Run: harness requests`)
  if (matches.length > 1) throw new Exit(1, `${matches.length} open requests match ${prefix}. Use a longer sha.`)
  const r = matches[0]
  const sha8 = r.sha.slice(0, 8)
  const digest8 = r.digest.slice(0, 8)
  const review = r.review_seq === null ? null : (db.query("select prompt_text t from journal where seq = ?").get(r.review_seq) as { t: string | null } | null)?.t
  const lines = (review ?? "(no review text journaled)").split("\n")
  const shown = lines.slice(0, 15).join("\n") + (lines.length > 15 ? `\n... ${lines.length - 15} more lines (full text on the harness page)` : "")
  gate(`\nHarness change ${sha8} (digest ${digest8}), asked by ${r.session_id ?? "unknown"}, ${age(r.created_at)} ago\n\n${shown}\n\n`, digest8, `the digest (${digest8})`, `Approve harness change ${sha8}`)
  upsertSession(db, { id: CLI_SESSION, tool: "cli", interactive: true })
  const out = command(db, { channel: "cli", session: CLI_SESSION, isRootSession: true, text: `HARNESS-OK ${sha8} ${digest8}` })
  if (out.kind !== "grant") throw new Exit(1, "The authority module did not accept this approval. Nothing granted.")
  return `Approved ${sha8} for 30 minutes (token ${out.tokenId}).\n`
}

function mergeOk(db: Database, args: string[]): string {
  const i = args.indexOf("--session")
  const session = i >= 0 ? args[i + 1] : undefined
  const prs = args.filter((a, k) => k !== i && k !== i + 1 && /^\d+$/.test(a))
  if (!prs.length || !session) throw new Exit(1, "usage: harness merge-ok <pr>... --session <id>")
  if (prs.length > 10) throw new Exit(1, "At most 10 PRs per approval.")
  if (!db.query("select 1 from sessions where id = ?").get(session)) throw new Exit(1, `Unknown session ${session}.`)
  const list = prs.join(" ")
  const many = prs.length > 1
  const label = many ? `the PR numbers (${list})` : `the PR number (${list})`
  gate(
    `\nMerge ${many ? "PRs" : "PR"} ${prs.map((p) => `#${p}`).join(", ")} for session ${session}.\n\n`,
    list,
    label,
    `Approve merge of PR ${list}`,
  )
  const out = command(db, { channel: "cli", session, isRootSession: true, text: `MERGE-OK ${list}` })
  if (out.kind !== "grant") throw new Exit(1, "The authority module did not accept this approval. Nothing granted.")
  return `Merge of ${many ? "PRs" : "PR"} ${prs.map((p) => `#${p}`).join(", ")} approved for 30 minutes, bound to session ${session} (token ${out.tokenId}).\n`
}

const USAGE = "usage: harness requests | approve <sha8> | merge-ok <pr>... --session <id>\n"

export function main(argv: string[]): number {
  const [verb, ...rest] = argv
  if (verb !== "requests" && verb !== "approve" && verb !== "merge-ok") {
    process.stderr.write(USAGE)
    return 1
  }
  try {
    const db = openLedger()
    try {
      process.stdout.write(verb === "requests" ? requests(db) : verb === "approve" ? approve(db, rest[0]) : mergeOk(db, rest))
    } finally {
      db.close()
    }
    return 0
  } catch (e) {
    if (e instanceof Exit) {
      process.stderr.write(e.message + "\n")
      return e.code
    }
    throw e
  }
}

if (import.meta.main) process.exit(main(process.argv.slice(2)))
