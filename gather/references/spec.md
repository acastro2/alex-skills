# Spec: gather — fetch-only intake for bard

Status: built 2026-11-13; `slack` added 2026-11-20. Contracts below match `scripts/gather.py`. Owner: Alex.

## Why

bard fetches and distills in one run, but no single host reaches every source.
Claude Code has M365 and Jira, Cursor had Slack, OpenCode had neither. So bard ran in
three places. Update 2026-11-13: OpenCode now reaches Slack and Jira natively (commit af5f36a), so Slack left gather. Update 2026-11-20: Slack came back, because bard's own Slack reads left Slack as the one source with no raw store, no cursor, and no ledger line. gather now fetches Slack through `opencode run` (contract 7). `gather` takes over the fetching. It writes raw, verbatim payloads to a local
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

## Facts added 2026-11-20 (Slack, verified live)

- `claude -p` cannot reach Slack: `claude mcp list` shows `claude.ai Slack` as `Needs authentication`,
  and the MyQ admin blocks Claude's Slack app.
- OpenCode reaches Slack with Cursor's approved client id. `opencode run --agent <a> --archived
  --format json -m <model> "<prompt>"` runs headless. Each tool call is one stdout line:
  `{"type":"tool_use","sessionID":"ses_...","part":{"type":"tool","tool":"slack_slack_read_channel",
  "state":{"status":"completed","input":{...},"output":"<text>","metadata":{"truncated":false,...}}}}`.
  `state.output` equals the MCP text byte for byte.
- No OpenCode API endpoint calls an MCP tool without a model, so a model is in the loop.
- Project config in the run cwd (`opencode.jsonc`) is honored. An agent that denies `*` and then
  allows only the Slack read tools blocked `glob`: no tool event came back for it.
- OpenCode cuts tool output at `tool_output.max_bytes` (default 51200). The run cwd config raises it
  (`max_bytes: 20000000`, `max_lines: 1000000`). `metadata.truncated` reports a cut.
- Results are JSON: search gives `{"results": "<markdown>", "pagination_info": "<text>"}`;
  `slack_read_channel` gives `{"messages": ..., "pagination_info": ...}`; `slack_read_user_profile`
  gives `{"result": "User ID: U...\n..."}`. `pagination_info` is either
  ``For the next page of results use cursor `<c>` `` or `There are no more messages available.`
- A search hit is markdown: `### Result i of n`, then `Channel: <name> (ID: C...)`, `Participants`,
  `From`, `Time`, `Permalink`, `Text`.
- Every `opencode run` saves a session in `~/.local/share/opencode/opencode.db` (directory = run cwd),
  even with `--archived`. `opencode session delete <id>` removes the session, its messages and parts.
- The runner model reads every result. Cursor models cannot use MCP tools through OpenCode: no
  `tool_use` event, and the model says "Tool not found". Model order (Alex, 2026-11-20):
  `claude-agent/haiku`, then `opencode-go/deepseek-v4.1-flash` (`high`).
- OpenCode reports parallel tool calls in completion order, not request order (live 2026-11-20: a 7-day run failed `call mismatch`). Slack rounds match each call to its request by exact tool and args; `claude -p` rounds keep the positional match.
- Rewriting `opencode.jsonc` right before each `opencode run` raced OpenCode's config reload: every
  call failed with `Agent not found: "gather-slack"`. The same run without the rewrite worked.
- `claude-agent/haiku` completed `slack_read_user_profile` with `{"response_format": "concise"}`.
  With `{}` it added `user_id: ""` and the call failed. It saves Claude Code sessions (tool results
  included) under `~/.claude/projects/<cwd, every non-alphanumeric character as ->/`.
- Not yet verified live: a full `gather.py run --sources slack` run, an empty search result, and the
  message format of a `read_channel` page.

## Sources (first cut)

