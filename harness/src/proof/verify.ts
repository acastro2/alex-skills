import type { Database } from "bun:sqlite"
import { createHash } from "node:crypto"
import { closeSync, existsSync, mkdtempSync, openSync, readdirSync, readFileSync, realpathSync, rmSync, statSync, symlinkSync } from "node:fs"
import { tmpdir } from "node:os"
import { join, relative } from "node:path"
import { append, upsertSession } from "../ledger/journal.ts"
import { ulid } from "../ledger/ulid.ts"
import { digestOf, type Bundle, type Rerun, type Verdict, type Verified } from "./bundle.ts"

const TIMEOUT_MS = 10 * 60 * 1000
const TAIL_LINES = 40

export interface VerifyOpts {
  session: string
  cwd: string
  commands: string[]
  baseSha?: string
  testGlobs?: string[]
  workerId?: string
  claimed?: unknown
  uiProof?: string[]
  summary?: string
  knownGaps?: string
  // A dirty tree is verified as a snapshot commit of the working tree (workers do not commit). Off: a dirty tree is partial.
  snapshot?: boolean
}

export function git(cwd: string, ...args: string[]): { code: number; out: string; err: string } {
  const p = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" })
  return { code: p.exitCode ?? 1, out: p.stdout.toString(), err: p.stderr.toString() }
}

function gitOk(cwd: string, ...args: string[]): string {
  const r = git(cwd, ...args)
  if (r.code !== 0) throw new Error(`git ${args.join(" ")} failed: ${r.err.trim()}`)
  return r.out
}

const lines = (s: string) => s.split("\n").filter(Boolean)
const sha256 = (b: Buffer | string) => createHash("sha256").update(b).digest("hex")

function blob(cwd: string, rev: string, path: string): string | null {
  const p = Bun.spawnSync(["git", "show", `${rev}:${path}`], { cwd, stdout: "pipe", stderr: "pipe" })
  return p.exitCode === 0 ? sha256(Buffer.from(p.stdout)) : null
}

function filesAt(cwd: string, rev: string, globs: string[]): string[] {
  const matchers = globs.map((g) => new Bun.Glob(g))
  return lines(gitOk(cwd, "ls-tree", "-r", "--name-only", rev)).filter((f) => matchers.some((m) => m.match(f)))
}

// shortcut: the repo's verify is read from the head tree, so a worker could edit it. Upgrade: restore it from base.
function repoVerify(root: string): string | null {
  const pkg = join(root, "package.json")
  if (existsSync(pkg)) {
    try {
      if (JSON.parse(readFileSync(pkg, "utf8")).scripts?.["harness.verify"]) return `${JSON.stringify(process.execPath)} run harness.verify`
    } catch {
      // not valid JSON: no verify from here
    }
  }
  const exe = join(root, "verify")
  if (existsSync(exe) && statSync(exe).isFile() && (statSync(exe).mode & 0o111) !== 0) return "./verify"
  const mk = join(root, "Makefile")
  if (existsSync(mk) && /^verify:/m.test(readFileSync(mk, "utf8"))) return "make verify"
  return null
}

