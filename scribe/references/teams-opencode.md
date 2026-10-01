# Source A in OpenCode — Teams through the ask-claude bridge

OpenCode has no Microsoft 365 connector, so the connector steps in
[teams.md](teams.md) run inside the `ask-claude` subagent instead of here. That
subagent **cannot write files**, and a 40–80 KB transcript must not be pasted
through the parent's context, so the payload is recovered from where Claude Code
leaves it on this Mac.

One session reads it twice: as a JSON string inside the session `.jsonl`, and, when
the result is too large to return inline, as the raw payload in
`<session>/tool-results/*.txt`. Both are byte-exact. `claude_session_payloads.py`
reads both, so nothing depends on the subagent's reply text.

## 1. Inventory and fetch with the subagent

Use [teams.md](teams.md) steps 2–4 as the brief — calendar search, the event's
`meetingTranscriptUrl`, and the occurrence window on the transcript URI are
unchanged. Two additions to that brief:

- Ask for a **manifest only**: per event its subject, connector event id, start and
  end in UTC, the transcript URI it read, whether a transcript exists, and the
  transcript's `createdDateTime`/`endDateTime`. For a recovered payload, the spill
  file's path if there is one, else `inline` with the character count.
- Tell it plainly: **do not paste transcript content, not one cue.** The bytes come
  from disk, so a paste only spends context and risks a truncation you cannot see.

Completion: every event in the window carries a verdict, and no transcript text
appears in the reply.

Cross-check that list against the CLI, because the CLI's `calendar search` drops
recurring instances — its `$filter` on `start/dateTime` matches the **series** start:

```bash
m365 --json request "/me/calendarView" \
  --param "startDateTime=2026-09-30T00:00:00Z" --param "endDateTime=2026-10-01T00:00:00Z" \
  --param '$select=subject,start,end,onlineMeeting' --param '$top=100'
```

`calendarView` and the connector list must agree. A disagreement means the CLI
query is wrong, not the connector.

## 2. Write the manifest

Straight from the reply, one row per meeting you asked for:

```json
[
  {"subject": "DLP Open Questions", "event_id": "AAkALg...",
   "start": "2026-09-30T16:30:00Z", "end": "2026-09-30T17:00:00Z"}
]
```

Every row is a promise: a row with no recoverable payload exits non-zero rather
than writing a partial set.

## 3. Recover and normalize

```bash
python3 ~/.agents/skills/scribe/scripts/claude_session_payloads.py \
  --manifest ~/.scribe/oc-manifest.json --normalize
```

Sibling imports mean the cwd picks the Claude Code project, so run it from the
directory the subagent ran in. `--project` overrides, and `--session` reads one
session log or spill file directly. Without `--normalize` you get only the payload
JSON and the `.vtt`.

It writes `~/.scribe/raw/<date>-<slug>.json` and `.vtt`, and with `--normalize`
also `~/.scribe/transcripts/<date>-<slug>.json`, then prints per meeting the cue
count, the slot, and the note path `write_note.py` will use.

Matching is exact: the URI token is base64url of the payload's `joinWebUrl`, so a
payload is tied to its own occurrence, and the URI whose `?start=&end=` window
overlaps the calendar slot wins. A URI read with no window is rebuilt from the
manifest slot and said so on stderr — that is the one case where the window is not
the URI's own.

## 4. Check before continuing

- The cue count and speaker count per meeting match the manifest. A missing
  payload, or a payload with no manifest row, is printed as `!!` or `note:` on
  stderr and named with its subject.
- The predicted note path's `HHMM` is the calendar slot (`1500` for a 15:00
  meeting), not the first cue's time.
- Keep the printed `state teams.<event_id> -> <note path>` lines for the state
  step of **Summary and write**.

Then continue at [Summary and write](../SKILL.md#summary-and-write-both-sources).

## Gotchas

- **A returned paste is not the record.** The subagent has no write tool and its
  proxy `write`/`shell` tools answer "No tool named ... is currently available", so
  the manifest and the disk artifacts are the only inputs you trust.
- **Two artifacts, one payload.** The `.jsonl` copy is double-encoded: parse the
  line, then parse the string inside it. The spill file is the payload itself.
- **A previously fetched occurrence can sit in the same session logs.** It is
  reported as unrequested and left alone; a series' only transcript may belong to
  an earlier occurrence that already has a note.
- **`FORBIDDEN 3003`** means no transcript is readable for that meeting, whatever
  the cause. On 2026-09-30 the organiser's address was on curo.com, but the join URL
  carried the same tenant id as every other meeting, so "another tenant" was a guess,
  not evidence. The HiDock copy is the record.
- Verified 2026-09-30: four meetings recovered from real session artifacts, byte-identical
  to the raw files built by hand, 294/272/261/395 cues and named speakers.
