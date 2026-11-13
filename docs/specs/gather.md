# Spec: gather — fetch-only intake for bard

Status: agreed design, build started 2026-11-13. Owner: Alex.

## Why

bard fetches and distills in one run, but no single host reaches every source.
Claude Code has M365 and Jira, Cursor had Slack, OpenCode had neither. So bard ran in
three places. Update 2026-11-13: OpenCode now reaches Slack and Jira natively (commit af5f36a), so Slack left gather; bard reads it natively. `gather` takes over the fetching. It writes raw, verbatim payloads to a local
store, and bard then reads only local files, from any host (OpenCode by default).

Skill category (AGENTS.md): **Alex's systems**. It records which host reaches which source,
and the calls that are proven.

## Facts this design rests on (verified 2026-11-13)

- Cursor headless is blocked by the admin: `cursor-agent -p` →
  `Your team administrator has disabled headless Cursor CLI usage.`
- `claude -p --model haiku --tools "" --allowedTools <tool>` ran
  `chat_message_search` and `outlook_email_search` headless. The raw `tool_result` text was
  in the `stream-json` stdout (2,621 and 34,309 chars). Cost USD 0.02–0.03 per run.
  M365 and Atlassian connectors show `connected` there; Slack shows `needs-auth`.
- **All 135 MCP tools stay visible to the model, write tools included.** `--allowedTools`
  does not hide them. The guard below is required, not optional.
- A headless run is saved as a Claude Code session unless `--no-session-persistence` is set.
  Saved runs would be swept by bard as coding sessions.
- `m365 doctor` → `auth: missing`. Not used in the first cut.
- Teams: `chat_message_search` with `recipient` returns every message in Alex's chats, but
  **channel posts have no recipient**, so channels need a separate read.
  `sender` = Alex covers chats and channels.
- Max page size: `chat_message_search` 25, `outlook_email_search` 25,
  `sharepoint_search` 50, `teams_list_channel_messages` 50.

## Shape

```text
 /gather (any host; OpenCode by default)
   gather.py run
     ├─ for each source: build a round of exact calls ─► claude -p (haiku, no built-ins,
     │      --no-session-persistence, stream-json) ─► parse tool_use / tool_result pairs
     │      ├─ guard: a tool_use outside the round's allowlist → abort, exit 3, write nothing
     │      └─ paging: read nextOffset / nextCursor in code, next round, until done or cap
     ├─ gh (subprocess) ─► GitHub
     └─ writes ~/.gather/raw/<source>/<YYYY-MM-DD>/<run_id>-<n>.json   (one per tool call)
               ~/.gather/state.json      (cursor per source)
               ~/.gather/ledger/<run_id>.json  (one line per source)

 /bard ─► reads ~/.gather/raw (seen-set `gather_seen`) + ledger, instead of its comms lanes.
          No ~/.gather, or a source missing from the ledger → bard's current lane (fallback).
```

## Sources (first cut)

| Source | Kind | Calls |
|---|---|---|
| `teams_chats` | window | `chat_message_search` `query:"*"`, `recipient:<me>`, `afterDateTime:<cursor>`, page by `nextOffset` |
| `teams_mine` | window | same with `sender:<me>`; its channel hits name the channels Alex posted in |
| `teams_channels` | window | for each channel found in `teams_mine`: `teams_list_channel_messages` (roots), then replies per root (`parentMessageId`); keep only items with activity after the cursor |
| `mail` | window | `outlook_email_search` `recipient:<me>` and `sender:<me>`, `afterDateTime:<cursor>` |
| `calendar` | window | `outlook_calendar_search` over cursor → now |
| `sharepoint` | window | `sharepoint_search` `query:"*"`, `author:<display name>` (the mail matches nothing), `afterDateTime:<cursor>` (docs Alex authored or changed; docs he only opened are out of reach) |
| `jira` | snapshot | `searchJiraIssuesUsingJql` `assignee = currentUser() AND statusCategory != Done` (no date: bard filters by changelog), then `getJiraIssue` `expand: changelog` per hit, in batches of up to 10 per round |
| `github` | snapshot | `gh search prs --review-requested=@me --state=open` and `gh search prs --involves=@me --updated=>=<cursor date>` |

