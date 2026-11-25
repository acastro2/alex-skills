// Shell line parser for the guard rules. Pure, never throws.
// It is a scanner, not a full shell: it splits a line into simple commands, walks
// substitutions and `bash -c` style wrappers, and reports redirect targets.
// shortcut: heredoc bodies are code only when a shell reads them; no variable expansion (except ${IFS}),
// no aliases or functions. `cd` is tracked within one line; `cd -`, `popd` and `cd $X` make the cwd unknown.

// The `cd` arguments applied so far, in order. null means a directory we cannot resolve.
export type Dirs = ReadonlyArray<string | null>

export interface Parsed {
  commands: string[][] // simple commands, wrappers unwrapped, program basenamed
  programs: string[] // every program seen, wrappers included (sudo, env, bash...)
  redirects: string[] // targets of >, >>, >|, &>, N>
  dirs: Dirs[] // the cd chain in force for each command, parallel to commands
  redirectDirs: Dirs[] // same for each redirect
  decodedShell: boolean // decoded text (base64 -d, xxd -r, openssl enc -d) is fed to a shell
  cwd: Dirs // parser state: the cd chain at the current point of the scan
  inline: Array<{ code: string; dirs: Dirs }> // heredoc bodies an interpreter reads as its program
  nest: number // parser state: how many interpreter-in-interpreter levels are open
}

const MAX_DEPTH = 16
const MAX_NEST = 3
// Programs that run inline code (-c, -e) or a program read from stdin.
export const INTERP_CODE = /^(python[\d.]*|bun|node|nodejs|deno|perl|ruby|php)$/
export const INLINE_FLAG = /^(?:-[A-Za-z]*[ce]|-p|-E|--eval|--print|eval)$/
const ASSIGN = /^[A-Za-z_][A-Za-z0-9_]*(\[[^\]]*\])?\+?=/
const RESERVED = new Set(["if", "then", "else", "elif", "fi", "do", "done", "while", "until", "!", "{", "}", "esac"])
const SHELLS = new Set(["bash", "sh", "zsh", "dash", "ksh"])
const DONE = Symbol("done")

type Redirect = null | "out" | "dup" | "in" | "here" | "heredoc"

