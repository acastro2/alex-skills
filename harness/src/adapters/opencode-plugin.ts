// OpenCode V2 plugin. Hooks: permission evaluate (tool.before), execute.after (tool.after),
// session prompt, and the bus event session.execution.succeeded (stop).
import { decide } from "../core.ts"
import type { Decision, EventName, HarnessEvent } from "../types.ts"
import { DECIDE_TIMEOUT_MS, shellFailureCheck, withTimeout } from "./claude.ts"
import { fromOpenCode } from "./normalize.ts"

const ASK_PREFIX = "Ask Alex with the question tool, then retry."

// Only the parts of the V2 plugin context this plugin uses.
type Ctx = {
  location?: { directory?: string }
  permission: { hook: (name: "evaluate", fn: (e: any) => any) => Promise<unknown> }
  tool: { hook: (name: "execute.after", fn: (e: any) => any) => Promise<unknown> }
  session: {
    hook: (name: "prompt", fn: (e: any) => any) => Promise<unknown>
    get: (input: { sessionID: string }) => Promise<any>
    context: (input: { sessionID: string }) => Promise<any[]>
    synthetic: (input: { sessionID: string; text: string }) => Promise<unknown>
  }
  event: {
    subscribe: (options?: { signal?: AbortSignal }) => AsyncIterable<{ type?: string; location?: { directory?: string }; data?: any }>
  }
}

function lastAssistantText(messages: any[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]
    if (m?.type !== "assistant") continue
    const text = (m.content ?? [])
      .filter((p: any) => p?.type === "text" && p.text?.trim())
      .map((p: any) => p.text.trim())
      .join("\n\n")
    if (text) return text
  }
  return ""
}

export default {
  id: "harness",
  async setup(ctx: Ctx) {
    const controller = new AbortController()
    const cwd = ctx.location?.directory ?? process.cwd()
    const parents = new Map<string, string | null>()
    const sentBack = new Set<string>()

    async function parentOf(sessionID: string): Promise<string | null> {
      if (!sessionID) return null
      if (parents.has(sessionID)) return parents.get(sessionID)!
      let parent: string | null = null
      try {
        const info = await ctx.session.get({ sessionID })
        parent = info?.parentID ?? info?.parentSessionID ?? info?.parent?.id ?? null
      } catch {}
      parents.set(sessionID, parent)
      return parent
    }

    async function ask(name: EventName, data: Record<string, unknown>): Promise<Decision> {
      const sessionID = String(data.sessionID ?? "")
      const ev: HarnessEvent = fromOpenCode(name, { cwd, ...data, parentSession: await parentOf(sessionID) })
      return withTimeout(decide(ev), DECIDE_TIMEOUT_MS)
    }

    await ctx.permission.hook("evaluate", async (e: any) => {
      const resource = Array.isArray(e.resources) ? e.resources[0] : undefined
      const input =
        e.action === "shell"
          ? { command: resource }
          : ["edit", "write", "read"].includes(e.action)
            ? { filePath: resource }
            : { resources: e.resources }
      try {
        const d = await ask("tool.before", { sessionID: e.sessionID, tool: e.action, input })
        if (d.outcome === "deny") {
          e.effect = "deny"
          e.message = d.message ?? ""
        } else if (d.outcome === "ask") {
          e.effect = "deny"
          e.message = d.message ? `${ASK_PREFIX} ${d.message}` : ASK_PREFIX
        }
      } catch {
        if (e.action !== "shell" || typeof resource !== "string") return
        const msg = await shellFailureCheck(resource, cwd)
        if (msg !== null) {
          e.effect = "deny"
          e.message = msg
        }
      }
    })

    await ctx.tool.hook("execute.after", async (e: any) => {
      try {
        const d = await ask("tool.after", {
          sessionID: e.sessionID,
          tool: e.tool,
          input: e.input,
          result: e.result,
          status: e.status,
          error: e.error,
        })
        if (!d.context || !e.result) return
        if (!Array.isArray(e.result.content)) e.result.content = []
        e.result.content.push({ type: "text", text: d.context })
      } catch {}
    })

    await ctx.session.hook("prompt", async (e: any) => {
      try {
        const d = await ask("prompt", { sessionID: e.sessionID, prompt: e.prompt?.text ?? "" })
        if (d.context) await ctx.session.synthetic({ sessionID: e.sessionID, text: d.context })
      } catch {}
    })

    void (async () => {
      try {
        for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
          if (event?.type !== "session.execution.succeeded") continue
          // One plugin instance loads per location: only the owner answers.
          if (event.location?.directory && event.location.directory !== ctx.location?.directory) continue
          const sessionID: string | undefined = event.data?.sessionID
          if (!sessionID) continue
          try {
            let reply = ""
            try {
              reply = lastAssistantText(await ctx.session.context({ sessionID }))
            } catch {}
            const d = await ask("stop", { sessionID, reply, stopActive: sentBack.has(sessionID) })
            if (d.outcome === "deny" && d.message) {
              sentBack.add(sessionID)
              await ctx.session.synthetic({ sessionID, text: d.message })
            } else {
              sentBack.delete(sessionID)
            }
          } catch {}
        }
      } catch (error) {
        if (!controller.signal.aborted) console.error("[harness] event stream stopped", error)
      }
    })()

    return () => controller.abort()
  },
}