`<me>` comes from `get_me` at run start, never from a file in the repo.
Out of scope: AI session stores and scribe notes (already local files bard reads), Planner,
To Do, Todoist (no host has the tools), Graph `insights/used`.

## Contracts

1. **Raw record.** One JSON file per tool call:
   `{source, tool, args, run_id, fetched_at, provenance: "verbatim"|"model-copied", content}`.
   `content` is the tool result text, byte-for-byte, never the model's reply.
2. **Guard.** Any `tool_use` whose name is not in the round's allowlist, or any built-in tool
   use, aborts the source: exit 3, no raw files from that round, ledger `aborted: guard`.
3. **Ledger.** Every source in the run gets exactly one line:
   `fetched N calls, M items` | `error: <reason>` | `capped at <pages>` | `aborted: guard <tool>` |
   `not fetched: <why>`. An empty result is `fetched 0`, never a missing line. The reason is
   fixed text (`claude failed`, `gh failed`, `tool error`, `spill`, `unexpected result`,
   `get_me failed`); exception and tool text go to `logs/<run_id>.log` (0600), never the
   ledger. A guard abort stops the run; later sources get
   `not fetched: run stopped after a guard abort`. A `get_me` failure marks only the window sources `error: get_me failed`; `jira` and `github` still run, and one ledger holds all lines.
4. **Cursor.** A window source's cursor moves to the run start time only when the source
   ended `fetched`. Error, cap, or abort leave it where it was. It never moves backwards.
   A `--since` later than the cursor, or with no cursor, leaves it where it was.
   Snapshot sources have no cursor; they keep `last_ok` in `state.json`, and `github` asks
   for PRs updated since `last_ok` minus one day. First run with no cursor: 7 days back.
   A page with as many items as its `limit` and no end hint, or a `gh` result with 100
   items, ends the source `capped`. `state.json` is written atomically.
   A window source that ends `fetched` also records `covered_from[source]`: the start of the
   window it fetched. It is kept only when absent or earlier than the stored value, so it never
   moves later. Snapshot sources have none.
5. **Spill.** A result over about 50 KB comes as a `<persisted-output>` preview in the
   message and in full in the line's `tool_use_result` (verified 2026-11-13: 96,003 chars,
   parses). gather stores the full text, or fails with `error: spill`. The spill file is
   deleted at run end, so it is never a source. The runner sets
   `MAX_MCP_OUTPUT_TOKENS=200000`; above the cap the result is only an error text.
6. **No persistence, no ask.** Every `claude -p` call passes `--no-session-persistence` and
   `--permission-mode dontAsk` (without it an unlisted MCP tool ran, live 2026-11-13). The
   runner removes its empty project folder on any exit, and on a timeout also the spilled
   `tool-results` files. A non-error result must be JSON or the connector's empty text
   `(<tool> completed with no output)`; anything else is `error: unexpected result`.
7. **Slack.** Removed 2026-11-13. bard reads Slack natively in OpenCode.

8. **bard reads.** bard sweeps every raw file not in `gather_seen`, marks
   `model-copied` text as not quotable verbatim, and copies the gather ledger lines into its
   coverage ledger. A source fetched more than `--max-age-hours` (default 24) ago is a gap.
   Recorded through `bard/scripts/state.py`.

## Seams under test

- `claude` subprocess (boundary): an injected runner. Unit tests feed it stream-json
  shaped like the real captured runs (synthetic message text, no real data). One opt-in
  integration test (`GATHER_LIVE=1`) runs real `claude -p` for `teams_mine` over 1 day.
- Filesystem: the store root is a parameter (`--root`, default `~/.gather`). Tests use a
  temp dir.
- Clock: run start time is a parameter in the core functions.

## Acceptance

- `python3 -m pytest gather/tests -q` passes (guard, ledger, cursor, spill,
  pairing tool_use → tool_result by id).
- `uv run --with pyyaml python scripts/validate_skill_graph.py` → PASS.
- `GATHER_LIVE=1 python3 gather/scripts/gather.py run --sources teams_mine --since 1d --root <tmp>`
  writes ≥1 raw file whose `content` equals the stream's tool_result text, plus a ledger.
- No new files under `~/.claude/projects/` from that run.

## Not in the first cut

Parallel sources, Planner/To Do/Todoist, `m365` CLI path, Slack headless, removing bard's
old lanes.