| Source | Kind | Calls |
|---|---|---|
| `teams_chats` | window | `chat_message_search` `query:"*"`, `recipient:<me>`, `afterDateTime:<cursor>`, page by `nextOffset`; in day chunks (contract 4) |
| `teams_mine` | window | same with `sender:<me>`; its channel hits name the channels Alex posted in |
| `teams_channels` | window | for each channel found in `teams_mine`: `teams_list_channel_messages` (roots), then replies per root (`parentMessageId`); keep only items with activity after the cursor |
| `mail` | window | `outlook_email_search` `recipient:<me>` and `sender:<me>`, `afterDateTime:<cursor>` |
| `calendar` | window | `outlook_calendar_search` over cursor → now + 14 days (upcoming deadlines), one chain |
| `sharepoint` | window | `sharepoint_search` `query:"*"`, `author:<display name>` (the mail matches nothing), `afterDateTime:<cursor>` (docs Alex authored or changed; docs he only opened are out of reach) |
| `jira` | snapshot | `searchJiraIssuesUsingJql` `assignee = currentUser() AND statusCategory != Done` (no date: bard filters by changelog), then `getJiraIssue` `expand: changelog` per hit, in batches of up to 10 per round |
| `github` | snapshot | `gh search prs --review-requested=@me --state=open` and `gh search prs --involves=@me --updated=>=<cursor date>` |
| `slack` | window | `opencode run`, Slack tools only (contract 7): user profile, three searches (DMs, mentions of me, my posts), `read_channel` per DM channel, `read_thread` per thread; one span, no day chunks |
| `github_activity` | stream | `gh api users/<login>/events?per_page=100&page=1..3`, `gh search prs --involves=@me --updated=>=<date> --json number,repository,updatedAt`, then `gh api repos/<repo>/issues/<n>/timeline?per_page=100 --paginate --slurp` per touched item, newest activity first, max 200 |

`<me>` comes from `get_me` at run start, never from a file in the repo.
Out of scope: AI session stores and scribe notes (already local files bard reads), Planner,
To Do, Todoist (no host has the tools), Graph `insights/used`.

`github_activity` exists because `github` keeps only PR metadata, and its search missed every PR
commented on or closed in the 25 minutes before a live check (2026-11-13). The events API is
real time and carries comment bodies, but in that check it dropped 3 of 21 comments and all 11
closes; the timelines hold them. `IssuesEvent` covers plain issues, which search does not return.
A full involves search is `capped at gh limit 100`. On any cap `last_ok` still moves: the events
API keeps only 300 events, so a retry cannot fetch more, and a stuck mark widens every later
window. `M items` is in-window events plus timelines fetched. Known gap: inline review comments
are in the events (when not dropped) but not in the timelines.

## Contracts

1. **Raw record.** One JSON file per tool call:
   `{source, tool, args, run_id, fetched_at, provenance: "verbatim", content}`.
   `content` is the tool result text, byte-for-byte, never the model's reply. `args` hold Alex's
   address and display name, so a record never leaves `~/.gather`.
2. **Guard.** Any `tool_use` whose name is not in the round's allowlist, or any built-in tool
   use, aborts the source: exit 3, no raw files from that round, ledger `aborted: guard`.
3. **Ledger.** Every source in the run gets exactly one line:
   `fetched N calls, M items` | `partial: N calls, M items, K issue errors` | `error: <reason>` |
   `capped at N pages` | `capped at gh limit 100` | `capped at events limit 300` | `capped at 200 timelines` | `aborted: guard <tool>` | `not fetched: <why>`.
   An empty result is `fetched 1 calls, 0 items`, never a missing line. `partial` is a `jira`
   run where K `getJiraIssue` calls failed: the records read are stored, `last_ok` stays, exit 1.
   The reason is fixed text (`claude failed`, `gh failed`, `tool error`, `spill`,
   `unexpected result`, `call mismatch`, `paging`, `no jira site`, `unknown source`,
   `get_me failed`, `state unreadable`, `opencode failed`, `no slack user id`); exception and tool text go to `logs/<run_id>.log`
   (0600), never the ledger. One ledger file is written per run and rewritten after each
   source, together with `state.json`, so a crash keeps the finished sources. A corrupt
   `state.json` (not an object, or `cursors`, `last_ok`, `covered_from` not an object) gives every
   source `error: state unreadable`, and the file is left as it was. A guard abort stops the run; later sources get
   `not fetched: run stopped after a guard abort`. A `get_me` failure marks only the window sources `error: get_me failed`; `jira`, `github`, and `github_activity` still run, and one ledger holds all lines.
