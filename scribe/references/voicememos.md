# Source C — Apple Voice Memos

Store facts (verified 2026-11-12, macOS 26): recordings live in
`~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/` as `.m4a`, indexed
by `CloudRecordings.db` (Core Data, WAL mode, held open while the app runs). Table
`ZCLOUDRECORDING`: `ZUNIQUEID` (the memo's stable id), `ZDATE` (start, seconds since
2001-01-01 UTC), `ZDURATION` (seconds), `ZCUSTOMLABEL` (title, often empty), `ZPATH` (file
name in the folder), `ZEVICTIONDATE` (set when iCloud removed the local copy). iPhone memos
arrive through iCloud, on the Mac's Voice Memos iCloud toggle; Alex's work Mac blocks iCloud
Drive by MDM, and whether that also stops Voice Memos sync is **not verified**. Every memo
becomes a note (Alex, 2026-11-12), like every HiDock recording. scribe never edits, moves, or
deletes a memo.

1. Inventory:

   ```bash
   cd ~/.agents/skills/scribe/scripts
   python3 voicememos.py list --since <YYYY-MM-DD of voicememos_last_run> --json
   ```

   It copies the database and its `-wal`/`-shm` to a temp folder and reads the copy: the
   newest memos sit in the `-wal` file until the app checkpoints, so a read of the main file
   alone misses them, and a direct open would contend with the running app. Exit 3 = the
   store is missing or unreadable (Voice Memos never opened, or the terminal has no Full Disk
   Access). Each item: `id`, `start` (UTC), `duration_s`, `title` (null for an empty or
   "New Recording N" label), `audio` (path), `local` (false = iCloud has not downloaded the
   file yet: ask Alex to open that memo in Voice Memos once, then rerun). `--min-seconds`
   defaults to 30; memos are often short on purpose, unlike the 120 s HiDock floor.
2. Skip every `id` already under `voicememos` or `skipped` in `.scribe-state.json`.
3. Apply [Teams-first dedupe](../SKILL.md#teams-first-dedupe): a memo of a Teams meeting that
   already has a Teams note is skipped as `teams-covers`, by the same rule as HiDock.
4. Transcribe each new local memo, reading the file in place (no copy). **Apple's transcript
   first** (Alex, 2026-11-12): recent macOS writes one into the `.m4a` itself
   (`moov/trak/udta/tsrp`, JSON of words with start and end times, no speaker labels).

   ```bash
   python3 voicememo_transcript.py "<audio>" -o ~/.scribe/transcripts/vm-<id>.json \
     --voicememo-id <id> --start <start> [--title "<title>"]
   ```

   Exit 4 = the memo has no Apple transcript: fall back to whisper with the same output path:

   ```bash
   uv run --with mlx-whisper --with mlx-audio python transcribe.py "<audio>" \
     -o ~/.scribe/transcripts/vm-<id>.json --source voicememo --voicememo-id <id> \
     --start <start> [--title "<title>"]
   ```

   Both write `source: voicememo` and the file's sha256 in provenance; the Apple path also
   writes `transcript_source: apple`, `word_count`, and `coverage` (last word end / memo
   length). **Check `coverage`:** today's 28-minute memo ended its transcript at 78% (verified
   2026-11-12); whether that was silence or a cut-off transcript is not known. Below 0.9, say so
   in the note's footer. Apple's text has no speaker labels, so its turns carry `speaker: null`
   and the summary refers to "the speaker" unless the text names people. Apple-vs-whisper
   accuracy on Alex's voice is not measured yet.
5. Title: the memo's own title when it has one, else a calendar match (a memo recorded in a
   meeting slot), else a short factual title from content (`Memo about <topic>`), else
   `Untitled memo`. Then name the speaker labels exactly as in the HiDock step 5 rules
   ([hidock.md](hidock.md)): text evidence only, never a guessed name.
6. Continue at [Summary and write](../SKILL.md#summary-and-write-every-source). State keys are
   `voicememos.<id>` → note path; move `voicememos_last_run` only after the list and every
   transcription finished.
