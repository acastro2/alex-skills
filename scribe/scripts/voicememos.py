#!/usr/bin/env python3
"""List Apple Voice Memos recordings on this Mac, read-only.

Voice Memos keeps its index in a Core Data SQLite file in WAL mode, open while the app runs.
This script copies the database and its -wal/-shm sidecars to a temp folder and reads the
copy, so it never takes a lock on, or writes to, the live store. Audio files are read in
place by the caller; nothing here copies, moves, or deletes a recording.

Usage:
  voicememos.py list [--since YYYY-MM-DD] [--min-seconds N] [--json]
Exit codes: 0 ok, 3 the store is missing or unreadable (Voice Memos never opened, or the
terminal lacks Full Disk Access).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

STORE = Path.home() / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
CORE_DATA_EPOCH = 978307200  # 2001-01-01T00:00:00Z, the zero of Core Data dates
# Titles the app gives by itself carry no meaning: "New Recording", "New Recording 12".
GENERIC_TITLE = re.compile(r"^New Recording( \d+)?$", re.I)


def core_data_to_iso(seconds: float) -> str:
    moment = dt.datetime.fromtimestamp(seconds + CORE_DATA_EPOCH, dt.timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def read_rows(db: Path) -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="scribe-vm-") as tmp:
        copy = Path(tmp) / db.name
        for suffix in ("", "-wal", "-shm"):
            src = db.with_name(db.name + suffix)
            if src.exists():
                shutil.copy2(src, copy.with_name(copy.name + suffix))
        con = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "SELECT ZUNIQUEID, ZDATE, ZDURATION, ZCUSTOMLABEL, ZPATH, ZEVICTIONDATE "
                "FROM ZCLOUDRECORDING ORDER BY ZDATE"
            ).fetchall()
        finally:
            con.close()
    return [
        {"id": r[0], "date": r[1], "duration": r[2], "label": r[3], "path": r[4], "evicted": r[5] is not None}
        for r in rows
    ]


def to_memo(row: dict, store: Path) -> dict:
    audio = store / row["path"] if row["path"] else None
    label = (row["label"] or "").strip()
    return {
        "id": row["id"],
        "start": core_data_to_iso(row["date"]) if row["date"] is not None else None,
        "duration_s": round(row["duration"] or 0, 1),
        "title": None if not label or GENERIC_TITLE.match(label) else label,
        "audio": str(audio) if audio else None,
        # An iCloud memo the Mac has not downloaded yet has a row but no file.
        "local": bool(audio and audio.exists()),
        "evicted": row["evicted"],
    }


def select(memos: list[dict], since: dt.date | None, min_seconds: float) -> list[dict]:
    out = []
    for memo in memos:
        if not memo["id"] or not memo["start"]:
            continue
        if since and dt.date.fromisoformat(memo["start"][:10]) < since:
            continue
        if memo["duration_s"] < min_seconds:
            continue
        out.append(memo)
    return out


def main(argv: list[str] | None = None, store: Path = STORE) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--since", type=dt.date.fromisoformat, default=None)
    ls.add_argument("--min-seconds", type=float, default=30)
    ls.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    db = store / "CloudRecordings.db"
    try:
        memos = [to_memo(r, store) for r in read_rows(db)]
    except (OSError, sqlite3.Error) as exc:
        print(f"Voice Memos store unreadable at {db}: {exc}. Open Voice Memos once, and give the "
              "terminal Full Disk Access if macOS blocks it.", file=sys.stderr)
        return 3
    memos = select(memos, args.since, args.min_seconds)
    if args.json:
        json.dump(memos, sys.stdout, indent=2)
        print()
    else:
        for m in memos:
            flag = "" if m["local"] else "  (not on this Mac yet: open it in Voice Memos to download)"
            print(f"{m['start']}  {m['duration_s']:>7.0f}s  {m['title'] or '-'}  {m['id']}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
