---
name: scribe
description: >-
  Turn Alex's meetings into cleaned transcript notes in the Obsidian vault at
  Scribe/Meetings/Transcripts, from two sources: Microsoft Teams transcripts (via the
  Microsoft 365 connector) and HiDock P1 call recordings (pulled over USB, transcribed
  locally with mlx-whisper). Use when the user runs /scribe, asks to fetch, pull, clean,
  or save meeting transcripts or call recordings, to sync the HiDock, or to prepare
  meeting notes for bard. On-demand only. Read-only on the device and on Microsoft 365.
  Never commits, never runs a server, never sends audio or transcripts off the Mac.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, ToolSearch, mcp__claude_ai_Microsoft_365__outlook_calendar_search, mcp__claude_ai_Microsoft_365__read_resource
---

# scribe — meetings → cleaned transcript notes

scribe is the intake step of Alex's knowledge pipeline: **scribe → bard → ea-projects-curator**.
It fetches raw transcripts, cleans them, adds a short summary, and writes one note per meeting
into the vault. It does not distill knowledge (bard does) and does not publish anything
(ea-projects-curator does).

```mermaid
graph TD
  T[Teams meeting] --> T2[M365 connector: calendar event + transcript URI]
  T2 --> P1[teams_transcript.py: VTT to turns]
  H[HiDock P1 on USB] --> H2[hidock_pull.py sync: .hda to ~/.scribe/audio/*.mp3]
  H2 --> H3[transcribe.py: mlx-whisper, local]
  P1 --> C[you: full transcript, summary]
  H3 --> C
  C --> W[write_note.py: glossary, filler, note]
  W --> O[vault Scribe/Meetings/Transcripts/]
  O --> B[bard sweep later]
```

## Paths (verified 2026-09-03)

- Vault root: `/Users/alexandrecastro/Developer/obsidian/Alex`
- Notes: `<vault>/Scribe/Meetings/Transcripts/<YYYY-MM-DD HHMM> <title>.md`
- Glossary: `<vault>/Scribe/Glossary.md` (`- wrong => Right` lines; scribe applies, you may append)
- State: `<vault>/Scribe/.scribe-state.json`
- Local store (outside the vault, never synced): `~/.scribe/audio/` (MP3s from the device,
  deleted after transcription; the device keeps the only copy), `~/.scribe/transcripts/`
  (normalized JSON, kept), `~/.scribe/raw/` (raw M365 payloads)
- Scripts: `~/.agents/skills/scribe/scripts/` — run from that directory with
  `uv run --with pyusb --with mlx-whisper python <script>` (uv caches the env; first run ~45 s)

**First run on a new Mac**: `brew install libusb ffmpeg` (pyusb needs libusb; whisper and ffprobe
need ffmpeg), then run `transcribe.py` once with `--allow-download` so the
`mlx-community/whisper-large-v3-turbo` weights (1.5 GB) land in the Hugging Face cache; every later
run stays offline. On this Mac all three were already present on 2026-09-03.

## Hard constraints (never violate)

- **On-demand only.** No scheduler, no watcher, no autonomous run.
- **Read-only on the device.** `hidock_pull.py` implements only list and download. Never add a
  delete, format, or settings command. HiNotes manages device storage, not scribe.
- **Read-only on Microsoft 365.** Calendar search and transcript read only.
- **Audio and transcripts stay on this Mac.** Local whisper only. Never send audio, transcript
  text, or summaries to Exa, a web tool, or any external service: a call recording is confidential
  even when it sounds like small talk, and Attain is a regulated lender. HiNotes cloud is not a
  source (no API, no export).
- **Never hold a whole meeting.** Every work recording becomes a note, including calls that
  touch HR, compensation, performance, or personal topics. Keep every note `confidential: true`
  and keep the local-only handling rules above (Alex, 2026-09-08; reaffirmed 2026-09-23 after
  two 1:1s were wrongly held).
- **Withhold only HR-data segments, by Attain policy.** Attain security policy limits HR data
  (compensation, payroll, benefits, performance, HR cases about named people) to a named
  allowlist, and Alex's account is not on it. In a trimmed copy of the JSON
  (`<id>.trimmed.json`), replace only those turns or sentences with
  `[Segment withheld under Attain HR-data policy: <topic>.]`, record the span in
  `provenance.withheld`, add one summary bullet that says so, and write the note from the
  trimmed copy. Everything else stays in full, including org design and role definitions
  discussed in general terms. The original JSON stays in `~/.scribe/transcripts/`. Only an
  admin edit of the policy allowlist changes this rule.
- **scribe does not curate.** Every work recording and every Teams transcript becomes a note,
  including standups, 1:1s, and calls that turn out to be personal. Deciding what matters is
  bard's job, not scribe's. The Teams-wins dedup in Source B drops a HiDock copy that carries
  strictly less information (no speaker names) than the Teams note of the same meeting; it is
  not a judgment about relevance. The sync date and minimum-duration filters still apply.
