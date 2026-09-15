# Source A — Microsoft Teams

Verified end to end by ea-projects-curator on 2026-08-28; the mechanics moved here unchanged.

1. Load the tools:
   `ToolSearch("select:mcp__claude_ai_Microsoft_365__outlook_calendar_search,mcp__claude_ai_Microsoft_365__read_resource")`.
2. Find candidate meetings: `outlook_calendar_search` with `query: "*"` and a
   `afterDateTime`/`beforeDateTime` window covering the requested days. Search by the **real
   calendar subject** (the AAB forum is `Architecture Advisory Board`, not "Architecture Review
   Forum"). The search returns 25 events per page; when the result ends with `nextOffset`,
   call again with `offset` until it is gone (two working days already exceed one page). Skip
   events already present in state under `teams`.
3. For each event, `read_resource` on `calendar:///events/{eventId}` to get its
   `meetingTranscriptUrl`. Every Teams meeting carries one, so its presence proves nothing.
4. `read_resource` on that URL. It looks like
   `meeting-transcript:///events/{token}?start={iso}&end={iso}`. Recurring occurrences carry
   `start`/`end`, which pin the series to one occurrence; keep them. **One-off meetings carry no
   window**: append `?start=<event start>&end=<event end>` yourself, converted to UTC
   (`2026-09-04T09:00 Central` → `start=2026-09-04T14%3A00%3A00.000Z`). Without a window the read
   returns "the most recent transcripts of the series, capped", which is the wrong occurrence
   for a series and works only by luck for a one-off.
   `NOT_FOUND transcripts_empty`, `NOT_FOUND 3004`, and `FORBIDDEN 3003` all mean no transcript
   for that occurrence: record `no-transcript` for that event. **Check every occurrence, every
   run.** A standup that had no transcript yesterday is not evidence about today; the read costs
   one call, and inferring from history was a mistake made on 2026-09-04.
5. The payload comes back two ways. Above roughly 50 KB (an 85-minute AAB is ~114 KB) the
   harness saves it to a file and gives you the path: do not `Read` it (one giant line), copy it
   to `~/.scribe/raw/<eventId>.json`. Below that it arrives **inline** in the tool result, and
   the only way to disk is to write it yourself. Write the `content` (WEBVTT) to
   `~/.scribe/raw/<eventId>.vtt` with the Write tool **exactly as received**: every cue, every
   "Yeah.", every garble. Do not drop filler, do not fix names inline; the cleaner drops filler
   and the glossary fixes names, and the raw file is the record that lets anyone check the note.
   Then wrap it into the payload shape (`{"meeting": {...}, "transcripts": [{"createdDateTime",
   "endDateTime", "content"}]}`) with a short Python snippet. Pass the **real** URI, with the
   window, as `--transcript-uri`; it lands in provenance, and a placeholder there is a false
   record. Then:

   ```bash
   cd ~/.agents/skills/scribe/scripts
   uv run python teams_transcript.py ~/.scribe/raw/<eventId>.json \
     -o ~/.scribe/transcripts/<eventId>.json --event-id <eventId> --transcript-uri "<url>"
   ```

   stderr prints the occurrence window, cue and turn counts, and the speaker list. Confirm the
   window matches the event you meant. `meeting.startDateTime` is the SERIES start; the script
   ignores it on purpose. Two transcripts in one payload means you dropped the window params:
   the script refuses and you re-fetch. The note's `date`/`end` and its filename come from the
   `?start=&end=` calendar slot in the URI (so the AAB note is `... 1500 ...`, not `1459`); the
   transcript's own first/last cue times land in provenance.
6. Continue at [Summary and write](../SKILL.md#summary-and-write-both-sources).
