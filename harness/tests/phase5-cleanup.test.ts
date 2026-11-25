// Phase 5 cleanup rules (D20, D22, D23, D38): process registration, stop-processes, session.end kill,
// stop-cleanup, stop-handoff-protocol, and the live handoff at session.start. Processes here are real.
import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import type { Database } from "bun:sqlite"
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { closeCore, decide } from "../src/core.ts"
import { openLedger } from "../src/ledger/db.ts"
import { keepProcess } from "../src/worktree/lifecycle.ts"
import type { HarnessEvent } from "../src/types.ts"

let dir: string
let db: Database
const spawned: { pid: number; kill: () => void }[] = []

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-p5-"))
  process.env.HARNESS_STATE_DIR = dir
  process.env.HARNESS_JUDGE = "fallback"
  delete process.env.HARNESS_DISABLE
  db = openLedger()
})

afterEach(() => {
  for (const p of spawned.splice(0)) p.kill()
  closeCore()
  db.close()
  delete process.env.HARNESS_STATE_DIR
  delete process.env.HARNESS_JUDGE
  delete process.env.HARNESS_SCRATCH_LIMIT_MB
  rmSync(dir, { recursive: true, force: true })
})

const ev = (over: Partial<HarnessEvent>): HarnessEvent => ({ v: 1, event: "tool.after", tool: "claude", session: "s1", parentSession: null, cwd: "/tmp", time: Date.now(), ...over })
const prompt = (session = "s1") => decide(ev({ event: "prompt", prompt: "go", session }))
const stop = (reply: string, session = "s1") => decide(ev({ event: "stop", reply, session }))
const end = (session = "s1") => decide(ev({ event: "session.end", session }))
const rows = (session = "s1") => db.query("select pid, port, keep, ended_at from processes where session_id = ?").all(session) as { pid: number; port: number | null; keep: number; ended_at: number | null }[]
// A killed child of this test stays a zombie until reaped, so read the process state, not kill -0.
const alive = (pid: number) => {
  const stat = Bun.spawnSync(["ps", "-o", "stat=", "-p", String(pid)], { stdout: "pipe" }).stdout.toString().trim()
  return stat !== "" && !stat.startsWith("Z")
}

// A real sleeper, reported the way `cmd & echo PID: $!` reports it.
function sleeper(): number {
  const p = Bun.spawn(["sleep", "300"], { stdio: ["ignore", "ignore", "ignore"] })
  spawned.push({ pid: p.pid, kill: () => p.kill("SIGKILL") })
  return p.pid
}
const registerSleeper = async (session = "s1") => {
  const pid = sleeper()
  await decide(ev({ session, toolName: "shell", input: { command: "sleep 300 & echo PID: $!", cwd: "/tmp" }, output: `PID: ${pid}` }))
  return pid
}
const gone = async (pid: number) => {
  for (let i = 0; i < 40 && alive(pid); i++) await Bun.sleep(50)
  return !alive(pid)
}

describe("processes", () => {
  test("a server found on its port is registered, and stop names it or is sent back", async () => {
    const probe = Bun.listen({ port: 0, hostname: "127.0.0.1", socket: { data() {} } })
    const port = probe.port
    probe.stop(true)
    const p = Bun.spawn(["python3", "-m", "http.server", String(port), "--bind", "127.0.0.1"], { stdio: ["ignore", "ignore", "ignore"] })
    spawned.push({ pid: p.pid, kill: () => p.kill("SIGKILL") })
    for (let i = 0; i < 60 && !(await fetch(`http://127.0.0.1:${port}/`).then(() => true, () => false)); i++) await Bun.sleep(50)

    await prompt()
    await decide(ev({ toolName: "shell", input: { command: `python3 -m http.server ${port} &`, cwd: "/tmp" }, output: "" }))
    expect(rows().map((r) => [r.pid, r.port])).toEqual([[p.pid, port]])

    const bad = await stop("Started it.")
    expect(bad.outcome).toBe("deny")
    expect(bad.ruleId).toBe("stop-processes")
    expect(bad.message).toContain(`PID ${p.pid}, port ${port}`)
    expect(bad.message).toContain("keep_process")

    expect((await stop(`The server on port ${port} stays up.`)).outcome).toBe("allow")
  })

  test("session.end kills an unkept process and keeps a kept one", async () => {
    await prompt()
    const gonePid = await registerSleeper()
    const keptPid = await registerSleeper()
    keepProcess(db, { session: "s1", pid: keptPid, keep: true })

    await end()
    expect(await gone(gonePid)).toBe(true)
    expect(alive(keptPid)).toBe(true)
    expect(rows().map((r) => [r.pid, r.ended_at !== null])).toEqual([[gonePid, true], [keptPid, false]])
    expect(db.query("select data_json from journal where event = 'process.killed'").all()).toHaveLength(1)
  })

  test("a kept process is reported once at the next session.start in the same repo", async () => {
    const repo = mkdtempSync(join(tmpdir(), "harness-p5-repo-"))
    Bun.spawnSync(["git", "init", "-q"], { cwd: repo })
    try {
      await decide(ev({ event: "session.start", cwd: repo }))
      await prompt()
      const pid = await registerSleeper()
      keepProcess(db, { session: "s1", pid, keep: true })
      await end()

      const first = await decide(ev({ event: "session.start", session: "s2", cwd: repo }))
      expect(first.context).toContain(`PID ${pid}`)
      const again = await decide(ev({ event: "session.start", session: "s3", cwd: repo }))
      expect(again.context ?? "").not.toContain(`PID ${pid}`)
    } finally {
      rmSync(repo, { recursive: true, force: true })
    }
  })

  test("a pid that now runs another command is not killed", async () => {
    await prompt()
    const pid = await registerSleeper()
    db.query("update journal set data_json = json_set(data_json, '$.cmdHash', 'other') where event = 'process.registered'").run()
    await end()
    expect(alive(pid)).toBe(true)
    expect(db.query("select 1 from journal where event = 'process.skipped'").all()).toHaveLength(1)
  })
})

