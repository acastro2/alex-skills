# Session stores — per-store index mechanics

Reference for sweep step 3 in `SKILL.md` ("Also scan the time indexes"). Read it before you
scan the stores. Each entry gives the path, the session-start field, and the pitfalls that
already cost a sweep.

- Claude Code: `~/.claude/history.jsonl` (`.timestamp` epoch-ms; `.sessionId`, `.project`).
- Cortex: `~/.snowflake/cortex/conversations/<uuid>.json` → `.created_at`.
- Pi: `~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl` — the filename
  timestamp is the session start (UTC ISO). Pi dir names start with `--`, so
  glob with a `./` prefix or absolute paths: bare `--...` paths are parsed as
  options by `head`/`jq`/`ls`/`find` and silently return nothing. The record
  shape is NOT the same as Claude Code's: a Pi turn is
  `{"type":"message","message":{"role":"user","content":[{"type":"text","text":...}]}}`,
  so the selector is `select(.type=="message" and .message.role=="user")` and the
  text is under `.message.content[]`. A jq filter written against the Claude Code
  shape returns an empty string per line, which looks exactly like "this session
  had no user messages" — verify with `jq -r '.type' <file> | sort | uniq -c`
  before concluding a session is empty.
- **opencode (every sweep, since 2026-09-25)**: `~/.local/share/opencode/opencode.db`,
  opened read-only (`sqlite3 -readonly`). Live data is in `session_v2` (one row per
  session; `parent_id IS NULL` = main session, non-null = subagent) and
  `session_message` (`session_id`, `type`, `time_created` epoch-ms, `data` JSON). Select
  sessions that have `session_message.time_created` newer than `watermark`, not
  `session_v2.time_created` alone, because sessions span days. Text lives in `data`: a
  `user` row has `.text`; an `assistant` row has `.content[]`, keep only
  `type=="text"` parts (drop `reasoning` and tool parts). Skip subagent sessions unless
  the parent points at them, and skip `*-smoke`/`cctest` scratch directories. The
  legacy `session` table is stale (last row 2026-08); never use it as the cursor.
  Verified 2026-09-25: 139 sessions (51 main) in one week, the second-largest store
  after Claude Code, and the first opencode-free sweep missed all of it.
  **Compute the cursor in code, never type it.** Convert `watermark` with
  `datetime.fromisoformat(...).timestamp()*1000` in the same script that queries. On
  2026-10-14 a hand-typed epoch in a lane brief was three days in the future, so the lane
  saw zero messages until it caught the error itself. **Query order matters on this
  2.7 GB file:** select from `session_message` by `time_created` first, then look up each
  `session_v2` row by its exact `id`. A `LIKE` on `session_v2.id` joined to
  `session_message` ran past the 120 s tool timeout twice (2026-10-14).
- **Shell pitfall in the vault:** `grep` is aliased to `ugrep` in Alex's shell, and an
  `ls | grep` inside the vault hung until the tool timeout (2026-10-14). List or match
  vault files with Python (`glob`, `os.listdir`) instead.
- **Read and write the state through `scripts/state.py`** (`show`, `record`). It owns the
  merge rules, refuses a watermark that moves backwards or names a whole day, and writes
  atomically. Do not hand-edit `.bard-state.json`.
- **scribe meeting notes** (since 2026-09-03): `<vault>/Scribe/Meetings/Transcripts/*.md`,
  one note per meeting written by the `scribe` skill (Teams transcripts and HiDock
  call recordings). **Select by the seen-set, not by `date`:** sweep every note whose
  vault-relative path is not in `scribe_seen` in `.bard-state.json`. Frontmatter `date`
  is the meeting start, and scribe often writes a note a day or more after the meeting
  (late HiDock sync, Teams transcript not ready). By then `watermark` has moved past
  that `date`, so a date filter skips the note forever. Do not use file mtime either:
  vault sync can rewrite it. If `scribe_seen` is absent, seed it with the notes whose
  `date` is more than 7 days before `watermark`, and sweep the rest; dedupe absorbs any
  repeat. A note scribe rewrites with `--force` keeps its path and is not re-swept; ask
  Alex if he wants it swept again. They are the meeting-side twin of the coding
  sessions: same STEP 1-5, same quote rule. Read the whole note; `## Summary`,
  `## Decisions`, `## Actions` are scribe's digest, `## Transcript` is the verbatim
  source and the only thing you may quote. Provenance is the note path
  (`Obsidian: Scribe/Meetings/Transcripts/<file>`) plus the frontmatter
  `provenance` block; never invent more. HiDock notes carry diarization labels
  (`speaker 0`, `speaker 1`, ...), and scribe adds a hedge — `speaker 1 (likely
  Alexandre Castro)` — only where the transcript's own text supports it, quoting that
  text in `provenance.speaker_hints`. Treat a hedged name as likely, not certain: when
  you attribute a quote or a commitment, keep the hedge or say the speaker is inferred.
  A plain `speaker N` is unattributed — never guess who it was. `## Actions` lines owned
  by Alex are board candidates for `Todo.md`; the others are context, not tasks. scribe
  writes everything, including standups and 1:1s: the half-life filter in STEP 1 is
  where the noise dies, so expect to drop most of them. People and HR material inside a
  note is distilled like any other durable knowledge, into the `People` hub — the
  consumer-PII ban covers third-party datafiles, not meeting knowledge (Alex,
  2026-09-24).
