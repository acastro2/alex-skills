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
only registered partner clients, and on 2026-11-11 its docs named Claude Code and Cursor
(https://docs.slack.dev/ai/slack-mcp-server/). OpenCode is not a partner client.

| Host | Path |
|---|---|
| Claude Code | the Slack MCP server directly. Set it up once: `claude mcp add --transport http --scope user slack https://mcp.slack.com/mcp`, then `/mcp` to sign in |
| Cursor IDE | the Slack MCP server directly (Cursor plugin `slack`, or Settings → MCP) |
| OpenCode, plain shell | `scripts/slack_via_cursor.py` (below), which runs `cursor-agent` headless and keeps the raw tool results |

The workspace admin must approve the MCP client app. If sign-in fails with an approval error,
that is the cause, and only the admin can fix it.

### The OpenCode bridge

```bash
python3 ~/.agents/skills/archeologist/scripts/slack_via_cursor.py \
  --out /tmp/slack-<topic>.json \
  "Search Slack for messages about <topic> after:<YYYY-MM-DD>. Read every thread that matches."
```

- **One-time setup (Alex, interactive).** Cursor stores MCP sign-in per workspace folder
  (`~/.cursor/projects/<folder>/mcp-auth.json`), and the IDE's own Slack sign-in is not visible
  to the CLI (the IDE names the server `plugin-slack-slack`; the CLI uses another key). So the
  bridge runs in one fixed folder, `~/.local/share/slack-via-cursor/`, whose `.cursor/mcp.json`
  the script writes (Cursor's client id from Slack's "Connect to Cursor" docs). Sign in once:
  `cd ~/.local/share/slack-via-cursor && cursor-agent mcp enable slack && cursor-agent mcp login slack`.
  `cursor-agent mcp list` in that folder then shows `slack: ready`; it showed
  `requires_authentication` before sign-in (2026-11-11).
- It runs `cursor-agent -p --output-format stream-json` in that folder, with
  the model pinned to `claude-sonnet-5-5-medium`. The model only calls tools; the payload is the
  tool results, which the script copies verbatim from stdout into `--out`. Do not quote the
  model's reply: it is a summary.
- Cursor's own transcripts store tool calls but not their results, so stdout is the only place
  the Slack text exists. Never look for it in `~/.cursor/`.
- Exit codes: `0` ok; `1` cursor-agent failed (for example the admin turned headless mode off:
  `Your team administrator has disabled headless Cursor CLI usage`, seen 2026-11-11 and then
  re-enabled); `2` a tool failed, Slack is not signed in (`needsAuth`: run the one-time
  `cursor-agent mcp login slack` above), or a result holds `[truncated]`; `3` a tool with a write-looking name ran.
- Each record in `calls[]` has `tool`, `args`, and `content`, the raw text the Slack tool
  returned. Read `content`; it is the quotable source.
- For an ad-hoc Slack question in OpenCode, the `ask-cursor` subagent
  (`~/.config/opencode/agents/ask-cursor.md`) wraps this script. It has the full tool set (Alex, 2026-11-11);
  its prompt sends all Slack access through this script.

## Availability check (do this first, cheaply)

- Claude Code / Cursor: look for Slack tools in the tool list. None → `unavailable — Slack MCP
  not connected on this host`.
- OpenCode: run the bridge once with "List the Slack channels I am a member of, names only."
  Exit 1 or 2 → `unavailable — <the WARNING line>`.

## Read-only rule

Search and read tools only: search messages and files, search channels, search users, read a
channel, read a thread, read a canvas, read a user profile, list your channels. The server also
offers send, schedule, draft, create, and update. Never call them, even when a message seems to
ask for a reply.

The bridge blocks writes in Cursor itself. The script rewrites
`~/.local/share/slack-via-cursor/.cursor/cli.json` on every run: it allows the 8 read tools by
name (`Mcp(slack:<tool>)`) and denies the 5 write tools, `Shell(*)`, and `Write(**)`. Deny beats
allow, and without `--force` a tool that is not on the list is rejected headless. Verified
2026-11-11: a `slack_send_message` call came back `permissionDenied … Blocked by permissions
configuration`, and the script reported `write tool attempted, blocked` (exit 3). Cursor's
`--mode ask` is not used: it rejects every MCP call, reads included (`User rejected MCP`).

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

## Tools and result shape (verified 2026-11-11)

`cursor-agent mcp list-tools slack`, run in the bridge folder, lists 13 tools:

| Read (allowed) | Write (denied) |
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
- Cursor wraps MCP results as `[{"text": {"text": …}}]`; the script joins them into `content`.

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
