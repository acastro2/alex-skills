# SOURCE H: Pi agent sessions (CURRENT, PRIMARY)

## Contents

- Storage layout and line schema
- H1: candidate-session triage
- H2: full-text search with provenance
- H3: session listing
- H4: reading a session in order
- H5: executed tool calls and commands
- H6: subagent artifacts
- H7: subagent run log
- Citation format

Work done in **Pi** (the pi coding agent, the tool the user is running right now) lives under
`~/.pi/agent/sessions/`. Pi is the other actively-used coding agent, so search it alongside
Source A for recent work — the same question may have been worked on in either tool. Read-only:
these are plain JSONL files; never modify them.

## Storage layout

- One directory per project: `~/.pi/agent/sessions/--<path>--/`, where `<path>` is the absolute
  cwd with `/` replaced by `-`, wrapped in `--...--`. Dots are PRESERVED (unlike Claude Code).
  Example: `/Users/alexandrecastro/.agents/skills` -> `--Users-alexandrecastro-.agents-skills--`.
  As with Claude Code, NEVER trust a constructed path: start GLOBAL (`rg -l` over
  `~/.pi/agent/sessions/`) and resolve specific sessions by uuid (the header's `.id`).
- `<timestamp>_<uuid>.jsonl` — one main session per file. Filename timestamp is session start
  with colons as dashes (`2026-08-10T16-18-06-228Z_<uuid>.jsonl`).
- `subagent-artifacts/` — delegated subagent runs for that project's sessions:
  `<runId>_<agent>[_<childIndex>]_transcript.jsonl` (same AgentMessage schema as main sessions),
  plus `<runId>_<agent>_input.md` (task brief), `_output.md` (result), and `_meta.json`
  (runId, agent, full task text). Real delegated work often lives ONLY here.
- `<timestamp>_<uuid>/<entry-id>/run-<N>/session.jsonl` — the SAME subagent runs, stored a
  second way: one dir per parent-session entry, `run-<N>` numbering retries within that entry.
  Same JSONL schema as main sessions, but the header's `id` is the SUBAGENT's own uuid (not the
  parent's) and `cwd` is inherited. Identify them by the `session_info` name
  `subagent-<agent>-<runId>[-<childIndex>]` (e.g. `subagent-ado-<runId>-1`,
  `subagent-reviewer-<runId>-1`) — the `<runId>` matches the subagent-artifacts filenames of the
  same run. The parent session links each one via a `custom_message` entry whose content is the
  path to `.../run-0/session.jsonl`. This machine has ~120 nested subagent sessions alongside
  ~420 main files: delegated work is real content, search it like main sessions.
- `~/.pi/agent/run-history.jsonl` — global log of subagent runs: `{agent, taskHash, ts, status,
  duration}`. Task text is REDACTED (hash only): use for presence/timing ("did any researcher run
  last week?"), never content.

## Line schema (the fields that matter)

| Field | Meaning |
|-------|---------|
| Line 1 (header) | `{"type":"session","version":3,"id":"<uuid>","timestamp":"...","cwd":"...","parentSession":"..."}` — session id + project; `parentSession` marks a `/fork`ed session. This is the ONLY line with `.cwd` and `.id` — entries below carry neither. |
| `.type` (per line) | `session`, `message`, `model_change`, `thinking_level_change`, `compaction`, `branch_summary`, `custom`, `custom_message`, `label`, `session_info` |
| `.message.role` | `user` / `assistant` / `toolResult` / `bashExecution` / `custom` |
| `.message.content` | USUALLY an array of blocks: `{type:"text",text}`, `{type:"thinking",thinking}`, `{type:"image",data,mimeType}`, `{type:"toolCall",name,arguments}`. CAN be a plain string for typed/slash user input. jq filters MUST guard both (`if type=="array"`) or they throw `Cannot iterate over string`. |
| `.timestamp` | ISO-8601 string (per entry) |
| `.message.model` | Model used (on assistant messages) |
| `session_info` entries | `{"type":"session_info","name":"..."}` — user-set display name (`/name`); the last one in the file is the session title |
| `compaction` / `branch_summary` entries | `.summary` — distilled context; often the fastest way to see what a long session covered |

Resume: `pi --session <path|id>` (path or uuid) or the `/resume` picker in the TUI.

## Strategy H1: Triage
```bash
rg -l -i -g '*.jsonl' "<kw>" ~/.pi/agent/sessions/ 2>/dev/null
```
(`-g '*.jsonl'` also sweeps subagent transcripts — fine for triage; keeps the `.md` artifacts out.)

## Strategy H2: Full-text content search (with provenance)

Session id comes from the file HEADER, not per line, so use a while-loop (not `xargs`) and read
`.id` from line 1. Filter is total: string-vs-array `content` guard, `text`/`thinking` both
checked, `else empty` for every other entry type. Excludes subagent transcripts (H6 covers them):
```bash
KEYWORD="authentication"
for f in $(rg -l -i -g '*.jsonl' -g '!*_transcript.jsonl' "$KEYWORD" ~/.pi/agent/sessions/ 2>/dev/null); do
  sid=$(head -1 "$f" | jq -r '.id // empty' 2>/dev/null)
  jq -rc --arg k "$KEYWORD" --arg sid "$sid" '
    if (.type=="message") then
      . as $l
      | ((.message.content // []) | if type=="array" then . else [{type:"text", text:.}] end)[]
      | select((.type=="text" or .type=="thinking")
               and (((.text // .thinking) // "") | ascii_downcase | contains($k|ascii_downcase)))
      | {sid:$sid, ts:$l.timestamp, role:$l.message.role, snippet:((.text // .thinking)[0:200])}
    elif ((.type=="compaction" or .type=="branch_summary")
          and ((.summary // "") | ascii_downcase | contains($k|ascii_downcase))) then
      {sid:$sid, ts:.timestamp, role:.type, snippet:(.summary[0:200])}
    else empty end' "$f" 2>/dev/null
done | head -30
```
H2 runs over main sessions AND the nested `<...>/run-<N>/session.jsonl` subagent sessions
automatically (same schema; only `*_transcript.jsonl` is excluded). A hit whose uuid you do not
recognize as a main session is likely subagent work — read the `session_info` name to see which
agent (`subagent-<agent>-...`) spawned it.

## Strategy H3: Session listing (uuid -> project + start + name)

> **Gotcha: `--`-prefixed dir names are parsed as options.** Every dir under
> `~/.pi/agent/sessions/` starts with `--` (e.g. `--Users-alexandrecastro-Developer--`).
> Any bare `--...` path handed to `head`, `jq`, `ls`, `find`, etc. is treated as a
> command-line option and fails (or silently returns nothing). Always glob with a
> `./` prefix or use absolute paths: `./*/*.jsonl`, `./--Users...--/...`, or the
> `~`-expanded absolute form below. `rg` output is safe when the search root is
> absolute; when in doubt, `sed 's#^#./#'` the paths.

```bash
for f in ~/.pi/agent/sessions/*/*.jsonl; do
  jq -rc 'select(.type=="session") | {sid:.id, cwd:.cwd, when:.timestamp}' "$f" 2>/dev/null | head -1
done | sort
```
Add the display name per file: `jq -rc 'select(.type=="session_info") | .name' "$f" | tail -1`. Filter
by project with `| select(.cwd|ascii_downcase|contains("grafana"))`.

## Strategy H4: Read a session in order
```bash
F=~/.pi/agent/sessions/--Users-alexandrecastro-Developer--/2026-08-01T12-00-00-000Z_<uuid>.jsonl
jq -r 'select(.type=="message") | . as $l
  | ((.message.content // []) | if type=="array" then . else [{type:"text", text:.}] end)[]
  | select(.type=="text" or .type=="thinking")
  | "[\($l.message.role)] \(.text // .thinking)\n---"' "$F" | head -200
```

## Strategy H5: What was actually DONE (tool calls + bash)
```bash
# Tool calls (note: block type is "toolCall", not "tool_use"):
jq -rc 'select(.type=="message") | .message.content[]?
  | select(.type=="toolCall") | {tool:.name, input:(.arguments|tostring|.[0:160])}' "$F"

# Commands actually executed (bashExecution role carries command + exitCode):
jq -rc 'select(.type=="message" and .message.role=="bashExecution")
  | {cmd:.message.command[0:160], exit:.message.exitCode}' "$F"
```

## Strategy H6: Subagent artifacts (delegated work)

Transcript records: `{recordType, runId, agent, childIndex, cwd, ts, timestamp, role, message}` —
the `message` field has the same content-block schema as main sessions. NOTE: after the `[]`
block projection, provenance fields must come from `$l` (the record), not bare `.runId`:
```bash
for f in $(rg -l -i -g '*_transcript.jsonl' "$KEYWORD" ~/.pi/agent/sessions/ 2>/dev/null); do
  jq -rc --arg k "$KEYWORD" '
    select(.recordType=="message" and (.message.role=="user" or .message.role=="assistant"))
    | . as $l
    | ((.message.content // []) | if type=="array" then . else [{type:"text", text:.}] end)[]
    | select((.type=="text" or .type=="thinking")
             and (((.text // .thinking) // "") | ascii_downcase | contains($k|ascii_downcase)))
    | {run:$l.runId, agent:$l.agent, role:$l.message.role, ts:$l.timestamp,
       snippet:((.text // .thinking)[0:200])}' "$f" 2>/dev/null
done | head -30
```
For the exact task a subagent was given, read the sibling `<runId>_<agent>_input.md` (the brief)
and `<runId>_<agent>_meta.json` (full task text + runId). The same runs also exist as nested
sessions (`<timestamp>_<uuid>/<entry-id>/run-<N>/session.jsonl`): the artifact `<runId>` matches
the `subagent-<agent>-<runId>-...` session name — search BOTH when a delegated run matters (H2
already sweeps the nested ones; this pass covers the transcripts).

## Strategy H7: Subagent run log (presence + timing only)
```bash
jq -rc '{agent, when:(.ts|todate), status, duration}' ~/.pi/agent/run-history.jsonl | tail -20
```

## Citation format
Cite as: `Pi: <timestamp>_<uuid>.jsonl (cwd: /path, YYYY-MM-DD)` — or just `Pi: <uuid>` inline.
