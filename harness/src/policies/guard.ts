// tool.before for shell, edit and write: the destructive, authority and path rules (Phase 1).
import { homedir } from "node:os"
import { checkShell } from "../shell/rules.ts"
import { checkPath } from "../shell/paths.ts"
import { shellCtx } from "../shell/ctx.ts"
import { mode } from "../ledger/registry.ts"
import { hit, allow, type Env, type Out } from "./util.ts"

const SHELL_RULES = ["recursive-delete", "merge-in-shell", "destructive-git", "harness-self", "ledger-write", "harness-config-write"]

// shellCtx runs 3 git calls. Cache per cwd for a few seconds: the OpenCode plugin lives for hours.
const CTX_TTL_MS = 5000
const ctxCache = new Map<string, { at: number; ctx: ReturnType<typeof shellCtx> }>()

export function ctxFor(cwd: string) {
  const c = ctxCache.get(cwd)
  if (c && Date.now() - c.at < CTX_TTL_MS) return c.ctx
  const ctx = shellCtx(cwd)
  ctxCache.set(cwd, { at: Date.now(), ctx })
  return ctx
}

export function repoOf(cwd: string): string | null {
  return ctxFor(cwd).repoRoot ?? null
}

export function guardShell(env: Env): Out | null {
  const i = env.ev.input ?? {}
  const command = String(i.command ?? "")
  if (!command.trim()) return null
  const cwd = String(i.cwd ?? env.ev.cwd)
  const ctx = ctxFor(cwd)
  const skipped: string[] = []
  let rules = SHELL_RULES
  while (rules.length) {
    const found = checkShell(command, { ...ctx, only: rules })
    if (!found) break
    if (mode(env.db, found.ruleId) === "off") {
      skipped.push(found.ruleId)
      rules = rules.filter((r) => r !== found.ruleId)
      continue
    }
    return hit(env, found.ruleId, found.message)
  }
  return skipped.length ? allow({ data: { skipped } }) : null
}

export function guardPath(env: Env): Out | null {
  const i = env.ev.input ?? {}
  const p = String(i.path ?? "")
  if (!p) return null
  const op = env.ev.toolName === "write" ? "write" : "edit"
  const found = checkPath(p, op, { home: process.env.HOME || homedir(), cwd: env.ev.cwd })
  return found ? hit(env, found.ruleId, found.message) : null
}
