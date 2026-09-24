# SOURCE A: Claude Code transcripts (PRIMARY)

## Contents

- Storage layout and line schema
- A1: candidate-session triage
- A2: full-text search with provenance
- A3: session titles
- A4: prompt index
- A5: executed tool calls
- A6: reading a session in order

## Storage layout

- One directory per project: `~/.claude/projects/<encoded-cwd>/`. The directory name is the
  absolute cwd with every `/` and `.` replaced by `-`.
  Example: `/Users/AlexandreCastro/.config/opencode` -> `-Users-AlexandreCastro--config-opencode`.
  To go from a known path to its transcript dir:
  ```bash
  CWD="/Users/AlexandreCastro/Developer"
  ENC=$(printf '%s' "$CWD" | sed 's#[/.]#-#g')
  ls ~/.claude/projects/"$ENC"/
  ```
  Every line also carries a `.cwd` field, so you can filter by project without decoding the dir name.
  **NEVER trust a constructed encoded path.** A session is frequently NOT in the dir you would
  guess from the project name (work done from `/Users/.../Developer` lands in `-Users-...-Developer`,
  not in a `-grafana-improvements` subdir). Always start GLOBAL: `grep -rli` / `find ~/.claude/projects`
  over the whole tree. To locate a specific session's file, resolve by UUID
  (`find ~/.claude/projects -name '*<uuid>*'`) or filter on `.cwd` -- do not assemble the dir name and `ls` it.
- Transcripts are nested at MORE than one depth. A single project dir contains:
  - `<session-uuid>.jsonl` -- the main session (one JSON object per line).
  - `<session-uuid>/subagents/agent-*.jsonl` -- transcripts of subagents spawned in that
    session. These share the parent's `.sessionId` and use the identical line schema, and they
    are usually FAR more numerous than the main sessions. **Never skip them** -- most of the real
    work (delegated reads, edits, searches) lives here.
  - `<session-uuid>/subagents/workflows/wf_<id>/agent-*.jsonl` -- subagents spawned inside a
    workflow get one more directory level. Measured 2026-09-24 on this machine: 384 workflow
    transcripts against 198 flat `subagents/agent-*.jsonl` under `~/.claude/projects/`, so a
    flat `subagents/*.jsonl` glob misses the majority. The recursive enumeration below finds
    them; the dirs also hold `agent-*.meta.json` and `journal.jsonl` (workflow bookkeeping,
    lines like `{"type":"started","agentId":...}`, no `.message` -- harmless to the filters
    below, which only read `user`/`assistant` lines).
  - `<session-uuid>/tool-results/*.txt` -- externalized large tool outputs (plain text, not JSON).
- Because of that nesting, do NOT use `~/.claude/projects/*/*.jsonl` (it misses the subagent
  dirs). Always enumerate recursively. The canonical, FAST pattern for every content pass below
  is **ripgrep-prefilter -> jq** (measured ~6x faster than scanning all files on a specific
  keyword, and ~40x faster than `grep` for triage):
  ```bash
  rg -l -i -g '*.jsonl' "<kw>" ~/.claude/projects/ 2>/dev/null | xargs jq -rc '<filter>'
  ```
  - `-g '*.jsonl'` is REQUIRED: a bare `rg`/`grep` of the project dir also matches `.js`/`.txt`/
    `.md`/tool-result files, and feeding those to jq throws `parse error` which aborts the batch.
  - Paths here never contain spaces (UUIDs + dash-encoded dirs), so newline `xargs` is safe.
  - `<filter>` MUST be total (never error): see the WARNING in A2 about `xargs jq` aborting.
  - rg returns the identical file set as `grep -rli` here (no `.git` in `~/.claude`, so no ignore
    rules apply); it is just dramatically faster.
- `~/.claude/history.jsonl` is a global fast index of user prompts: `{display, timestamp (epoch ms), project, sessionId}` (entries that pasted content also carry `pastedContents`). It indexes top-level prompts only -- subagent activity is not here, so still search the transcripts for delegated work.

## Line schema (the fields that matter)

| Field | Meaning |
|-------|---------|
| `.type` | `user`, `assistant`, `ai-title`, `last-prompt`, `attachment`, `queue-operation` |
| `.sessionId` | Session UUID (this is the ID to report; resume with `claude --resume <uuid>`) |
| `.cwd` | Working directory of the session (use to filter by project) |
| `.gitBranch` | Branch at the time |
| `.timestamp` | ISO-8601 string |
| `.message.role` | `user` / `assistant` |
| `.message.content` | USUALLY an array of blocks: `{type:"text",text}`, `{type:"thinking",thinking}`, `{type:"tool_use",name,input}`, `{type:"tool_result",content}`. **But sometimes a plain string** (slash-commands, typed commands). Any jq filter MUST guard for both (`if type=="array"`) or it throws `Cannot iterate over string` and aborts the batch. |
| `.aiTitle` | On `ai-title` lines: the human-readable session title (repeats; dedupe by sessionId) |
| `.toolUseResult` | Tool output payload on some lines |

