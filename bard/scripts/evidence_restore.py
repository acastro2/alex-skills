#!/usr/bin/env python3
"""Restore Evidence files from a manifest backup.

The backup is created before a repair run. This restores only the files in the
manifest, verifies every hash, and leaves generated catalog files in place.
Rebuild the catalog after a restore.

Run:
    python3 scripts/evidence_restore.py --backup <dir> --vault <vault> --dry-run
    python3 scripts/evidence_restore.py --backup <dir> --vault <vault>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restore Evidence files from a backup manifest.")
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    manifest_path = args.backup / "manifest.json"
    if not manifest_path.exists():
        print(f"error: no manifest at {manifest_path}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())
    evidence = args.vault / "Evidence"
    missing = 0
    bad = 0
    restored = 0
    for row in manifest:
        source = args.backup / "Evidence" / row["path"]
        target = evidence / row["path"]
        if not source.exists():
            print(f"missing backup file: {row['path']}", file=sys.stderr)
            missing += 1
            continue
        if sha(source) != row["sha256"]:
            print(f"backup hash mismatch: {row['path']}", file=sys.stderr)
            bad += 1
            continue
        if args.dry_run:
            restored += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha(target) != row["sha256"]:
            print(f"restore hash mismatch: {row['path']}", file=sys.stderr)
            bad += 1
            continue
        restored += 1
    verb = "verified" if args.dry_run else "restored"
    print(f"{verb}: {restored}; missing: {missing}; bad: {bad}")
    return 1 if missing or bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
