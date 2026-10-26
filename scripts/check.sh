#!/usr/bin/env bash
# Is this repo green? One command, one exit code.
#
#   scripts/check.sh            # the rules, then every offline test suite
#   scripts/check.sh --tools    # also the ub-mode tools' own suites
#
# Each suite keeps its own interpreter and dependencies: three run under pytest, two under
# unittest, scribe needs pyusb, and the ub-mode tools carry a venv of their own. That is why
# this is a script and not one pytest invocation: the interpreter is the thing that varies,
# so the script owns it in one place.
#
# The ub-mode lane is behind a flag on purpose. Those tools are vendored at pinned commits,
# one of their tests needs babashka (`bb`), and the mutator suite takes about 75 seconds.
# The lane skips the babashka test, with the reason printed, when `bb` is absent.
#
# Nothing here touches the network and nothing here writes to the repo.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2

UV="${UV:-uv}"
WITH_TOOLS=0
[ "${1:-}" = "--tools" ] && WITH_TOOLS=1

if ! command -v "$UV" >/dev/null 2>&1; then
  echo "check: uv is required (https://docs.astral.sh/uv/). Set UV=/path/to/uv to point at it." >&2
  exit 2
fi

steps=0
failures=0

step() { printf '\n== %s\n' "$*"; steps=$((steps + 1)); }
run() { step "$*"; "$@" || failures=$((failures + 1)); }
run_in() { local dir="$1"; shift; step "$* (in $dir)"; ( cd "$dir" && "$@" ) || failures=$((failures + 1)); }

# --- rules ---------------------------------------------------------------------
run "$UV" run --with pyyaml python -m skillcheck
run "$UV" run --with pyyaml python ea-projects-curator/tests/ea_projects_curator_audit.py

# --- tests ---------------------------------------------------------------------
run "$UV" run --with pytest --with pyyaml python -m pytest scripts/tests ea-projects-curator/tests -q
run "$UV" run --with pytest --with requests python -m pytest browser-cookie-auth/tests -q
run "$UV" run --with pytest python -m pytest bard/tests -q
run "$UV" run --with pytest --with pyusb python -m pytest scribe/tests -q
run python3 -m unittest discover -s browser-apple-events/tests -p 'test_*.py'
run python3 -m unittest discover -s alex-voice/tests -p 'test_*.py'
run_in m365/scripts python3 -m unittest tests

# --- ub-mode tools, behind --tools ---------------------------------------------
if [ "$WITH_TOOLS" = "1" ]; then
  TOOLS_PY="ub-mode/tools/.venv/bin/python"
  if [ ! -x "$TOOLS_PY" ]; then
    echo "check: $TOOLS_PY is missing; run ub-mode/tools/setup.sh first" >&2
    exit 2
  fi
  run "$TOOLS_PY" -m pytest ub-mode/tools/src/dryer/tests -q
  run "$TOOLS_PY" -m pytest ub-mode/tools/src/mutator/tests -q
  if command -v bb >/dev/null 2>&1; then
    run "$TOOLS_PY" -m pytest ub-mode/tools/src/crapper/tests -q
  else
    echo "== crapper: skipping the babashka test (bb is not installed)"
    run "$TOOLS_PY" -m pytest ub-mode/tools/src/crapper/tests -q \
      -k "not test_project_snapshot_is_readable_as_crap4clj_edn"
  fi
fi

# --- verdict -------------------------------------------------------------------
printf '\n'
if [ "$failures" -ne 0 ]; then
  printf 'FAIL: %s of %s step(s) failed\n' "$failures" "$steps"
  exit 1
fi
printf 'PASS: %s step(s)\n' "$steps"
