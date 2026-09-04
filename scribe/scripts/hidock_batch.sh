#!/usr/bin/env bash
# Sync the HiDock, transcribe every new MP3, delete the audio once its JSON exists.
# Usage: hidock_batch.sh <since YYYY-MM-DD> [min-seconds]
set -euo pipefail
SINCE="${1:?usage: hidock_batch.sh <since YYYY-MM-DD> [min-seconds]}"
MIN_SECONDS="${2:-120}"
AUDIO="$HOME/.scribe/audio"
DONE="$HOME/.scribe/transcripts"
cd "$(dirname "$0")"

uv run --with pyusb python hidock_pull.py sync -o "$AUDIO" \
  --done-dir "$DONE" --since "$SINCE" --min-seconds "$MIN_SECONDS"

for f in "$AUDIO"/*.mp3; do
  [ -e "$f" ] || continue
  stem="$(basename "$f" .mp3)"
  if [ -f "$DONE/$stem.json" ]; then rm -f "$f"; continue; fi
  echo "=== transcribing $stem ===" >&2
  uv run --with mlx-whisper python transcribe.py "$f" -o "$DONE/$stem.json" && rm -f "$f"
done
echo "DONE" >&2