- **Write only** inside `<vault>/Scribe/`, `~/.scribe/`, and the state file. Never touch
  `Bard/`, `Evidence/`, `Todo.md`, or any other vault folder. Never edit an existing transcript
  note; re-run with `--force` only when Alex asks for a rewrite.
- **Never invent.** No guessed names, owners, dates, or decisions in the summary: bard and the
  AAB recap build on these notes as the record of what was said, so one invented owner becomes a
  wrong commitment downstream. A garbled proper noun you cannot confirm stays described, not
  named. A transcript that ends mid-sentence gets a footer line saying so.
- **Never `git`, never a server, never commit.** Alex reviews and signs every commit himself.
  `obsidian sync:status vault=Alex` at the end is fine (see **Sync the vault**); `obsidian reload`
  is not, it hangs.

## Modes

Argument decides the mode. With no argument, run both sources for the window since `last_run`.

- `/scribe` — Teams + HiDock, everything new since the state watermark (default 7 days back on
  a first run).
- `/scribe teams [YYYY-MM-DD | YYYY-MM-DD..YYYY-MM-DD]` — Teams only, for a day or a range.
- `/scribe hidock` — HiDock only: sync the device, skip what Teams covers, transcribe the
  rest, write notes. Run Teams first in a combined run so the coverage check sees the notes.
- `/scribe status` — writes nothing. Read `.scribe-state.json`, run `hidock_pull.py list --json`,
  and list the calendar events in the window; report three tables: device recordings not yet in
  state, Teams events not yet in state, and the skipped map. Use it before a big run or when a
  note seems missing.

Teams needs the Microsoft 365 connector, so it works in Claude Code only. HiDock works in
Claude Code and Pi.

## Source routing

- **Teams intake:** for `/scribe teams` or the Teams part of `/scribe`, read
  [Source A: Microsoft Teams](references/teams.md) before fetching transcripts.
- **HiDock intake:** for `/scribe hidock` or the HiDock part of `/scribe`, read
  [Source B: HiDock P1](references/hidock.md) before accessing the device.
- **Combined run:** finish Teams notes through **Summary and write** first. Then
  process HiDock so the coverage check sees the Teams notes.
- **Status:** read both references, but use only Teams steps 1–2 for calendar
  inventory and HiDock step 1 with `list --json` for device inventory. Report the
  three tables in **Modes** and stop. Do not fetch transcripts, sync/download audio,
  transcribe, write summaries/notes, or update state.

Run all shell commands from `~/.agents/skills/scribe/scripts/`, not from the
reference directory. HiDock-only in Pi has no M365 connector: use the no-calendar
fallback in Source B; do not assume Teams coverage.

### Teams-first dedupe

**Teams wins.** Before transcribing, match the recording to the calendar:
`outlook_calendar_search` with `query: "*"` over start −10 min to start +10 min. Skip the
recording with reason `teams-covers` ONLY when a scribe Teams note already exists for that slot
and the match is unambiguous (one event, same start within 10 min, similar length). Teams has
speaker names; whisper does not, so the HiDock copy adds nothing then. In every other case,
including concurrent meetings, a Teams note with almost no cues, or Source A not yet run, write
the HiDock note; a duplicate is bard's problem, a missing meeting is not recoverable.
`meetingTranscriptUrl` on the event is NOT proof of a transcript: every Teams meeting carries
it. Expect `no-transcript` for most standups and 1:1s and `FORBIDDEN 3003` for meetings
organized by someone whose transcript you may not look up; both mean the HiDock copy is the
record. A recording whose window overlaps two calendar events matches neither: write the
HiDock note and let the summary say which meeting it turned out to be.

## Source A — Microsoft Teams

Use the Teams intake route above. The source mechanics end at **Summary and write**.

## Source B — HiDock P1

Use the HiDock intake route above. Apply **Teams-first dedupe** before any
transcription, including a batch run. The source mechanics end at **Summary and write**.

## Summary and write (both sources)

1. **Read the normalized JSON in full** (`turns[].text`). Do not summarize from grep hits.
2. **Keep the full meeting** except HR-data segments (see **Hard constraints**). Summarize
   every other topic. Apply the normal transcript cleaning below.
3. **Write the summary file** to `~/.scribe/transcripts/<id>.summary.md`. Voice: neutral
   reference, terse, factual, like a bard note. Shape:

   ```markdown
   ## Summary
   One-sentence description first (it becomes the frontmatter `description`).
   3-8 bullets: what was discussed, in order, outcome-first. Name people only when the
   transcript names them. Unclear proper noun → describe it, do not guess.

   ## Decisions
   Only decisions someone stated as decided. Empty section → omit it.

   ## Actions
   `Owner → action (due if stated)`. Only explicit commitments. Empty → omit.
   ```

   HiDock notes have no speaker labels: write "the caller" / "the other party" unless a name is
   spoken. Never label a voice as Alex from tone alone.
