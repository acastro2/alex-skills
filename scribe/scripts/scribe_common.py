"""Shared helpers for the scribe skill: schema I/O, text cleaning, and slugging.

Used by both source normalizers (teams_transcript.py, and later a hidock
normalizer) and by write_note.py, so the normalized-transcript contract and
the cleaning rules live in exactly one place.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCHEMA_VERSION = "scribe.transcript/1"

_FILLER_PATTERN = re.compile(r"\b(?:um|uh|uhm|hmm|erm)\b", re.IGNORECASE)
_DUPLICATE_WORD_PATTERN = re.compile(r"\b(\w+)(?:\s+\1\b)+", re.IGNORECASE)
_WHITESPACE_PATTERN = re.compile(r"\s+")
_FILENAME_FORBIDDEN_PATTERN = re.compile(r'[\/\\:\*\?"<>\|]')

UNTITLED = "Untitled meeting"


# --- normalized transcript I/O -------------------------------------------------

def load_transcript(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dump_transcript(transcript: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(transcript, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# --- turn merging ----------------------------------------------------------

def merge_consecutive_turns(turns: list[dict]) -> list[dict]:
    """Merge consecutive turns from the same speaker into one, keeping the
    earliest start. Teams (and cleaning) both produce runs of same-speaker
    fragments that read as noise unless merged. A None speaker (unlabelled
    source, e.g. HiDock) never merges with anything, even another None turn —
    there is no evidence two unlabelled turns share a speaker."""
    merged: list[dict] = []
    for turn in turns:
        same_speaker = (
            merged
            and merged[-1]["speaker"] is not None
            and merged[-1]["speaker"] == turn["speaker"]
        )
        if same_speaker:
            merged[-1]["text"] = (merged[-1]["text"] + " " + turn["text"]).strip()
        else:
            merged.append({"start": turn["start"], "speaker": turn["speaker"], "text": turn["text"]})
    return merged


# --- glossary -----------------------------------------------------------------

def load_glossary(path: str | Path | None) -> list[tuple[str, str]]:
    """Parse `- wrong => Right` lines. Missing file or no path = no glossary."""
    if path is None:
        return []
    file_path = Path(path)
    if not file_path.exists():
        return []
    pairs: list[tuple[str, str]] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*-\s*(.+?)\s*=>\s*(.+?)\s*$", line)
        if m:
            pairs.append((m.group(1), m.group(2)))
    return pairs


def apply_glossary(text: str, glossary: list[tuple[str, str]]) -> tuple[str, int]:
    """Case-insensitive, word-boundary replacement. Returns (text, replacement count)."""
    count = 0
    for wrong, right in glossary:
        pattern = re.compile(r"\b" + re.escape(wrong) + r"\b", re.IGNORECASE)
        text, n = pattern.subn(right, text)
        count += n
    return text, count


# --- cleaning -------------------------------------------------------------

def drop_fillers(text: str) -> str:
    return _FILLER_PATTERN.sub("", text)


def collapse_duplicate_words(text: str) -> str:
    return _DUPLICATE_WORD_PATTERN.sub(r"\1", text)


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", text).strip()


def clean_text(text: str, glossary: list[tuple[str, str]]) -> tuple[str, int]:
    text, count = apply_glossary(text, glossary)
    text = drop_fillers(text)
    text = collapse_duplicate_words(text)
    text = collapse_whitespace(text)
    return text, count


def clean_turns(turns: list[dict], glossary: list[tuple[str, str]]) -> tuple[list[dict], int]:
    """Clean each turn's text, drop turns whose text became empty, then
    re-merge consecutive same-speaker turns. Dropping empty turns first means a
    filler-only turn between two same-speaker turns no longer keeps them apart.
    Returns (cleaned turns, total glossary replacements applied)."""
    non_empty = []
    total = 0
    for turn in turns:
        text, count = clean_text(turn["text"], glossary)
        total += count
        if text:
            non_empty.append({"start": turn["start"], "speaker": turn["speaker"], "text": text})
    merged = merge_consecutive_turns(non_empty)
    return merged, total


# --- filenames and timestamps ----------------------------------------------

def sanitize_title_for_filename(title: str | None) -> str:
    if not title:
        return UNTITLED
    cleaned = _FILENAME_FORBIDDEN_PATTERN.sub("", title)
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()
    if not cleaned:
        return UNTITLED
    return cleaned[:80].strip()


def format_seconds_as_hms(seconds: float) -> str:
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def local_date_and_hhmm(start_iso_utc: str, tz_name: str = "America/Chicago") -> tuple[str, str]:
    """Convert an ISO 8601 UTC timestamp to (YYYY-MM-DD, HHMM) in tz_name."""
    dt_utc = datetime.fromisoformat(start_iso_utc.replace("Z", "+00:00"))
    dt_local = dt_utc.astimezone(ZoneInfo(tz_name))
    return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%H%M")


# --- YAML (hand-written; stdlib only) --------------------------------------

def yaml_dquote(value: str) -> str:
    """Double-quote a scalar, escaping backslashes and double quotes."""
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_flow_list(items: list[str]) -> str:
    """A YAML flow-style list of double-quoted string scalars, e.g. ["A", "B"]."""
    return "[" + ", ".join(yaml_dquote(item) for item in items) + "]"