4. **Cursor and chunks.** A window source's cursor moves to the run start minus 15 minutes
   (overlap: Teams and mail search can index a message late) only when the source ended
   `fetched`. Error or abort leave it where it was. It never moves backwards. A `--since` later
   than the cursor, or with no cursor, leaves it where it was. Snapshot sources have no cursor;
   they keep `last_ok` in `state.json`, and `github` asks for PRs updated since `last_ok` minus
   one day. First run with no cursor: 7 days back.
   The CLI fetches a window source other than `calendar` in one-day chunks, oldest first. Each
   chunk is a full paging chain with `afterDateTime` = chunk start and `beforeDateTime` = chunk
   end. A page with as many items as its `limit` and no end hint, `--max-pages` reached in a
   chunk, or a `gh` result with 100 items, ends the source `capped`. On a capped chunk the pages
   read are stored, later chunks are not fetched, and the cursor moves to the start of the capped
   chunk (never backwards, and not with a `--since` later than the cursor). `covered_from` moves
   to the window start only if a chunk before the capped one finished. The next run resumes at the
   capped day. `moreResults: false` ends paging even when a `nextOffset` is present.
   `state.json` is written atomically.
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
   `(<tool> completed with no output)`; anything else is `error: unexpected result`. So is a JSON
   body whose only keys are `error`, `message`, `code`, `status`, `statusCode`, and a Jira search
   result that is not `{"issues": {"nodes": [...]}}`.