async function runCommand(command: string, cwd: string): Promise<Rerun> {
  const dir = mkdtempSync(join(tmpdir(), "harness-run-"))
  const file = join(dir, "out")
  // Output goes to a file, not a pipe: a child that outlives a timeout cannot hold the read open.
  const fd = openSync(file, "w")
  try {
    const p = Bun.spawn(["sh", "-c", command], { cwd, stdin: "ignore", stdout: fd, stderr: fd, timeout: TIMEOUT_MS, killSignal: "SIGKILL" })
    const code = await p.exited
    const timedOut = p.signalCode === "SIGKILL"
    closeSync(fd)
    const tail = lines(readFileSync(file, "utf8")).slice(-TAIL_LINES).join("\n")
    return { command, exit: timedOut ? 124 : (code ?? 1), tail: timedOut ? `${tail}\n[timed out after 10 minutes]`.trim() : tail }
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
}

function store(
  db: Database,
  o: VerifyOpts,
  head: string,
  verdict: Verdict,
  did: Record<string, any>,
  verified: Verified,
): Bundle {
  const id = ulid()
  const row = {
    head_sha: head,
    verdict,
    did_json: JSON.stringify(did),
    works_json: JSON.stringify({ claimed: o.claimed ?? null, ui_proof: o.uiProof ?? [] }),
    verified_json: JSON.stringify(verified),
    summary: o.summary ?? null,
    known_gaps: o.knownGaps ?? null,
  }
  const seq = db
    .transaction(() => {
      upsertSession(db, { id: o.session, tool: "unknown" })
      const seq = append(db, {
        session_id: o.session,
        event: "bundle",
        outcome: verdict,
        data: { bundleId: id, verdict, head_sha: head, digest: digestOf(row) },
      })
      db.query(
        `insert into bundles(id, worker_id, session_id, journal_seq, head_sha, did_json, works_json, verified_json, verdict, summary, known_gaps)
         values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      ).run(id, o.workerId ?? null, o.session, seq, head, row.did_json, row.works_json, row.verified_json, verdict, row.summary, row.known_gaps)
      return seq
    })
    .immediate()
  git(o.cwd, "-c", "user.name=harness", "-c", "user.email=harness@localhost", "notes", "--ref=harness", "add", "-f", "-m", `Verified: ${verdict} ${id}`, head)
  return {
    id,
    sessionId: o.session,
    workerId: o.workerId ?? null,
    journalSeq: seq,
    headSha: head,
    verdict,
    did,
    works: JSON.parse(row.works_json),
    verified,
    summary: row.summary,
    knownGaps: row.known_gaps,
  }
}

// A commit of the working tree on top of HEAD, built in a temporary index so the checkout, its index and
// its refs stay as they are. The commit is unreferenced; git prunes it later.
function snapshotCommit(cwd: string): string {
  const tmp = mkdtempSync(join(tmpdir(), "harness-snap-"))
  try {
    const env = {
      ...process.env,
      GIT_INDEX_FILE: join(tmp, "index"),
      GIT_AUTHOR_NAME: "harness",
      GIT_AUTHOR_EMAIL: "harness@localhost",
      GIT_COMMITTER_NAME: "harness",
      GIT_COMMITTER_EMAIL: "harness@localhost",
    }
    const run = (...args: string[]) => {
      const p = Bun.spawnSync(["git", ...args], { cwd, env, stdout: "pipe", stderr: "pipe" })
      if (p.exitCode !== 0) throw new Error(`git ${args.join(" ")} failed: ${p.stderr.toString().trim()}`)
      return p.stdout.toString().trim()
    }
    run("read-tree", "HEAD")
    run("add", "-A")
    const tree = run("write-tree")
    return run("commit-tree", tree, "-p", "HEAD", "-m", "harness snapshot of uncommitted work")
  } finally {
    rmSync(tmp, { recursive: true, force: true })
  }
}

const realOr = (p: string): string => {
  try {
    return realpathSync(p)
  } catch {
    return p
  }
}

export async function verify(db: Database, o: VerifyOpts): Promise<Bundle> {
  const base = o.baseSha
  if (base) gitOk(o.cwd, "rev-parse", "--verify", `${base}^{commit}`)
  const clean = gitOk(o.cwd, "status", "--porcelain").trim() === ""
  const snapshot = !clean && o.snapshot === true
  const head = snapshot ? snapshotCommit(o.cwd) : gitOk(o.cwd, "rev-parse", "HEAD").trim()

  const changed = base ? lines(gitOk(o.cwd, "diff", "--name-only", `${base}..${head}`)) : []
  const did: Record<string, any> = {
    base_sha: base ?? null,
    head_sha: head,
    commits: lines(gitOk(o.cwd, "log", "--format=%H %s", base ? `${base}..${head}` : "-1")),
    diff_stat: base ? gitOk(o.cwd, "diff", "--stat", `${base}..${head}`).trim() : "",
    test_hashes: {} as Record<string, { base: string | null; head: string | null }>,
    tests_changed: [] as string[],
    ...(snapshot ? { snapshot: true } : {}),
  }

  if (!clean && !snapshot) return store(db, o, head, "partial", did, { clean, reruns: [], verdict: "partial", reason: "uncommitted changes" })
  if (changed.length && changed.every((f) => f.endsWith(".md")))
    return store(db, o, head, "green", did, { clean, reruns: [], verdict: "green", reason: "docs only" })

  let restore: string[] = []
  if (base && o.testGlobs?.length) {
    restore = filesAt(o.cwd, base, o.testGlobs)
    const all = new Set([...restore, ...filesAt(o.cwd, head, o.testGlobs)])
    for (const f of [...all].sort()) {
      const h = { base: blob(o.cwd, base, f), head: blob(o.cwd, head, f) }
      did.test_hashes[f] = h
      if (h.base !== h.head) did.tests_changed.push(f)
    }
  }

  const tmp = mkdtempSync(join(tmpdir(), "harness-verify-"))
  const wt = join(tmp, "wt")
  const reruns: Rerun[] = []
  try {
    gitOk(o.cwd, "worktree", "add", "--detach", wt, head)
    if (base && restore.length) gitOk(wt, "checkout", base, "--", ...restore)
    linkDeps(o.cwd, wt)
    const commands = [...o.commands]
    const committed = repoVerify(wt)
    if (committed && !commands.includes(committed)) commands.push(committed)
    // A command that names the source folder (`cd <worktree> && bun test`) must run in this copy of the recorded sha,
    // not in the live folder, which may change while it runs (seen live 2026-11-28). Longest path first.
    const top = git(o.cwd, "rev-parse", "--show-toplevel").out.trim() || o.cwd
    const homes = [...new Set([top, realOr(top)])].sort((a, b) => b.length - a.length)
    const local = (c: string) => homes.reduce((s, h) => s.split(h).join(wt), c)
    for (const c of commands) reruns.push({ ...(await runCommand(local(c), wt)), command: c })
  } finally {
    git(o.cwd, "worktree", "remove", "--force", wt)
    rmSync(tmp, { recursive: true, force: true })
  }

  const verified: Verified = reruns.length
    ? { clean, reruns, verdict: reruns.every((r) => r.exit === 0) ? "green" : "red" }
    : { clean, reruns, verdict: "partial", reason: "no acceptance commands" }
  return store(db, o, head, verified.verdict, did, verified)
}

// The re-run worktree has only tracked files. Link the source checkout's installed
// dependencies (node_modules at the repo root and one level down) so acceptance
// commands that need them can run. Read-only use: the links point at the source.
function linkDeps(cwd: string, wt: string): void {
  const top = Bun.spawnSync(["git", "rev-parse", "--show-toplevel"], { cwd, stdout: "pipe", stderr: "ignore" })
  const root = top.exitCode === 0 ? top.stdout.toString().trim() : cwd
  const dirs = [root]
  try {
    for (const e of readdirSync(root, { withFileTypes: true })) if (e.isDirectory() && !e.name.startsWith(".") && e.name !== "node_modules") dirs.push(join(root, e.name))
  } catch {}
  for (const d of dirs) {
    const nm = join(d, "node_modules")
    const target = join(wt, relative(root, d), "node_modules")
    if (existsSync(nm) && existsSync(join(target, "..")) && !existsSync(target)) {
      try { symlinkSync(nm, target, "dir") } catch {}
    }
  }
}
