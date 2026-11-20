---
name: gather
description: >-
  Fetch Alex's comms and work items (Teams, Outlook mail, calendar, SharePoint, Slack, Jira,
  GitHub) into a local raw store at ~/.gather, verbatim, with a ledger and a
  cursor per source, so bard can run from any host. Use when the user runs /gather, asks to
  pull, refresh, or fetch the raw comms that bard will read, or asks what gather last
  fetched. Fetch only: it never reads meaning into a message. Not for distilling notes,
  that is bard, and not for finding or reading one mail, chat, or meeting, that is m365 or
  archeologist.
allowed-tools: Read, Bash
---

# gather: fetch-only intake for bard

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

OpenCode reaches Slack and Jira natively, but not M365. Claude Code reaches M365 and Jira, but not
Slack: the admin blocks Claude's Slack app. So gather uses both. `gather.py` runs on any host that has
`claude`, `opencode` and `gh` installed. For M365 and Jira it calls `claude -p` (haiku, built-in tools off,
`--permission-mode dontAsk`, `--no-session-persistence`) to make exact MCP calls. For Slack it calls
`opencode run`. In both cases it stores the tool result text byte for byte. bard then reads local files only.

Provider note for Slack: the runner model reads every Slack result, so Slack text goes to that model's
provider. gather tries `claude-agent/haiku` first, and falls back to `opencode-go/deepseek-v4.1-flash`
(`#high`). A Cursor model does not work here: it cannot call OpenCode MCP tools (verified 2026-11-20).
A fallback is written to the run log.

Spec: `references/spec.md`. Run the script by its full path:
`python3 ~/.agents/skills/gather/scripts/gather.py <command>`.

## Commands

```text
gather.py run [--sources a,b] [--since 1d|ISO] [--root ~/.gather] [--max-pages 40] [--me ADDR]
gather.py status                 # cursors and the last ledger
gather.py prune [--older-than 30d]   # delete old raw day folders and logs
```

`dontAsk` denies every tool not in `--allowedTools`. Without it, an unlisted MCP tool ran live.

Exit: 0 every source fetched (a source not built yet, such as `teams_channels`, is reported
but does not fail the run); 1 any error, cap, or other gap; 3 any guard abort; 2 usage.
`<me>` (mail) and the display name come from `get_me` at run start unless `--me` / `--me-name` are given. Never write an address outside `~/.gather`: the raw `args` hold Alex's address and display name, so keep them out of the vault, this repo, tickets, and commits.
If `get_me` fails, each requested window source gets `error: get_me failed`. `jira`, `github`, and `github_activity` do not need `me`, so they still run. One ledger file is written per run. `state.json` and the ledger are saved after each source, so a crash or Ctrl-C keeps the finished sources. Exit 1.
A guard abort stops the run: later sources get `not fetched: run stopped after a guard abort`.

## Sources

| Source | Kind | Reached by | State in slice 1 |
|---|---|---|---|
| `teams_chats` | window | `chat_message_search`, `recipient` = me | real |
| `teams_mine` | window | `chat_message_search`, `sender` = me | real |
| `mail` | window | `outlook_email_search`, recipient = me and sender = me | real, live 2026-11-13 |
| `calendar` | window | `outlook_calendar_search`, cursor to now plus 14 days (upcoming deadlines); one chain, not chunked | real, live 2026-11-13 |
| `sharepoint` | window | `sharepoint_search`, `author` = my display name (the mail matches nothing, seen live) | real, live 2026-11-13; docs only opened are out of reach |
| `github` | snapshot | `gh search prs`: review requested (open), and involves me, updated since the last good run minus 1 day (`last_ok` in `state.json`), else 7 days or `--since`. Never as `acastro2` (personal): that account gives `not fetched: active gh account is the personal one`. Each record carries the login | real, live 2026-11-13 |
| `github_activity` | stream | My own GitHub events (`gh api users/<login>/events`, 3 pages of 100), then the timeline of each issue or PR they touch or `gh search prs --involves=@me` finds: comments, reviews, closes. Newest activity first, up to 200 timelines. Same window and personal-account rule as `github`. Why and limits: `references/spec.md` | real, live 2026-11-13 |
| `slack` | window | OpenCode Slack tools through `opencode run --agent gather-slack`. One span from the cursor, not chunked. First `read_user_profile` (args `{"response_format": "detailed"}`: with `{}` the model added a `user_id` key and the call failed) for my user id (none gives `error: no slack user id`). Then three `search_public_and_private` chains: DMs (`channel_types` `im,mpim`), mentions of me, and my own posts, each from the day before the window start (`after:` leaves out the date typed). Then `read_channel` for each DM channel found (`oldest` = window start), and `read_thread` for each thread a hit points to (`thread_ts` in the permalink, else the `p<digits>` part for a hit outside the DM channels), deduped. Up to 10 calls per runner round, paged by the `cursor` in `pagination_info`. Items = search hits. No `get_me` needed | built 2026-11-20; live run is the open check |
| `teams_channels` | window | channel reads, from channels found in `teams_mine` | `not fetched`: no channel hit seen yet, shape unverified |
| `jira` | snapshot | Atlassian MCP: every open issue assigned to me (`assignee = currentUser() AND statusCategory != Done`), then `getJiraIssue` with `expand=changelog` per issue, up to 10 per `claude -p` round; bard filters by changelog date | real, live 2026-11-13 |

