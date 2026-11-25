import { expect, test } from "bun:test"
import { join } from "node:path"

const root = join(import.meta.dir, "..")

function run(command: string) {
  const r = Bun.spawnSync([process.execPath, "guard-lite.ts"], {
    cwd: root,
    stdin: Buffer.from(JSON.stringify({ tool_name: "Bash", tool_input: { command }, cwd: "/tmp" })),
    stdout: "pipe",
    stderr: "pipe",
  })
  return { code: r.exitCode, out: r.stdout.toString() }
}

test("denies a recursive delete outside the allowlist", () => {
  const r = run("rm -rf /home/x/repo")
  expect(r.code).toBe(0)
  expect(JSON.parse(r.out)).toEqual({
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Recursive delete outside the allowlist. Name the exact files, or ask Alex.",
    },
  })
})

test("prints nothing for ls", () => {
  const r = run("ls")
  expect(r.code).toBe(0)
  expect(r.out).toBe("")
})
