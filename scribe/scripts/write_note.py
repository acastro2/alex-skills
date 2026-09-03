#!/usr/bin/env python3
"""Turn a normalized scribe transcript (scribe.transcript/1) into a cleaned Obsidian note.

Usage:
    python3 write_note.py <transcript.json> --vault <vault_root> \\
        [--summary-file summary.md] [--description "text"] [--title "text"] \\
        [--glossary <vault>/Scribe/Glossary.md] \\
        [--attendees "A,B"] [--tags a,b] [--force] [--dry-run]

Cleaning (deterministic, see scribe_common.clean_turns): glossary replacement,
filler-word removal, duplicate-word collapse, whitespace collapse, then
consecutive same-speaker turns are re-merged and empty turns dropped.

Note path: <vault>/Scribe/Meetings/Transcripts/<YYYY-MM-DD HHMM> <title>.md,
where HHMM is the local time (America/Chicago) of the transcript start.

On success prints only the written path to stdout; stats go to stderr.
--dry-run prints the note body to stdout and writes nothing.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import scribe_common as common


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _strip_line_markers(line: str) -> str:
    text = line.strip()
    if text.startswith("- ") or text.startswith("* "):
        text = text[2:].strip()
    return text.strip("*").strip()


def _description(summary_text: str | None, source: str) -> str:
    """First non-empty, non-heading line of the summary, with list/bold markers
    stripped. The model writes its own `## Summary` etc. headings, so those must
    be skipped to reach the actual sentence."""
    if summary_text:
        for raw_line in summary_text.splitlines():
            if not raw_line.strip() or raw_line.strip().startswith("#"):
                continue
            candidate = _strip_line_markers(raw_line)
            if candidate:
                return candidate
    return f"Meeting transcript ({source})"


def build_frontmatter(
    transcript: dict,
    title: str,
    description: str,
    attendees: list[str],
    tags: list[str],
    glossary_replacements: int,
) -> str:
    lines = ["---"]
    lines.append("type: transcript")
    lines.append(f"title: {common.yaml_dquote(title)}")
    lines.append(f"description: {common.yaml_dquote(description)}")
    lines.append(f"date: {transcript['start']}")

    end = transcript.get("end")
    if end:
        lines.append(f"end: {end}")
        start_dt = _parse_iso(transcript["start"])
        end_dt = _parse_iso(end)
        duration_min = round((end_dt - start_dt).total_seconds() / 60)
        lines.append(f"duration_min: {duration_min}")

    lines.append(f"source: {transcript['source']}")
    lines.append(f"speakers: {common.yaml_flow_list(transcript.get('speakers', []))}")
    if attendees:
        lines.append(f"attendees: {common.yaml_flow_list(attendees)}")

    all_tags = ["scribe", "meeting", f"source/{transcript['source']}"] + tags
    lines.append(f"tags: {common.yaml_flow_list(all_tags)}")

    lines.append("confidential: true")

    provenance = transcript.get("provenance") or {}
    if provenance:
        lines.append("provenance:")
        for key, value in provenance.items():
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif isinstance(value, (int, float)):
                rendered = str(value)
            else:
                rendered = common.yaml_dquote(str(value))
            lines.append(f"  {key}: {rendered}")
    else:
        lines.append("provenance: {}")

    lines.append("cleaned: true")
    lines.append(f"glossary_replacements: {glossary_replacements}")
    lines.append(f"scribe_schema: {transcript['schema']}")
    lines.append("---")
    return "\n".join(lines)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_body(title: str, summary_text: str | None, turns: list[dict]) -> str:
    parts = [f"# {title}"]
    if summary_text is not None:
        parts.append(summary_text.rstrip())
    transcript_lines = ["## Transcript"]
    for turn in turns:
        timestamp = common.format_seconds_as_hms(turn["start"])
        if turn["speaker"] is None:
            transcript_lines.append(f"**[{timestamp}]** {turn['text']}")
        else:
            transcript_lines.append(f"**[{timestamp}] {turn['speaker']}:** {turn['text']}")
    parts.append("\n\n".join(transcript_lines))
    return "\n\n".join(parts)


def build_note(
    transcript: dict,
    glossary: list[tuple[str, str]],
    summary_file: str | None,
    attendees: list[str],
    tags: list[str],
    description_override: str | None = None,
    title_override: str | None = None,
) -> tuple[str, list[dict], int]:
    """Returns (note content, cleaned turns, glossary replacement count)."""
    cleaned_turns, glossary_replacements = common.clean_turns(transcript["turns"], glossary)

    raw_title = title_override or transcript.get("title")
    title = raw_title if raw_title else common.UNTITLED

    summary_text = None
    if summary_file:
        summary_text = Path(summary_file).read_text(encoding="utf-8")

    description = description_override or _description(summary_text, transcript["source"])

    frontmatter = build_frontmatter(transcript, title, description, attendees, tags, glossary_replacements)
    body = build_body(title, summary_text, cleaned_turns)
    note = frontmatter + "\n\n" + body + "\n"
    return note, cleaned_turns, glossary_replacements


def note_path_for(vault: str, transcript: dict, title_override: str | None = None) -> Path:
    date_str, hhmm = common.local_date_and_hhmm(transcript["start"])
    sanitized_title = common.sanitize_title_for_filename(title_override or transcript.get("title"))
    filename = f"{date_str} {hhmm} {sanitized_title}.md"
    return Path(vault) / "Scribe" / "Meetings" / "Transcripts" / filename


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript_json", help="Path to a scribe.transcript/1 JSON file")
    parser.add_argument("--vault", required=True, help="Obsidian vault root")
    parser.add_argument("--summary-file", default=None, help="Markdown file with the model's summary")
    parser.add_argument(
        "--description",
        default=None,
        help="Override the frontmatter description; wins over the summary-derived one",
    )
    parser.add_argument("--title", default=None, help="Override the transcript title (note heading and filename)")
    parser.add_argument("--glossary", default=None, help="Markdown glossary file (- wrong => Right per line)")
    parser.add_argument("--attendees", default=None, help="Comma-separated attendee names")
    parser.add_argument("--tags", default=None, help="Comma-separated extra tags")
    parser.add_argument("--force", action="store_true", help="Overwrite the note if it already exists")
    parser.add_argument("--dry-run", action="store_true", help="Print the note to stdout; write nothing")
    args = parser.parse_args()

    transcript = common.load_transcript(args.transcript_json)
    glossary = common.load_glossary(args.glossary)
    attendees = _split_csv(args.attendees)
    tags = _split_csv(args.tags)

    note, cleaned_turns, glossary_replacements = build_note(
        transcript, glossary, args.summary_file, attendees, tags, args.description, args.title
    )
    note_path = note_path_for(args.vault, transcript, args.title)

    if args.dry_run:
        sys.stdout.write(note)
        return

    if note_path.exists() and not args.force:
        sys.exit(f"Note already exists: {note_path} (pass --force to overwrite)")

    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(note, encoding="utf-8")

    print(str(note_path))
    print(
        f"turns={len(cleaned_turns)} speakers={len(transcript.get('speakers', []))} "
        f"glossary_replacements={glossary_replacements}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
