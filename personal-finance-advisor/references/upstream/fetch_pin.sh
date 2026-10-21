#!/usr/bin/env bash
# fetch_pin <dir> <url> <sha> [sparse-path]
set -euo pipefail
dir="$1" url="$2" sha="$3" sparse="${4:-}"
git init -q "$dir"
git -C "$dir" remote add origin "$url" 2>/dev/null || git -C "$dir" remote set-url origin "$url"
if [ -n "$sparse" ]; then
  git -C "$dir" config core.sparseCheckout true
  printf '/%s/\n' "$sparse" > "$dir/.git/info/sparse-checkout"
fi
git -C "$dir" fetch -q --depth 1 --filter=blob:none origin "$sha"
git -C "$dir" checkout -q --detach FETCH_HEAD
[ "$(git -C "$dir" rev-parse HEAD)" = "$sha" ] || { echo "pin mismatch: $dir" >&2; exit 1; }
