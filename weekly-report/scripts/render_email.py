#!/usr/bin/env python3
"""Render the weekly status email: the report's words (report JSON) in a designed template, with
every number computed from the collector's facts JSON.

  render_email.py --report R --facts F --out OUT [--template light] [--draft]

Output is a plain <html><head><body> document: no doctype, no title, no comments, no
<!--[if mso]> blocks, because those give an empty body in Outlook's AppleScript. The dark-mode
<style> goes in <head>, because a <style> in the body shows up as visible text.
Colors and layout live in assets/email/<template>.html, never here.
Exit 0 on success, 2 for a bad report or bad JSON, 1 when the Outlook draft fails."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from string import Template
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")
ASSETS = Path(__file__).resolve().parents[1] / "assets" / "email"
MAX_DECISIONS, MAX_DONE, MAX_NEXT = 5, 7, 5
DAY_BAR_MAX, MIN_BAR = 72, 2
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SOURCE_NAMES = {"github": "GitHub"}
NOT_FETCHED = "\u2013"

DRAFT_SCRIPT = """on run argv
  set h to read POSIX file (item 1 of argv) as «class utf8»
  tell application "Microsoft Outlook"
    set m to make new outgoing message with properties {subject:(item 2 of argv), content:h}
    open m
  end tell
end run
"""


class ReportError(ValueError):
    """The report or facts cannot make a valid email."""


def load_blocks(name: str) -> dict[str, str]:
    if not re.fullmatch(r"[a-z0-9_-]+", name):
        raise ReportError(f"template: bad name {name!r}")
    path = ASSETS / f"{name}.html"
    if not path.exists():
        raise ReportError(f"template: {path} not found")
    _, *parts = re.split(r"<!-- @block (\w+) -->", path.read_text(encoding="utf-8"))
    # Only the newlines go: some blocks start with a deliberate space.
    return {parts[i]: re.sub(r"<!--.*?-->", "", parts[i + 1], flags=re.S).strip("\n")
            for i in range(0, len(parts), 2)}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text_field(owner: dict, key: str, where: str) -> str:
    value = owner.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReportError(f"{where}: missing '{key}'")
    return value


def share(part: int, whole: int, scale: int) -> int:
    """round(scale * part / whole), halves up, in integers."""
    return (2 * scale * part + whole) // (2 * whole)


def clock(stamp: str | None) -> str:
    if not stamp:
        return "unknown"
    try:
        moment = dt.datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return "unknown"
    moment = moment.replace(tzinfo=TZ) if moment.tzinfo is None else moment.astimezone(TZ)
    hour = moment.hour % 12 or 12
    return f"{MONTHS[moment.month - 1]} {moment.day}, {hour}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'} CT"


def week_range(first: dt.date, last: dt.date) -> str:
    start = f"{MONTHS[first.month - 1]} {first.day}"
    end = str(last.day) if first.month == last.month else f"{MONTHS[last.month - 1]} {last.day}"
    return f"{start}–{end}"


class Email:
    def __init__(self, blocks: dict[str, str]):
        self.blocks = blocks

    def block(self, name: str) -> str:
        if name not in self.blocks:
            raise ReportError(f"template: missing block '{name}'")
        return self.blocks[name]

    def fill(self, block: str, /, **slots: object) -> str:
        try:
            return Template(self.block(block)).substitute(slots)
        except KeyError as exc:
            raise ReportError(f"template: block '{block}' needs slot {exc}") from exc

    def link(self, item: dict, where: str) -> str:
        url, ref = item.get("url"), item.get("ref")
        if not url:
            return ""
        if not str(url).startswith(("https://", "http://")):
            raise ReportError(f"{where}: url must start with http:// or https://")
        return self.fill("link", url=esc(url), ref=esc(ref or urlparse(str(url)).netloc))

    def decision(self, n: int, item: dict) -> tuple[str, str]:
        where = f"decisions[{n - 1}]"
        options = item.get("options")
        if not isinstance(options, list) or not options:
            raise ReportError(f"{where}: needs at least one option")
        picks = [i for i, o in enumerate(options) if o.get("picked")]
        if len(picks) != 1:
            raise ReportError(f"{where}: exactly one option must be picked")
        rows = []
        for i, option in enumerate(options):
            code, label = f"{n}{chr(65 + i)}", esc(text_field(option, "label", f"{where}.options[{i}]"))
            if i == picks[0]:
                detail = self.fill("option_detail", detail=esc(option["detail"])) if option.get("detail") else ""
                rows.append(self.fill("option_picked", code=code, label=label, detail=detail))
            else:
                rows.append(self.fill("option_other", code=code, label=label))
        card = self.fill("decision", n=n, ask=esc(text_field(item, "ask", where)),
                         options="\n".join(rows), why=esc(text_field(item, "why", where)))
        return card, f"{n}{chr(65 + picks[0])}"

    def done(self, groups: list) -> str:
        rows = []
        for g, group in enumerate(groups):
            rows.append(self.fill("done_theme" if g else "done_theme_first",
                                  theme=esc(text_field(group, "theme", f"done[{g}]").upper())))
            for i, item in enumerate(group.get("items") or []):
                where = f"done[{g}].items[{i}]"
                rows.append(self.fill("done_item", text=esc(text_field(item, "text", where)),
                                      link=self.link(item, where)))
        count = sum(len(g.get("items") or []) for g in groups)
        return self.fill("done", count=count, rows="\n".join(rows))

    def blocked(self, items: list) -> str:
        rows = []
        for i, item in enumerate(items):
            who = item.get("waiting_on")
            waiting = self.fill("blocked_waiting", name=esc(who)) if who else ""
            rows.append(self.fill("blocked_item", text=esc(text_field(item, "text", f"blocked[{i}]")),
                                  waiting=waiting))
        return self.fill("blocked", rows="\n".join(rows))

    def team(self, report: dict, team: dict, window: list[dt.date]) -> str:
        prs, jira = team.get("prs"), team.get("jira")
        days = [window[0] + dt.timedelta(days=i) for i in range(5)]
        merged = [p.get("closed") for p in (prs or {}).get("merged", [])]
        counts = [merged.count(d.isoformat()) for d in days]
        total, peak = sum(counts), max(counts)
        shown = (lambda n: n) if prs is not None else (lambda n: NOT_FETCHED)
        busiest = counts.index(peak) if peak else -1
        bars = [self.fill("day_bar_busy" if i == busiest else "day_bar", count=shown(n),
                          h=share(n, peak, DAY_BAR_MAX) if n else MIN_BAR) for i, n in enumerate(counts)]
        labels = [self.fill("day_label_busy" if i == busiest else "day_label", name=d.strftime("%a"))
                  for i, d in enumerate(days)]
        if prs is None:
            takeaway = "Merges not fetched."
        elif busiest < 0:
            takeaway = "No merges this week."
        else:
            takeaway = f"{WEEKDAYS[busiest]} carried the week: {peak} of {total} merges."
        in_review = sum(1 for p in (prs or {}).get("open", []) if not p.get("draft"))

        fetched = jira is not None
        jira = jira or {}
        resolved = sum(1 for t in jira.get("resolved", []) if not t.get("bulk"))
        created, bugs = len(jira.get("created", [])), len(jira.get("bugs", []))
        scale = max(resolved, created, bugs)
        if team.get("jira") is None:
            flow = "Tickets not fetched."
        elif resolved > created:
            flow = f"Backlog shrank by {resolved - created} tickets."
        elif created > resolved:
            flow = f"Backlog grew by {created - resolved} tickets."
        else:
            flow = "Backlog held steady."
        rows = []
        for name, value in (("flow_resolved", resolved), ("flow_created", created), ("flow_bugs", bugs)):
            width = share(value, scale, 100) if scale and fetched else 0
            rest = self.fill("flow_rest", w=100 - width) if width < 100 else ""
            rows.append(self.fill(name, w=width, rest=rest, value=value if fetched else NOT_FETCHED))
        cleanup = sum(r.get("count", 0) for r in jira.get("bulk_runs", []))
        note = "\n" + self.fill("bulk_note", count=cleanup) if cleanup > 0 and fetched else ""

        lines = [self.fill("team_line", text=esc(text_field(item, "text", f"team[{i}]")),
                           link=self.link(item, f"team[{i}]"))
                 for i, item in enumerate(report.get("team") or [])]
        return self.fill("team", team_name=esc(str(team.get("name") or "").upper()), chart_takeaway=takeaway,
                         day_bars="\n".join(bars), day_labels="\n".join(labels),
                         prs_merged=shown(total), prs_in_review=shown(in_review), flow_takeaway=flow,
                         flow_rows="\n".join(rows), bulk_note=note, lines="\n".join(lines))

    def footer(self, facts: dict, team: dict | None, range_text: str) -> str:
        status = (self.fill("footer_fresh") if facts.get("bard_fresh")
                  else self.fill("footer_stale", last_run=clock(facts.get("bard_last_run"))))
        notes = ""
        if team is not None:
            names = []
            for gap in team.get("gaps") or []:
                source = gap.split(":")[0].strip().lower()
                name = SOURCE_NAMES.get(source, source.capitalize())
                if name not in names:
                    names.append(name)
            if (team.get("prs") or {}).get("truncated"):
                names.append("GitHub search capped, PR counts may be low")
            notes = ("\n" + self.fill("footer_gaps", gaps=esc(", ".join(names))) if names
                     else "\n" + self.fill("footer_no_gaps"))
        return self.fill("footer", status=status, collected=clock(facts.get("collected_at")),
                         range=range_text, notes=notes)


def check(report: dict, facts: dict) -> None:
    for key in ("from", "preview"):
        text_field(report, key, "report")
    for key in ("decisions", "done", "next"):
        if not isinstance(report.get(key), list):
            raise ReportError(f"report: missing '{key}' list")
    for key in ("week", "manager", "collected_at"):
        text_field(facts, key, "facts")
    if not isinstance(facts.get("window"), list) or len(facts["window"]) != 2:
        raise ReportError("facts: missing 'window'")
    for i, item in enumerate(report["next"]):
        if not isinstance(item, str) or not item.strip():
            raise ReportError(f"next[{i}]: must be a non-blank string")
    blocked = report.get("blocked")
    if blocked is not None and not (isinstance(blocked, list) and all(isinstance(b, dict) for b in blocked)):
        raise ReportError("blocked: must be a list of objects")
    limits = (("decisions", len(report["decisions"]), MAX_DECISIONS),
              ("done", sum(len(g.get("items") or []) for g in report["done"]), MAX_DONE),
              ("next", len(report["next"]), MAX_NEXT))
    for key, size, limit in limits:
        if size > limit:
            raise ReportError(f"{key}: at most {limit} items, got {size}")


def render(report: dict, facts: dict, template: str = "light") -> str:
    check(report, facts)
    email = Email(load_blocks(template))
    first, last = (dt.date.fromisoformat(d) for d in facts["window"])
    range_text = esc(week_range(first, last))
    cards, codes = [], []
    for n, item in enumerate(report["decisions"], start=1):
        card, code = email.decision(n, item)
        cards.append(card)
        codes.append(code)
    done_count = sum(len(g.get("items") or []) for g in report["done"])
    blocked = report.get("blocked") or []

    intro = (email.fill("decisions_codes", codes=esc(" ".join(codes))) if codes
             else email.fill("decisions_none"))
    sections = [
        email.fill("header", week_short=esc(facts["week"].split("-")[-1]), range=range_text, year=last.year,
                   from_name=esc(report["from"]), manager=esc(facts["manager"]),
                   n_decisions=len(cards), n_done=done_count, n_blocked=len(blocked)),
        email.fill("decisions_head", intro=intro), *cards,
        email.done(report["done"]),
    ]
    if report["next"]:
        sections.append(email.fill("next", rows="\n".join(
            email.fill("next_item", text=esc(t)) for t in report["next"])))
    if blocked:
        sections.append(email.blocked(blocked))
    team = facts.get("team")
    if team is not None:
        sections.append(email.team(report, team, [first, last]))
    sections.append(email.footer(facts, team, range_text))
    out = email.fill("frame", style=email.block("dark_style"), preview=esc(report["preview"]),
                     content="\n".join(sections))
    # Plain ASCII survives any Outlook read of the file.
    return out.encode("ascii", "xmlcharrefreplace").decode("ascii")


def open_draft(path: Path, subject: str) -> None:
    result = subprocess.run(["osascript", "-", str(path), subject], input=DRAFT_SCRIPT,
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"osascript exited {result.returncode}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--facts", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--template", default="light")
    ap.add_argument("--draft", action="store_true", help="also create and open an Outlook draft")
    args = ap.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        facts = json.loads(args.facts.read_text(encoding="utf-8"))
        if not isinstance(report, dict) or not isinstance(facts, dict):
            raise ReportError("report and facts must be JSON objects")
        out = render(report, facts, args.template)
    except (ReportError, OSError, ValueError, AttributeError, TypeError) as exc:
        print(f"render_email: {exc}", file=sys.stderr)
        return 2
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out, encoding="utf-8")
    except OSError as exc:
        print(f"render_email: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    if args.draft:
        try:
            open_draft(args.out, f"{facts['week'].split('-')[-1]} status")
        except (RuntimeError, OSError) as exc:
            print(f"render_email: Outlook draft failed: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