describe("stop-cleanup", () => {
  test("sends back when scratch files written this session pass the limit", async () => {
    process.env.HARNESS_SCRATCH_LIMIT_MB = "1"
    const scratch = mkdtempSync(join(tmpdir(), "harness-p5-scratch-"))
    try {
      writeFileSync(join(scratch, "big.bin"), Buffer.alloc(2 * 1024 * 1024, 1))
      await prompt()
      await decide(ev({ toolName: "write", input: { path: join(scratch, "big.bin") }, output: "ok" }))
      const r = await stop("Wrote scratch.")
      expect(r.outcome).toBe("deny")
      expect(r.ruleId).toBe("stop-cleanup")
      expect(r.message).toContain("limit 1 MB")
    } finally {
      rmSync(scratch, { recursive: true, force: true })
    }
  })

  test("sends back when a removed worktree of this session is still on disk", async () => {
    const wt = mkdtempSync(join(tmpdir(), "harness-p5-wt-"))
    try {
      await prompt()
      db.query("insert into worktrees(id, session_id, repo, path, branch, state, created_at) values('w1', 's1', '/r', ?, 'b', 'removed', 1)").run(wt)
      const r = await stop("Landed.")
      expect(r.ruleId).toBe("stop-cleanup")
      expect(r.message).toContain(wt)
    } finally {
      rmSync(wt, { recursive: true, force: true })
    }
  })
})

describe("stop-handoff-protocol", () => {
  const repoWith = (handoff: string) => {
    const repo = mkdtempSync(join(tmpdir(), "harness-p5-hand-"))
    const run = (...a: string[]) => Bun.spawnSync(["git", ...a], { cwd: repo, stdout: "pipe", stderr: "pipe" })
    run("init", "-q")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    run("config", "commit.gpgsign", "false")
    mkdirSync(join(repo, "docs"))
    writeFileSync(join(repo, "docs", "HANDOFF.md"), handoff)
    run("add", ".")
    run("commit", "-q", "-m", "init")
    return { repo, file: join(repo, "docs", "HANDOFF.md"), run }
  }
  const edit = (file: string) => decide(ev({ toolName: "edit", input: { path: file }, output: "ok" }))

  test("sends back an edited committed HANDOFF.md over 150 lines", async () => {
    const { repo, file, run } = repoWith(Array.from({ length: 151 }, (_, i) => `line ${i}`).join("\n") + "\n")
    try {
      await prompt()
      await edit(file)
      run("commit", "-qam", "touch")
      const r = await stop("Edited the handoff.")
      expect(r.ruleId).toBe("stop-handoff-protocol")
      expect(r.message).toContain("workstream_update")
    } finally {
      rmSync(repo, { recursive: true, force: true })
    }
  })

  test("sends back a running process entry with a PID, passes a short file with lasting text", async () => {
    const { repo, file, run } = repoWith("# Handoff\n\nGotcha: run bun test.\n")
    try {
      await prompt()
      writeFileSync(file, "# Handoff\n\nGotcha: run bun test.\n\n## Running processes\n- pid 4242: bun serve\n")
      await edit(file)
      run("commit", "-qam", "live")
      const bad = await stop("Edited the handoff.")
      expect(bad.ruleId).toBe("stop-handoff-protocol")

      await prompt()
      writeFileSync(file, "# Handoff\n\nGotcha: run bun test.\nGotcha: ss needs a port.\n")
      await edit(file)
      run("commit", "-qam", "lasting")
      expect((await stop("Edited the handoff.")).outcome).toBe("allow")
    } finally {
      rmSync(repo, { recursive: true, force: true })
    }
  })
})