A window source other than `calendar` is fetched in day chunks: its window (cursor to now) is cut into one-day spans, oldest first. Each chunk is a full paging chain with `afterDateTime` = chunk start and `beforeDateTime` = chunk end. `--max-pages` counts per chunk, so a busy week no longer hits the cap in its first days.

Proven live 2026-11-13: teams_chats, teams_mine, mail, calendar, sharepoint, github, github_activity, jira (including two spilled issues of 61 KB and 92 KB). A page cap has not happened live yet. `beforeDateTime` was verified live 2026-11-13 on `chat_message_search` and `outlook_email_search`.

Slack runs `opencode run` in `~/.gather/run-opencode`. gather writes one static `opencode.jsonc` there, and only when the file is missing or different: a rewrite before each run raced OpenCode's config reload and gave `Agent not found` (live 2026-11-20). Agent `gather-slack` denies every tool and allows the four Slack read tools, and the config lifts OpenCode's 51200-byte cut on tool output. The parser still allows only the tools of each round: a tool part outside them is a guard abort. A part with `metadata.truncated` is `error: spill`. A failed run on the first model (non-zero exit, timeout, an error event, or calls asked but no tool part in the output) is retried once on the opencode-go model, which then stays for the rest of the run. The prompt tells the model to pass each args object exactly as given and add no keys.

`claude-agent` models also save Claude Code sessions, tool results included, in Claude Code's own project folder for the run-opencode cwd (the folder name is the cwd path with every non-alphanumeric character as `-`). gather removes that folder after every attempt. It is gather's own cwd folder; gather skips it if it is a symlink and touches no other path. OpenCode saves every run as a session even with `--archived`, so gather deletes each session id it sees in stdout with `opencode session delete`. A delete that fails writes the id to `run-opencode/orphans` (0600), and the next run deletes it first. gather never touches a session it did not create. At the start and end of a run, gather also lists sessions in that cwd and deletes those whose directory is exactly the cwd, which catches a run killed before it printed an id.

## Store (`~/.gather`)

```text
raw/<source>/<YYYY-MM-DD>/<run_id>-<n>.json   one file per tool call
state.json                                    {"cursors": {window source: ISO time}, "last_ok": {snapshot source: ISO time}, "covered_from": {window source: ISO time}}
ledger/<run_id>.json                          {"sources": {source: line}}
logs/<run_id>.log                             error details (exception and tool text), may hold private text
run/                                          cwd of claude -p, so no session lands in a real project
run-opencode/                                 cwd of opencode run: opencode.jsonc (written once), and orphans (session ids not yet deleted)
```

Raw record: `{source, tool, args, run_id, fetched_at, provenance: "verbatim", content}`.
`content` is the tool result text, never the model's reply. `args` are the arguments the
model actually sent. A large result (about 50 KB and up) arrives in the stream as a `<persisted-output>`
preview; gather takes the full text from the same line's `tool_use_result`. The file the
preview names is deleted when the run ends, so it is never read. The runner sets
`MAX_MCP_OUTPUT_TOKENS=200000`: above the default cap the result is only an error text
(`Error: result (N characters) exceeds maximum allowed tokens`) with no data. Either case
without the full text fails the source with `error: spill`.

## Ledger lines

Every source in a run gets exactly one line:

