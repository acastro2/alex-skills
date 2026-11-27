// Writes the harness hook entries (manifest.ts) into Claude Code settings and the OpenCode plugin dir.
// Usage: bun src/install.ts [--dry-run] [--dev] [--uninstall] [--claude-settings <path>] [--opencode-plugins <dir>] [--bun <path>]
//        [--no-mcp] [--mcp-project <dir>]
import { existsSync, mkdirSync, readFileSync, readlinkSync, realpathSync, rmSync, symlinkSync, writeFileSync, copyFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join, resolve } from "node:path"
import { HARNESS_ID_FLAG, MANIFEST, type ManifestEntry } from "./manifest.ts"

type Json = Record<string, any>

export interface Options {
  dryRun: boolean
  uninstall: boolean
  claudeSettings: string
  opencodePlugins: string
  bun: string
  root: string
  mcp: boolean // register the `harness` MCP server (agent tools) through each tool's own CLI
  mcpProject: string | null // null = user/global scope; a dir = that project only (scratch tests)
}

const ROOT = resolve(dirname(import.meta.path), "..")

function shellQuote(s: string): string {
  return /^[\w@%+=:,./-]+$/.test(s) ? s : `'${s.replace(/'/g, `'\\''`)}'`
}

export function commandFor(entry: ManifestEntry, bun: string, root: string): string {
  const parts = (entry.command ?? []).map((p) => p.replace("{bun}", bun).replace("{root}", root))
  return [...parts.map(shellQuote), `${HARNESS_ID_FLAG}${entry.id}`].join(" ")
}

function harnessId(hook: any): string | null {
  const m = typeof hook?.command === "string" ? new RegExp(`(?:^|\\s)${HARNESS_ID_FLAG}(\\S+)`).exec(hook.command) : null
  return m ? m[1] : null
}

function desiredGroup(entry: ManifestEntry, bun: string, root: string): Json {
  return {
    ...(entry.matcher ? { matcher: entry.matcher } : {}),
    hooks: [{ type: "command", command: commandFor(entry, bun, root) }],
  }
}

/** Return settings with exactly the wanted harness hooks; every other key and hook is untouched. */
export function applyHooks(current: Json, entries: ManifestEntry[], bun: string, root: string): Json {
  const next: Json = structuredClone(current)
  const wanted = new Map(entries.filter((e) => e.tool === "claude").map((e) => [e.id, e]))
  const placed = new Set<string>()
  const hadHooks = next.hooks !== undefined
  const hooks: Json = (next.hooks ??= {})

  for (const event of Object.keys(hooks)) {
    const groups: any[] = hooks[event]
    if (!Array.isArray(groups)) continue
    const kept: any[] = []
    for (const group of groups) {
      const list: any[] = Array.isArray(group?.hooks) ? group.hooks : []
      const ids = list.map(harnessId)
      if (!ids.some((id) => id !== null)) {
        kept.push(group)
        continue
      }
      const id = ids[0]
      const entry = id ? wanted.get(id) : undefined
      if (list.length === 1 && id && entry && entry.event === event && !placed.has(id)) {
        kept.push(desiredGroup(entry, bun, root)) // same slot, so a re-run changes nothing
        placed.add(id)
        continue
      }
      const others = list.filter((h) => harnessId(h) === null)
      if (others.length) kept.push({ ...group, hooks: others })
    }
    hooks[event] = kept
  }
  for (const entry of wanted.values()) {
    if (placed.has(entry.id)) continue
    ;(hooks[entry.event] ??= []).push(desiredGroup(entry, bun, root))
  }
  // Drop event arrays that stripping emptied. An array that was already empty stays.
  for (const event of Object.keys(hooks)) {
    const was = current.hooks?.[event]
    if (Array.isArray(hooks[event]) && hooks[event].length === 0 && !(Array.isArray(was) && was.length === 0)) delete hooks[event]
  }
  const wasEmptyObject = hadHooks && Object.keys(current.hooks).length === 0
  if (Object.keys(hooks).length === 0 && !wasEmptyObject) delete next.hooks
  return next
}

export function pluginSource(root: string): string {
  return `// Installed by harness/src/install.ts. Do not edit.\nexport { default } from ${JSON.stringify(join(root, "src/adapters/opencode-plugin.ts"))}\n`
}

