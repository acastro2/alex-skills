#!/usr/bin/env python3
"""Collect the facts for one weekly report: the Mon-Fri window, the bard board, the Bard
notes written that week, and the user's GitHub pull requests. Judgment stays with the model;
this script only gathers what can be counted, so two runs over the same week agree.

Usage:
  collect.py --vault <vault> [--date YYYY-MM-DD] [--no-github] > facts.json
Config (optional): ~/.config/weekly-report.json
  {"manager": "<first name>", "exclude_headings": ["Personal"], "github_orgs": ["org", ...]}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")
CONFIG = Path.home() / ".config" / "weekly-report.json"
PRIORITY = re.compile(r"(🔺|⏫|🔼|🔽|⏬)")
DONE_DATE = re.compile(r"✅ (\d{4}-\d{2}-\d{2})\s*$")
MARKER = "<!-- BARD:START"
PR_LIMIT = 200
# bard tags a Personal line when it moves to the flat Done list, where the heading is lost.
PERSONAL_TAG = re.compile(r"(?<!\S)#personal(?!\S)", re.IGNORECASE)


def week_window(day: dt.date) -> tuple[dt.date, dt.date]:
    """Mon-Fri of the week that holds `day`. A Saturday or Sunday belongs to the week that
    just ended, so a weekend run reports the finished week, not an empty new one."""
    monday = day - dt.timedelta(days=day.weekday())
    return monday, monday + dt.timedelta(days=4)


def iso_week_label(monday: dt.date) -> str:
    year, week, _ = monday.isocalendar()
    return f"{year}-W{week:02d}"


def in_window(day: dt.date, window: tuple[dt.date, dt.date]) -> bool:
    return window[0] <= day <= window[1]


def parse_board(text: str, window: tuple[dt.date, dt.date], exclude: list[str]) -> dict:
    """Read only bard's part of Todo.md (below the marker). Open lines keep their horizon
    heading; done lines count only when their ✅ date falls in the window. A heading that
    names an excluded word (for example Personal) hides everything below it, sub-headings
    included, until the next heading at the same level or higher."""
    body = text.split(MARKER, 1)[1] if MARKER in text else text
    words = [re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in exclude]
    out = {"open": [], "done": []}
    heading, hidden_at = "", None
    for line in body.splitlines():
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            heading = line.lstrip("#").strip()
            if hidden_at is not None and level <= hidden_at:
                hidden_at = None
            if hidden_at is None and any(w.search(heading) for w in words):
                hidden_at = level
            continue
        if hidden_at is not None or PERSONAL_TAG.search(line):
            continue
        if line.startswith("- [x]"):
            m = DONE_DATE.search(line)
            if m and in_window(dt.date.fromisoformat(m.group(1)), window):
                out["done"].append({"line": line[6:].strip(), "date": m.group(1)})
        elif line.startswith("- [ ]"):
            p = PRIORITY.findall(line)
            out["open"].append({"line": line[6:].strip(), "horizon": heading, "priority": p[-1] if p else None})
    return out


def parse_archive(text: str, window: tuple[dt.date, dt.date]) -> list[dict]:
    """Done items bard already rolled over to the archive can still belong to this week."""
    done = []
    for line in text.splitlines():
        m = DONE_DATE.search(line) if line.startswith("- [x]") and not PERSONAL_TAG.search(line) else None
        if m and in_window(dt.date.fromisoformat(m.group(1)), window):
            done.append({"line": line[6:].strip(), "date": m.group(1)})
    return done


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    block = text[4:].split("\n---", 1)[0]
    meta = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    return meta


def note_day(timestamp: str) -> dt.date | None:
    """A note's `timestamp` is ISO 8601 with Z or an offset; the report day is Chicago time."""
    try:
        moment = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=TZ)
    return moment.astimezone(TZ).date()


