---
name: gather
description: >-
  Fetch Alex's comms and work items (Teams, Outlook mail, calendar, SharePoint, Jira,
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

OpenCode reaches Slack and Jira natively (since 2026-11-13), but not M365; Claude Code reaches
M365 and Jira. Slack is not in gather: bard reads it natively in OpenCode. `gather.py` runs on any host that has `claude` and `gh` installed. It
calls `claude -p` (haiku, built-in tools off, `--permission-mode dontAsk`, `--no-session-persistence`)
to make exact MCP calls, and stores the tool result text byte for byte. bard then reads local files only.

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
If `get_me` fails, each requested window source gets `error: get_me failed`. `jira` and `github` do not need `me`, so they still run. One ledger file is written per run. `state.json` and the ledger are saved after each source, so a crash or Ctrl-C keeps the finished sources. Exit 1.
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
| `teams_channels` | window | channel reads, from channels found in `teams_mine` | `not fetched`: no channel hit seen yet, shape unverified |
| `jira` | snapshot | Atlassian MCP: every open issue assigned to me (`assignee = currentUser() AND statusCategory != Done`), then `getJiraIssue` with `expand=changelog` per issue, up to 10 per `claude -p` round; bard filters by changelog date | real, live 2026-11-13 |

A window source other than `calendar` is fetched in day chunks: its window (cursor to now) is cut into one-day spans, oldest first. Each chunk is a full paging chain with `afterDateTime` = chunk start and `beforeDateTime` = chunk end. `--max-pages` counts per chunk, so a busy week no longer hits the cap in its first days.

Proven live 2026-11-13: teams_chats, teams_mine, mail, calendar, sharepoint, github, jira (including two spilled issues of 61 KB and 92 KB). A page cap has not happened live yet. `beforeDateTime` was verified live 2026-11-13 on `chat_message_search` and `outlook_email_search`.

## Store (`~/.gather`)

```text
raw/<source>/<YYYY-MM-DD>/<run_id>-<n>.json   one file per tool call
state.json                                    {"cursors": {window source: ISO time}, "last_ok": {snapshot source: ISO time}, "covered_from": {window source: ISO time}}
ledger/<run_id>.json                          {"sources": {source: line}}
logs/<run_id>.log                             error details (exception and tool text), may hold private text
run/                                          cwd of claude -p, so no session lands in a real project
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
  `unknown source`, `get_me failed`. The detail (exception text, start of the tool result)
  goes to `logs/<run_id>.log` (0600), never to the ledger.
  - `unexpected result`: a non-error result that is not JSON or the connector's empty text
    `(<tool> completed with no output)` (an auth page, for example); or a JSON body whose only keys
    are `error`, `message`, `code`, `status`, `statusCode`; or a Jira search without
    `{"issues": {"nodes": [...]}}`, or one that says there is a next page but gives no cursor.
  - `call mismatch`: the model changed the calls or their arguments three times in a row.
  - `paging`: a page says `moreResults` is true but gives no `nextOffset` or `nextCursor`. A page
    with `moreResults: false` ends paging even if it carries a `nextOffset`.
  - `no jira site`: no Atlassian site with `read:jira-work` scope.
- `capped at N pages`: a chain stopped at `--max-pages` (per chunk), or a page had as many items as its `limit`
  and no end hint. The pages read are stored. The cursor moves to the start of the capped chunk
  (never backwards), so the next run resumes at the capped day; `covered_from` moves to the window
  start only if a chunk before the capped one finished. If the first chunk caps (or the source is `calendar`), the cursor
  stays, or pins to the window start when there is none. A `--since` later than the cursor leaves it alone. `jira` and `github` have no cursor.
  To get past a very busy day, raise `--max-pages` for that run.
- `capped at gh limit 100`: a `gh search prs` query returned 100 items, the limit. `gh` has no
  paging here, so older items are cut. The records are stored; narrow the window with `--since`.
- `aborted: guard <tool>`: the model called a tool outside the allowlist (all 135 MCP tools,
  write tools included, stay visible to haiku). Nothing stored, cursor stays, exit 3.
- `not fetched: <why>`: the source is not built yet (`teams_channels`), the run stopped after a guard abort, the active `gh` account is the personal one, or the source needs the display name and `get_me` gave none (`not fetched: no display name from get_me`).

A window source's cursor moves to the run start minus 15 minutes, only on `fetched`, and
never backwards (after a cap, see `capped at N pages`). The 15 minutes catch a message that Teams or mail search indexed late. First
run: 7 days back. A `--since` later than the cursor, or with no cursor, does not move it: the
gap behind it was not fetched. A window source also records `covered_from`: the start of the earliest window it fetched. It only moves earlier, and bard reads it to find a gap before its own watermark. A snapshot source (`github`, `jira`) records `last_ok` the same way and has no `covered_from`. Treat any line that is not `fetched` as a coverage gap, never as "nothing there".

## Retention

Raw files and logs older than 30 days are noise. Run `gather.py prune --older-than 30d` weekly. It deletes `raw/<source>/<YYYY-MM-DD>/` day folders and `logs/<run_id>.log` files older than the limit, by the date in the name, and prints how many it removed. It never touches `state.json` or `ledger/`.

## Privacy

Raw comms stay in `~/.gather` (folders 700, files 600). Never copy them into the vault, this repo, a ticket, or a
commit. Never write an address outside `~/.gather`: the raw `args` hold Alex's address and display name. Use `--root` with a temp dir for tests.
