# SOURCE B: Legacy opencode database (HISTORICAL)

**Path**: `~/.local/share/opencode/opencode.db` (SQLite, read-only). Large: always `LIMIT`.
Search this for context from before the Claude Code migration, or when Source A is empty.

## Strategy B1: Full-text search (primary)
```bash
KEYWORD="authentication"
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT s.id, s.title, sm.seq, sm.type, sm.data
  FROM session s JOIN session_message sm ON s.id = sm.session_id
  WHERE json_extract(sm.data, '\$.text') LIKE '%${KEYWORD}%'
  ORDER BY s.time_archived DESC, sm.seq DESC LIMIT 30;"
```

## Strategy B2: Session title search
```bash
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT id, title, time_archived, agent, model FROM session
  WHERE title LIKE '%${KEYWORD}%' ORDER BY time_archived DESC LIMIT 20;"
```

## Strategy B3: Recent context
```bash
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT id, title, time_archived, agent FROM session
  ORDER BY time_archived DESC NULLS LAST LIMIT 20;"
```

## Strategy B4: Legacy message table
```bash
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT s.id, s.title, m.data FROM session s JOIN message m ON s.id = m.session_id
  WHERE json_extract(m.data, '\$.text') LIKE '%${KEYWORD}%'
  ORDER BY s.time_archived DESC LIMIT 30;"
```

## Strategy B5: Todos
```bash
sqlite3 ~/.local/share/opencode/opencode.db "
  SELECT session_id, content, status, priority FROM todo
  WHERE content LIKE '%${KEYWORD}%' ORDER BY priority DESC, status ASC LIMIT 20;"
```

### opencode schema reference

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `session` | Conversation threads | `id`, `title`, `project_id`, `time_archived`, `agent`, `model` |
| `message` | Legacy message store | `id`, `session_id`, `data` (JSON: role, text, agent, mode, path) |
| `session_message` | Modern message projection | `id`, `session_id`, `type`, `seq`, `data` (JSON: time, text, files, agents) |
| `event` | Append-only event log | `aggregate_id` (session_id), `seq`, `type`, `data` |
| `todo` | Per-session task lists | `session_id`, `status`, `priority`, `content` |

Notes: timestamps in `data` are epoch ms (`datetime(ts/1000,'unixepoch')`); JSON columns need
`json_extract()`; use `.mode markdown` / `.headers on` for readable output.