/** Unified-style line diff with 3 lines of context. Empty string when equal. */
export function unifiedDiff(a: string, b: string, name: string): string {
  if (a === b) return ""
  const x = a === "" ? [] : a.replace(/\n$/, "").split("\n")
  const y = b === "" ? [] : b.replace(/\n$/, "").split("\n")
  const lcs = Array.from({ length: x.length + 1 }, () => new Array<number>(y.length + 1).fill(0))
  for (let i = x.length - 1; i >= 0; i--)
    for (let j = y.length - 1; j >= 0; j--)
      lcs[i][j] = x[i] === y[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1])
  const ops: { t: " " | "+" | "-"; s: string }[] = []
  let i = 0
  let j = 0
  while (i < x.length || j < y.length) {
    if (i < x.length && j < y.length && x[i] === y[j]) {
      ops.push({ t: " ", s: x[i] })
      i++
      j++
    } else if (j < y.length && (i === x.length || lcs[i][j + 1] >= lcs[i + 1][j])) ops.push({ t: "+", s: y[j++] })
    else ops.push({ t: "-", s: x[i++] })
  }
  const show = ops.map((o, k) => o.t !== " " || ops.slice(Math.max(0, k - 3), k + 4).some((p) => p.t !== " "))
  const out = [`--- ${a === "" ? "/dev/null" : name}`, `+++ ${b === "" ? "/dev/null" : name}`]
  let gap = false
  ops.forEach((o, k) => {
    if (!show[k]) return (gap = true), undefined
    if (gap) out.push("@@")
    gap = false
    out.push(o.t + o.s)
  })
  return out.join("\n")
}

function readText(path: string): string {
  return existsSync(path) ? readFileSync(path, "utf8") : ""
}

/** Same rule as src/ledger/db.ts. */
function stateDir(): string {
  return process.env.HARNESS_STATE_DIR ?? join(homedir(), ".local", "state", "harness")
}

/**
 * Hooks run `<stateDir>/bin/bun`, a symlink to the real binary. A versioned path (mise, brew) vanishes on upgrade,
 * the hook exits 127, Claude Code treats that as non-blocking, and every guard turns off silently.
 */
function ensureStableBun(opts: Options): { stable: string; line: string } {
  const stable = join(stateDir(), "bin", "bun")
  let target: string
  try {
    target = realpathSync(opts.bun) // follows the stable link too, so a self-loop cannot form
  } catch {
    return { stable, line: `warning: --bun ${opts.bun} does not resolve; stable bun link left as is` }
  }
  let current: string | null = null
  try {
    current = readlinkSync(stable)
  } catch {}
  if (current === target) return { stable, line: `no change: ${stable}` }
  if (opts.dryRun) return { stable, line: `would link: ${stable} -> ${target}` }
  mkdirSync(dirname(stable), { recursive: true })
  rmSync(stable, { force: true })
  symlinkSync(target, stable)
  return { stable, line: `linked: ${stable} -> ${target}` }
}

export function run(inOpts: Options): { report: string; changed: boolean } {
  const lines: string[] = []
  let changed = false
  const stable = join(stateDir(), "bin", "bun")
  const opts: Options = { ...inOpts, bun: stable }
  if (!inOpts.uninstall) {
    const line = ensureStableBun(inOpts).line // uninstall leaves the link alone
    lines.push(line)
    if (/^(linked|would link):/.test(line)) changed = true
  }

  // Claude settings
  const oldText = readText(opts.claudeSettings)
  let current: Json = {}
  if (oldText.trim()) {
    try {
      current = JSON.parse(oldText)
    } catch (e) {
      throw new Error(`${opts.claudeSettings} is not valid JSON: ${(e as Error).message}`)
    }
  }
  const entries = opts.uninstall ? [] : MANIFEST
  const next = applyHooks(current, entries, opts.bun, opts.root)
  const settingsChanged = JSON.stringify(next) !== JSON.stringify(current)
  if (settingsChanged) {
    changed = true
    const newText = JSON.stringify(next, null, 2) + "\n"
    if (opts.dryRun) lines.push(unifiedDiff(oldText === "" ? "" : JSON.stringify(current, null, 2) + "\n", newText, opts.claudeSettings))
    else {
      mkdirSync(dirname(opts.claudeSettings), { recursive: true })
      if (existsSync(opts.claudeSettings)) {
        const bak = `${opts.claudeSettings}.harness-bak-${Date.now()}`
        copyFileSync(opts.claudeSettings, bak)
        lines.push(`backup: ${bak}`)
      }
      writeFileSync(opts.claudeSettings, newText)
      lines.push(`wrote: ${opts.claudeSettings}`)
    }
  } else lines.push(`no change: ${opts.claudeSettings}`)

  // OpenCode plugin
  const pluginPath = join(opts.opencodePlugins, "harness.ts")
  const hasPlugin = MANIFEST.some((e) => e.tool === "opencode" && e.transport === "plugin")
  const oldPlugin = readText(pluginPath)
  const newPlugin = opts.uninstall || !hasPlugin ? "" : pluginSource(opts.root)
  if (oldPlugin !== newPlugin) {
    changed = true
    if (opts.dryRun) lines.push(unifiedDiff(oldPlugin, newPlugin, pluginPath))
    else if (newPlugin === "") {
      rmSync(pluginPath, { force: true })
      lines.push(`removed: ${pluginPath}`)
    } else {
      mkdirSync(opts.opencodePlugins, { recursive: true })
      writeFileSync(pluginPath, newPlugin)
      lines.push(`wrote: ${pluginPath}`)
    }
  } else lines.push(`no change: ${pluginPath}`)

  if (opts.mcp) for (const l of mcpSteps(opts)) lines.push(l), (changed ||= l.startsWith("ran:") || l.startsWith("would run:"))

  return { report: lines.join("\n"), changed }
}

