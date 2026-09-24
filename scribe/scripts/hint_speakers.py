#!/usr/bin/env python3
"""Apply a model's speaker-to-name reading to a normalized transcript.

Reading a transcript and deciding who spoke is a language judgement, so the model
does it and writes `<id>.speakers.json`:

    {"speaker 1": {"name": "Alexandre Castro",
                   "evidence": "\\"i'm alex i'm the enterprise architect\\" at 00:00:35"}}

This module does not guess. It is the gatekeeper and applier: it refuses a name that
is not on the attendee list, a label the transcript does not contain, an entry with no
quoted evidence, and any name claimed by two labels. Accepted names are hedged in the
label ("speaker 1 (likely Alexandre Castro)") and the quote is recorded in provenance.

Idempotent: re-running over an already-hinted transcript changes nothing.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys

import scribe_common as common

_HINT_SUFFIX = re.compile(r"\s*\(likely [^)]*\)\s*$")


def load_mapping(path: str) -> dict[str, dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _attendee_for(name: str, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate.lower() == name.strip().lower():
            return candidate
    return None


def validate(mapping: dict[str, dict], turns: list[dict], candidates: list[str]) -> tuple[dict, dict]:
    """Split the model's mapping into (accepted, refused). Every refusal carries the
    reason it was refused, so the run can say why a label stayed anonymous."""
    labels = {turn["speaker"] for turn in turns if turn.get("speaker") is not None}
    accepted: dict[str, dict] = {}
    refused: dict[str, str] = {}

    for label, entry in mapping.items():
        if label not in labels:
            refused[label] = "label not in transcript"
            continue
        attendee = _attendee_for(entry.get("name") or "", candidates)
        if attendee is None:
            refused[label] = f"name {entry.get('name')!r} is not an attendee"
            continue
        if not (entry.get("evidence") or "").strip():
            refused[label] = "no evidence quoted"
            continue
        accepted[label] = {"name": attendee, "evidence": entry["evidence"].strip()}

    seen: dict[str, str] = {}
    duplicates = set()
    for label, hint in accepted.items():
        key = hint["name"].lower()
        if key in seen:
            duplicates.add(seen[key])
            duplicates.add(label)
        seen[key] = label
    for label in duplicates:
        refused[label] = "name claimed by two labels"
        del accepted[label]
    return accepted, refused


def _base_label(label: str) -> str:
    return _HINT_SUFFIX.sub("", label).strip()


def apply_hints(transcript: dict, hints: dict[str, dict]) -> dict:
    """Write the hints onto the turn speakers and the speaker list, and record the
    evidence in provenance. Labels without a hint are left exactly as they are, so a
    run without a mapping never erases an earlier one."""
    updated = copy.deepcopy(transcript)
    for turn in updated["turns"]:
        base = _base_label(turn["speaker"]) if turn.get("speaker") else turn.get("speaker")
        if base in hints:
            turn["speaker"] = f"{base} (likely {hints[base]['name']})"
    updated["speakers"] = [
        f"{_base_label(label)} (likely {hints[_base_label(label)]['name']})"
        if _base_label(label) in hints
        else label
        for label in updated.get("speakers", [])
    ]
    provenance = updated.setdefault("provenance", {})
    provenance["speaker_hint_status"] = "ok" if hints else "none"
    if hints:
        provenance["speaker_hints"] = "; ".join(
            f"{label}={hint['name']}: {hint['evidence']}" for label, hint in sorted(hints.items())
        )
    return updated


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("transcript_json", help="Path to a scribe.transcript/1 JSON file (rewritten in place)")
    parser.add_argument("--attendees", default=None, help="Comma-separated meeting attendees")
    parser.add_argument("--name", action="append", default=[], help="Extra allowed name; repeatable")
    parser.add_argument("--from-file", default=None, help="The model's <id>.speakers.json mapping")
    args = parser.parse_args(argv)

    candidates = _split_csv(args.attendees) + args.name
    transcript = common.load_transcript(args.transcript_json)
    mapping = load_mapping(args.from_file) if args.from_file else {}
    accepted, refused = validate(mapping, transcript["turns"], candidates)
    updated = apply_hints(transcript, accepted)
    common.dump_transcript(updated, args.transcript_json)

    for label, hint in sorted(accepted.items()):
        print(f"named {label} -> {hint['name']}: {hint['evidence']}", file=sys.stderr)
    for label, reason in sorted(refused.items()):
        print(f"refused {label}: {reason}", file=sys.stderr)
    print(
        f"candidates={len(candidates)} named={len(accepted)} refused={len(refused)} "
        f"status={updated['provenance']['speaker_hint_status']}",
        file=sys.stderr,
    )
    print(str(args.transcript_json))
    return 0


if __name__ == "__main__":
    sys.exit(main())
