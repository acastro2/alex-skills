#!/usr/bin/env python3
"""List what bard has not yet read in the gather store (`~/.gather`).

Why a script: bard reads gather's raw files instead of searching Teams, mail, and the rest
itself. It must know which files are new, what each source's latest fetch said, and which
files are not quotable. Doing that by eye over a growing folder is how a sweep skips a file.

    python3 scripts/gather_inbox.py list --state <vault>/Bard/.bard-state.json

Read-only. It prints one JSON object:

- `available`: false when the store folder is missing; every comms lane then falls back.
- `unseen`: {source: [relative paths]} for raw files not in the state's `gather_seen`. A snapshot
  source (jira, github) lists only the files of its newest run; each file has the name
  `<run_id>-<n>.json`.
- `superseded`: unseen files of older snapshot runs, sorted. A newer full snapshot replaces
  them, so bard marks them seen without reading.
- `ledger`: {source: line} from the newest ledger file that mentions the source.
- `fetched_at`: {source: `started_at` of the newest ledger file that has the source}.
- `covered_from`: {source: ISO time} copied from gather's `state.json`: how far back gather's
  history reaches for a window source.
- `fallback`: sources whose latest line does not start with `fetched`, whose latest fetch is
  older than `--max-age-hours` (default 24; a ledger with no `started_at` counts as old), or
  that have no line at all: a coverage gap. With `--state`, a window source (every source but
  jira and github, which hold every open item) whose `covered_from` is missing or later than the
  bard watermark is a gap too: gather never fetched the days before it. A `partial:` line is a
  gap. So is a `fetched ... 0 items` line for teams_chats, teams_mine, or mail when the run
  started on a Monday to Friday (UTC): a working day is never silent.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_ROOT = "~/.gather"
DEFAULT_MAX_AGE_HOURS = 24
# Every comms source gather can fill. One with no ledger line was never fetched: a gap.
SOURCES = ("teams_chats", "teams_mine", "teams_channels", "mail", "calendar", "sharepoint",
           "jira", "github", "slack")
# Snapshot sources hold every open item, so they have no history window to cover.
SNAPSHOT = ("jira", "github")
# A zero from these on a working day is a coverage failure, not a quiet day.
BUSY = ("teams_chats", "teams_mine", "mail")
_ITEMS = re.compile(r"\b(\d+) items\b")


def _json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _latest_ledger(root: Path) -> tuple[dict[str, str], dict[str, str | None]]:
    """Per source, the line and the run start from the newest ledger file; the file name is the run time."""
    lines: dict[str, str] = {}
    started: dict[str, str | None] = {}
    for path in sorted((root / "ledger").glob("*.json")):
        data = _json(path)
        sources = data.get("sources")
        if isinstance(sources, dict):
            for name, line in sources.items():
                lines[name] = str(line)
                started[name] = data.get("started_at") if isinstance(data.get("started_at"), str) else None
    return lines, started


def _is_stale(started_at: str | None, cutoff: datetime) -> bool:
    try:
        when = datetime.fromisoformat((started_at or "").replace("Z", "+00:00"))
    except ValueError:
        return True
    return when.tzinfo is None or when < cutoff


def _instant(text: object) -> datetime | None:
    if not isinstance(text, str):
        return None
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def _starts_after(covered_from: object, watermark: datetime) -> bool:
    """True when gather's history for a source is missing, unreadable, or starts after the watermark."""
    start = _instant(covered_from)
    return start is None or start > watermark


def _run_id(relative: str) -> str:
    """`raw/jira/2026-11-13/<run_id>-<n>.json` -> `<run_id>`."""
    return Path(relative).stem.rsplit("-", 1)[0]


def _empty_on_a_working_day(line: str, started_at: str | None) -> bool:
    found = _ITEMS.search(line)
    when = _instant(started_at)
    return bool(found) and int(found.group(1)) == 0 and when is not None and when.weekday() < 5


def listing(root: Path, seen: set[str], now: datetime | None = None,
            max_age_hours: float = DEFAULT_MAX_AGE_HOURS, watermark: str | None = None) -> dict:
    """With `now` set, a fetched line older than `max_age_hours` is a gap. With `watermark` set,
    so is a window source whose gather history starts after it."""
    root = Path(root)
    if not root.is_dir():
        return {"available": False, "unseen": {}, "ledger": {}, "fallback": [], "superseded": [],
                "fetched_at": {}, "covered_from": {}}

    unseen: dict[str, list[str]] = {}
    for path in sorted((root / "raw").glob("*/*/*.json")):
        relative = path.relative_to(root).as_posix()
        if relative not in seen:
            unseen.setdefault(path.relative_to(root / "raw").parts[0], []).append(relative)
    superseded: list[str] = []
    for source in SNAPSHOT:
        files = unseen.get(source, [])
        if files:
            newest = max(_run_id(name) for name in files)
            unseen[source] = [name for name in files if _run_id(name) == newest]
            superseded += [name for name in files if _run_id(name) != newest]

    ledger, fetched_at = _latest_ledger(root)
    stale: set[str] = set()
    if now is not None:
        cutoff = now - timedelta(hours=max_age_hours)
        stale = {name for name, line in ledger.items()
                 if line.startswith("fetched") and _is_stale(fetched_at[name], cutoff)}
    covered_from = _json(root / "state.json").get("covered_from")
    covered_from = dict(covered_from) if isinstance(covered_from, dict) else {}
    short: set[str] = set()
    floor = _instant(watermark)
    if floor is not None:
        short = {name for name, line in ledger.items()
                 if line.startswith("fetched") and name not in SNAPSHOT
                 and _starts_after(covered_from.get(name), floor)}
    empty = {name for name in BUSY if name in ledger and ledger[name].startswith("fetched")
             and _empty_on_a_working_day(ledger[name], fetched_at[name])}
    fallback = sorted({name for name, line in ledger.items() if not line.startswith("fetched")}
                      | stale | short | empty | {name for name in SOURCES if name not in ledger})
    return {
        "available": True,
        "unseen": dict(sorted(unseen.items())),
        "ledger": ledger,
        "fetched_at": fetched_at,
        "covered_from": covered_from,
        "fallback": fallback,
        "superseded": sorted(superseded),
    }


def _bard_state(path: str | None) -> dict:
    return _json(Path(path)) if path and Path(path).is_file() else {}


def _seen_from_state(path: str | None) -> set[str]:
    items = _bard_state(path).get("gather_seen", [])
    return set(items) if isinstance(items, list) else set()


def _watermark_from_state(path: str | None) -> str | None:
    mark = _bard_state(path).get("watermark")
    return mark if isinstance(mark, str) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List unread files in the gather store.")
    sub = parser.add_subparsers(dest="command", required=True)
    list_ = sub.add_parser("list", help="print the listing as JSON")
    list_.add_argument("--root", default=DEFAULT_ROOT)
    list_.add_argument("--state", default=None, help="the bard state file; its gather_seen is skipped")
    list_.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS,
                       help="a fetched source older than this is a gap (default 24)")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser()
    now = datetime.now(timezone.utc)
    out = listing(root, _seen_from_state(args.state), now, args.max_age_hours, _watermark_from_state(args.state))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