## Strategy A1: Fast triage with ripgrep (find candidate sessions)

`rg` is the cheapest first pass (~40x faster than `grep -rl`, same file set). Find which
transcript files even mention the term:
```bash
rg -l -i -g '*.jsonl' "authentication" ~/.claude/projects/ 2>/dev/null
```
`-l` lists files (= sessions), `-i` case-insensitive, `-g '*.jsonl'` restricts to transcripts
(keeps `.js`/`.txt`/`.md` out of any downstream jq). Use this to narrow before spending jq.

## Strategy A2: Full-text content search (with provenance)

Pull matching message text with session + timestamp + role attached. Triage with `rg` first,
then run jq only on the matching files:
```bash
KEYWORD="authentication"
rg -l -i -g '*.jsonl' "$KEYWORD" ~/.claude/projects/ 2>/dev/null \
| xargs jq -rc --arg k "$KEYWORD" '
    select(.type=="user" or .type=="assistant")
    | . as $l
    | (($l.message.content // []) | if type=="array" then . else [{type:"text", text:.}] end)[]
    | select((.type=="text" or .type=="thinking")
             and (((.text // .thinking) // "") | ascii_downcase | contains($k|ascii_downcase)))
    | {sid:$l.sessionId, ts:$l.timestamp, branch:$l.gitBranch, role:$l.message.role,
       snippet:((.text // .thinking)[0:200])}
  ' 2>/dev/null | head -30
```
(Covers main sessions AND subagent transcripts. To restrict to one project, swap the `rg` root
to `~/.claude/projects/<encoded-cwd>`.)

> **WARNING - why this exact shape (do not "simplify" it):**
> - `if type=="array" then . else [{type:"text", text:.}] end` handles `content` being a plain
>   string (slash-commands / typed commands). Without it jq throws `Cannot iterate over string`.
> - That matters because **a single non-zero jq exit makes `xargs` ABORT the whole run** and
>   silently drop every remaining file (BSD `xargs` returns on first failure). A filter that can
>   error therefore truncates your results without warning. Keep the filter TOTAL so jq exits 0.
> - `-g '*.jsonl'` keeps non-JSON files out (they cause `parse error`, another abort trigger).
> - The old `find … | xargs -0 jq '($l.message.content // [])[]'` emitted ~1000 such errors and
>   under-reported. This shape is a strict superset and runs error-free.

## Strategy A3: Session title search

Titles live on `ai-title` lines. Map sessionId -> title (deduped):
```bash
find ~/.claude/projects -name '*.jsonl' -print0 | xargs -0 \
  jq -rc 'select(.type=="ai-title") | {sid:.sessionId, title:.aiTitle}' 2>/dev/null | sort -u
```
Filter by adding `| select(.aiTitle|ascii_downcase|contains("redis"))` before the object build.
(`ai-title` lines only appear in main `<uuid>.jsonl` files, but searching recursively is harmless.)

## Strategy A4: Prompt index (fast "what was I working on")

`history.jsonl` is small and one line per user prompt: ideal for keyword + recency scans.
```bash
KEYWORD="redis"
jq -rc --arg k "$KEYWORD" '
  select(.display|ascii_downcase|contains($k|ascii_downcase))
  | {sid:.sessionId, project, when:(.timestamp/1000|todate), prompt:(.display[0:120])}
' ~/.claude/history.jsonl 2>/dev/null | tail -30
```
(epoch ms -> readable: `.timestamp/1000|todate`.)

## Strategy A5: What was actually DONE (tool calls)

To see actions (edits, commands, MCP calls) rather than chat:
```bash
SID_FILE=~/.claude/projects/<encoded-cwd>/<uuid>.jsonl
jq -rc 'select(.type=="assistant") | .message.content[]?
  | select(.type=="tool_use") | {tool:.name, input:(.input|tostring|.[0:160])}' "$SID_FILE"
```

## Strategy A6: Read a session in order

Once you have a promising `<uuid>.jsonl`, reconstruct the human-readable thread (the
`if type=="array"` guard keeps string-typed `content` from erroring):
```bash
jq -r 'select(.type=="user" or .type=="assistant")
  | ((.message.content // []) | if type=="array" then . else [{type:"text", text:.}] end)[]
  | select(.type=="text") | "\(.text)\n---"' "$SID_FILE" | head -200
```
