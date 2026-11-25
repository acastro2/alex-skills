// tool.before on subagent calls: the spawn rules and the worker contract (D17, Phase 3 "Spawn").
import { mode } from "../ledger/registry.ts"
import { hit, type Env, type Out } from "./util.ts"

export const CONTRACT_MARKER = "HARNESS-CONTRACT v1"

export const CONTRACT = [
  CONTRACT_MARKER,
  "- Load the `coding` skill first.",
  "- No git writes (add, commit, checkout, branch, stash, reset) outside your own worktree.",
  "- If a test looks wrong, flag it. Do not edit it.",
  "- End your reply with SUMMARY: and KNOWN_GAPS: sections.",
].join("\n")

export const isGeneral = (agent: unknown) => agent === "general" || agent === "general-purpose"

export function guardSpawn(env: Env): Out | null {
  const i = env.ev.input ?? {}
  // A follow-up to a running worker (sessionID set) steers it; it is not a new spawn.
  if (typeof i.sessionID === "string" && i.sessionID) return null
  const prompt = String(i.prompt ?? "")
  const model = i.model

  if (typeof model !== "string" || !model.trim()) {
    const o = hit(env, "spawn-model", "Set `model`, see AGENTS.md Execution.")
    if (o) return o
  }
  if (!isGeneral(i.agent)) return null

  if (!/^ACCEPTANCE:/m.test(prompt)) {
    const o = hit(env, "spawn-acceptance", "Add an ACCEPTANCE: block with the exact commands that prove the work.")
    if (o) return o
  }
  if (mode(env.db, "spawn-acceptance") === "off" || prompt.includes(CONTRACT_MARKER)) return null

  if (env.ev.tool === "claude") {
    return {
      decision: { outcome: "modify", input: { ...i, prompt: `${prompt.trimEnd()}\n\n${CONTRACT}` }, ruleId: "spawn-acceptance" },
      ruleId: "spawn-acceptance",
      reason: "worker contract appended",
    }
  }
  // OpenCode cannot change the input (Phase 0), so the deny message carries the contract.
  return hit(env, "spawn-acceptance", `Add this worker contract to the prompt, then retry:\n${CONTRACT}`)
}
