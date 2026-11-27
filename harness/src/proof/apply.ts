import type { Database } from "bun:sqlite"
import { createHash } from "node:crypto"
import { existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, readlinkSync, rmSync } from "node:fs"
import { homedir, tmpdir } from "node:os"
import { join } from "node:path"
import { consume, holds, requestApply } from "../ledger/authority.ts"
import { getMeta, setMeta } from "../ledger/db.ts"
import { append, upsertSession } from "../ledger/journal.ts"
import { ulid } from "../ledger/ulid.ts"
import { git } from "./verify.ts"

const EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
const sha256 = (b: Buffer | string) => createHash("sha256").update(b).digest("hex")

const stateDir = () => process.env.HARNESS_STATE_DIR ?? join(homedir(), ".local", "state", "harness")
export const appliedDir = (sha: string) => join(stateDir(), "applied", sha)

// Same algorithm as the inline copy in bin/harness-rollback, which must not depend on the code it restores.
export function treeHash(root: string): string {
  const entries: [string, string][] = []
  const walk = (dir: string, rel: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === "node_modules") continue
      const path = join(dir, e.name)
      const r = rel ? `${rel}/${e.name}` : e.name
      if (e.isDirectory()) walk(path, r)
      else entries.push([r, lstatSync(path).isSymbolicLink() ? sha256(`link:${readlinkSync(path)}`) : sha256(readFileSync(path))])
    }
  }
  walk(root, "")
  entries.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
  return sha256(entries.map(([r, h]) => `${r}\0${h}\n`).join(""))
}

function extract(repo: string, sha: string, dir: string): void {
  const a = Bun.spawnSync(["git", "archive", "--format=tar", sha, "harness"], { cwd: repo, stdout: "pipe", stderr: "pipe" })
  if (a.exitCode !== 0) throw new Error(`git archive failed: ${a.stderr.toString().trim()}`)
  mkdirSync(dir, { recursive: true })
  const t = Bun.spawnSync(["tar", "-x", "-C", dir], { stdin: a.stdout, stdout: "pipe", stderr: "pipe" })
  if (t.exitCode !== 0) throw new Error(`tar failed: ${t.stderr.toString().trim()}`)
}

// The review diffs against main. A sha that already sits on main shows its own change against its parent.
function mainBase(repo: string, sha: string): string {
  const ok = (rev: string) => git(repo, "rev-parse", "--verify", "--quiet", `${rev}^{commit}`).out.trim()
  for (const m of ["origin/HEAD", "origin/main", "origin/master", "main", "master"]) {
    const tip = ok(m)
    if (!tip) continue
    const mb = git(repo, "merge-base", sha, tip).out.trim()
    if (mb && mb !== sha) return mb
  }
  return ok(`${sha}^`) || EMPTY_TREE
}

function installArgs(): string[] {
  const a: string[] = []
  if (process.env.HARNESS_CLAUDE_SETTINGS) a.push("--claude-settings", process.env.HARNESS_CLAUDE_SETTINGS)
  if (process.env.HARNESS_OPENCODE_PLUGINS) a.push("--opencode-plugins", process.env.HARNESS_OPENCODE_PLUGINS)
  return a
}

function runInstall(dir: string, extra: string[] = []): { code: number; out: string } {
  const p = Bun.spawnSync([process.execPath, join(dir, "harness", "src", "install.ts"), ...extra, ...installArgs()], {
    stdout: "pipe",
    stderr: "pipe",
  })
  return { code: p.exitCode ?? 1, out: (p.stdout.toString() + p.stderr.toString()).trim() }
}

export interface RequestResult {
  requestId: string
  sha8: string
  digest8: string
  review: string
}