4. **Write the note**:

   ```bash
   uv run python write_note.py ~/.scribe/transcripts/<id>.json \
     --vault /Users/alexandrecastro/Developer/obsidian/Alex \
     --summary-file ~/.scribe/transcripts/<id>.summary.md \
     --glossary /Users/alexandrecastro/Developer/obsidian/Alex/Scribe/Glossary.md \
     [--title "..."] [--attendees "A,B"] [--tags aab,forum]
   ```

   The script applies the glossary (case-insensitive, whole words), drops filler words, merges
   same-speaker turns, and writes frontmatter (`type: transcript`, `source`, `date`, `speakers`,
   `provenance`, `confidential: true`). It refuses to overwrite without `--force`. stdout is the
   note path.
5. **Glossary upkeep**: when you confirmed a garble → real name during the summary, append a
   `- wrong => Right` line to `<vault>/Scribe/Glossary.md`. Only confirmed ones.
6. **State**: add the item to `.scribe-state.json` (`teams.<eventId>` or `hidock.<deviceFile>` →
   note path, plus `skipped.<id>` → reason). When Alex asks to recover a previously skipped
   recording, use its existing local JSON even if it is older than the watermark. Remove its
   old `skipped` entry only after the note is successfully written. Do not backfill unrelated
   historical skips unless requested. Set `last_run` to now (ISO) at the end.
7. **Sync the vault**: Obsidian watches the filesystem, so new files show up on their own. Run
   only `obsidian sync:status vault=Alex` (expect `status: synced`). Do NOT run
   `obsidian reload`: on 2026-09-03 it printed `Reloading...` and never returned. Wrap the CLI in
   a 20 s timeout (macOS has no `timeout` binary; use `python3 -c` with `subprocess.run(...,
   timeout=20)`), and report "Obsidian not running" if it times out.
8. **Report** in one table: source, meeting, date, duration, speakers, note path or skip reason.
   Reasons you assign: `teams-covers`, `no-transcript`. Reasons the sync script prints
   (`already present`, `already transcribed`, `shorter than --min-seconds`, `older than --since`):
   quote them as printed.
   Then one line for glossary lines added and one for the vault sync status.

## State file shape

```json
{
  "last_run": "2026-09-03T16:40:12Z",
  "teams": { "<eventId>": "<vault>/Scribe/Meetings/Transcripts/2026-09-02 1500 Architecture Advisory Board.md" },
  "hidock": { "2026Sep02-113150-Rec13.hda": "<vault>/Scribe/Meetings/Transcripts/2026-09-02 1131 EKSKubernetesBackstage Discussion.md" },
  "skipped": { "2026Sep02-150056-Rec17.hda": "teams-covers: 2026-09-02 1500 Architecture Advisory Board" }
}
```

Keys are the Teams event id and the device filename, so a re-run recognises both sources without
re-fetching. `skipped` values start with the reason, then a short why.

## Note shape (what bard and ea-projects-curator read)

```markdown
---
type: transcript
title: "Architecture Advisory Board"
description: "One-sentence summary."
date: 2026-09-02T20:00:56Z
end: 2026-09-02T21:25:40Z
duration_min: 85
source: teams            # or hidock
speakers: ["Ana Silva", "Bruno Costa"]   # who actually spoke; [] for hidock
attendees: ["Ana Silva", "Bruno Costa", "Carla Reyes"]
tags: ["scribe", "meeting", "source/teams"]
confidential: true
provenance:
  teams_event_id: "..."
  transcript_uri: "..."
  cue_count: 729
cleaned: true
glossary_replacements: 3
scribe_schema: scribe.transcript/1
---

# Architecture Advisory Board

## Summary
...

## Transcript

**[00:00:12] Ana Silva:** ...        # teams
**[00:00:12]** ...                   # hidock (no speaker labels)
```

## Known limits

- An inline Teams payload reaches disk only through the model writing it out, so the raw file is
  a copy, not a download. The cue count on stderr from `teams_transcript.py` is the only check;
  compare it against the payload if a note looks thin.

- No speaker diarization on HiDock audio. Follow-up candidate: pyannote or a channel split if a
  future firmware records stereo.
- Whisper still garbles names. The glossary fixes the known ones; the summary step catches the
  rest only when you check.
- Teams path needs Claude Code (M365 connector). In Pi, run `/scribe hidock` only.
- The state file is the only dedupe. Deleting it re-processes everything; `write_note.py` then
  refuses to overwrite existing notes, which is the safety net.

## Tests

```bash
cd ~/.agents/skills && uv run --with pytest --with pyusb pytest scribe/tests -q
```

59 tests: protocol parsing on a real captured device listing, the silent-device retry and exit 4,
Teams VTT parsing, cleaning, note layout, transcription grouping, and one real-device listing
that auto-skips when the P1 is not plugged in.
