# SOURCE H: Cursor sessions, CLI and IDE (CURRENT, PRIMARY)

## Contents

- Storage layout and line schema
- H1: candidate-session triage
- H2: full-text search with provenance
- H3: session listing (CLI and IDE)
- H4: reading a session in order
- H5: tool calls
- Pitfalls
- Citation format

Work done in **Cursor**, the `cursor-agent` CLI and the Cursor IDE agent, is the third current
coding store after Claude Code and OpenCode. Read-only: never write to `~/.cursor/` or the IDE
database. Open the database with `sqlite3 -readonly`; the IDE holds it open and a write lock
can corrupt it. Layout verified 2026-11-11 on `cursor-agent` 2026.11.11.

## Storage layout

- **Transcripts, both CLI and IDE:**
  `~/.cursor/projects/<encoded-cwd>/agent-transcripts/<uuid>/<uuid>.jsonl`. `<encoded-cwd>` is
  the absolute path with `/` as `-`, without the leading dash
  (`/Users/<user>/Developer` → `Users-<user>-Developer`); long paths are cut and end in a short
  hash (`...-Library-CloudStorage-1a2b3c4`). It is lossy, so do not decode it to a path; take the real
  cwd from H3. A window with no folder writes to `empty-window/`. This is
  the one readable store for both clients: on 2026-11-11 it held 12 of 14 CLI chats and 4 of 7
  IDE composers (the rest were empty drafts).
- **CLI chat index:** `~/.cursor/chats/<hash>/<uuid>/meta.json` →
  `{"createdAtMs", "updatedAtMs", "cwd", "hasConversation"}`. `store.db` beside it is a blob
  store; do not parse it, because the transcript has the same text.
- **IDE chat index:** `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`,
  table `composerHeaders` (`composerId`, `workspaceId`, `createdAt`, `lastUpdatedAt` epoch-ms,
  `isArchived`, `isSubagent`, `value` JSON with `.name` = chat title). The workspace folder is in
  `~/Library/Application Support/Cursor/User/workspaceStorage/<workspaceId>/workspace.json`
  (`.folder`, a `file://` URI).

## Line schema

| Line | Shape |
|---|---|
| user turn | `{"role":"user","message":{"content":[{"type":"text","text":"<timestamp>Wednesday, Nov 11, 2026, 11:11 AM (UTC-6)</timestamp>\n<user_query>…</user_query>"}]}}` |
| assistant turn | `{"role":"assistant","message":{"content":[{"type":"text","text":…} or {"type":"tool_use","name":…,"input":{…}}]}}` |
| turn end | `{"type":"turn_ended","status":"success"}` (no `role`) |

- **Only user turns carry a time**, inside the `<timestamp>` tag, in local time with the UTC
  offset. Every user turn had one on 2026-11-11 (34 of 34). Assistant turns have none: date
  them by the user turn before them.
- **No tool results.** The transcript keeps the tool call (`tool_use`), never what the tool
  returned. A claim that rests on a tool's output cannot be quoted from here.
- The session id is the `<uuid>` in the file name. The file has no header line.

Resume: `cursor-agent --resume <uuid>` (CLI chats). IDE chats open from the IDE's chat history.

## Strategy H1: Triage

```bash
rg -l -i -g '*.jsonl' "<kw>" ~/.cursor/projects/*/agent-transcripts/ 2>/dev/null
```

## Strategy H2: Full-text content search (with provenance)

The id comes from the file name and the project from the folder, so use a loop, not `xargs`.
The filter is total: it skips `turn_ended` lines and non-text blocks.

```bash
KEYWORD="authentication"
for f in $(rg -l -i -g '*.jsonl' "$KEYWORD" ~/.cursor/projects/*/agent-transcripts/ 2>/dev/null); do
  sid=$(basename "$f" .jsonl); proj=$(echo "$f" | sed -E 's#.*/projects/([^/]+)/agent-transcripts/.*#\1#')
  jq -rc --arg k "$KEYWORD" --arg sid "$sid" --arg p "$proj" '
    select(.role=="user" or .role=="assistant") | . as $l
    | (.message.content // [])[]
    | select(.type=="text" and ((.text // "") | ascii_downcase | contains($k|ascii_downcase)))
    | {sid:$sid, project:$p, role:$l.role,
       ts:((.text | capture("<timestamp>(?<t>[^<]+)</timestamp>").t) // null),
       snippet:(.text[0:200])}' "$f" 2>/dev/null
done | head -30
```

## Strategy H3: Session listing (uuid → cwd + start + title)

```bash
# CLI chats
for m in ~/.cursor/chats/*/*/meta.json; do
  jq -rc --arg id "$(basename "$(dirname "$m")")" '{sid:$id, cwd, created:(.createdAtMs/1000|todate)}' "$m"
done | sort
# IDE chats (title + workspace id)
sqlite3 -readonly "$HOME/Library/Application Support/Cursor/User/globalStorage/state.vscdb" \
  "select composerId, workspaceId, datetime(createdAt/1000,'unixepoch'), json_extract(value,'$.name')
   from composerHeaders where isArchived=0 and isSubagent=0 order by createdAt desc"
```

## Strategy H4: Read a session in order

```bash
F=$(ls ~/.cursor/projects/*/agent-transcripts/<uuid>/<uuid>.jsonl)
jq -r 'select(.role) | . as $l | (.message.content // [])[] | select(.type=="text")
  | "[\($l.role)] \(.text)\n---"' "$F" | head -200
```

## Strategy H5: Tool calls (what the agent tried to do)

```bash
jq -rc 'select(.role=="assistant") | .message.content[] | select(.type=="tool_use")
  | {tool:.name, input:(.input|tostring|.[0:160])}' "$F"
```

## Pitfalls

- **Skip scratch and bridge sessions.** `private-tmp-*` project folders are scratch runs started
  from other agents, and any project folder or cwd that contains `slack-via-cursor` is this
  skill's own Slack bridge (`scripts/slack_via_cursor.py`, folder
  `Users-<user>-local-share-slack-via-cursor`): every bridge run creates a Cursor chat. Neither is Alex's work.
- `empty-window/` is real work in an IDE window with no folder open; do not skip it.
- The IDE flushes the transcript while a chat runs. A file can be newer than its
  `lastUpdatedAt`, so select by file mtime and filter turns by their `<timestamp>`.

## Citation format

Cite as: `Cursor: <uuid> (cwd: /path, YYYY-MM-DD)` — add `CLI` or `IDE` when you know it.
