// The `harness` MCP server (D29, D34): typed tools for what an agent does on purpose.
// It offers tools only. Enforcement stays in the hooks, and the kill switch stays the ledger flag.
import type { Database } from "bun:sqlite"
import { existsSync } from "node:fs"
import { join } from "node:path"
import { Server } from "@modelcontextprotocol/sdk/server/index.js"
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js"
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js"
import { isOff } from "../ledger/authority.ts"
import { openLedger } from "../ledger/db.ts"
import { verifyChain } from "../ledger/journal.ts"
import { RULES, mode, seed } from "../ledger/registry.ts"
import { keepProcess, workstreamUpdate, worktreeNew } from "../worktree/lifecycle.ts"
import { mergePr } from "../worktree/merge.ts"

type Args = Record<string, unknown>
interface Ctx {
  db: Database
  session: string
}
interface Tool {
  name: string
  description: string
  inputSchema: Record<string, unknown>
  annotations: Record<string, boolean>
  run: (args: Args, ctx: Ctx) => unknown | Promise<unknown>
}

const sessionArg = { type: "string", description: "Session id. Optional: the harness uses HARNESS_SESSION when it is set." }
const schema = (properties: Record<string, unknown>, required: string[] = [], extra = false) => ({
  type: "object",
  properties: { ...properties, session: sessionArg },
  required,
  additionalProperties: extra,
})

function str(a: Args, k: string, req: true): string
function str(a: Args, k: string, req?: false): string | undefined
function str(a: Args, k: string, req = false): string | undefined {
  const v = a[k]
  if (v === undefined || v === null) {
    if (req) throw new Error(`missing argument: ${k}`)
    return undefined
  }
  if (typeof v !== "string" || (req && v === "")) throw new Error(`argument ${k} must be a${req ? " non-empty" : ""} string`)
  return v
}
function int(a: Args, k: string, req: true): number
function int(a: Args, k: string, req?: false): number | undefined
function int(a: Args, k: string, req = false): number | undefined {
  const v = a[k]
  if (v === undefined || v === null) {
    if (req) throw new Error(`missing argument: ${k}`)
    return undefined
  }
  if (typeof v !== "number" || !Number.isInteger(v)) throw new Error(`argument ${k} must be an integer`)
  return v
}
function strs(a: Args, k: string): string[] | undefined {
  const v = a[k]
  if (v === undefined || v === null) return undefined
  if (!Array.isArray(v) || v.some((x) => typeof x !== "string")) throw new Error(`argument ${k} must be an array of strings`)
  return v as string[]
}

// A sibling lane ships these modules later. Import one only when its file exists, so a real
// error inside it is not hidden behind "not shipped yet".
async function viaOptional(rel: string, fn: string, notYet: string, call: (f: (...a: unknown[]) => unknown) => unknown) {
  const file = join(import.meta.dir, "..", rel)
  if (!existsSync(file)) return { ok: false, message: notYet }
  const f = ((await import(file)) as Record<string, unknown>)[fn]
  if (typeof f !== "function") return { ok: false, message: `${rel} does not export ${fn}()` }
  return call(f as (...a: unknown[]) => unknown)
}

