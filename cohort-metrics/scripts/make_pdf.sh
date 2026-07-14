#!/usr/bin/env bash
# Render impact-deck.html to a one-slide-per-page PDF using system Chrome
# (headless --print-to-pdf). No puppeteer/node dependency.
# Usage: bash make_pdf.sh [out_dir]   (out_dir default: ./cohort-out)
set -euo pipefail
OUT="${1:-cohort-out}"
HTML="$(cd "$OUT" && pwd)/impact-deck.html"
PDF="$(cd "$OUT" && pwd)/impact-deck.pdf"
[ -f "$HTML" ] || { echo "Missing $HTML (run build_deck.py first)"; exit 1; }

# Locate a Chrome/Chromium binary.
CHROME=""
for c in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "$(command -v google-chrome 2>/dev/null || true)" \
  "$(command -v chromium 2>/dev/null || true)" \
  "$(command -v chromium-browser 2>/dev/null || true)"; do
  [ -n "$c" ] && [ -x "$c" ] && CHROME="$c" && break
done
[ -n "$CHROME" ] || { echo "No Chrome/Chromium found. Open $HTML and print to PDF manually."; exit 1; }

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=4000 \
  --print-to-pdf="$PDF" "file://$HTML" 2>/dev/null
echo "Wrote $PDF"
