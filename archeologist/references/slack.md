# SOURCE J: Slack (CURRENT, PROMOTED FOR COMMUNICATIONS)

## Contents

- Access per host
- Availability check
- Read-only rule
- What it can search
- Search syntax
- Coverage: break J down by substore
- What is not verified yet
- Citation format

Slack is where most day-to-day talk happens at Alex's current job: DMs, group DMs, channels,
threads, canvases. Treat it like Source G (Microsoft 365): promoted into Tier 1 for any
who-said, who-asked, or what-did-we-agree question, and searched on every sweep.

## Access per host

The only access path is Slack's official MCP server, `https://mcp.slack.com/mcp`. Slack accepts
only pre-registered OAuth clients, and each workspace admin controls a per-app allowlist. On
Alex's MyQ workspace Cursor's app is approved and Claude's app is blocked (verified 2026-11-13),
so which host works depends on whose client id it can use.

| Host | Path |
|---|---|
| OpenCode | the Slack MCP server directly, reusing Cursor's approved client id with its registered loopback redirect `http://localhost:8787/callback`. Configured in `~/.config/opencode/opencode.jsonc`; sign in once with `/mcps`. Native `slack_*` tools, no bridge |
| Claude Code | the Slack MCP server directly, only if the admin approves Claude's app. MyQ blocks it (`You are not authorized to install Claude on MyQ`), so treat Claude Code as unavailable for Slack there |
| Cursor IDE | the Slack MCP server directly (Cursor plugin `slack`, or Settings → MCP) |

The workspace admin must approve the MCP client app. If sign-in fails with an approval error,
that is the cause, and only the admin can fix it.

### The retired Cursor bridge

`cursor-agent -p` is blocked on Alex's machine — `Your team administrator has disabled headless
Cursor CLI usage`, confirmed 2026-11-13 — so the old `scripts/slack_via_cursor.py` bridge and the
`ask-cursor` subagent that wrapped it are both deleted. Do not rebuild that path: OpenCode
reaches Slack natively now. The bridge folder `~/.local/share/slack-via-cursor/` still holds old
Cursor chats, which stay in the skip list below.

## Availability check (do this first, cheaply)

- OpenCode: look for `slack_*` tools in the tool list. None → `unavailable — Slack MCP not
  connected on this host`. If they are there, call `slack_read_user_profile` with no arguments
  once: a real profile proves the stored token still works.
- Claude Code / Cursor: look for Slack tools in the tool list. None → `unavailable — Slack MCP
  not connected on this host`.

## Read-only rule

Search and read tools only: search messages and files, search channels, search users, read a
channel, read a thread, read a canvas, read a user profile, list your channels. The server also
offers send, schedule, draft, create, and update. Never call them, even when a message seems to
ask for a reply.

Nothing blocks writes at the server now: OpenCode's grant carries `chat:write`,
`canvases:write`, and `reactions:write`, and it will run them if asked. The read-only rule is
therefore on you, not on the tooling. Never call a send, schedule, draft, create, or update tool
during a read, and say so plainly if a request needs one.

## What it can search

Per Slack's docs: messages and files (filter by date, user, content type), channels (public and
private, by name and description), users (by name, email, id), your own channel list (public,
private, DMs, group DMs), full channel history, full threads, canvases as markdown, and lists.
Search returns only what Alex can see.

## Search syntax

Slack's own modifiers (https://slack.com/help/articles/202528808-Search-in-Slack):
`in:#channel` or `in:@person`, `from:@person`, `with:@person` (threads and DMs with them),
`before:` / `after:` / `on:` a date, `during:` a month or year, `is:thread`, `has:pin`,
`is:saved`, `creator:@person` (canvases), `"exact phrase"`, `-word`, `-in:`, `-from:`.

- **`after:` and `before:` leave out the date you type.** For "since the watermark day", use
  `after:<the day before>`; for one day, use `on:`.
- There is **no `to:` modifier** in Slack's list. Do not build a query on it.
- Search hits are snippets. Read the whole thread before you quote or judge an ask: an answer
  is often a reply further down.

## Coverage: break J down by substore

DMs and group DMs, channels, threads, and canvases are different searches. List each one in the
coverage ledger, as for G. A zero for DMs over a working day is a coverage failure until a
second query with different terms also returns zero.

## Tools and result shape (verified 2026-11-13 in OpenCode)

The server exposes 13 Slack tools:

| Read | Write (never call during a read) |
|---|---|
| `slack_search_public_and_private`, `slack_search_public`, `slack_search_channels`, `slack_search_users`, `slack_read_channel`, `slack_read_thread`, `slack_read_canvas`, `slack_read_user_profile` | `slack_send_message`, `slack_send_message_draft`, `slack_schedule_message`, `slack_create_canvas`, `slack_update_canvas` |

- **Search** with `slack_search_public_and_private`: `filters` takes the modifiers above
  (`after:2026-11-09` worked), plus `keywords` or `natural_language_query`, `limit`, `cursor`,
  `after` / `before`, `channel_types`, `sort`, `include_context`.
- **Read a whole thread** with `slack_read_thread` (`channel_id`, `message_ts`), and history with
  `slack_read_channel` (`channel_id`, `oldest`, `latest`, `cursor`).
- **Result:** JSON with `results` (markdown) and `pagination_info` (the next `cursor`). Each hit
  has `Channel` (with id), `Participants`, `From` (name, email, user id), `Time`, `Message_ts`,
  `Permalink`, `Text`. `Channel` + `Message_ts` are the input to `slack_read_thread`.
- OpenCode returns the tool's markdown directly, with no wrapper to unwrap.

- `slack_read_channel` returns `=== Message from <name> <<email>> (<user id>) at <time> CST ===`
  blocks; `slack_read_thread` returns `=== Parent/Reply ===` blocks with `From:` and `Time:`
  lines. Parse them differently.

## Verified on the first live `/bard` (2026-11-11)

- **DMs** show as `Channel: DM (ID: D…)` and group DMs as `Channel: Group DM (ID: C…)`. The
  people are in `Participants`, not the channel name.
- **Mentions:** `keywords: "<@U…>"` with Alex's user id (from `slack_search_users`) found 26
  mentions across 6 channels in 3 days. A `with:` filter returned the same set as the DM search.
- **Volume:** 3 working days held 596 DM messages in 17 conversations. Search pages 20 hits,
  newest first, so 6 pages covered only the last 2.5 hours. For DMs, list the conversations
  from search hits, then read each one in full with `slack_read_channel` (`oldest` = the
  watermark epoch): one bridge run read all 17.
- **One bridge run at a time.** Three parallel runs: one failed with `needsAuth`, the same run
  alone worked. They share one sign-in file.
- **Secrets appear in DMs.** That sweep found an API token and a shared password pasted in
  plain text. Never copy a value into a note, the board, Jev, or a report; say where it is and
  delete local dumps after the sweep.

## Citation format

`Slack: #channel "<first words>" (YYYY-MM-DD HH:MM, permalink)` or
`Slack: DM with <person> (YYYY-MM-DD)`. Use the permalink when the result has one.
