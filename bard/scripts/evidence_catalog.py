#!/usr/bin/env python3
"""Build and check the Evidence catalog.

One JSON object per Markdown document in Evidence/, plus a rendered CATALOG.md.
The catalog is the machine index agents read first. It carries the fields the old
Markdown-only table could not: original path, source mirror, canonical copy, dates.

Run:
    python3 scripts/evidence_catalog.py build --vault /path/to/vault
    python3 scripts/evidence_catalog.py check --vault /path/to/vault
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
TOP_LEVEL_INDEX = {"README.md", "AGENTS.md", "CATALOG.md"}

TYPE_HEADINGS = [
    ("adr", "Decisions (ADR)"),
    ("rfc", "Proposals (RFC)"),
    ("sad", "Solution architecture (SAD)"),
    ("sow", "Statements of work (SOW)"),
    ("standard", "Standards"),
    ("runbook", "Runbooks"),
    ("plan", "Plans and proposals"),
    ("brief", "Technical briefs"),
    ("report", "Reports"),
    ("deck", "Decks and newsletters"),
    ("template", "Templates"),
    ("note", "Notes"),
    ("digest", "Developer digests"),
]

FOLDER_DOC_TYPE = {
    "ADRs": "adr",
    "RFCs": "rfc",
    "SADs": "sad",
    "SOWs": "sow",
    "Standards": "standard",
    "Runbooks": "runbook",
    "Plans-Proposals": "plan",
    "Tech-Briefs": "brief",
    "Reports": "report",
    "Decks": "deck",
    "Templates": "template",
    "Notes": "note",
    "Confidential": "note",
}

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        quote = value[0]
        inner = value[1:-1]
        if quote == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        parts: list[str] = []
        current: list[str] = []
        quote: str | None = None
        escaped = False
        for char in inner:
            if escaped:
                current.append(char)
                escaped = False
                continue
            if char == "\\":
                escaped = True
                current.append(char)
                continue
            if quote:
                current.append(char)
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
                current.append(char)
            elif char == ",":
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        parts.append("".join(current).strip())
        return [parse_scalar(part) for part in parts if part]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in ("null", "none", "~"):
        return None
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, bool]:
    """Parse the simple YAML subset used by the vault. No PyYAML dependency."""
    if not text.startswith("---"):
        return {}, text, False
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if not match:
        return {}, text, False
    block = match.group(1)
    body = text[match.end():]
    data: dict[str, Any] = {}
    lines = block.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line.startswith((" ", "\t")):
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if raw == "":
            items: list[Any] = []
            next_index = index + 1
            while next_index < len(lines):
                candidate = lines[next_index]
                stripped = candidate.lstrip()
                if not stripped.startswith("- "):
                    break
                items.append(parse_scalar(stripped[2:].strip()))
                next_index += 1
            if items:
                data[key] = items
                index = next_index
                continue
        data[key] = parse_scalar(raw)
        index += 1
    return data, body, True


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def clean_markdown(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_paragraph(body: str) -> str:
    in_code = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped:
            continue
        if stripped.startswith("<"):
            cleaned = clean_markdown(stripped)
            if len(cleaned) >= 40:
                return cleaned
            continue
        if stripped.startswith("#") or stripped.startswith("|") or stripped.startswith(">"):
            continue
        if stripped.upper() == stripped and sum(char.isalpha() for char in stripped) > 3 and len(stripped) < 90:
            continue
        if stripped.startswith(("- ", "* ", "1. ")):
            continue
        if stripped.startswith("---"):
            continue
        if len(stripped) < 40:
            continue
        return clean_markdown(stripped)
    return ""


def month_number(name: str) -> int | None:
    return MONTHS.get(name.lower().rstrip("."))


def parse_date_text(text: str) -> tuple[str | None, str]:
    match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}", "day"
    match = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(20\d{2})", text)
    if match:
        month = month_number(match.group(1))
        if month:
            return f"{match.group(3)}-{month:02d}-{int(match.group(2)):02d}", "day"
    match = re.search(r"(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(20\d{2})", text)
    if match:
        month = month_number(match.group(2))
        if month:
            return f"{match.group(3)}-{month:02d}-{int(match.group(1)):02d}", "day"
    match = re.search(r"([A-Za-z]{3,9})\.?\s+(20\d{2})", text)
    if match:
        month = month_number(match.group(1))
        if month:
            return f"{match.group(2)}-{month:02d}", "month"
    match = re.search(r"(20\d{2})-(\d{2})\b", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}", "month"
    match = re.search(r"(20\d{2})", text)
    if match:
        return match.group(1), "year"
    return None, "unknown"


METADATA_KEYS = [
    "date of review", "date proposed", "last updated", "sandbox-built",
    "created", "dated", "published", "revision", "status", "built", "as of", "date",
]


def metadata_date(line: str) -> tuple[str | None, str]:
    """Read a date only from a metadata cell or a short metadata line."""
    stripped = line.strip()
    if stripped.startswith("|") and stripped.endswith("|"):
        cells = [cell.strip().strip("*").strip() for cell in stripped.strip("|").split("|")]
        for index, cell in enumerate(cells[:-1]):
            key = cell.lower().rstrip(":").strip()
            if key in METADATA_KEYS:
                parsed, precision = parse_date_text(cells[index + 1])
                if parsed:
                    return parsed, precision
    if len(stripped) <= 220:
        for key in METADATA_KEYS:
            pattern = re.compile(
                r"(?:^|\*\*|\|)\s*" + re.escape(key) + r"\b\s*\*{0,2}\s*:?\s*\*{0,2}",
                re.I,
            )
            match = pattern.search(stripped)
            if not match:
                continue
            rest = stripped[match.end():]
            if len(rest) > 160:
                continue
            parsed, precision = parse_date_text(rest)
            if parsed:
                return parsed, precision
    return None, "unknown"


def extract_date(fm: dict[str, Any], filename: str, body: str) -> tuple[str | None, str, str]:
    """Return (date, precision, source). Never invents a day."""
    for key in ("date", "created", "timestamp"):
        value = fm.get(key)
        if not value:
            continue
        text = str(value)
        parsed, precision = parse_date_text(text)
        if parsed:
            return parsed, precision, "frontmatter"

    match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}", "day", "filename"

    for line in body.splitlines()[:300]:
        parsed, precision = metadata_date(line)
        if parsed:
            return parsed, precision, "body"
    return None, "unknown", "none"


def normalise_doc_type(path: Path, fm: dict[str, Any]) -> tuple[str, bool]:
    explicit = fm.get("doc_type")
    if explicit:
        return str(explicit).strip().lower(), True
    kind = str(fm.get("type") or "").strip().lower()
    if kind == "developer-digest" or path.name == "_digest.md":
        return "digest", True
    if kind == "evidence-twin":
        return str(fm.get("doc_type") or "note").strip().lower(), False
    folder = path.parts[0] if path.parts else ""
    if folder in FOLDER_DOC_TYPE:
        return FOLDER_DOC_TYPE[folder], False
    return "note", False


def source_mirror_for(path: Path) -> str | None:
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "Sources":
        if parts[1] in ("Architecture", "Architecture-Private", "Developer"):
            return parts[1]
    return None


def load_old_flags(catalog_path: Path) -> dict[str, dict[str, bool]]:
    flags: dict[str, dict[str, bool]] = {}
    if not catalog_path.exists():
        return flags
    for line in catalog_path.read_text(errors="ignore").splitlines():
        match = re.match(r"^\|\s*\[[^\]]*\]\(([^)]+)\)\s*\|", line)
        if not match:
            continue
        cells = line.strip().strip("|").split("|")
        flag_cell = cells[-1].strip() if cells else ""
        path = urllib.parse.unquote(match.group(1))
        flags[path] = {
            "jev_unsure": "\u2754" in flag_cell,
            "empty_text": "\u2205" in flag_cell,
            "source_mirror": "\U0001f4e6" in flag_cell,
        }
    return flags


def eligible_files(evidence: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(evidence.rglob("*.md")):
        rel = path.relative_to(evidence)
        if "_originals" in rel.parts:
            continue
        if any(part.endswith(".assets") for part in rel.parts):
            continue
        if rel.as_posix() in TOP_LEVEL_INDEX:
            continue
        if rel.as_posix() in (
            "Sources/Architecture/README.md",
            "Sources/Architecture-Private/README.md",
            "Sources/Developer/README.md",
        ):
            continue
        if path.name.startswith("."):
            continue
        files.append(path)
    return files


def build_row(evidence: Path, path: Path, old_flags: dict[str, dict[str, bool]]) -> dict[str, Any]:
    rel = path.relative_to(evidence)
    rel_posix = rel.as_posix()
    text = path.read_text(errors="ignore")
    fm, body, _ = parse_frontmatter(text)

    doc_type, explicit_type = normalise_doc_type(rel, fm)
    title = str(fm.get("title") or first_heading(body) or path.stem).strip()
    topic = fm.get("topic")
    topic = str(topic).strip() if topic else None
    sensitivity = str(fm.get("sensitivity") or "").strip().lower() or None
    if not sensitivity:
        if rel.parts and rel.parts[0] == "Confidential" or fm.get("confidential") is True:
            sensitivity = "confidential"
        else:
            sensitivity = "internal"

    date, precision, date_source = extract_date(fm, path.stem, body)
    if fm.get("date_source"):
        date_source = str(fm["date_source"]).strip()
    if fm.get("date_precision"):
        precision = str(fm["date_precision"]).strip()

    summary = ""
    if sensitivity != "confidential":
        if fm.get("description"):
            summary = clean_markdown(str(fm["description"]))
        else:
            summary = first_paragraph(body)
    if not summary:
        summary = clean_markdown(str(fm.get("description") or "")) or title
    summary = summary[:300].rstrip()

    original = fm.get("original")
    if not original:
        source = fm.get("source")
        if source and (str(source).startswith("/") or str(source).startswith("http")):
            original = source
    original = str(original).strip() if original else None
    original_status = "recorded" if original else "not_recorded"
    source_status = "not_applicable"
    if original and str(original).startswith("/"):
        source_status = "ok" if os.path.exists(str(original)) else "missing"

    related = fm.get("related") or []
    if isinstance(related, str):
        related = [related]
    related = [str(item).strip() for item in related if str(item).strip()]

    old = old_flags.get(rel_posix, {})
    return {
        "schema": SCHEMA_VERSION,
        "path": rel_posix,
        "title": title,
        "doc_type": doc_type,
        "topic": topic,
        "sensitivity": sensitivity,
        "date": date,
        "date_precision": precision,
        "date_source": date_source,
        "summary": summary,
        "canonical": True,
        "duplicate_of": None,
        "source_mirror": source_mirror_for(rel),
        "original": original,
        "original_status": original_status,
        "source_status": source_status,
        "twin_of": (str(fm.get("twin_of")).strip() if fm.get("twin_of") else None),
        "format": (str(fm.get("format")).strip() if fm.get("format") else None),
        "jev_unsure": bool(old.get("jev_unsure", False)),
        "empty_text": bool(old.get("empty_text", False)),
        "needs_tag": not (explicit_type and topic),
        "related": related,
    }


def apply_canonical(rows: list[dict[str, Any]]) -> None:
    curated: dict[str, str] = {}
    for row in rows:
        if not row["path"].startswith("Sources/"):
            curated.setdefault(Path(row["path"]).stem.lower(), row["path"])
    for row in rows:
        if row["path"].startswith("Sources/"):
            stem = Path(row["path"]).stem.lower()
            if stem in curated:
                row["canonical"] = False
                row["duplicate_of"] = curated[stem]


def collect_rows(vault: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evidence = vault / "Evidence"
    old_flags = load_old_flags(evidence / "CATALOG.md")
    files = eligible_files(evidence)
    rows = [build_row(evidence, path, old_flags) for path in files]
    apply_canonical(rows)
    rows.sort(key=lambda row: row["path"])
    excluded_originals = sum(
        1 for path in evidence.rglob("*.md") if "_originals" in path.relative_to(evidence).parts
    )
    meta = {
        "schema": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "vault": str(vault),
        "row_count": len(rows),
        "eligible_files": len(files),
        "excluded_originals": excluded_originals,
        "generator": "evidence_catalog.py",
    }
    return rows, meta


def render_catalog(rows: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["doc_type"], []).append(row)

    lines = [
        "---",
        "type: index",
        'title: "Evidence catalog"',
        'description: One row per document in Evidence: path, type, topic, sensitivity, date and summary. Generated; do not edit by hand.',
        "---",
        "",
        "# Evidence catalog",
        "",
        f"{len(rows)} documents. Generated from note frontmatter by `~/.agents/skills/bard/scripts/evidence_catalog.py`.",
        "Machine-readable copy: `catalog.jsonl` (same rows, one JSON object per line).",
        "",
        "Flags: \U0001f512 confidential \u00b7 \U0001f4e6 from a raw mirror under `Sources/` \u00b7 \u2754 Jev was unsure, tag is a best guess \u00b7 \u2205 no extractable text (image-only original) \u00b7 \u2605 canonical copy \u00b7 \u21b3 duplicate of a curated copy",
        "",
    ]
    for doc_type, heading in TYPE_HEADINGS:
        subset = grouped.get(doc_type)
        if not subset:
            continue
        lines.extend([f"## {heading} \u2014 {len(subset)}", "", "| Path | Topic | Date | Summary | Flags |", "|---|---|---|---|---|"])
        for row in subset:
            flags = []
            if row["sensitivity"] == "confidential":
                flags.append("\U0001f512")
            if row["source_mirror"]:
                flags.append("\U0001f4e6")
            if row["jev_unsure"]:
                flags.append("\u2754")
            if row["empty_text"]:
                flags.append("\u2205")
            if row["canonical"]:
                flags.append("\u2605")
            else:
                flags.append("\u21b3")
            label = str(row["title"]).replace("|", "\\|")
            summary = str(row["summary"]).replace("|", "\\|")
            topic = (row["topic"] or "").replace("|", "\\|")
            link = urllib.parse.quote(row["path"], safe="/")
            lines.append(
                f"| [{label}]({link}) | {topic} | {row['date'] or ''} | {summary} | {' '.join(flags)} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_atomic(path: Path, text: str) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text)
    os.replace(temp, path)


def build(vault: Path) -> int:
    evidence = vault / "Evidence"
    if not evidence.is_dir():
        print(f"error: no Evidence folder at {evidence}", file=sys.stderr)
        return 2
    rows, meta = collect_rows(vault)
    jsonl = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n"
    write_atomic(evidence / "catalog.jsonl", jsonl)
    write_atomic(evidence / "catalog.meta.json", json.dumps(meta, indent=2, sort_keys=True) + "\n")
    write_atomic(evidence / "CATALOG.md", render_catalog(rows))
    print(f"built {meta['row_count']} rows; excluded {meta['excluded_originals']} originals")
    return 0


def check(vault: Path) -> int:
    evidence = vault / "Evidence"
    jsonl_path = evidence / "catalog.jsonl"
    if not jsonl_path.exists():
        print("error: catalog.jsonl missing", file=sys.stderr)
        return 2
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for number, line in enumerate(jsonl_path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: {exc}")
    paths = [row.get("path") for row in rows]
    duplicates = sorted({path for path in paths if paths.count(path) > 1})
    if duplicates:
        errors.append(f"duplicate paths: {duplicates[:5]}")
    for row in rows:
        path = row.get("path")
        if not path or not (evidence / path).exists():
            errors.append(f"missing file: {path}")
        if row.get("source_mirror") and row["path"].startswith("Sources/"):
            pass
        if row.get("canonical") is False and not row.get("duplicate_of"):
            errors.append(f"non-canonical without duplicate_of: {path}")
    canonical = {row["path"] for row in rows if row.get("canonical")}
    for row in rows:
        target = row.get("duplicate_of")
        if target and target not in canonical:
            errors.append(f"duplicate_of target not canonical: {target}")
    if errors:
        for error in errors[:20]:
            print(f"error: {error}", file=sys.stderr)
        print(f"{len(errors)} errors", file=sys.stderr)
        return 1
    print(f"check OK: {len(rows)} rows")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or check the Evidence catalog.")
    parser.add_argument("command", choices=("build", "check"))
    parser.add_argument("--vault", required=True, type=Path)
    args = parser.parse_args(argv)
    return build(args.vault) if args.command == "build" else check(args.vault)


if __name__ == "__main__":
    raise SystemExit(main())
