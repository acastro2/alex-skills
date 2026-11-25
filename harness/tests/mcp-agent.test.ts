import { afterAll, beforeAll, expect, test } from "bun:test"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { Client } from "@modelcontextprotocol/sdk/client/index.js"
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js"

let dir: string
let client: Client

beforeAll(async () => {
  dir = mkdtempSync(join(tmpdir(), "harness-mcp-"))
  client = new Client({ name: "test-client", version: "1.0.0" })
  await client.connect(
    new StdioClientTransport({
      command: process.execPath,
      args: [join(import.meta.dir, "..", "src", "mcp", "agent.ts")],
      env: { HARNESS_STATE_DIR: dir, HARNESS_SESSION: "mcp-test", PATH: process.env.PATH ?? "" },
      stderr: "ignore",
    }),
  )
})

afterAll(async () => {
  await client.close()
  rmSync(dir, { recursive: true, force: true })
})

const call = async (name: string, args: Record<string, unknown> = {}) =>
  (await client.callTool({ name, arguments: args })) as { isError?: boolean; structuredContent?: Record<string, unknown>; content: { text: string }[] }

test("lists all 10 agent tools (D29)", async () => {
  const { tools } = await client.listTools()
  expect(tools.map((t) => t.name).sort()).toEqual(
    ["harness_apply", "harness_request", "harness_status", "job_run_now", "jobs_status", "keep_process", "merge_pr", "verify", "workstream_update", "worktree_new"].sort(),
  )
  for (const t of tools) expect(t.inputSchema.properties).toHaveProperty("session")
})

test("harness_status returns JSON with chainOk: true", async () => {
  const r = await call("harness_status")
  expect(r.isError).toBeFalsy()
  expect(JSON.parse(r.content[0].text).chainOk).toBe(true)
  expect(r.structuredContent).toMatchObject({ chainOk: true, killSwitch: false, session: "mcp-test", openGrants: 0 })
})

test("merge_pr without Alex's token fails with the MERGE-OK message", async () => {
  const r = await call("merge_pr", { repo: "o/r", pr: 7 })
  expect(r.structuredContent).toMatchObject({ ok: false })
  expect(String(r.structuredContent?.message)).toContain("MERGE-OK")
})

test("bad arguments come back as a tool error", async () => {
  const bad = await call("keep_process", { pid: 1, keep: true })
  expect(bad.isError).toBe(true)
  expect(bad.content[0].text).toContain("bad pid")
})
