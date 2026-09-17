#!/usr/bin/env bash
# Put the m365 CLI on PATH by symlinking the skill's script into ~/.local/bin.
# Symlink, not copy, so the installed command cannot drift from the skill.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$HOME/.local/bin"
SCRIPT="$SKILL_DIR/scripts/m365.py"

chmod +x "$SCRIPT"
mkdir -p "$TARGET"
ln -sf "$SCRIPT" "$TARGET/m365"

case ":$PATH:" in
  *":$TARGET:"*) ;;
  *) echo "warning: $TARGET is not on PATH - add it to your shell profile" >&2 ;;
esac

echo "installed: $TARGET/m365 -> $SCRIPT"
command -v m365 >/dev/null && echo "resolves to: $(command -v m365)"
