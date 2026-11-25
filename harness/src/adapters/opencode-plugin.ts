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
  tool: { hook: (name: "execute.before" | "execute.after", fn: (e: any) => any) => Promise<unknown> }
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

    const owners = new Map<string, boolean>()
    async function ownsSession(sessionID: string): Promise<boolean> {
      const here = ctx.location?.directory
      if (!here) return true
      if (owners.has(sessionID)) return owners.get(sessionID)!
      let dir: string | undefined
      try {
        const info = await ctx.session.get({ sessionID })
        dir = info?.location?.directory ?? info?.directory
      } catch {}
      const mine = dir === undefined ? false : dir === here
      if (dir !== undefined) owners.set(sessionID, mine)
      return mine
    }

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

    async function ask(name: EventName, data: Record<string, unknown>, extra: Partial<HarnessEvent> = {}): Promise<Decision> {
      const sessionID = String(data.sessionID ?? "")
      const ev: HarnessEvent = { ...fromOpenCode(name, { cwd, ...data, parentSession: await parentOf(sessionID) }), ...extra }
      return withTimeout(decide(ev), DECIDE_TIMEOUT_MS)
    }

    // The permission event shows no arguments for subagent and MCP calls (seen live 2026-11-25), so their
    // rules run in execute.before below, which sees the real input.
    const argsHidden = (action: unknown) =>
      typeof action === "string" && !["shell", "edit", "write", "read", "patch"].includes(action)

    await ctx.permission.hook("evaluate", async (e: any) => {
      if (argsHidden(e.action)) return
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

    // The permission event carries no MCP arguments, so the session binding happens here (D29):
    // every call to the harness MCP server gets the caller's real session, whatever the model wrote.
    await ctx.tool.hook("execute.before", async (e: any) => {
      if (typeof e.tool !== "string" || !argsHidden(e.tool) || !e.sessionID) return
      const input = e.input && typeof e.input === "object" ? e.input : {}
      if (e.tool.startsWith("harness_")) {
        input.session = e.sessionID // in place, in case the host keeps its own reference
        e.input = input
      }
      let d: Decision
      try {
        d = await ask("tool.before", { sessionID: e.sessionID, tool: e.tool, input })
      } catch {
        return // fail open: only the destructive shell rules fail closed, and they run in evaluate
      }
      // OpenCode cannot change the input here; a thrown error stops the call and the agent reads the message.
      if (d.outcome === "deny") throw new Error(d.message ?? "Blocked by the harness.")
      if (d.outcome === "ask") throw new Error(d.message ? `${ASK_PREFIX} ${d.message}` : ASK_PREFIX)
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
          if (event?.type !== "session.execution.succeeded" && event?.type !== "session.compaction.ended") continue
          // One plugin instance loads per location: only the owner answers.
          if (event.location?.directory && event.location.directory !== ctx.location?.directory) continue
          const sessionID: string | undefined = event.data?.sessionID
          if (!sessionID) continue
          // Stop events carry no location, and every loaded instance sees every session on the service.
          // Answer only for sessions that live in this instance's location.
          if (!(await ownsSession(sessionID))) continue
          // A finished compaction (verified in the V2 OpenAPI event schemas: data.sessionID, reason auto|manual):
          // put the session state back from the ledger. There is no return channel here, so it goes in as synthetic text.
          if (event.type === "session.compaction.ended") {
            try {
              const d = await ask("session.start", { sessionID }, { input: { source: "compact" } })
              if (d.context) await ctx.session.synthetic({ sessionID, text: d.context })
            } catch {}
            continue
          }
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