def bard_notes(bard_dir: Path, window: tuple[dt.date, dt.date]) -> list[dict]:
    notes = []
    for path in sorted(bard_dir.glob("*.md")):
        meta = frontmatter(path.read_text(errors="replace"))
        if meta.get("type") in (None, "hub", "board", "index", "reference"):
            continue
        day = note_day(meta.get("timestamp", ""))
        if day and in_window(day, window):
            notes.append({k: meta.get(k) for k in ("title", "type", "description", "up", "source", "resource")})
    return notes


def select_prs(raw: list[dict], window: tuple[dt.date, dt.date]) -> list[dict]:
    """Keep open PRs, and merged or closed ones only when they closed inside the window. An
    old PR that only got a comment this week is not this week's work. `state` from
    `gh search` already tells merged from closed-unmerged."""
    kept = []
    for p in raw:
        stamp = p.get("closedAt") or ""
        closed = stamp[:10] if stamp and not stamp.startswith("0001") else None
        if closed and not in_window(dt.date.fromisoformat(closed), window):
            continue
        kept.append({"repo": p["repository"]["nameWithOwner"], "number": p["number"], "title": p["title"],
                     "state": p["state"], "url": p["url"], "closed": closed})
    return kept


def github_prs(window: tuple[dt.date, dt.date], orgs: list[str], run=subprocess.run) -> dict:
    """Authored and reviewed PRs touched or merged in the window. Read-only `gh search`.
    `--updated` matches only the last update, so a PR merged this week and commented on later
    needs the second, `--merged-at` search. A search that returns a full page may have
    dropped results, so it is named in `truncated`."""
    span = f"{window[0].isoformat()}..{window[1].isoformat()}"
    truncated = []
    def search(name: str, *flags: str) -> list[dict]:
        found: dict[str, dict] = {}
        for date_filter in (f"--updated={span}", f"--merged-at={span}"):
            cmd = ["gh", "search", "prs", *flags, date_filter, "--limit", str(PR_LIMIT),
                   "--json", "repository,number,title,state,closedAt,url,updatedAt"]
            for org in orgs:
                cmd += ["--owner", org]
            proc = run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip()[:300])
            page = json.loads(proc.stdout or "[]")
            if len(page) >= PR_LIMIT:
                truncated.append(f"{name} {date_filter.split('=')[0]}")
            found.update({p["url"]: p for p in page})
        return list(found.values())
    authored = search("authored", "--author", "@me")
    mine = {a["url"] for a in authored}
    reviewed = [p for p in search("reviewed", "--reviewed-by", "@me") if p["url"] not in mine]
    return {"authored": select_prs(authored, window), "reviewed": select_prs(reviewed, window),
            "truncated": truncated}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", type=Path, required=True)
    ap.add_argument("--date", type=dt.date.fromisoformat, default=None, help="any day in the week; default today")
    ap.add_argument("--no-github", action="store_true")
    args = ap.parse_args(argv)

    config = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    today = dt.datetime.now(TZ).date()
    window = week_window(args.date or today)
    bard_dir = args.vault / "Bard"
    state_file = bard_dir / ".bard-state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}

    board = parse_board((args.vault / "Todo.md").read_text(), window, config.get("exclude_headings", ["Personal"]))
    archive = bard_dir / "Done Archive.md"
    if archive.exists():
        seen = {d["line"] for d in board["done"]}
        board["done"] += [d for d in parse_archive(archive.read_text(), window) if d["line"] not in seen]

    facts = {
        "week": iso_week_label(window[0]),
        "window": [window[0].isoformat(), window[1].isoformat()],
        "manager": config.get("manager"),
        "bard_last_run": state.get("last_run"),
        "bard_fresh": bool(state.get("last_run")) and note_day(state["last_run"]) == today,
        "board": board,
        "notes": bard_notes(bard_dir, window),
        "github": None,
        "github_error": None,
        "report_path": str(args.vault / "Reports" / "Weekly" / f"{iso_week_label(window[0])}.md"),
    }
    if not args.no_github:
        try:
            facts["github"] = github_prs(window, config.get("github_orgs", []))
        except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            facts["github_error"] = str(exc)
    json.dump(facts, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
