// tool.before: agents may not reach the harness page (D61). They read state through the `harness_status` MCP tool.
// Only tool.before events come here, so the harness's own process and `harness serve` are never checked.
import { parse } from "../shell/parse.ts"
import { hit, isBrowseTool, type Env, type Out } from "./util.ts"

const RULE = "page-port"
const MESSAGE = "The harness page is Alex's. Agents read state through the `harness_status` MCP tool."

// Programs that open a TCP connection. `opencode api` is not in the list: it talks to OpenCode, not the page.
const CLIENTS = new Set(["curl", "wget", "nc", "ncat", "netcat", "socat", "telnet", "http", "https", "httpie", "xh"])
// An interpreter counts only when its code makes a network call. A script that merely contains the
// page's URL as text (an edit to a doc) is not a connection (seen live 2026-11-25).
const INTERPRETERS = new Set(["bun", "node", "deno", "python", "python3", "ruby", "perl", "php"])
const NET_CALL = /fetch\(|urlopen|urllib\.request|requests\.|http\.client|httpx|aiohttp|socket\.|net\.connect|http\.get|https\.get|Net::HTTP|open-uri|IO::Socket|LWP|file_get_contents\(\s*['"]https?:|Bun\.connect|WebSocket/

const READ_ONLY_BROWSE = new Set(["navigate", "snapshot", "screenshot", "screenshot_diff", "wait_for", "scroll", "emulate", "tabs", "status"])

const ports = (): string[] => [...new Set([process.env.HARNESS_PORT?.trim() || "", "4317", "4316"].filter((p) => /^\d+$/.test(p)))]

// A loopback host followed by the port: a URL, `host:port`, `nc host port` or /dev/tcp/host/port.
function loopbackPort(text: string): boolean {
  const re = new RegExp(`(?:localhost|127(?:\\.\\d{1,3}){3}|\\[?::1\\]?|0\\.0\\.0\\.0)[:/ \\t]+(?:${ports().join("|")})(?!\\d)`, "i")
  return re.test(text)
}

export function guardPagePort(env: Env): Out | null {
  const { ev } = env
  if (ev.toolName === "shell") {
    const command = String(ev.input?.command ?? "")
    if (!command.trim()) return null
    // shortcut: the whole line is tested once a client program or /dev/tcp shows up. No per-argument parsing.
    const progs = parse(command).programs
    const client = progs.some((p) => CLIENTS.has(p)) || command.includes("/dev/tcp/") ||
      (progs.some((p) => INTERPRETERS.has(p)) && NET_CALL.test(command))
    return client && loopbackPort(command) ? hit(env, RULE, MESSAGE) : null
  }
  if (isBrowseTool(ev.toolName)) {
    // Looking is allowed: an agent must screenshot its own UI work (stop-ui-proof). Acting is not: a
    // click, fill or eval on Alex's signed-in tab is Alex's. Every grant still needs his fresh passkey tap.
    const name = String(ev.toolName).replace(/^mcp:browse:|^browse_/, "")
    if (READ_ONLY_BROWSE.has(name)) return null
    return loopbackPort(JSON.stringify(ev.input ?? {})) ? hit(env, RULE, MESSAGE) : null
  }
  return null
}