- `fetched N calls, M items`: complete. An empty result is `fetched 1 calls, 0 items`, not a gap.
- `partial: N calls, M items, K issue errors`: a `jira` run where K `getJiraIssue` calls came back as errors. Those issues have no record (N counts stored records, M the issue keys the search found). The records read are stored, `last_ok` does not move, the error text is in the run log, and the exit is 1. Treat it as a coverage gap.
- `error: state unreadable`: `state.json` is not a JSON object, or its `cursors`, `last_ok`, or `covered_from` is not an object. Every requested source gets this line, nothing is fetched, and `state.json` is left as it was.
- `error: <reason>`: nothing stored. The reason is fixed text: `claude failed`, `gh failed`,
  `tool error`, `spill`, `unexpected result`, `call mismatch`, `paging`, `no jira site`,
  `unknown source`, `get_me failed`, `opencode failed`, `no slack user id`. The detail (exception text, start of the tool result)
  goes to `logs/<run_id>.log` (0600), never to the ledger.
  - `unexpected result`: a non-error result that is not JSON or the connector's empty text
    `(<tool> completed with no output)` (an auth page, for example); or a JSON body whose only keys
    are `error`, `message`, `code`, `status`, `statusCode`; or a Jira search without
    `{"issues": {"nodes": [...]}}`, or one that says there is a next page but gives no cursor.
  - `call mismatch`: the model changed the calls or their arguments three times in a row.
  - `paging`: a page says `moreResults` is true but gives no `nextOffset` or `nextCursor`. A page
    with `moreResults: false` ends paging even if it carries a `nextOffset`.
  - `no jira site`: no Atlassian site with `read:jira-work` scope.
  - `opencode failed`: `opencode run` failed on both models, or another Slack-run error with no better reason.
  - `no slack user id`: the Slack profile text had no `User ID: U...`.
- `capped at N pages`: a chain stopped at `--max-pages` (per chunk), or a page had as many items as its `limit`
  and no end hint. The pages read are stored. The cursor moves to the start of the capped chunk
  (never backwards), so the next run resumes at the capped day; `covered_from` moves to the window
  start only if a chunk before the capped one finished. If the first chunk caps (or the source is `calendar`), the cursor
  stays, or pins to the window start when there is none. A `--since` later than the cursor leaves it alone. `jira` and `github` have no cursor.
  To get past a very busy day, raise `--max-pages` for that run.
- `capped at gh limit 100`: a `gh search prs` query returned 100 items, the limit. `gh` has no
  paging here, so older items are cut. The records are stored; narrow the window with `--since`.
- `capped at events limit 300`: `github_activity` read 3 full pages of events, all inside the window. Older events are cut, and the events API keeps no more, so `last_ok` still moves: the gap is reported once.
- `capped at 200 timelines`: `github_activity` touched more than 200 items. It fetched the 200 with the newest activity. `last_ok` still moves, so a busy day does not cap every later run.
- `aborted: guard <tool>`: the model called a tool outside the allowlist (all 135 MCP tools,
  write tools included, stay visible to haiku). Nothing stored, cursor stays, exit 3.
- `not fetched: <why>`: the source is not built yet (`teams_channels`), the run stopped after a guard abort, the active `gh` account is the personal one, or the source needs the display name and `get_me` gave none (`not fetched: no display name from get_me`).

`slack` is a window source for the cursor rules below, but it has no day chunks and it does not start `get_me`. A cap on any Slack chain gives `capped at N pages`; the cursor then stays or pins to the window start, and `covered_from` does not move. A read page that has neither a `cursor` nor `no more` ends its chain, because a message count cannot be read from the page; only a full search page is a cap.

A window source's cursor moves to the run start minus 15 minutes, only on `fetched`, and
never backwards (after a cap, see `capped at N pages`). The 15 minutes catch a message that Teams or mail search indexed late. First
run: 7 days back. A `--since` later than the cursor, or with no cursor, does not move it: the
gap behind it was not fetched. A window source also records `covered_from`: the start of the earliest window it fetched. It only moves earlier, and bard reads it to find a gap before its own watermark. A snapshot source (`github`, `jira`) records `last_ok` the same way and has no `covered_from`. `github_activity` also keeps `last_ok`, and it moves even after a cap. Treat any line that is not `fetched` as a coverage gap, never as "nothing there".

## Retention

Raw files and logs older than 30 days are noise. Run `gather.py prune --older-than 30d` weekly. It deletes `raw/<source>/<YYYY-MM-DD>/` day folders and `logs/<run_id>.log` files older than the limit, by the date in the name, and prints how many it removed. It never touches `state.json` or `ledger/`.

## Privacy

Raw comms stay in `~/.gather` (folders 700, files 600). The Slack runner model sees every Slack result (see the provider note above). Never copy them into the vault, this repo, a ticket, or a
commit. Never write an address outside `~/.gather`: the raw `args` hold Alex's address and display name. Use `--root` with a temp dir for tests.