const TOOLS: Tool[] = [
  {
    name: "merge_pr",
    description:
      "Merge a pull request by rebase (never a merge commit). Needs Alex's one-time token: he types `MERGE-OK <pr>` as the first line of a prompt. Without it, the call fails and runs nothing.",
    inputSchema: schema(
      {
        repo: { type: "string", description: "owner/name, e.g. acastro2/alex-skills" },
        pr: { type: "integer", minimum: 1, description: "Pull request number" },
      },
      ["repo", "pr"],
    ),
    annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: true },
    run: (a, c) => mergePr(c.db, { session: c.session, repo: str(a, "repo", true), pr: int(a, "pr", true) }),
  },
  {
    name: "worktree_new",
    description:
      "Create your git worktree at ~/.worktrees/<repo>/<name> on a new branch <name>, based on origin/HEAD, and record it. Returns {id, path, branch}. Work in that path; never write in the main checkout.",
    inputSchema: schema(
      {
        name: { type: "string", description: "Branch and folder name: letters, digits, '.', '_', '-'" },
        repo_cwd: { type: "string", description: "Any path inside the repo. Defaults to the server's working directory." },
        workstream_id: { type: "string", description: "Attach to this workstream. Omit to start a new one." },
      },
      ["name"],
    ),
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
    run: (a, c) =>
      worktreeNew(c.db, {
        session: c.session,
        repoCwd: str(a, "repo_cwd") ?? process.cwd(),
        name: str(a, "name", true),
        workstreamId: str(a, "workstream_id"),
      }),
  },
  {
    name: "workstream_update",
    description:
      "Change your own workstream entry in the live handoff: title, state, and next steps. Add steps, mark steps done by id, or reorder them. Never edit HANDOFF.live.md by hand. Returns the entry with step ids.",
    inputSchema: schema({
      workstream_id: { type: "string", description: "Defaults to your latest open workstream, or a new one." },
      title: { type: "string" },
      state: { type: "string", description: "e.g. active, blocked, done. 'done' removes it from the live view." },
      steps: {
        type: "object",
        properties: {
          add: { type: "array", items: { type: "string" }, description: "New steps, appended in order" },
          done: { type: "array", items: { type: "string" }, description: "Step ids to mark done" },
          reorder: { type: "array", items: { type: "string" }, description: "Step ids in the new order; unlisted steps follow" },
        },
        additionalProperties: false,
      },
    }),
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
    run: (a, c) => {
      const s = a.steps as Args | undefined
      return workstreamUpdate(c.db, {
        session: c.session,
        workstreamId: str(a, "workstream_id"),
        title: str(a, "title"),
        state: str(a, "state"),
        steps: s ? { add: strs(s, "add"), done: strs(s, "done"), reorder: strs(s, "reorder") } : undefined,
      })
    },
  },
  {
    name: "keep_process",
    description:
      "Mark a process you started to survive session end (keep=true), or to be killed with it (keep=false). Use keep=true only for a server Alex asked to keep up, and name it in your reply.",
    inputSchema: schema(
      {
        pid: { type: "integer", minimum: 2 },
        keep: { type: "boolean" },
        command: { type: "string", description: "What it runs, for the handoff and the report" },
        port: { type: "integer", minimum: 1, maximum: 65535 },
      },
      ["pid", "keep"],
    ),
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    run: (a, c) => {
      if (typeof a.keep !== "boolean") throw new Error("argument keep must be a boolean")
      return keepProcess(c.db, { session: c.session, pid: int(a, "pid", true), keep: a.keep, command: str(a, "command"), port: int(a, "port") })
    },
  },
  {
    name: "harness_status",
    description:
      "Read the harness state: kill switch, mode of each rule, open grants, live sessions, and whether the journal hash chain is intact (chainOk).",
    inputSchema: schema({}),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    run: (_a, c) => {
      const chain = verifyChain(c.db)
      const count = (sql: string, ...p: number[]) => Number((c.db.query(sql).get(...p) as { n: number }).n)
      return {
        session: c.session,
        killSwitch: isOff(c.db),
        rules: Object.fromEntries(RULES.map((r) => [r.id, mode(c.db, r.id)])),
        openGrants: count("select count(*) as n from tokens where used_at is null and expires_at > ?", Date.now()),
        liveSessions: count("select count(*) as n from sessions where ended_at is null"),
        chainOk: chain.ok,
        ...(chain.ok ? {} : { badSeq: chain.badSeq }),
      }
    },
  },
  {
    name: "verify",
    description: "Run the acceptance commands in a directory and record the proof bundle. Ships in Phase 3.",
    inputSchema: schema({
      cwd: { type: "string", description: "Directory to run in. Defaults to the server's working directory." },
      commands: { type: "array", items: { type: "string" }, description: "Acceptance commands" },
    }),
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
    run: (a, c) =>
      viaOptional("proof/verify.ts", "verify", "verify ships in Phase 3", (f) =>
        f(c.db, { session: c.session, cwd: str(a, "cwd") ?? process.cwd(), commands: strs(a, "commands") ?? [] }),
      ),
  },
  {
    name: "harness_request",
    description: "Ask Alex to approve a change to the harness itself. Returns the request id and the rendered review he must approve.",
    inputSchema: schema(
      {
        sha: { type: "string", description: "Full 40-character commit sha to apply" },
        cwd: { type: "string", description: "Repo path. Defaults to the server's working directory." },
      },
      ["sha"],
    ),
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
    run: (a, c) => viaOptional("proof/apply.ts", "request", "harness_request ships in Phase 1b", (f) =>
        f(c.db, { session: c.session, sha: str(a, "sha", true), cwd: str(a, "cwd") }),
      ),
  },
  {
    name: "harness_apply",
    description: "Apply an approved harness change. Needs Alex's HARNESS-OK grant for that request.",
    inputSchema: schema(
      {
        request_id: { type: "string", description: "Id from harness_request" },
        cwd: { type: "string", description: "Repo path. Defaults to the server's working directory." },
      },
      ["request_id"],
    ),
    annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: false },
    run: (a, c) => viaOptional("proof/apply.ts", "apply", "harness_apply ships in Phase 1b", (f) =>
        f(c.db, { requestId: str(a, "request_id", true), cwd: str(a, "cwd") }),
      ),
  },
  {
    name: "jobs_status",
    description: "List the scheduled harness jobs with their last run and result. Ships with the jobs lane.",
    inputSchema: schema({}),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    run: () => viaOptional("jobs/jobs.ts", "status", "jobs_status ships with the jobs lane", (f) => f()),
  },
  {
    name: "job_run_now",
    description: "Run one scheduled harness job now, outside its schedule. Ships with the jobs lane.",
    inputSchema: schema({ name: { type: "string", description: "Job name from jobs_status" } }, ["name"]),
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
    run: (a) => viaOptional("jobs/jobs.ts", "runNow", "job_run_now ships with the jobs lane", (f) => f(str(a, "name", true))),
  },
]

export function createAgentServer(db: Database): Server {
  const server = new Server({ name: "harness", version: "1.0.0" }, { capabilities: { tools: {} } })

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOLS.map(({ run: _run, ...t }) => ({ ...t, title: t.name })),
  }))

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const tool = TOOLS.find((t) => t.name === req.params.name)
    if (!tool) return { isError: true, content: [{ type: "text", text: `unknown tool: ${req.params.name}` }] }
    const args = (req.params.arguments ?? {}) as Args
    try {
      // HARNESS_SESSION wins, so a model cannot name another session's id to borrow its token.
      const session = process.env.HARNESS_SESSION || str(args, "session") || server.getClientVersion()?.name || "unknown"
      const result = await tool.run(args, { db, session })
      const structured = (typeof result === "object" && result !== null ? result : { result }) as Record<string, unknown>
      return { content: [{ type: "text", text: JSON.stringify(structured, null, 2) }], structuredContent: structured }
    } catch (e) {
      return { isError: true, content: [{ type: "text", text: e instanceof Error ? e.message : String(e) }] }
    }
  })
  return server
}

if (import.meta.main) {
  const db = openLedger()
  seed(db)
  await createAgentServer(db).connect(new StdioServerTransport())
  console.error("harness MCP server running on stdio")
}
