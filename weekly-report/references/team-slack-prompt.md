# Team Slack channels: the prompt Alex pastes into Cursor

Slack is reached only by hand: the admin blocked headless cursor-agent, so never automate
it. Alex opens interactive Cursor (it has the Slack tools), pastes the prompt below, and
gives the file to `collect.py --slack`. This reads the team's channels, which gather's own
Slack prompt does not: gather reads only Alex's DMs and mentions.

Fill `<channels>` from `team.slack_channels` in `~/.config/weekly-report.json`, `<mon>` and
`<fri>` from the report window, and `<out>` as `~/.weekly-report/team-slack-<fri>.json`.
That path is weekly-report's own, not gather's store, so the two never mix.

```text
You are in Cursor with the Slack tools. Read only. Write nothing to Slack.
Window: <mon> to <fri>, America/Chicago. Slack `after:` leaves out the date you type, so
search from the day before and drop older messages by their timestamp.

1. For each channel in <channels>, read the channel history in the window with
   slack_read_channel. Page until the window is covered. A name ending in `*` is a prefix:
   find the one channel whose name starts with it, and say its full name in your reply. If
   more than one matches, stop and list them. Private channels are read only if I am a
   member; name any channel you cannot read.
2. For each message in the window that has replies, read the thread with slack_read_thread.
3. Write the file <out> as JSON:
   {"calls": [{"tool": "<tool name>", "args": {...}, "content": "<result>"}]}
   One entry per read call. `content` is the tool result copied in full, character for
   character. Do not summarise, trim, or fix it.
4. Reply with the file path, the number of calls, each prefix's full channel name, and any
   channel you could not read. Nothing else.
```
