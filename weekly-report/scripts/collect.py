#!/usr/bin/env python3
"""Collect the facts for one weekly report: the Mon-Fri window, the bard board, the Bard
notes written that week, the user's GitHub pull requests, and, when configured, how the team's
product moved (team PRs, saved Jira pages, saved Slack reads). Judgment stays with the model;
this script only gathers what can be counted, so two runs over the same week agree.

Usage:
  collect.py --vault <vault> [--date YYYY-MM-DD] [--no-github] [--jira FILE ...] [--slack FILE] > facts.json
Config (optional): ~/.config/weekly-report.json
  {"manager": "<first name>", "exclude_headings": ["Personal"], "github_orgs": ["org", ...],
   "team": {"name": "<team name>", "org": "<github org>", "repos": ["<repo>", ...]}}
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
# A backlog cleanup closes many tickets within seconds of each other; that is not a week of work.
BULK_MIN = 10
BULK_GAP = dt.timedelta(seconds=60)
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


def team_prs(window: tuple[dt.date, dt.date], team: dict, mine_urls: set[str], run=subprocess.run) -> dict:
    """The team's merged and open PRs. Searches the whole org and filters to the team repos
    here: a long `--repo` list makes GitHub search return 0 rows with exit 0."""
    span = f"{window[0].isoformat()}..{window[1].isoformat()}"
    repos = set(team["repos"])
    truncated = []
    def search(name: str, *flags: str) -> list[dict]:
        cmd = ["gh", "search", "prs", "--owner", team["org"], *flags, "--limit", str(PR_LIMIT),
               "--json", "repository,number,title,author,closedAt,url,isDraft,state"]
        proc = run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip()[:300])
        page = json.loads(proc.stdout or "[]")
        if len(page) >= PR_LIMIT:
            truncated.append(f"team {name}")
        rows = []
        for p in page:
            if p["repository"]["name"] not in repos:
                continue
            stamp = p.get("closedAt") or ""
            rows.append({"repo": p["repository"]["name"], "number": p["number"], "title": p["title"],
                         "author": (p.get("author") or {}).get("login"), "url": p["url"],
                         "closed": stamp[:10] if stamp and not stamp.startswith("0001") else None,
                         "draft": bool(p.get("isDraft")), "mine": p["url"] in mine_urls})
        return rows
    merged = search("merged", f"--merged-at={span}")
    open_ = search("open", "--state", "open", f"--updated={span}")
    return {"merged": merged, "open": open_, "truncated": truncated}


def chicago_day(stamp: str | None) -> dt.date | None:
    """Jira stamps look like 2026-11-13T09:19:03.024-0600; the report day is Chicago time."""
    return dt.datetime.fromisoformat(stamp).astimezone(TZ).date() if stamp else None


def find_bulk_runs(resolutions: list[tuple[str, dt.datetime]]) -> list[list[tuple[str, dt.datetime]]]:
    """Runs of at least BULK_MIN resolutions, each within BULK_GAP of the one before, in time order."""
    runs: list[list[tuple[str, dt.datetime]]] = []
    for item in sorted(resolutions, key=lambda r: r[1]):
        if runs and item[1] - runs[-1][-1][1] <= BULK_GAP:
            runs[-1].append(item)
        else:
            runs.append([item])
    return [run for run in runs if len(run) >= BULK_MIN]


def parse_jira(pages: list[str], window: tuple[dt.date, dt.date]) -> dict:
    """Merge saved `searchJiraIssuesUsingJql` pages into resolved, created and bug lists. `missing`
    counts issues the search reported but the pages did not carry, so a skipped page shows."""
    issues: dict[str, dict] = {}
    moments: dict[str, dt.datetime] = {}
    total = 0
    for text in pages:
        data = json.loads(text)
        me = data.get("context", {}).get("atlassianAccountId")
        total = max(total, data["issues"].get("totalCount", 0))  # only the first page has it
        for node in data["issues"]["nodes"]:
            f = node["fields"]
            assignee = f.get("assignee")
            if f.get("resolutiondate"):
                moments.setdefault(node["key"], dt.datetime.fromisoformat(f["resolutiondate"]))
            issues.setdefault(node["key"], {
                "key": node["key"], "summary": f["summary"], "type": f["issuetype"]["name"],
                "status": f["status"]["name"], "assignee": assignee["displayName"] if assignee else None,
                "url": node["webUrl"], "created": chicago_day(f["created"]),
                "resolved": chicago_day(f.get("resolutiondate")),
                "mine": bool(assignee) and bool(me) and assignee.get("accountId") == me})
    def inside(day: dt.date | None) -> bool:
        return day is not None and in_window(day, window)
    items = list(issues.values())
    bulk_runs = find_bulk_runs([(k, m) for k, m in moments.items() if inside(issues[k]["resolved"])])
    bulk_keys = {k for run in bulk_runs for k, _ in run}
    for i in items:
        i["bulk"] = i["key"] in bulk_keys
    out = {"resolved": [i for i in items if inside(i["resolved"])],
           "created": [i for i in items if inside(i["created"])],
           "bugs": [i for i in items if i["type"] == "Bug" and (inside(i["created"]) or inside(i["resolved"]))]}
    for i in items:
        i["created"] = i["created"].isoformat()
        i["resolved"] = i["resolved"].isoformat() if i["resolved"] else None
    return {**out, "bulk_runs": [{"start": run[0][1].isoformat(), "count": len(run)} for run in bulk_runs],
            "total": total, "missing": max(0, total - len(items))}


def parse_slack(text: str) -> dict:
    """A saved paste of Slack reads: {"calls": [{"tool", "args", "content"}]}. Content stays verbatim."""
    calls = json.loads(text).get("calls")
    if not isinstance(calls, list) or not calls:
        raise ValueError("slack file needs a non-empty 'calls' list")
    for c in calls:
        if not (isinstance(c, dict) and isinstance(c.get("tool"), str)
                and isinstance(c.get("args"), dict) and isinstance(c.get("content"), str)):
            raise ValueError("each slack call needs tool (str), args (object), content (str)")
    return {"calls": len(calls), "items": [{k: c[k] for k in ("tool", "args", "content")} for c in calls]}


def team_facts(team: dict, window: tuple[dt.date, dt.date], facts: dict, args: argparse.Namespace) -> dict:
    """The team block and its gaps, in the order github, jira, slack, datadog."""
    gaps = []
    prs, prs_error = None, None
    if args.no_github:
        gaps.append("github: not fetched (--no-github)")
    else:
        mine = {p["url"] for p in (facts["github"] or {}).get("authored", [])}
        try:
            prs = team_prs(window, team, mine)
        except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            prs_error = str(exc)
            gaps.append(f"github: {prs_error}")
    # A broken paste file must cost only its own source, never Alex's own facts.
    jira = slack = None
    if not args.jira:
        gaps.append("jira: not fetched")
    else:
        try:
            jira = parse_jira([p.read_text() for p in args.jira], window)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            gaps.append(f"jira: unreadable page ({type(exc).__name__}: {exc})"[:300])
        else:
            if jira["missing"] > 0:
                gaps.append(f"jira: {jira['missing']} issues missing (pass every page; bulk flags are unreliable)")
    if not args.slack:
        gaps.append("slack: not fetched")
    else:
        try:
            slack = parse_slack(args.slack.read_text())
        except (OSError, ValueError, AttributeError) as exc:
            gaps.append(f"slack: unreadable file ({exc})"[:300])
    gaps.append("datadog: not fetched")
    return {"name": team.get("name"), "prs": prs, "prs_error": prs_error, "jira": jira, "slack": slack, "gaps": gaps}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", type=Path, required=True)
    ap.add_argument("--date", type=dt.date.fromisoformat, default=None, help="any day in the week; default today")
    ap.add_argument("--no-github", action="store_true")
    ap.add_argument("--jira", type=Path, action="append", help="saved Jira search page; repeat per page")
    ap.add_argument("--slack", type=Path, help="saved Slack reads, JSON")
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
        "team": None,
        "report_path": str(args.vault / "Reports" / "Weekly" / f"{iso_week_label(window[0])}.md"),
    }
    if not args.no_github:
        try:
            facts["github"] = github_prs(window, config.get("github_orgs", []))
        except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            facts["github_error"] = str(exc)
    if config.get("team"):
        facts["team"] = team_facts(config["team"], window, facts, args)
    json.dump(facts, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
