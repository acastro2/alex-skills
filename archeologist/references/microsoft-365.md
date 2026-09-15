# SOURCE G: Microsoft 365 (SECONDARY; PRIMARY for comms/meetings)

Teams chats, tenant SharePoint search, Outlook mail + calendar — via the `claude_ai_Microsoft_365`
MCP connector. Human-coordination evidence: agreements in chat, meeting timing, doc sharing,
email threads. READ-ONLY: use ONLY the search/list/read tools below; never the send/create/
delete/update tools even though the connector exposes them.

## Availability check (do this first, cheaply)

The connector is interactively authenticated and its tools are usually DEFERRED — a direct call
fails with InputValidationError until the schema is loaded. Load what you need via ToolSearch
(`select:mcp__claude_ai_Microsoft_365__chat_message_search,...`). If ToolSearch finds nothing,
the connector isn't in this session: report "M365 store unavailable this session" in NO DATA and
move on. Never treat unavailability as "no results".

## Strategy G1: Teams messages (who said what, when)
- `mcp__claude_ai_Microsoft_365__chat_message_search` — keyword search across chat messages.
- `mcp__claude_ai_Microsoft_365__teams_list_chats` — enumerate chats (map names → threads).

## Strategy G2: SharePoint (tenant-wide doc discovery)
- `mcp__claude_ai_Microsoft_365__sharepoint_search` — finds docs across ALL sites, including ones
  outside the local OneDrive sync (Source F only sees the synced Architecture library). Use it to
  locate canonical org-shared copies of ADRs/SADs and docs on other teams' sites.
- `mcp__claude_ai_Microsoft_365__sharepoint_folder_search` — scoped folder lookups.
- `mcp__claude_ai_Microsoft_365__read_resource` — fetch content of a found item.

## Strategy G3: Outlook mail (agreements, announcements, threads)
- `mcp__claude_ai_Microsoft_365__outlook_email_search` — keyword/sender/date search.

## Strategy G4: Calendar (when did we meet, with whom)
- `mcp__claude_ai_Microsoft_365__outlook_calendar_search` — meetings by subject/attendee/date.

## Citation format
- `M365/Teams: "<chat or channel>" (YYYY-MM-DD) — "<quoted snippet>"`
- `M365/SharePoint: <site>/<path or filename>` (include the URL when available)
- `M365/Mail: "<subject>" from <sender> (YYYY-MM-DD)`
- `M365/Calendar: "<event subject>" (YYYY-MM-DD)`

## Guardrail specifics for this store
- Results may contain other people's messages/mail: quote the minimum needed as evidence, never
  dump whole threads into the briefing.
- Anything that looks legally privileged, counsel-touched, or incident-forensics: cite that it
  exists at most — do not quote content (same rule as the other stores, but comms hit it more).