export function request(db: Database, o: { session: string; sha: string; cwd?: string }): RequestResult {
  if (!/^[0-9a-f]{40}$/.test(o.sha)) throw new Error("sha must be 40 lowercase hex characters")
  const cwd = o.cwd ?? process.cwd()
  const repo = git(cwd, "rev-parse", "--show-toplevel").out.trim()
  if (!repo) throw new Error(`not a git repository: ${cwd}`)
  if (git(repo, "cat-file", "-e", `${o.sha}^{commit}`).code !== 0) throw new Error(`unknown commit: ${o.sha}`)

  // Review against what is installed now: a diff against main alone hides every commit since the last apply.
  const cur = getMeta(db, "current_apply")
  const installed = cur ? (db.query("select sha from applies where id = ?").get(cur) as { sha: string } | null)?.sha : null
  const base = installed && git(repo, "merge-base", "--is-ancestor", installed, o.sha).code === 0 ? installed : mainBase(repo, o.sha)
  const range = `${base}..${o.sha}`
  const diff = git(repo, "diff", range, "--", "harness/").out.trim()
  const status = (path: string) =>
    git(repo, "diff", "--name-status", range, "--", path)
      .out.split("\n")
      .filter(Boolean)
  const tests = status("harness/tests").filter((l) => !l.startsWith("A"))
  const manifest = status("harness/src/manifest.ts")
  const registry = git(repo, "diff", "-U0", range, "--", "harness/src/ledger/registry.ts")
    .out.split("\n")
    .filter((l) => /^[+-](?![+-])/.test(l) && /rule\(|mode/.test(l))

  let dry: string
  const tmp = mkdtempSync(join(tmpdir(), "harness-review-"))
  try {
    extract(repo, o.sha, tmp)
    dry = existsSync(join(tmp, "harness", "src", "install.ts")) ? runInstall(tmp, ["--dry-run"]).out : "no harness/src/install.ts in this commit"
  } finally {
    rmSync(tmp, { recursive: true, force: true })
  }

  const list = (xs: string[]) => (xs.length ? xs.map((x) => `- ${x}`).join("\n") : "- none")
  const review = [
    `HARNESS REVIEW ${o.sha}`,
    `Base: ${base}`,
    "",
    "## Flags",
    "Changed or deleted test files:",
    list(tests),
    "Manifest changes (harness/src/manifest.ts):",
    list(manifest),
    "Rule mode changes (harness/src/ledger/registry.ts):",
    list(registry),
    "",
    "## Config entry diff (install.ts --dry-run)",
    dry || "no output",
    "",
    "## Diff (harness/)",
    diff || "no change under harness/",
    "",
  ].join("\n")

  const digest = sha256(review)
  const requestId = requestApply(db, { session: o.session, sha: o.sha, digest, review })
  setMeta(db, `request_repo:${requestId}`, repo)
  return { requestId, sha8: o.sha.slice(0, 8), digest8: digest.slice(0, 8), review }
}

export type ApplyResult = { ok: true; sha: string; applyId: string; dir: string } | { ok: false; reason: string }

export function apply(db: Database, o: { requestId: string; now?: number; cwd?: string }): ApplyResult {
  const now = o.now ?? Date.now()
  const req = db.query("select id, session_id, sha, state from requests where id = ?").get(o.requestId) as {
    id: string
    session_id: string | null
    sha: string
    state: string
  } | null
  if (!req) return { ok: false, reason: "unknown request" }
  if (req.state !== "open") return { ok: false, reason: `request is ${req.state}` }
  const tokenId = holds(db, { kind: "harness", session: req.session_id ?? "", requestId: req.id, now })
  if (!tokenId) return { ok: false, reason: "no HARNESS-OK grant for this request" }
  if (!consume(db, tokenId, now)) return { ok: false, reason: "grant already used or expired" }

  const fail = (reason: string): ApplyResult => {
    db.query("update requests set state = 'failed' where id = ?").run(req.id)
    append(db, { session_id: req.session_id, event: "harness.apply", outcome: "deny", reason, data: { request_id: req.id, sha: req.sha } })
    return { ok: false, reason }
  }

  const repo = o.cwd ?? getMeta(db, `request_repo:${req.id}`) ?? process.cwd()
  const dir = appliedDir(req.sha)
  try {
    rmSync(dir, { recursive: true, force: true })
    extract(repo, req.sha, dir)
  } catch (e) {
    return fail((e as Error).message)
  }
  const tree = treeHash(join(dir, "harness"))
  if (existsSync(join(dir, "harness", "bun.lock"))) {
    const i = Bun.spawnSync([process.execPath, "install", "--frozen-lockfile", "--ignore-scripts"], {
      cwd: join(dir, "harness"),
      stdout: "pipe",
      stderr: "pipe",
    })
    if (i.exitCode !== 0) return fail(`bun install failed: ${i.stderr.toString().trim()}`)
  }
  const ins = runInstall(dir)
  if (ins.code !== 0) return fail(`install.ts failed: ${ins.out}`)

  const applyId = ulid(now)
  db.transaction(() => {
    db.query("insert into applies(id, request_id, token_id, sha, tree_hash, schema_version, applied_at) values(?, ?, ?, ?, ?, ?, ?)").run(
      applyId,
      req.id,
      tokenId,
      req.sha,
      tree,
      Number(getMeta(db, "schema_version") ?? 0),
      now,
    )
    setMeta(db, "current_apply", applyId)
    db.query("update requests set state = 'applied' where id = ?").run(req.id)
    append(db, {
      session_id: req.session_id,
      event: "harness.apply",
      outcome: "allow",
      data: { request_id: req.id, sha: req.sha, tree_hash: tree, apply_id: applyId },
      time: now,
    })
  }).immediate()
  return { ok: true, sha: req.sha, applyId, dir }
}

export type RollbackResult = { ok: true; sha: string } | { ok: false; reason: string }

// Restores the previous applied SHA from applied/, after a tree-hash check.
export function rollback(db: Database, o: { session?: string; now?: number } = {}): RollbackResult {
  const now = o.now ?? Date.now()
  const curId = getMeta(db, "current_apply")
  if (!curId) return { ok: false, reason: "nothing applied" }
  const prev = db
    .query(
      `select id, sha, tree_hash from applies
       where rowid < (select rowid from applies where id = ?) and rolled_back_at is null
       order by rowid desc limit 1`,
    )
    .get(curId) as { id: string; sha: string; tree_hash: string } | null
  if (!prev) return { ok: false, reason: "no previous apply" }
  const dir = appliedDir(prev.sha)
  if (!existsSync(join(dir, "harness"))) return { ok: false, reason: `missing ${dir}` }
  if (treeHash(join(dir, "harness")) !== prev.tree_hash) return { ok: false, reason: "tree hash mismatch" }
  const ins = runInstall(dir)
  if (ins.code !== 0) return { ok: false, reason: `install.ts failed: ${ins.out}` }
  db.transaction(() => {
    if (o.session) upsertSession(db, { id: o.session, tool: "unknown" })
    db.query("update applies set rolled_back_at = ? where id = ?").run(now, curId)
    setMeta(db, "current_apply", prev.id)
    append(db, {
      session_id: o.session ?? null,
      event: "harness.rollback",
      outcome: "allow",
      data: { from_apply: curId, to_apply: prev.id, sha: prev.sha },
      time: now,
    })
  }).immediate()
  return { ok: true, sha: prev.sha }
}
