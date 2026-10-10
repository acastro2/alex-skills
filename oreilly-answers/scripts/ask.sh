#!/usr/bin/env bash
# Ask every question in QUESTIONS (one per line) and write raw JSON plus one combined Markdown file.
# Usage: ask.sh QUESTIONS_FILE OUT_DIR [SESSION]
set -euo pipefail
questions=$1; out=$2; session=${3:-oreilly}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out/raw" "$HOME/.cache/oreilly-answers"
browser-control session new "$session" >/dev/null 2>&1 || true

i=0
while IFS= read -r q || [ -n "$q" ]; do
  [ -z "$q" ] && continue
  i=$((i + 1))
  # Python writes the question: a shell ">" fails under zsh noclobber and silently re-asks the old one.
  python3 -c 'import sys; open(sys.argv[1], "w").write(sys.argv[2])' "$HOME/.cache/oreilly-answers/q.txt" "$q"
  browser-control execute --json --session "$session" --file "$here/ask.js" > "$out/raw/q$i.json" 2> "$out/raw/q$i.err" || true
  python3 "$here/to_md.py" --check "$out/raw/q$i.json" "$q" || true
done < "$questions"

python3 "$here/to_md.py" "$out/raw" > "$out/answers.md"
echo "wrote $out/answers.md ($i questions)"
