// tool.before: agents may not reach the harness page (D61). They read state through the `harness_status` MCP tool.
// Only tool.before events come here, so the harness's own process and `harness serve` are never checked.
import { parse } from "../shell/parse.ts"
import { hit, isBrowseTool, type Env, type Out } from "./util.ts"

const RULE = "page-port"
const MESSAGE = "The harness page is Alex's. Agents read state through the `harness_status` MCP tool."

// Programs that open a TCP connection. `opencode api` is not in the list: it talks to OpenCode, not the page.
const CLIENTS = new Set([
  "curl", "wget", "nc", "ncat", "netcat", "socat", "telnet", "http", "https", "httpie", "xh",
  "bun", "node", "deno", "python", "python3", "ruby", "perl", "php",
])

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
    const client = parse(command).programs.some((p) => CLIENTS.has(p)) || command.includes("/dev/tcp/")
    return client && loopbackPort(command) ? hit(env, RULE, MESSAGE) : null
  }
  if (isBrowseTool(ev.toolName)) {
    return loopbackPort(JSON.stringify(ev.input ?? {})) ? hit(env, RULE, MESSAGE) : null
  }
  return null
}
