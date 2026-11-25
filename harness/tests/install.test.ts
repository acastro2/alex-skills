import { beforeEach, describe, expect, test } from "bun:test"
import { existsSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { MANIFEST } from "../src/manifest.ts"

const ROOT = join(import.meta.dir, "..")

const ORIGINAL = {
  model: "opus",
  hooks: { Stop: [{ hooks: [{ type: "command", command: "echo other-stop" }] }] },
}

let dir: string
let settings: string
let plugins: string

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "harness-install-"))
  settings = join(dir, "settings.json")
  plugins = join(dir, "opencode", "plugins")
  writeFileSync(settings, JSON.stringify(ORIGINAL, null, 2) + "\n")
})

async function install(...flags: string[]) {
  const p = Bun.spawn(
    [process.execPath, "src/install.ts", ...flags, "--claude-settings", settings, "--opencode-plugins", plugins],
    { cwd: ROOT, stdout: "pipe", stderr: "pipe" },
  )
  const [stdout, stderr, code] = await Promise.all([new Response(p.stdout).text(), new Response(p.stderr).text(), p.exited])
  expect(code, stderr).toBe(0)
  return stdout
}

const read = () => JSON.parse(readFileSync(settings, "utf8"))
const harnessCommands = (s: any): string[] =>
  Object.values<any[]>(s.hooks).flatMap((groups) => groups.flatMap((g) => g.hooks.map((h: any) => h.command as string))).filter((c) => c.includes("--harness-id="))

describe("install", () => {
  test("adds every Claude manifest entry and keeps the other hook and key", async () => {
    await install()
    const s = read()
    expect(s.model).toBe("opus")
    expect(s.hooks.Stop[0]).toEqual(ORIGINAL.hooks.Stop[0])
    const claudeEntries = MANIFEST.filter((e) => e.tool === "claude")
    const cmds = harnessCommands(s)
    expect(cmds.length).toBe(claudeEntries.length)
    for (const e of claudeEntries) expect(cmds.some((c) => c.endsWith(`--harness-id=${e.id}`))).toBe(true)
    const guard = s.hooks.PreToolUse.find((g: any) => g.matcher === "Bash")
    expect(guard.hooks[0].command).toContain("guard-lite.ts")
    expect(s.hooks.PreToolUse.find((g: any) => g.matcher === "*").hooks[0].command).toContain("src/adapters/claude.ts tool.before")
  })

  test("a second install makes no change", async () => {
    await install()
    const before = readFileSync(settings, "utf8")
    const baks = readdirSync(dir).filter((f) => f.includes("harness-bak"))
    const out = await install()
    expect(readFileSync(settings, "utf8")).toBe(before)
    expect(readdirSync(dir).filter((f) => f.includes("harness-bak"))).toEqual(baks)
    expect(out).toContain("no change")
  })

  test("--dry-run prints a diff and writes nothing", async () => {
    const before = readFileSync(settings, "utf8")
    const out = await install("--dry-run")
    expect(readFileSync(settings, "utf8")).toBe(before)
    expect(existsSync(join(plugins, "harness.ts"))).toBe(false)
    expect(readdirSync(dir).filter((f) => f.includes("harness-bak"))).toEqual([])
    expect(out).toContain("+++")
    expect(out).toContain("--harness-id=claude-pre-tool")
  })

  test("writes a backup before the first change", async () => {
    await install()
    expect(readdirSync(dir).filter((f) => f.startsWith("settings.json.harness-bak-")).length).toBe(1)
  })

  test("writes the plugin file with an absolute re-export", async () => {
    await install()
    const text = readFileSync(join(plugins, "harness.ts"), "utf8")
    expect(text).toContain(JSON.stringify(join(ROOT, "src/adapters/opencode-plugin.ts")))
    expect(text).toContain("export { default } from")
  })

  test("--uninstall restores the original hooks and removes the plugin file", async () => {
    await install()
    await install("--uninstall")
    expect(read()).toEqual(ORIGINAL)
    expect(existsSync(join(plugins, "harness.ts"))).toBe(false)
  })

  // Seen live 2026-11-25: /fork-tab did not exist in OpenCode, because nothing linked the command files.
  test("links /fork-tab into both commands dirs, idempotently, and uninstall removes the links", async () => {
    const { readlinkSync, lstatSync } = await import("node:fs")
    await install()
    const cc = join(dir, "commands", "fork-tab.md") // next to the settings file
    const oc = join(dir, "opencode", "commands", "fork-tab.md")
    expect(lstatSync(cc).isSymbolicLink() && lstatSync(oc).isSymbolicLink()).toBe(true)
    expect(readFileSync(cc, "utf8")).toContain("--tool claude")
    expect(readFileSync(oc, "utf8")).toContain("--tool opencode")
    expect(await install()).toContain("no change: " + cc)
    await install("--uninstall")
    expect(existsSync(cc) || existsSync(oc)).toBe(false)
    void readlinkSync
  })
})