type Runner = (argv: string[], cwd?: string) => { code: number; out: string }
const sh: Runner = (argv, cwd) => {
  try {
    const r = Bun.spawnSync(argv, { cwd, stdout: "pipe", stderr: "pipe" })
    return { code: r.exitCode ?? 1, out: (r.stdout.toString() + r.stderr.toString()).trim() }
  } catch (e) {
    return { code: 127, out: (e as Error).message }
  }
}

/** The commands that register (or remove) the agent MCP server. Each CLI owns its config file. */
export function mcpCommands(opts: Options): { tool: string; check: string[]; add: string[]; remove: string[]; cwd?: string }[] {
  const server = [opts.bun, join(opts.root, "src/mcp/agent.ts")]
  const cwd = opts.mcpProject ?? undefined
  const ccScope = opts.mcpProject ? "local" : "user"
  return [
    {
      tool: "claude",
      cwd,
      check: ["claude", "mcp", "get", "harness"],
      add: ["claude", "mcp", "add-json", "-s", ccScope, "harness", JSON.stringify({ type: "stdio", command: server[0], args: server.slice(1) })],
      remove: ["claude", "mcp", "remove", "-s", ccScope, "harness"],
    },
    {
      tool: "opencode",
      cwd,
      check: ["opencode", "mcp", "list"],
      add: ["opencode", "mcp", "add", ...(opts.mcpProject ? [] : ["--global"]), "harness", "--", ...server],
      remove: [], // opencode has no `mcp remove`; uninstall prints the manual step
    },
  ]
}

export function mcpSteps(opts: Options, run: Runner = sh): string[] {
  const out: string[] = []
  for (const c of mcpCommands(opts)) {
    const have = run(c.check, c.cwd)
    const present = c.tool === "claude" ? have.code === 0 : /\bharness\b/.test(have.out)
    if (opts.uninstall) {
      if (!present) out.push(`no change: ${c.tool} mcp harness`)
      else if (!c.remove.length) out.push(`manual: remove the "harness" entry under "mcp" in the ${c.tool} config`)
      else if (opts.dryRun) out.push(`would run: ${c.remove.join(" ")}`)
      else out.push(run(c.remove, c.cwd).code === 0 ? `ran: ${c.remove.join(" ")}` : `failed: ${c.remove.join(" ")}`)
      continue
    }
    if (present) out.push(`no change: ${c.tool} mcp harness`)
    else if (opts.dryRun) out.push(`would run: ${c.add.join(" ")}`)
    else {
      const r = run(c.add, c.cwd)
      out.push(r.code === 0 ? `ran: ${c.add.join(" ")}` : `failed (${r.code}): ${c.add.join(" ")}: ${r.out.slice(0, 200)}`)
    }
  }
  return out
}

export function parseArgs(argv: string[]): Options {
  const o: Options = {
    dryRun: false,
    uninstall: false,
    claudeSettings: join(homedir(), ".claude/settings.json"),
    opencodePlugins: join(homedir(), ".config/opencode/plugins"),
    bun: process.execPath,
    root: ROOT,
    mcp: true,
    mcpProject: null,
  }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    const val = () => {
      const v = argv[++i]
      if (v === undefined) throw new Error(`${a} needs a value`)
      return resolve(v)
    }
    if (a === "--dry-run") o.dryRun = true
    else if (a === "--uninstall") o.uninstall = true
    else if (a === "--dev") {
      // shortcut: --dev and the default both install from this working tree; the applied-SHA path (D71) comes later.
    } else if (a === "--claude-settings") o.claudeSettings = val()
    else if (a === "--opencode-plugins") o.opencodePlugins = val()
    else if (a === "--bun") o.bun = val()
    else if (a === "--no-mcp") o.mcp = false
    else if (a === "--mcp-project") o.mcpProject = val()
    else throw new Error(`unknown argument: ${a}`)
  }
  // A custom settings or plugin path means a test or scratch install: never touch the real MCP config
  // unless the caller names a project dir for it.
  const custom = argv.includes("--claude-settings") || argv.includes("--opencode-plugins")
  if (custom && !o.mcpProject) o.mcp = false
  if (process.env.HARNESS_NO_MCP) o.mcp = false
  return o
}

if (import.meta.main) {
  try {
    const { report } = run(parseArgs(process.argv.slice(2)))
    console.log(report)
  } catch (e) {
    console.error((e as Error).message)
    process.exit(1)
  }
}
