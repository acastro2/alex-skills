#!/usr/bin/env bash
# Sync the HiDock, transcribe every new MP3 with a small worker pool, and delete
# the audio once its JSON exists. A failed file keeps its MP3 for the next run
# and makes the script exit 1.
# Usage: hidock_batch.sh <since YYYY-MM-DD> [min-seconds] [jobs]
set -euo pipefail
SINCE="${1:?usage: hidock_batch.sh <since YYYY-MM-DD> [min-seconds] [jobs]}"
MIN_SECONDS="${2:-120}"
JOBS="${3:-3}"
AUDIO="$HOME/.scribe/audio"
DONE="$HOME/.scribe/transcripts"
cd "$(dirname "$0")"

case "$JOBS" in
  ''|*[!0-9]*) echo "error: jobs must be a positive integer, got '$JOBS'" >&2; exit 2 ;;
esac
if [ "$JOBS" -lt 1 ]; then
  echo "error: jobs must be >= 1, got '$JOBS'" >&2
  exit 2
fi
if [ "$JOBS" -gt 4 ]; then
  echo "note: capping jobs at 4 (each transcription needs several GB of memory)" >&2
  JOBS=4
fi

uv run --with pyusb python hidock_pull.py sync -o "$AUDIO" \
  --done-dir "$DONE" --since "$SINCE" --min-seconds "$MIN_SECONDS"

# Build the transcription env once so parallel jobs do not race to create it.
uv run --with mlx-whisper --with mlx-audio python -c "pass"

running=()
failed=0
for f in "$AUDIO"/*.mp3; do
  [ -e "$f" ] || continue
  stem="$(basename "$f" .mp3)"
  if [ -f "$DONE/$stem.json" ]; then rm -f "$f"; continue; fi
  echo "=== transcribing $stem ===" >&2
  (
    start=$SECONDS
    if uv run --with mlx-whisper --with mlx-audio python transcribe.py "$f" -o "$DONE/$stem.json"; then
      rm -f "$f"
      echo "=== done $stem rc=0 wall=$((SECONDS - start))s ===" >&2
      exit 0
    else
      rc=$?
      echo "=== failed $stem rc=$rc wall=$((SECONDS - start))s (mp3 kept) ===" >&2
      exit 1
    fi
  ) &
  running+=($!)
  while [ "${#running[@]}" -ge "$JOBS" ]; do
    wait "${running[0]}" || failed=1
    running=("${running[@]:1}")
  done
done
if [ "${#running[@]}" -gt 0 ]; then
  for pid in "${running[@]}"; do wait "$pid" || failed=1; done
fi

if [ "$failed" -ne 0 ]; then
  echo "FAILED: at least one recording was not transcribed; its MP3 stays in $AUDIO" >&2
  exit 1
fi
echo "DONE" >&2
