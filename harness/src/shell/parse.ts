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
}

const MAX_DEPTH = 16
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
  let decoded = false // a decoder ran earlier in the current pipeline
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
        if (decoded && SHELLS.has(c[0])) out.decodedShell = true
        if (isDecoder(c)) decoded = true
      }
    }
    seg = []
  }
  // Text a shell reads from stdin runs as commands. Only when a shell program is on the line.
  const flushDocs = () => {
    if (docs.length && out.programs.slice(lineProg).some((p) => SHELLS.has(p))) for (const d of docs) scan(d, out, depth + 1)
    docs = []
    lineProg = out.programs.length
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

function unwrap(a: string[], out: Parsed, depth: number): string[] | null | typeof DONE {
  const p = a[0]
  const rest = a.slice(1)
  const inner = (k: number) => (k < rest.length ? rest.slice(k) : null)

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
      for (let k = 0; k < rest.length && rest[k].startsWith("-"); k++) {
        if (rest[k] === "-c" && rest[k + 1] !== undefined) {
          const m = /^alias\.[^=]+=!([\s\S]*)$/.exec(rest[k + 1])
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
  const out: Parsed = { commands: [], programs: [], redirects: [], dirs: [], redirectDirs: [], decodedShell: false, cwd: [] }
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