const DECODE_RE = /\b(?:base64\s+(?:-[a-zA-Z]*[dD]\b|--decode)|xxd\s+-[a-zA-Z]*r|openssl\s+[^|)`]*\s-d\b)/
const hasSubst = (s: string) => s.includes("$(") || s.includes("`")

function isDecoder(c: string[]): boolean {
  const args = c.slice(1)
  switch (c[0]) {
    case "base64":
      return args.some((a) => a === "--decode" || /^-[a-zA-Z]*[dD][a-zA-Z]*$/.test(a))
    case "xxd":
      return args.some((a) => /^-[a-zA-Z]*r[a-zA-Z]*$/.test(a))
    case "openssl":
      return args.includes("-d")
  }
  return false
}

function baseName(p: string): string {
  const t = p.replace(/\/+$/, "")
  const i = t.lastIndexOf("/")
  return (i >= 0 ? t.slice(i + 1) : t) || p
}

function closeTick(line: string, from: number): number {
  for (let j = from; j < line.length; j++) {
    if (line[j] === "\\") j++
    else if (line[j] === "`") return j
  }
  return line.length
}

// line[open] is "(". Returns the index of the matching ")", or line.length.
function balanced(line: string, open: number): number {
  let depth = 0
  for (let j = open; j < line.length; j++) {
    const c = line[j]
    if (c === "\\") j++
    else if (c === "'") {
      j = line.indexOf("'", j + 1)
      if (j < 0) return line.length
    } else if (c === '"') {
      for (j++; j < line.length && line[j] !== '"'; j++) if (line[j] === "\\") j++
    } else if (c === "(") depth++
    else if (c === ")" && --depth === 0) return j
  }
  return line.length
}

// line[i] is "`" or "$" followed by "(". Scans the inner text as code, returns the next index.
function substitution(line: string, i: number, out: Parsed, depth: number): number {
  if (line[i] === "`") {
    const end = closeTick(line, i + 1)
    scan(line.slice(i + 1, end).replace(/\\`/g, "`"), out, depth + 1)
    return Math.min(end + 1, line.length)
  }
  const open = i + 1
  const end = balanced(line, open)
  if (line[open + 1] !== "(") scan(line.slice(open + 1, end), out, depth + 1)
  return Math.min(end + 1, line.length)
}

// ---- interpreter code that shells out ----
// shortcut: reads string literals next to known call names; no variables, no concatenation of two
// variables. A non-literal part becomes $X so the rm rules treat the target as unknown. Upgrade with a real parser.

const q1 = (s: string) => `'${s.replace(/'/g, "'\\''")}'`
const UNKNOWN = '"$X"'
const CALL = /\b(?:subprocess\.(?:run|call|Popen|check_output|check_call|getoutput|getstatusoutput)|Bun\.\$|(?:system|popen|exec|execSync|execFile|execFileSync|spawn|spawnSync|execa|shell_exec|passthru))(?![\w$])(?:\s*\(\s*|\s*(?=["'`]))/g
const CONCAT = /^(?:[+%]|\.(?![A-Za-z_])|\.format\b)/

interface Lit {
  text: string
  end: number
}

function skipWs(code: string, i: number): number {
  while (i < code.length && /\s/.test(code[i])) i++
  return i
}

// A string literal at code[i] (python r/b/f prefixes, triple quotes, backticks). Interpolations become $X.
function strLit(code: string, i: number): Lit | null {
  let j = i
  let raw = false
  let fmt = false
  const pre = /^[rRbBfFuU]{1,2}(?=['"])/.exec(code.slice(j, j + 3))
  if (pre) {
    raw = /r/i.test(pre[0])
    fmt = /f/i.test(pre[0])
    j += pre[0].length
  }
  const quote = code[j]
  if (quote !== "'" && quote !== '"' && quote !== "`") return null
  const close = quote !== "`" && code.startsWith(quote.repeat(3), j) ? quote.repeat(3) : quote
  j += close.length
  let text = ""
  while (j < code.length && !code.startsWith(close, j)) {
    const c = code[j]
    const e = code[j + 1]
    if (c === "\\" && e !== undefined) {
      if (raw) text += c + e
      else text += e === "n" ? "\n" : e === "t" ? "\t" : "\"'`\\".includes(e) ? e : c + e
      j += 2
    } else if (((fmt || quote === "`") && c === "{") || (c === "$" && e === "{" && quote !== "'") || (c === "#" && e === "{" && quote === '"')) {
      const open = c === "{" ? j : j + 1
      const k = code.indexOf("}", open)
      text += "$X"
      j = k < 0 ? code.length : k + 1
    } else {
      text += c
      j++
    }
  }
  return { text, end: Math.min(j + close.length, code.length) }
}

// Index of the next top-level `,` or closer after an expression.
function skipExpr(code: string, i: number): number {
  let depth = 0
  while (i < code.length) {
    const c = code[i]
    const lit = strLit(code, i)
    if (lit) i = lit.end
    else if ("([{".includes(c)) {
      depth++
      i++
    } else if (")]}".includes(c)) {
      if (depth === 0) return i
      depth--
      i++
    } else if ((c === "," || c === ";") && depth === 0) return i
    else i++
  }
  return i
}

interface Item {
  k: "s" | "l" | "u" | "stop" // string, list, unknown, keyword argument or object (end of the command part)
  raw: string
  words: string[] // shell words
  partial: boolean // a literal joined to something we cannot see
}

function listItem(code: string, i: number): { item: Item; end: number } {
  const words: string[] = []
  i++
  for (let n = 0; n < 64; n++) {
    i = skipWs(code, i)
    if (i >= code.length || code[i] === "]") break
    const lit = strLit(code, i)
    let end = lit ? lit.end : i
    const next = skipExpr(code, end)
    if (lit) words.push(CONCAT.test(code.slice(skipWs(code, end), next).trim()) ? q1(lit.text) + UNKNOWN : q1(lit.text))
    else words.push(UNKNOWN)
    end = next
    i = code[end] === "," ? end + 1 : end
  }
  return { item: { k: "l", raw: "", words, partial: false }, end: code[i] === "]" ? i + 1 : i }
}

function callItems(code: string, from: number): Item[] {
  const res: Item[] = []
  let i = from
  for (let n = 0; n < 16; n++) {
    i = skipWs(code, i)
    const c = code[i]
    if (c === undefined || c === ")" || c === ";") break
    let item: Item
    let end: number
    const qw = /^qw\s*\(([^)]*)\)/.exec(code.slice(i, i + 400))
    if (c === "[") {
      const l = listItem(code, i)
      item = l.item
      end = l.end
    } else if (qw) {
      item = { k: "l", raw: "", words: qw[1].split(/\s+/).filter(Boolean).map(q1), partial: false }
      end = i + qw[0].length
    } else {
      const lit = strLit(code, i)
      if (lit) {
        const next = skipExpr(code, lit.end)
        const partial = CONCAT.test(code.slice(skipWs(code, lit.end), next).trim())
        item = { k: "s", raw: lit.text, words: [partial ? q1(lit.text) + UNKNOWN : q1(lit.text)], partial }
      } else {
        const stop = c === "{" || /^[A-Za-z_]\w*\s*=(?!=)/.test(code.slice(i, i + 80))
        item = { k: stop ? "stop" : "u", raw: "", words: [UNKNOWN], partial: false }
      }
      end = skipExpr(code, lit ? lit.end : i)
    }
    if (item.k === "stop") break
    res.push(item)
    i = code[end] === "," ? end + 1 : end
    if (code[end] !== ",") break
  }
  return res
}

// The command line a call such as os.system("...") or subprocess.run(["rm", "-rf", x]) runs, or null.
function callCommand(code: string, from: number): string | null {
  const it = callItems(code, from)
  const first = it[0]
  if (!first || first.k === "u") return null
  if (first.k === "l") return first.words.join(" ")
  const second = it[1]
  if (second && (second.k === "s" || second.k === "l")) {
    return it.flatMap((x) => (x.k === "u" ? [UNKNOWN] : x.words)).join(" ")
  }
  return first.raw + (first.partial ? "$X" : "")
}

// Shell command lines that inline interpreter code runs through system(), exec(), subprocess and the like.
function shellOuts(code: string, interp: string): string[] {
  const found: string[] = []
  for (const m of code.matchAll(CALL)) {
    const cmd = callCommand(code, m.index + m[0].length)
    if (cmd) found.push(cmd)
  }
  if (/^(ruby|perl|php)$/.test(interp)) {
    for (let i = code.indexOf("`"); i >= 0; i = code.indexOf("`", i)) {
      const lit = strLit(code, i) as Lit
      if (lit.text.trim()) found.push(lit.text)
      i = lit.end
    }
    for (const m of code.matchAll(/(?:%x|\bqx)\(([^)]*)\)/g)) found.push(m[1])
  }
  return found
}

// Scan the shell lines hidden in interpreter code, as if they were typed. Nesting is capped.
function scanInline(code: string, interp: string, out: Parsed, depth: number): void {
  if (out.nest >= MAX_NEST) return
  out.nest++
  try {
    for (const cmd of shellOuts(code, interp)) scan(cmd, out, depth + 1)
  } finally {
    out.nest--
  }
}

function scan(line: string, out: Parsed, depth: number): void {
  if (depth > MAX_DEPTH) return
  const savedDirs = out.cwd
  const n = line.length
  let seg: string[] = []
  let cur = ""
  let inWord = false
  let pending: Redirect = null
  const heredocs: string[] = []
  let docs: string[] = [] // heredoc bodies and here-strings of the current line
  let lineProg = out.programs.length
  let lineCmd = out.commands.length
  let decoded = false // a decoder ran earlier in the current pipeline
  let procDecoded = false // the current command reads a <(...) that decodes text
  const parens: Dirs[] = []
  let i = 0

  const flush = () => {
    if (!inWord) return
    const w = cur
    cur = ""
    inWord = false
    const kind = pending
    pending = null
    if (kind === "out") addRedirect(w)
    else if (kind === "dup") {
      if (!/^(\d+|-)$/.test(w)) addRedirect(w)
    } else if (kind === "heredoc") heredocs.push(w)
    else if (kind === "here") docs.push(w)
    else if (kind === null) seg.push(w)
  }
  const addRedirect = (w: string) => {
    out.redirects.push(w)
    out.redirectDirs.push(out.cwd)
  }
  const endSeg = () => {
    flush()
    pending = null
    if (seg.length) {
      const c = emit(seg, out, depth)
      if (c) {
        if ((decoded || procDecoded) && (SHELLS.has(c[0]) || c[0] === "source" || c[0] === ".")) out.decodedShell = true
        if (isDecoder(c)) decoded = true
      }
    }
    procDecoded = false
    seg = []
  }
  // Text a shell reads from stdin runs as commands. Only when a shell program is on the line.
  // An interpreter with no script argument reads its program from stdin: the body is its inline code.
  const flushDocs = () => {
    if (docs.length) {
      if (out.programs.slice(lineProg).some((p) => SHELLS.has(p))) for (const d of docs) scan(d, out, depth + 1)
      const interp = out.commands.slice(lineCmd).find((c) => INTERP_CODE.test(c[0]) && c.slice(1).every((a) => a.startsWith("-")))
      if (interp)
        for (const d of docs) {
          out.inline.push({ code: d, dirs: out.cwd })
          scanInline(d, interp[0], out, depth)
        }
    }
    docs = []
    lineProg = out.programs.length
    lineCmd = out.commands.length
  }
  const dropFd = () => {
    if (inWord && /^\d+$/.test(cur)) {
      cur = ""
      inWord = false
    } else flush()
  }

  while (i < n) {
    const c = line[i]
    if (c === "\\") {
      if (line[i + 1] === "\n") i += 2
      else if (i + 1 < n) {
        cur += line[i + 1]
        inWord = true
        i += 2
      } else i++
    } else if (c === "'") {
      const j = line.indexOf("'", i + 1)
      const end = j < 0 ? n : j
      cur += line.slice(i + 1, end)
      inWord = true
      i = end + 1
    } else if (c === '"') {
      inWord = true
      i++
      while (i < n && line[i] !== '"') {
        const d = line[i]
        if (d === "\\" && i + 1 < n) {
          const e = line[i + 1]
          if (e === "\n") {
            /* continuation */
          } else if ('"\\$`'.includes(e)) cur += e
          else cur += d + e
          i += 2
        } else if (d === "`" || (d === "$" && line[i + 1] === "(")) {
          const next = substitution(line, i, out, depth)
          cur += line.slice(i, next)
          i = next
        } else {
          cur += d
          i++
        }
      }
      i++
    } else if (c === "$" && line[i + 1] === "'") {
      inWord = true
      i += 2
      while (i < n && line[i] !== "'") {
        if (line[i] === "\\" && i + 1 < n) {
          cur += line[i + 1]
          i += 2
        } else cur += line[i++]
      }
      i++
    } else if (c === "$" && line[i + 1] === "{") {
      const e = line.indexOf("}", i)
      const end = e < 0 ? n : e + 1
      cur += line.slice(i, end)
      inWord = true
      i = end
    } else if (c === "`" || (c === "$" && line[i + 1] === "(")) {
      const next = substitution(line, i, out, depth)
      cur += line.slice(i, next)
      inWord = true
      i = next
    } else if (c === "#" && !inWord) {
      while (i < n && line[i] !== "\n") i++
    } else if (c === " " || c === "\t" || c === "\r") {
      flush()
      i++
    } else if (c === "\n") {
      endSeg()
      decoded = false
      i++
      while (heredocs.length) {
        const d = heredocs.shift() as string
        const body: string[] = []
        while (i < n) {
          let e = line.indexOf("\n", i)
          if (e < 0) e = n
          const l = line.slice(i, e)
          i = e + 1
          if (l === d || l.replace(/^\t+/, "") === d) break
          body.push(l)
        }
        docs.push(body.join("\n"))
      }
      flushDocs()
    } else if (c === "|") {
      endSeg()
      if (line[i + 1] === "|") {
        decoded = false
        i += 2
      } else i += line[i + 1] === "&" ? 2 : 1
    } else if (c === "(" || c === ")") {
      endSeg()
      decoded = false
      if (c === "(") parens.push(out.cwd)
      else if (parens.length) out.cwd = parens.pop() as Dirs
      i++
    } else if (c === ";") {
      endSeg()
      decoded = false
      i++
    } else if (c === "&") {
      if (line[i + 1] === ">") {
        flush()
        i += line[i + 2] === ">" ? 3 : 2
        pending = "out"
      } else {
        endSeg()
        decoded = false
        i++
      }
    } else if (c === ">") {
      dropFd()
      i++
      if (line[i] === ">" || line[i] === "|") i++
      if (line[i] === "&") {
        i++
        pending = "dup"
      } else pending = "out"
    } else if (c === "<" && line[i + 1] === "(") {
      // Process substitution: the word is a file name, the inner text runs as commands.
      const end = balanced(line, i + 1)
      const before = out.commands.length
      scan(line.slice(i + 2, end), out, depth + 1)
      if (out.commands.slice(before).some(isDecoder)) procDecoded = true
      cur += "/dev/fd/63"
      inWord = true
      i = Math.min(end + 1, n)
    } else if (c === "<") {
      dropFd()
      if (line.startsWith("<<<", i)) {
        i += 3
        pending = "here"
      } else if (line.startsWith("<<", i)) {
        i += 2
        if (line[i] === "-") i++
        pending = "heredoc"
      } else {
        i++
        if (line[i] === "&") i++
        pending = "in"
      }
    } else {
      cur += c
      inWord = true
      i++
    }
  }
  endSeg()
  flushDocs()
  if (depth > 0) out.cwd = savedDirs
}

// Option skipping shared by the wrappers. Returns the index of the first non-option word.
function skipOpts(rest: string[], withArg: ReadonlySet<string>, assigns = false): number {
  let k = 0
  while (k < rest.length) {
    const w = rest[k]
    if (w === "--") return k + 1
    if (withArg.has(w)) k += 2
    else if (w.startsWith("-") && w.length > 1) k++
    else if (assigns && ASSIGN.test(w)) k++
    else break
  }
  return k
}

const set = (...s: string[]) => new Set(s)
const SUDO_ARGS = set("-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-r", "-t", "-U")
const XARGS_ARGS = set("-I", "-n", "-P", "-L", "-d", "-E", "-s", "-a", "--max-args", "--max-procs", "--max-lines", "--delimiter", "--arg-file", "--eof")
const ENV_ARGS = set("-u", "-C", "--unset", "--chdir")
const GIT_VALUE_OPTS = set("-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env")
const GIT_CMD_KEY = /^(?:core\.(?:sshCommand|pager|editor|fsmonitor|askPass)|sequence\.editor|diff\.external|gpg\.program)=([\s\S]*)$/i

function unwrap(a: string[], out: Parsed, depth: number): string[] | null | typeof DONE {
  const p = a[0]
  const rest = a.slice(1)
  const inner = (k: number) => (k < rest.length ? rest.slice(k) : null)

  // Inline interpreter code (-c, -e) may shell out: scan the command lines it runs.
  if (INTERP_CODE.test(p) && rest.some((w) => INLINE_FLAG.test(w))) scanInline(rest.join("\n"), p, out, depth)

  if (SHELLS.has(p)) {
    for (let k = 0; k < rest.length; k++) {
      const w = rest[k]
      if (/^-[a-zA-Z]*c[a-zA-Z]*$/.test(w)) {
        if (rest[k + 1] === undefined) return null
        if (hasSubst(rest[k + 1]) && DECODE_RE.test(rest[k + 1])) out.decodedShell = true
        scan(rest[k + 1], out, depth + 1)
        return DONE
      }
      if (w === "-o" || w === "+o") k++
      else if (!w.startsWith("-") && !w.startsWith("+")) return null
    }
    return null
  }
  switch (p) {
    case "eval":
      if (!rest.length) return null
      if (hasSubst(rest.join(" ")) && DECODE_RE.test(rest.join(" "))) out.decodedShell = true
      scan(rest.join(" "), out, depth + 1)
      return DONE
    case "git": {
      // `git -c alias.x='!cmd' x` runs cmd as a shell line.
      // Config keys whose value git runs as a command line (core.pager, core.sshCommand ...) are scanned too.
      for (let k = 0; k < rest.length && rest[k].startsWith("-"); k++) {
        if (rest[k] === "-c" && rest[k + 1] !== undefined) {
          const m = /^alias\.[^=]+=!([\s\S]*)$/.exec(rest[k + 1]) ?? GIT_CMD_KEY.exec(rest[k + 1])
          if (m) scan(m[1], out, depth + 1)
          k++
        } else if (GIT_VALUE_OPTS.has(rest[k])) k++
      }
      return null
    }
    case "busybox":
    case "builtin":
    case "setsid":
      return inner(skipOpts(rest, set()))
    case "env": {
      const si = rest.findIndex((w) => w === "-S" || w === "--split-string")
      if (si >= 0 && rest[si + 1] !== undefined) {
        scan(rest[si + 1], out, depth + 1)
        return DONE
      }
      return inner(skipOpts(rest, ENV_ARGS, true))
    }
    case "sudo":
      return inner(skipOpts(rest, SUDO_ARGS, true))
    case "xargs":
      return inner(skipOpts(rest, XARGS_ARGS))
    case "nohup":
    case "time":
    case "command":
      return inner(skipOpts(rest, p === "time" ? set("-f", "-o") : set()))
    case "exec":
      return inner(skipOpts(rest, set("-a")))
    case "nice":
      return inner(skipOpts(rest, set("-n")))
    case "timeout":
      return inner(skipOpts(rest, set("-s", "-k", "--signal", "--kill-after")) + 1)
  }
  return null
}

// A `cd` (or pushd) changes the directory for the commands after it. popd and `cd -` make it unknown.
function applyCd(a: string[], out: Parsed): void {
  if (a[0] === "popd") out.cwd = [...out.cwd, null]
  else {
    const pos = a.slice(1).filter((w) => w !== "--" && !/^-[LPe@]+$/.test(w))
    out.cwd = [...out.cwd, pos[0] === "-" ? null : (pos[0] ?? "~")]
  }
}

// Returns the final command it recorded itself, or null when wrappers handed the work to a nested scan.
function emit(raw: string[], out: Parsed, depth: number): string[] | null {
  let a = raw.slice()
  for (;;) {
    while (a.length && (RESERVED.has(a[0]) || ASSIGN.test(a[0]))) a.shift()
    if (!a.length) return null
    a[0] = baseName(a[0])
    out.programs.push(a[0])
    const next = unwrap(a, out, depth)
    if (next === DONE) return null
    if (next === null) {
      out.commands.push(a)
      out.dirs.push(out.cwd)
      if (a[0] === "cd" || a[0] === "pushd" || a[0] === "popd") applyCd(a, out)
      return a
    }
    a = next
  }
}

export function parse(line: string): Parsed {
  const out: Parsed = { commands: [], programs: [], redirects: [], dirs: [], redirectDirs: [], decodedShell: false, cwd: [], inline: [], nest: 0 }
  try {
    // ${IFS} and $IFS are whitespace in practice: `rm${IFS}-rf${IFS}/x` is `rm -rf /x`.
    scan(String(line ?? "").replace(/\$\{IFS\}|\$IFS(?![A-Za-z0-9_])/g, " "), out, 0)
  } catch {
    // keep what we have
  }
  return out
}

export const commands = (line: string): string[][] => parse(line).commands
export const programs = (line: string): string[] => parse(line).programs
export const redirects = (line: string): string[] => parse(line).redirects
