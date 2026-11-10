#!/usr/bin/env python3
"""Propose and apply cross-links between Evidence and Bard.

Hard links are only written when a key matches exactly: title, session ID,
GitHub pull-request URL, or an existing Scribe transcript path. Soft candidates
are reported, never applied automatically. Topic-hub links are deterministic and
can be applied with --hub-links.

Run:
    python3 scripts/evidence_links.py propose --vault /path/to/vault > links.csv
    python3 scripts/evidence_links.py apply --vault /path/to/vault --hub-links
    python3 scripts/evidence_links.py verify --vault /path/to/vault
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

TOPIC_HUB = {
    "Security & Identity": "Security & Identity",
    "Snowflake & Data": "Snowflake & Data",
    "Terraform & AWS IaC": "Terraform & AWS IaC",
    "Observability & Grafana": "Observability & Grafana",
    "Data Pipelines": "Data Pipelines",
    "AWS Ops": "AWS Ops",
    "Product Incident Debugging": "Product Incident Debugging",
    "Delivery & Docs": "Delivery & Docs",
    "Hiring & People": "Hiring & People",
    "Tooling, MCP & Skills": "Tooling, MCP & Skills",
    "AI & Agents": "Tooling, MCP & Skills",
}


def load_rows(evidence: Path) -> list[dict]:
    path = evidence / "catalog.jsonl"
    if not path.exists():
        raise SystemExit("catalog.jsonl missing; run evidence_catalog.py build first")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_bard(vault: Path) -> dict:
    notes = {}
    for path in (vault / "Bard").glob("*.md"):
        text = path.read_text(errors="ignore")
        fm, _, _ = evidence_catalog.parse_frontmatter(text)
        notes[path.stem] = {
            "title": str(fm.get("title") or path.stem),
            "description": str(fm.get("description") or ""),
            "source": str(fm.get("source") or ""),
            "resource": str(fm.get("resource") or ""),
            "repo": str(fm.get("repo") or ""),
        }
    return notes


def tokens(text: str) -> set[str]:
    stop = {
        "that", "this", "with", "from", "have", "were", "when", "then", "than",
        "which", "while", "after", "before", "into", "over", "under", "between",
        "about", "other", "their", "there", "these", "those", "using", "used",
        "make", "made", "does", "doesn", "also", "more", "most", "only", "just",
        "like", "need", "needs", "must", "should", "would", "could", "will",
    }
    return set(re.findall(r"[a-z0-9]{4,}", text.lower())) - stop


def hard_links(row: dict, text: str, bard: dict) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    by_title = {value["title"].lower(): name for name, value in bard.items()}
    title = row["title"].lower()
    if title in by_title:
        found.append(("hard_title", by_title[title], "exact title"))
    sources = {value["source"] for value in bard.values() if value["source"]}
    for session in set(re.findall(r"ses_[A-Za-z0-9]+", text)):
        if session in sources:
            note = next(name for name, value in bard.items() if value["source"] == session)
            found.append(("hard_session", note, session))
    pr_to_note = {
        value["resource"]: name
        for name, value in bard.items()
        if "github.com" in value["resource"] and "/pull/" in value["resource"]
    }
    for url in set(re.findall(r"https://github\.com/[^\s\]\)]+/pull/\d+", text)):
        if url in pr_to_note:
            found.append(("hard_pr", pr_to_note[url], url))
    return found


def soft_links(row: dict, bard: dict, limit: int = 3) -> list[tuple[float, str]]:
    evidence_tokens = tokens(row["title"] + " " + row["summary"])
    scored = []
    for name, value in bard.items():
        score = len(evidence_tokens & tokens(
            value["title"] + " " + value["description"] + " " + value["repo"]
        )) / max(1, len(evidence_tokens | tokens(
            value["title"] + " " + value["description"] + " " + value["repo"]
        )))
        if score >= 0.10:
            scored.append((score, name))
    scored.sort(reverse=True)
    return scored[:limit]


def hub_link(row: dict) -> str | None:
    hub = TOPIC_HUB.get(row.get("topic") or "")
    return f"Bard/{hub}" if hub else None


def propose(vault: Path) -> int:
    evidence = vault / "Evidence"
    rows = [row for row in load_rows(evidence) if not row["path"].startswith("Sources/")]
    bard = load_bard(vault)
    writer = csv.writer(sys.stdout)
    writer.writerow(["evidence_path", "kind", "target", "score", "reason"])
    for row in rows:
        text = (evidence / row["path"]).read_text(errors="ignore")
        for kind, target, reason in hard_links(row, text, bard):
            writer.writerow([row["path"], kind, target, "1.00", reason])
        for score, target in soft_links(row, bard):
            writer.writerow([row["path"], "soft", target, f"{score:.2f}", "token overlap"])
        hub = hub_link(row)
        if hub:
            writer.writerow([row["path"], "hub", hub, "1.00", f"topic: {row['topic']}"])
    return 0


def set_related(text: str, links: list[str]) -> tuple[str, bool]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if not match:
        return text, False
    fm, _, _ = evidence_catalog.parse_frontmatter(text)
    existing = fm.get("related") or []
    if isinstance(existing, str):
        existing = [existing]
    merged = []
    for link in list(existing) + links:
        value = str(link).strip()
        if value.startswith("[[") and value.endswith("]]"):
            value = value[2:-2].strip()
        if value and value not in merged:
            merged.append(value)
    if not merged:
        return text, False
    lines = match.group(1).splitlines()
    output: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("related:"):
            skipping = True
            continue
        if skipping and line.lstrip().startswith("- "):
            continue
        skipping = False
        output.append(line)
    output.append("related:")
    for link in merged:
        output.append(f'  - "[[{link}]]"')
    block = "\n".join(output)
    return f"---\n{block}\n---\n" + text[match.end():], True


def apply(vault: Path, hub_links: bool) -> int:
    evidence = vault / "Evidence"
    rows = [row for row in load_rows(evidence) if not row["path"].startswith("Sources/")]
    bard = load_bard(vault)
    changed = 0
    hard_count = 0
    hub_count = 0
    for row in rows:
        path = evidence / row["path"]
        text = path.read_text(errors="ignore")
        links: list[str] = []
        for _, target, _ in hard_links(row, text, bard):
            links.append(target)
            hard_count += 1
        if hub_links:
            hub = hub_link(row)
            if hub:
                links.append(hub)
                hub_count += 1
        if not links:
            continue
        new_text, ok = set_related(text, links)
        if ok and new_text != text:
            path.write_text(new_text)
            changed += 1
    print(f"links applied: {changed} files; hard {hard_count}; hub {hub_count}")
    return 0


def verify(vault: Path) -> int:
    evidence = vault / "Evidence"
    rows = load_rows(evidence)
    broken = []
    total = 0
    for row in rows:
        for link in row.get("related") or []:
            total += 1
            target = str(link).strip()
            if target.startswith("[[") and target.endswith("]]"):
                target = target[2:-2]
            target = target.split("|")[0].split("#")[0].strip()
            if not (vault / (target if target.lower().endswith(".md") else target + ".md")).exists():
                broken.append((row["path"], target))
    if broken:
        for path, target in broken[:20]:
            print(f"broken: {path} -> {target}", file=sys.stderr)
        print(f"{len(broken)} broken links", file=sys.stderr)
        return 1
    print(f"links OK: {total} links")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Propose, apply, or verify Evidence cross-links.")
    parser.add_argument("command", choices=("propose", "apply", "verify"))
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--hub-links", action="store_true", help="apply deterministic topic-hub links")
    args = parser.parse_args(argv)
    if args.command == "propose":
        return propose(args.vault)
    if args.command == "apply":
        return apply(args.vault, args.hub_links)
    return verify(args.vault)


if __name__ == "__main__":
    raise SystemExit(main())
