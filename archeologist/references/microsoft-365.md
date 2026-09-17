# SOURCE G: Microsoft 365 (SECONDARY; PRIMARY for comms/meetings)

Teams chats, tenant SharePoint search, Outlook mail + calendar. Human-coordination evidence:
agreements in chat, meeting timing, doc sharing, email threads. READ-ONLY on both paths.

Two ways in, and the host decides which:

| Host | Path |
|---|---|
| Claude Code | the `claude_ai_Microsoft_365` MCP connector |
| OpenCode, Pi, plain shell | the **`m365` CLI** (skill `m365`) |

## Availability check (do this first, cheaply)

**Claude:** the connector's tools are usually DEFERRED — a direct call fails with
InputValidationError until the schema is loaded. Load what you need via ToolSearch
(`select:mcp__claude_ai_Microsoft_365__chat_message_search,...`). If ToolSearch finds
nothing, try the CLI below.

**Any host:** check the CLI before using it, and read the result rather than assuming:

```bash
command -v m365 && m365 --json doctor
```

`doctor` reports `auth` plus one line per surface. A surface that says `fail:<code>` is
unavailable **this run**.

If neither path is available, report `NO DATA in G (connector absent, m365 CLI <reason>)`
and move on. Never treat unavailability as "no results". If `doctor` says `no_token`, say so
and ask Alexandre to run `m365 login` — it needs a browser and cannot be done for him.

## Tool map — same job, two hosts

| Job | Claude connector | CLI |
|---|---|---|
| keyword search across chat messages | `chat_message_search` | `m365 teams search "<q>"` |
| enumerate chats | `teams_list_chats` | `m365 teams chats` |
| read one chat's messages | `read_resource` on the chat | `m365 teams messages <chat-id>` |
| tenant-wide doc discovery | `sharepoint_search` | `m365 sharepoint search "<q>"` |
| site discovery | `sharepoint_search` | `m365 sharepoint search "<q>" --sites` |
| read a found item | `read_resource` | `m365 sharepoint read <url>` |
| mail keyword/sender/date search | `outlook_email_search` | `m365 mail search "<q>" [--sender S] [--after D]` |
| read one message | `read_resource` | `m365 mail read <id>` |
| meetings by subject/date | `outlook_calendar_search` | `m365 calendar search --after D --before D` |

The CLI's full surface is in the `m365` skill's `references/cli-reference.md`. Its outputs are
trimmed, not Graph pass-throughs; use `m365 request GET <path>` for a field a verb drops.

## What to pull

- **G1 Teams (who said what, when).** Search messages by keyword, or resolve a chat and read
  it. A chat id is the container: find it with `chats`, then read against it.
- **G2 SharePoint (tenant-wide doc discovery).** Finds docs across ALL sites, including ones
  outside the local OneDrive sync — Source F only sees the synced Architecture library. Use
  it for canonical org-shared copies of ADRs/SADs and docs on other teams' sites.
- **G3 Outlook mail (agreements, announcements, threads).** Search by keyword, sender, or
  date. Pass one axis at a time: Graph rejects combining `$search` with `$filter`.
- **G4 Calendar (when did we meet, with whom).** A date window is the reliable filter, and
  the event carries the organiser.

## Citation format

- `M365/Teams: "<chat or channel>" (YYYY-MM-DD) — "<quoted snippet>"`
- `M365/SharePoint: <site>/<path or filename>` (include the URL when available)
- `M365/Mail: "<subject>" from <sender> (YYYY-MM-DD)`
- `M365/Calendar: "<event subject>" (YYYY-MM-DD)`

## Guardrail specifics for this store

- Results may contain other people's messages/mail: quote the minimum needed as evidence, never
  dump whole threads into the briefing.
- Sensitive content is returned like any other: include the verbatim `classification` label with
  the reference and leave the decision to the caller. Do not withhold or soften it here.
- **Meeting transcripts are not reachable on the CLI path.** They need a scope the tenant has
  not consented to this tool. If a question turns on what was *said* in a meeting rather than
  what was written in chat, say the transcript is unavailable here instead of substituting chat.
