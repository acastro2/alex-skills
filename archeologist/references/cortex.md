# SOURCE C: Snowflake Cortex CLI conversations (CURRENT)

Work done in the **Cortex CLI** (Snowflake / data-engineering tasks) is NOT in the Claude Code
transcripts. It lives under `~/.snowflake/cortex/`. Search it alongside Source A for recent work.

## Storage layout

- `conversations/<uuid>.history.jsonl` -- the messages (one JSON object per line):
  `{content, id, role, user_sent_time}`. `role` is `user` / `assistant`. `content` is an ARRAY of
  blocks: `{type:"text", text}`, `{type:"tool_use", tool_use}`, `{type:"tool_result", tool_result}`.
  Chat text lives in the `text` blocks; `user_sent_time` is the timestamp.
- `conversations/<uuid>.json` -- per-session metadata: `working_directory`, `git_branch`,
  `git_root`, `created_at`, `session_id`, `subagent_name`/`subagent_type`. **The `title` is
  auto-generated junk** ("Chat for session: <uuid>") -- do NOT rely on it; use `working_directory`
  + `created_at` + content instead.
- `history` -- small global file of recent prompts (like CC `history.jsonl`).
- `thread_goals.sqlite` -- one table `thread_goals` (per-thread goals); small, query with sqlite3.
- Per-project plans: `<repo>/.cortex/plans/*.md` (e.g. `~/Developer/**/.cortex/plans/`), markdown
  with frontmatter (`session:`, `working_directory:`). The session UUID is the FILENAME stem.

## Strategy C1: Triage
```bash
rg -l -i -g '*.history.jsonl' "<kw>" ~/.snowflake/cortex/conversations/ 2>/dev/null
```

## Strategy C2: Full-text content search (with provenance)
Session id = the filename stem; timestamp = `user_sent_time`:
```bash
KEYWORD="..."
rg -l -i -g '*.history.jsonl' "$KEYWORD" ~/.snowflake/cortex/conversations/ 2>/dev/null \
| while IFS= read -r f; do sid=$(basename "$f" .history.jsonl); \
    jq -rc --arg k "$KEYWORD" --arg sid "$sid" '
      select(.role=="user" or .role=="assistant")
      | . as $l | (.content // [])[]
      | select((.type // "")=="text"
               and ((.text // "") | ascii_downcase | contains($k|ascii_downcase)))
      | {sid:$sid, ts:$l.user_sent_time, role:$l.role, snippet:(.text[0:200])}' "$f" 2>/dev/null
  done
```

## Strategy C3: Session metadata (map uuid -> project + date)
```bash
jq -rc '{sid:.session_id, cwd:.working_directory, branch:.git_branch, when:.created_at}' \
  ~/.snowflake/cortex/conversations/<uuid>.json 2>/dev/null
```
Scan all at once: `for j in ~/.snowflake/cortex/conversations/*.json; do jq -rc '...' "$j"; done`.

## Strategy C4: Plans (per-repo)
`.cortex/` lives inside git repos, so use `--no-ignore --hidden` or a repo may gitignore it and
rg will silently skip it:
```bash
rg -l -i --no-ignore --hidden "<kw>" ~/Developer/**/.cortex/plans/ 2>/dev/null
```

## Strategy C5: Thread goals
```bash
sqlite3 ~/.snowflake/cortex/thread_goals.sqlite "SELECT * FROM thread_goals LIMIT 20;"
```
