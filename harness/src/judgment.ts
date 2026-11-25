// Judgment module (D52): one Jev call per decision point, a hard timeout, and a keyword fallback.
// Callers keep the thresholds (0.80) and journal `jev-unavailable` when any answer has source "fallback".
import { homedir } from "node:os"
import { join } from "node:path"

export interface Answer {
  value: number // noul: probability of yes
  source: "jev" | "fallback"
}
export interface Question {
  q: string
  fallback: (summary: string) => number
}

const DEFAULT_TIMEOUT_MS = 3000
const STATE_MAX = 1500

function jevPath(): string {
  return process.env.HARNESS_JEV_MCP ?? join(process.env.HOME || homedir(), ".config", "opencode", "bin", "jev-mcp")
}

// Minimal stdio MCP client: newline-delimited JSON-RPC, matched by id.
async function callJev(questions: Record<string, string>, state: string, deadline: number): Promise<Record<string, number>> {
  const child = Bun.spawn([jevPath()], { stdin: "pipe", stdout: "pipe", stderr: "ignore" })
  const left = () => Math.max(1, deadline - Date.now())
  const pending = new Map<number, (m: any) => void>()
  let buf = ""
  const pump = (async () => {
    const dec = new TextDecoder()
    for await (const chunk of child.stdout as unknown as AsyncIterable<Uint8Array>) {
      buf += dec.decode(chunk, { stream: true })
      let i: number
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim()
        buf = buf.slice(i + 1)
        try {
          const m = JSON.parse(line)
          pending.get(m.id)?.(m)
        } catch {}
      }
    }
  })()
  const send = (msg: object) => {
    child.stdin.write(JSON.stringify(msg) + "\n")
    child.stdin.flush()
  }
  let n = 0
  const rpc = (method: string, params: object) =>
    new Promise<any>((resolve, reject) => {
      const id = ++n
      const t = setTimeout(() => reject(new Error(`jev ${method} timed out`)), left())
      pending.set(id, (m) => {
        clearTimeout(t)
        m.error ? reject(new Error(m.error.message ?? "jev error")) : resolve(m.result)
      })
      send({ jsonrpc: "2.0", id, method, params })
    })
  try {
    await rpc("initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "harness", version: "1" } })
    send({ jsonrpc: "2.0", method: "notifications/initialized" })
    const tools = (await rpc("tools/list", {})).tools as { name: string }[]
    const tool = tools.find((t) => t.name === "ask_jev") ?? tools.find((t) => t.name.includes("ask_jev"))
    if (!tool) throw new Error("ask_jev not offered")
    const qs: Record<string, object> = {}
    for (const [id, q] of Object.entries(questions)) qs[id] = { type: "noul", instructions: `Judging \`state\`: ${q}` }
    const res = await rpc("tools/call", { name: tool.name, arguments: { state: state.slice(0, STATE_MAX), questions: qs } })
    if (res.isError) throw new Error(String(res.content?.[0]?.text ?? "jev failed").slice(0, 200))
    const answers = JSON.parse(res.content[0].text).answers as Record<string, { noul?: number }>
    const out: Record<string, number> = {}
    for (const id of Object.keys(questions)) {
      const v = answers?.[id]?.noul
      if (typeof v === "number" && v >= 0 && v <= 1) out[id] = v
    }
    return out
  } finally {
    try {
      child.kill()
    } catch {}
    void pump.catch(() => {})
  }
}

export async function judge(
  qs: Record<string, string> | Record<string, Question>,
  summary: string,
  opts: { timeoutMs?: number } = {},
): Promise<Record<string, Answer>> {
  const specs: Record<string, Question> = {}
  for (const [id, v] of Object.entries(qs)) specs[id] = typeof v === "string" ? { q: v, fallback: () => 0 } : v
  const ids = Object.keys(specs)
  const result: Record<string, Answer> = {}
  const fallback = (id: string) => (result[id] = { value: specs[id].fallback(summary), source: "fallback" })

  let jev: Record<string, number> = {}
  if (ids.length && process.env.HARNESS_JUDGE !== "fallback") {
    const deadline = Date.now() + (opts.timeoutMs ?? DEFAULT_TIMEOUT_MS)
    let timer: ReturnType<typeof setTimeout> | undefined
    try {
      jev = await Promise.race([
        callJev(Object.fromEntries(ids.map((id) => [id, specs[id].q])), summary, deadline),
        new Promise<never>((_, rej) => (timer = setTimeout(() => rej(new Error("jev timed out")), Math.max(1, deadline - Date.now())))),
      ])
    } catch {
      jev = {}
    } finally {
      clearTimeout(timer)
    }
  }
  for (const id of ids) {
    if (id in jev) result[id] = { value: jev[id], source: "jev" }
    else fallback(id)
  }
  return result
}
