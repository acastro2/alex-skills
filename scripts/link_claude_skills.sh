#!/usr/bin/env bash
# Link every skill in this repo into ~/.claude/skills, one symlink per skill.
# Why per skill: claude.ai syncs personal skills into ~/.claude/skills/synced/. With one symlink
# for the whole folder, that sync landed inside this repo, where OpenCode and Pi found stale copies.
# Run it after you add or remove a skill. Safe to run again.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
dest="${HOME}/.claude/skills"
if [ -L "$dest" ]; then
  echo "$dest is still a symlink to the whole folder; remove it first (unlink \"$dest\")." >&2
  exit 1
fi
mkdir -p "$dest"
for link in "$dest"/*; do
  [ -L "$link" ] && [ ! -e "$link" ] && { rm "$link"; echo "removed dangling $(basename "$link")"; }
done
for dir in "$repo"/*/; do
  name="$(basename "$dir")"
  [ -f "$dir/SKILL.md" ] || continue
  [ -e "$dest/$name" ] || { ln -s "$repo/$name" "$dest/$name"; echo "linked $name"; }
done
