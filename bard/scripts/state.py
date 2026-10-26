#!/usr/bin/env python3
"""Read and write `Bard/.bard-state.json`.

Why a script: the state file is the only thing that stops a sweep from redoing work it
already did, and the write used to be a shell ritual in prose. Alex's zsh sets `noclobber`,
so a plain `> state.json` fails with "file exists" and leaves the OLD watermark in place. The
sweep then looks successful and the next one redoes everything (seen 2026-09-04).

This module writes atomically, refuses the two values that silently cause a re-sweep, and
reads the file back before it reports success.

    python3 scripts/state.py show <path>
    python3 scripts/state.py record <path> --watermark 2026-10-25T15:00:00Z \
        --seen Scribe/Meetings/Transcripts/2026-10-25-team-sync.md

Four facts it enforces:

- `watermark` moves forward. A value older than the stored one is a bug, not a decision.
- `watermark` carries a real time. A rounded day boundary (`...T00:00:00Z`) re-sweeps that
  whole day on the next run, so it is refused.
- `watermark` is not in the future. A typo in the year would skip every sweep until that
  date, silently, and the backwards check cannot see it.
- `scribe_seen` only grows. Notes are a set, and a repeat is free because dedupe absorbs it.

Any other key in the file is carried through the write untouched: this module owns three
facts, not the whole file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

DEFAULTS = {"last_run": None, "watermark": None, "scribe_seen": []}


class StateError(ValueError):
    """The state file, or the value being written, would cause a wrong sweep."""


def load(path: str | Path) -> dict:
    """The state, with defaults for a file that does not exist yet."""
    path = Path(path)
    if not path.exists():
        return {**DEFAULTS, "scribe_seen": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"{path} is not readable JSON: {error}") from error
    if not isinstance(data, dict):
        raise StateError(f"{path} must hold an object, got {type(data).__name__}")
    state = dict(data)
    state.setdefault("last_run", None)
    state.setdefault("watermark", None)
    state.setdefault("scribe_seen", [])
    if not isinstance(state["scribe_seen"], list):
        raise StateError(f"{path} has a non-list scribe_seen")
    return state


def _when(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise StateError(f"{field} must be an ISO-8601 timestamp with a time, got {value!r}")
    if "T" not in value and " " not in value:
        raise StateError(
            f"{field} {value!r} is a date without a time; use the real session start"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise StateError(f"{field} is not ISO-8601: {value!r}") from error
    if parsed.tzinfo is None:
        raise StateError(f"{field} needs a timezone, got {value!r}")
    return parsed


def _check_watermark(new: str, old: str | None) -> None:
    """A watermark that goes back, or names a whole day, re-sweeps work already done."""
    parsed_new = _when(new, "watermark")
    if parsed_new.hour == 0 and parsed_new.minute == 0 and parsed_new.second == 0:
        raise StateError(
            f"watermark {new!r} is a rounded day boundary; use the real session start, or the "
            f"next run re-sweeps that whole day"
        )
    if old:
        parsed_old = _when(old, "stored watermark")
        if parsed_new < parsed_old:
            raise StateError(
                f"watermark {new!r} is older than the stored {old!r}; a run never moves it back"
            )
    ahead = parsed_new - datetime.now().astimezone()
    if ahead > timedelta(days=1):
        raise StateError(
            f"watermark {new!r} is {ahead.days} day(s) ahead of the clock; a date typo here "
            f"skips every sweep until that date, so check it"
        )


def _write_atomic(path: Path, state: dict) -> None:
    """Write beside the target, then replace it: no truncated file, no noclobber surprise.

    The folder must already exist. Creating it was a footgun: a mistyped or moved vault path
    then wrote a state file somewhere else, exited 0, left the real state behind, and the next
    sweep redid the work this module exists to prevent.
    """
    if not path.parent.is_dir():
        raise StateError(
            f"{path.parent} does not exist; check the vault path, or create the Bard folder first"
        )
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise StateError(f"could not write {path}: {error}; the previous file is unchanged") from error


def record_run(
    path: str | Path,
    watermark: str,
    seen: list[str] | tuple[str, ...] = (),
    now: str | None = None,
) -> dict:
    """Record one sweep. Returns the state that was written and verified."""
    path = Path(path)
    state = load(path)
    _check_watermark(watermark, state.get("watermark"))

    merged = list(state["scribe_seen"])
    for note in seen:
        if note not in merged:
            merged.append(note)

    stamp = now or datetime.now().astimezone().isoformat(timespec="seconds")
    _when(stamp, "last_run")
    updated = dict(state)
    updated.update(last_run=stamp, watermark=watermark, scribe_seen=merged)

    _write_atomic(path, updated)

    written = load(path)
    if written != updated:
        raise StateError(f"{path} did not read back as written; do not trust this run")
    return updated


def seen(path: str | Path) -> set[str]:
    return set(load(path)["scribe_seen"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read or update Bard's state file.")
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="print the state as JSON")
    show.add_argument("path")

    record = sub.add_parser("record", help="record one sweep")
    record.add_argument("path")
    record.add_argument("--watermark", required=True)
    record.add_argument("--seen", action="append", default=[], help="repeat per note swept")
    record.add_argument("--now", default=None, help="override last_run, for a re-run")

    args = parser.parse_args(argv)
    try:
        if args.command == "show":
            print(json.dumps(load(args.path), indent=2))
            return 0
        state = record_run(args.path, args.watermark, args.seen, args.now)
    except StateError as error:
        print(f"STATE FAILED: {error}", file=sys.stderr)
        return 1

    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
