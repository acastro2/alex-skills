// tool.before for shell and web-fetch tools: advise when something secret-shaped goes to a host outside the allowlist (D62).
// Advisory only: it never denies. The journal row is event egress.warning, which the egress view reads.
import { mode } from "../ledger/registry.ts"
import { parse } from "../shell/parse.ts"
import { toolKind } from "../turn.ts"
import type { Env, Out } from "./util.ts"

const RULE = "egress"

const ALLOW = ["github.com", "api.github.com", "*.atlassian.net", "opencode.ai", "*.opencode.ai", "context7.com", "*.context7.com"]
const LOOPBACK = /^(localhost|127(\.\d{1,3}){3}|::1|\[::1\]|0\.0\.0\.0|.*\.localhost)$/

const NET = new Set(["curl", "wget", "http", "https", "httpie", "xh", "nc", "ncat", "netcat", "scp", "rsync"])
const URL_HOST = /[a-z][a-z0-9+.-]*:\/\/(?:[^\s/@'"]*@)?(\[[^\]]+\]|[^\s/:?#'"]+)/gi

// shortcut: a fixed list of options that take a value, so `curl -o out.txt host` does not read out.txt as a host.
const VALUE_SHORT = /^-[oOHdXuAeFTbcwmxKErYyz]$/
const VALUE_LONG =
  /^--(output|output-dir|header|data(-\w+)?|post-data|post-file|body-data|request|user|user-agent|referer|form|upload-file|cookie|cookie-jar|write-out|max-time|proxy|config|cacert|cert|key|resolve|connect-timeout|retry)$/
const NC_VALUE = /^-[pwsiqWTxX]$/

const ENV_SECRET = /\$\{?\w*(TOKEN|SECRET|PASSW(?:OR)?D|CREDENTIAL|KEY)\w*/
const AUTH_HEADER = /\bauthorization["']?\s*[:=]/i
const DOTFILE_DATA = /(?:--(?:data(?:-binary|-raw|-ascii|-urlencode)?|form|post-file)|-d|-F)\s*=?\s*["']?(?:\w+=)?@(?:\S*\/)?\.[A-Za-z_][\w.-]*|(?:--upload-file|-T)\s*=?\s*["']?(?:\S*\/)?\.[A-Za-z_][\w.-]*/
const TOKEN_PREFIX = /\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-[A-Za-z0-9_-]{20,}|xox[abp]-[\w-]{10,}|AKIA[0-9A-Z]{16}|eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,})/
const LONG_WORD = /[A-Za-z0-9_-]{40,}/g

function tokenLike(text: string): boolean {
  if (TOKEN_PREFIX.test(text)) return true
  for (const w of text.match(LONG_WORD) ?? []) {
    // Mixed case plus a digit. A git hash (hex) or a lowercase slug is not a token.
    if (/[a-z]/.test(w) && /[A-Z]/.test(w) && /\d/.test(w)) return true
  }
  return false
}

// What kind of secret the text carries. Names only, never the value.
export function secretKinds(text: string): string[] {
  const kinds: string[] = []
  const env = ENV_SECRET.exec(text)
  if (env) kinds.push(`an env var (${env[0]})`)
  if (AUTH_HEADER.test(text)) kinds.push("an Authorization header")
  const dot = DOTFILE_DATA.exec(text)
  if (dot) kinds.push(`a dotfile (${/\.[A-Za-z_][\w.-]*\s*$/.exec(dot[0].trim())?.[0] ?? "dotfile"})`)
  if (tokenLike(text)) kinds.push("a token-like string")
  return kinds
}

function allowed(host: string): boolean {
  const h = host.toLowerCase()
  if (LOOPBACK.test(h)) return true
  const extra = (process.env.HARNESS_EGRESS_ALLOW ?? "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean)
  return [...ALLOW, ...extra].some((a) => (a.startsWith("*.") ? h.endsWith(a.slice(1)) : h === a))
}

const urlHosts = (text: string): string[] => [...text.matchAll(URL_HOST)].map((m) => m[1].toLowerCase())

function hostsOf(argv: string[]): string[] {
  const prog = argv[0]
  const args = argv.slice(1)
  if (prog === "gh") {
    if (args[0] !== "api") return []
    const i = args.findIndex((a) => a === "--hostname")
    const named = i >= 0 ? args[i + 1] : args.find((a) => a.startsWith("--hostname="))?.slice(11)
    const hosts = [...(named ? [named] : []), ...urlHosts(args.join(" "))]
    return hosts.length ? hosts : ["github.com"]
  }
  const urls = urlHosts(args.join(" "))
  if (urls.length) return urls
  const found: string[] = []
  if (prog === "nc" || prog === "ncat" || prog === "netcat") {
    for (let i = 0; i < args.length; i++) {
      if (NC_VALUE.test(args[i])) i++
      else if (!args[i].startsWith("-")) return [args[i]]
    }
    return found
  }
  if (prog === "scp" || prog === "rsync") {
    for (const a of args) {
      const m = /^(?:[^@\s/:]+@)?([A-Za-z0-9][A-Za-z0-9.-]*|\[[0-9a-f:]+\]):/i.exec(a)
      if (m && !a.startsWith("-")) found.push(m[1])
    }
    return found
  }
  for (let i = 0; i < args.length; i++) {
    const a = args[i]
    if (VALUE_SHORT.test(a) || VALUE_LONG.test(a)) i++
    else if (!a.startsWith("-") && /^(localhost|[\w-]+(\.[\w-]+)*\.[a-z]{2,})(:\d+)?(\/|$)/i.test(a)) found.push(a.replace(/[:/].*$/, ""))
  }
  return found
}

export function guardEgress(env: Env): Out | null {
  const { ev } = env
  let hosts: string[] = []
  let text = ""
  const kind = toolKind(ev.toolName)
  if (kind === "shell") {
    text = String(ev.input?.command ?? "")
    if (!text.trim()) return null
    const cmds = parse(text).commands.filter((c) => NET.has(c[0]) || (c[0] === "gh" && c[1] === "api"))
    if (!cmds.length) return null
    hosts = cmds.flatMap(hostsOf)
    if (!hosts.length) hosts = ["an unknown host"]
  } else if (kind === "fetch") {
    text = JSON.stringify(ev.input ?? {})
    hosts = urlHosts(text)
    if (!hosts.length) return null
  } else return null

  const outside = [...new Set(hosts)].filter((h) => h === "an unknown host" || !allowed(h))
  if (!outside.length) return null
  const kinds = secretKinds(text)
  if (!kinds.length) return null
  if (mode(env.db, RULE) === "off") return null

  const message = `Egress: this sends ${kinds.join(" and ")} to ${outside.join(", ")}. Check it is meant to leave the machine.`
  return {
    decision: { outcome: "allow", context: message, ruleId: RULE },
    event: "egress.warning",
    ruleId: RULE,
    outcome: "advise",
    reason: message,
    data: { hosts: outside, kinds },
  }
}