7. **Slack.** Source `slack` is a window source (cursor and `covered_from`) with one span, because
   Slack `after:` is a date, and no day chunks. It does not start `get_me`. Window start = cursor,
   else `--since`, else 7 days back. The runner is `opencode_runner(root)`; the `runner(calls, allowed)
   -> stdout` seam is the same as for `claude -p`, and `run_round` takes the parser (`parse_opencode`).
   `run(..., slack_runner=...)` takes a separate runner, so tests inject a fake one.
   - **Calls.** `slack_slack_read_user_profile {"response_format": "detailed"}` gives my user id from `User ID: (U\w+)` (none:
     `error: no slack user id`). Then three `slack_slack_search_public_and_private` chains:
     DMs (`channel_types` `im,mpim`), mentions (`keywords: ["<@U...>"]`), and own posts
     (`filters: "from:<@U...> after:<D>"`), all with `limit: 20`, `include_context: false`,
     `sort: "timestamp"`. `D` = the day before the window start (UTC date), because `after:` leaves
     out the date typed. Then, up to 10 calls per runner round: `slack_slack_read_channel` for each DM
     channel id from the DM search (`oldest` = window start epoch seconds, `limit: 100`), and
     `slack_slack_read_thread` for each thread (`limit: 100`). A thread target is the permalink's
     `thread_ts` when present; else, for a hit outside the DM channels, the `p<digits>` path part as
     `<first 10>.<rest>`. Targets are deduped by `(channel, ts)`.
   - **Paging.** The `cursor` in `pagination_info` gives the next call a `cursor` argument. `no more`
     ends the chain. Neither, on a full search page, is `capped at N pages`. A read page with neither
     ends its chain: the page has no message count to compare. `--max-pages` counts per chain. A cap
     leaves the cursor where it was, or pins it to the window start, as for a capped first chunk.
   - **Items and ledger.** Items = total search hits. Line: `fetched N calls, M items`. N counts every
     stored record, the profile included.
   - **Parse.** A tool part whose `tool` is not in the round's allowed tools is a `GuardError`.
     `status` `completed` gives `state.output` as the content. `error` is a tool error with
     `state.error`. `metadata.truncated` true is a `SpillError`. The tools are the OpenCode ids
     `slack_slack_read_user_profile`, `slack_slack_search_public_and_private`,
     `slack_slack_read_channel`, `slack_slack_read_thread`.
   - **Runner.** cwd `<root>/run-opencode` (0700). It writes `opencode.jsonc` there from a constant,
     only when the file is missing or different, never per round: agents (V2 keys `agents` and
     `system`) `gather-slack` (mode primary, system prompt = the exact-calls instruction, which says to
     pass each args object exactly as given and add no keys; permissions deny `*` then allow the four
     Slack read tools), `tool_output` limits, and `"snapshots": false`. The per-round allowlist stays
     in the parser. Command: `opencode run --agent gather-slack --archived --format json -m
     <model> <prompt>`.
   - **Model fallback.** `SLACK_MODELS` = `claude-agent/haiku`, then `opencode-go/deepseek-v4.1-flash`
     (`high`). A Cursor model is not used: it cannot call OpenCode MCP tools. A runner failure
     (non-zero exit, timeout, an error event, or calls asked but no tool part in the output) on the first
     model retries that round once on the second and keeps it for
     the rest of the run. The run log gets `slack: fell back to opencode-go: <reason>`. A failure on
     the last model is `error: opencode failed`.
   - **Cleanup.** Every `sessionID` seen in stdout is deleted with `opencode session delete` in a
     `finally`. A failed delete writes the id to `<root>/run-opencode/orphans` (0600); the next run
     deletes orphans first. gather never touches a session it did not create. A run killed by a
     timeout keeps only the ids that reached stdout before the kill, so the first call and
     `runner.close()` (called from `cmd_run` in a `finally`) also run `opencode session list --format
     json` in the run cwd and delete every session whose `directory` equals the resolved cwd exactly,
     never by the list alone, because a non-git folder can share a project with other folders. A list
     failure is a note in `runner.notes`, never an error. After every attempt the
     `~/.claude/projects/<run-opencode cwd>` folder (the name `_project_dir` gives) is removed whole,
     because `claude-agent` models save Claude Code sessions there. It is skipped if it is a symlink,
     and no other path is touched.
   - **Privacy.** The runner model reads every Slack result, so Slack text goes to that model's
     provider.
   - **Not in scope.** Slack canvases and files, channel history without Alex in it, the `with:` search.

8. **bard reads.** bard sweeps every raw file not in `gather_seen` and copies the gather ledger
   lines into its coverage ledger. A source fetched more than `--max-age-hours` (default 24) ago is a gap.
   Recorded through `bard/scripts/state.py`.

9. **Retention.** `gather.py prune --older-than 30d` deletes `raw/<source>/<YYYY-MM-DD>/` day
   folders and `logs/<run_id>.log` files older than the limit (by the date in the name), and
   returns how many. It never touches `state.json` or `ledger/`. Run it weekly.

## Seams under test

- `claude` subprocess (boundary): an injected runner. Unit tests feed it stream-json
  shaped like the real captured runs (synthetic message text, no real data). One opt-in
  integration test (`GATHER_LIVE=1`) runs real `claude -p` for `teams_mine` over 7 days.
- Filesystem: the store root is a parameter (`--root`, default `~/.gather`). Tests use a
  temp dir.
- Clock: run start time is a parameter in the core functions.

## Acceptance

- `uv run --with pytest python -m pytest gather/tests -q` passes (guard, ledger, cursor, chunks,
  spill, prune, pairing tool_use → tool_result by id).
- `uv run --with pyyaml python -m skillcheck` → PASS.
- `GATHER_LIVE=1 python3 gather/scripts/gather.py run --sources teams_mine --since 7d --root <tmp>`
  writes ≥1 raw file whose `content` equals the stream's tool_result text, plus a ledger.
- No new files under `~/.claude/projects/` from that run.

## Not in the first cut

Parallel sources, Planner/To Do/Todoist, `m365` CLI path, removing bard's old lanes. (Slack headless
was in this list until 2026-11-20; it is built, see contract 7.)
