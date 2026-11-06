#!/usr/bin/env python3
"""Propose and apply document dates to curated Evidence notes.

Dates come from the Evidence catalog, which extracts them from frontmatter,
filename, or an explicit label in the body. This script never invents a date.

Run:
    python3 scripts/evidence_dates.py propose --vault /path/to/vault > dates.csv
    python3 scripts/evidence_dates.py apply --vault /path/to/vault --report dates.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_catalog


def load_rows(evidence: Path) -> list[dict]:
    path = evidence / "catalog.jsonl"
    if not path.exists():
        raise SystemExit("catalog.jsonl missing; run evidence_catalog.py build first")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def curated_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if not row["path"].startswith("Sources/")]


def date_snippet(path: Path, date: str) -> str:
    if not date:
        return ""
    text = path.read_text(errors="ignore")
    for line in text.splitlines()[:300]:
        if date in line or date[:7] in line:
            return line.strip()[:160]
    return ""


def propose(vault: Path) -> int:
    evidence = vault / "Evidence"
    rows = curated_rows(load_rows(evidence))
    writer = csv.writer(sys.stdout)
    writer.writerow(["path", "date", "date_precision", "date_source", "snippet"])
    for row in rows:
        writer.writerow([
            row["path"],
            row["date"] or "",
            row["date_precision"],
            row["date_source"],
            date_snippet(evidence / row["path"], row["date"] or ""),
        ])
    return 0


def set_frontmatter(text: str, updates: dict[str, str]) -> tuple[str, bool]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if not match:
        return text, False
    lines = match.group(1).splitlines()
    replaced: set[str] = set()
    output: list[str] = []
    for line in lines:
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if key in updates:
            output.append(f"{key}: {updates[key]}")
            replaced.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in replaced:
            output.append(f"{key}: {value}")
    block = "\n".join(output)
    return f"---\n{block}\n---\n" + text[match.end():], True


def apply(vault: Path, report: Path | None) -> int:
    evidence = vault / "Evidence"
    rows = curated_rows(load_rows(evidence))
    allowed: dict[str, dict] | None = None
    if report:
        allowed = {}
        with report.open(newline="") as handle:
            for row in csv.DictReader(handle):
                allowed[row["path"]] = row
    changed = skipped = 0
    for row in rows:
        if not row.get("date"):
            skipped += 1
            continue
        if allowed is not None and row["path"] not in allowed:
            skipped += 1
            continue
        path = evidence / row["path"]
        text = path.read_text(errors="ignore")
        updates = {
            "date": row["date"],
            "date_precision": row["date_precision"],
            "date_source": row["date_source"],
        }
        new_text, has_frontmatter = set_frontmatter(text, updates)
        if not has_frontmatter:
            skipped += 1
            continue
        if new_text != text:
            path.write_text(new_text)
            changed += 1
    print(f"dates applied: {changed}; skipped: {skipped}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Propose or apply Evidence document dates.")
    parser.add_argument("command", choices=("propose", "apply"))
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    return propose(args.vault) if args.command == "propose" else apply(args.vault, args.report)


if __name__ == "__main__":
    raise SystemExit(main())
