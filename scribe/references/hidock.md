# Source B — HiDock P1

Device facts (verified 2026-09-03): HiDock P1, USB 0x10D6:0xB00E, vendor protocol over bulk
endpoints, not a USB drive. Recordings are `YYYYMonDD-HHMMSS-RecNN.hda`, which are plain MP3
(mono, 48 kHz, 96 kbps). The filename timestamp is the device clock in Central time. The device
keeps every recording until HiNotes removes it; scribe never deletes.

1. Device check and inventory:

   ```bash
   cd ~/.agents/skills/scribe/scripts
   uv run --with pyusb python hidock_pull.py list
   ```

   Exit 2 = not plugged in. Exit 3 = USB claim error: another process holds the device. Tell
   Alex to close the HiNotes tab in Edge and any other scribe/pytest run, then retry once.
   Exit 4 = the device is connected but never answered the list request, even after the script's
   own retry: unplug, replug, retry. `No recordings found.` (exit 0) means the device answered
   with an empty list; if state shows recordings from yesterday, that is still suspicious, since
   HiNotes is the only thing that deletes. Run `list` again before believing it. On 2026-09-04
   a silent first request was reported as an empty device and nearly cost a day of calls.
2. Pull and transcribe in one go:

   ```bash
   ./hidock_batch.sh <YYYY-MM-DD of watermark>
   ```

   It runs `hidock_pull.py sync` (skips files already present with the same size, already
   transcribed in `--done-dir`, shorter than 120 s, or older than the date), then
   `transcribe.py` on each new MP3 (whisper transcription plus local speaker diarization in one
   run), and deletes the MP3 once its JSON exists. One JSON line per
   file from the sync (`downloaded` or `skipped` + reason), then one `=== transcribing <stem> ===`
   per file on stderr. ~7 MB/s download; a 40-minute call downloads in a few seconds. Every
   download is size- and magic-byte-checked. `--done-dir` is what stops re-downloads once the
   local audio is gone: a recording is done when `<stem>.json` exists there.
3. If you need the steps apart (one file, a re-run), the pieces are:

   ```bash
   uv run --with pyusb python hidock_pull.py sync -o ~/.scribe/audio \
     --done-dir ~/.scribe/transcripts --since <YYYY-MM-DD> --min-seconds 120
   uv run --with mlx-whisper --with mlx-audio python transcribe.py ~/.scribe/audio/<stem>.mp3 \
     -o ~/.scribe/transcripts/<stem>.json
   ```

   Runs offline with the cached `mlx-community/whisper-large-v3-turbo` (~95× realtime on the
   M5 Max, so a 40-minute call takes ~30 s; 18 recordings, 8.7 hours of audio, took 6 minutes on
   2026-09-03). Start time comes from the filename. Speaker labels come from
   `mlx-community/Nemotron-3-Diarization` via mlx-audio: each ASR segment takes the label of the
   span it overlaps most, turns split on 2 s pauses, on speaker change, and at 90 s, and spans
   with no overlap stay unlabeled. The diarizer adds seconds, not minutes (72-minute call: 1.96 s,
   1.08 GB peak, 2026-09-24). If diarization cannot run, the note is still written unlabeled and
   provenance says `diarization_status: skipped` or `failed`. First download needs
   `--allow-download` once; `transcribe.py` sets `HF_HUB_DISABLE_XET=1` itself. The script drops
   the repeated-line hallucinations whisper produces on silence. **Then delete the MP3**
   (`rm ~/.scribe/audio/<stem>.mp3`)
   once the JSON exists: Alex wants no local audio copies, the device keeps the recording. The
   JSON carries the file's sha256 in provenance, so the source stays verifiable.
4. Apply [Teams-first dedupe](../SKILL.md#teams-first-dedupe) before transcribing,
   as required in the core flow.
5. Title and attendees for what is left: one calendar match → its subject as `--title` and its
   attendee names as `--attendees`. No match, or Pi (no M365): read the transcript and pick a
   short factual title from content (`Call about <topic>`); if the content does not say what it
   is, `Untitled call`.
6. Continue at [Summary and write](../SKILL.md#summary-and-write-both-sources).
