#!/bin/sh
# Clone the three Uncle Bob tools at pinned commits and install them into one
# shared virtualenv under ub-mode/tools/.venv.
set -eu

HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
SRC="$HERE/src"
VENV="$HERE/.venv"
PY="$VENV/bin/python"

mkdir -p "$SRC"

# repo:commit
PINS="
crapper:6fd92c4c9bcc56efb64a2f8743d5a2993bcfd42d
dryer:66ff6d21a42c04afcad89c78a80066176d1294b0
mutator:a5a0cb803b66e0cdb8bf471b3b08af701d424a41
"

printf '%s\n' "$PINS" | while IFS=: read -r repo commit; do
  [ -n "$repo" ] || continue
  if [ ! -d "$SRC/$repo/.git" ]; then
    git clone --quiet "https://github.com/unclebob/$repo" "$SRC/$repo"
  fi
  git -C "$SRC/$repo" fetch --quiet --depth 1 origin "$commit"
  git -C "$SRC/$repo" checkout --quiet --detach "$commit"
  echo "pinned $repo at $commit"
done

if [ ! -x "$PY" ]; then
  python3 -m venv "$VENV"
fi

"$PY" -m pip install --quiet --upgrade pip
for repo in crapper dryer mutator; do
  "$PY" -m pip install --quiet --editable "$SRC/$repo"
done

echo
echo "installed:"
"$PY" -m crapper --help >/dev/null && echo "  crapper ok"
"$PY" -m dryer --help >/dev/null && echo "  dryer ok"
"$PY" -m mutator --help >/dev/null && echo "  mutator ok"
