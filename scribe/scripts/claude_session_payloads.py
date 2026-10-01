#!/usr/bin/env python3
"""Recover Teams transcript payloads that Claude Code fetched, from its on-disk session artifacts.

This is the OpenCode half of scribe Source A. OpenCode has no Microsoft 365
connector, so the fetch is delegated to the `ask-claude` subagent. That subagent
cannot write files, so the payload it read is taken from the two places Claude
Code leaves it on this Mac:

  * `<session>.jsonl` — every tool result, as a JSON string inside the line, so
    the payload arrives double-encoded (parse once for the envelope, again for
    the payload);
  * `<session>/tool-results/*.txt` — the harness writes the raw payload here when
    the result is too large to return inline (~50 KB and up).

The user-facing record is the payload's `transcripts[0].content` (WEBVTT), so this
script writes both the payload JSON and the WEBVTT byte-for-byte, then optionally
normalizes each one through teams_transcript.py.

Pairing is exact, not guessed: the `meeting-transcript:///events/<token>` token is
base64url(joinWebUrl) with the padding stripped, so a payload is matched to the
occurrence by its own joinWebUrl, and the winning URI is the one whose ?start=&end=
window overlaps the calendar slot from the manifest.

Usage:
    python3 claude_session_payloads.py --manifest manifest.json [--normalize]

The manifest is what the parent agent writes from the subagent's reply — one row
per meeting you asked for. See references/teams-opencode.md.

    [{"subject": "DLP Open Questions", "event_id": "AAkALg...",
      "start": "2026-09-30T16:30:00Z", "end": "2026-09-30T17:00:00Z"}]
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

# Sibling modules, so the script can be run from any directory: the cwd decides
# which Claude Code project to read, not where this file happens to live.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scribe_common as common  # noqa: E402
import teams_transcript  # noqa: E402
import write_note  # noqa: E402

_URI_PATTERN = re.compile(
    r"meeting-transcript:///events/[A-Za-z0-9_\-%=]+"
    r"(?:\?start=[^\"\\\s&]+&end=[^\"\\\s&]+)?"
)
_TOKEN_PATTERN = re.compile(r"meeting-transcript:///events/([A-Za-z0-9_\-%=]+)")
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")

DEFAULT_VAULT = "/Users/alexandrecastro/Developer/obsidian/Alex"


# --- reading the Claude Code artifacts -----------------------------------------

def default_project_dir(cwd: Path | None = None) -> Path:
    """Claude Code names a project directory after the working directory."""
    return Path.home() / ".claude" / "projects" / str(cwd or Path.cwd()).replace("/", "-")


def resolve_artifacts(project: Path | None, sessions: list[str], since_minutes: int) -> list[Path]:
    """The session logs and spilled tool results to read, newest last."""
    files: list[Path] = []
    if sessions:
        for entry in sessions:
            path = Path(entry).expanduser()
            if path.is_dir():
                files.extend(sorted(path.glob("*.jsonl")))
                files.extend(sorted((path / "tool-results").glob("*.txt")))
            else:
                files.append(path)
        return [f for f in files if f.exists()]

    if project is None:
        raise SystemExit("No project directory. Pass --project or --session.")
    if not project.is_dir():
        candidates = sorted(
            (p for p in (Path.home() / ".claude" / "projects").glob("-*") if p.is_dir()),
            key=lambda p: max((f.stat().st_mtime for f in p.glob("*.jsonl")), default=0),
            reverse=True,
        )[:5]
        listed = "\n".join(f"  {p}" for p in candidates) or "  (none)"
        raise SystemExit(
            f"{project} does not exist, so no sessions have run for this working directory.\n"
            f"Most recent Claude Code projects:\n{listed}\nPass --project with one of those."
        )
    cutoff = datetime.now(timezone.utc).timestamp() - since_minutes * 60
    for path in sorted(project.glob("*.jsonl")):
        if path.stat().st_mtime >= cutoff:
            files.append(path)
    for path in files:
        files.extend(sorted((path.with_suffix("") / "tool-results").glob("*.txt")))
    return files


def payloads_in(text: str) -> list[dict]:
    """Every Teams transcript payload in one artifact, however deeply it is wrapped."""
    found: list[dict] = []

    def walk(node) -> None:
        if isinstance(node, str):
            if '"transcripts"' in node and "WEBVTT" in node:
                try:
                    walk(json.loads(node))
                except ValueError:
                    pass
            return
        if isinstance(node, dict):
            transcripts = node.get("transcripts")
            if isinstance(transcripts, list) and transcripts and "content" in transcripts[0]:
                found.append(node)
                return
            for value in node.values():
                walk(value)
            return
        if isinstance(node, list):
            for value in node:
                walk(value)

    if text.lstrip().startswith("{"):  # a spilled payload: the file is the payload
        try:
            walk(json.loads(text))
            if found:
                return found
        except ValueError:
            pass
    walk(text)
    return found


def uris_in(text: str) -> set[str]:
    return set(_URI_PATTERN.findall(text))


def collect(files: list[Path]) -> tuple[list[dict], set[str]]:
    """All distinct payloads and transcript URIs across the artifacts."""
    payloads: list[dict] = []
    seen: set[tuple] = set()
    uris: set[str] = set()
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        uris |= uris_in(text)
        lines = [text] if path.suffix == ".txt" else text.splitlines()
        for line in lines:
            for payload in payloads_in(line):
                transcripts = payload["transcripts"]
                key = (
                    payload.get("meeting", {}).get("joinWebUrl"),
                    transcripts[0].get("createdDateTime"),
                    len(transcripts[0].get("content", "")),
                )
                if key in seen:
                    continue
                seen.add(key)
                payloads.append(payload)
    return payloads, uris


# --- matching -----------------------------------------------------------------

def subject_key(subject: str | None) -> str:
    return _SLUG_PATTERN.sub("-", (subject or "").lower()).strip("-")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _overlap(start_a, end_a, start_b, end_b) -> float:
    if not all((start_a, end_a, start_b, end_b)):
        return 0.0
    return max(0.0, (min(end_a, end_b) - max(start_a, start_b)).total_seconds())


def uri_window(uri: str) -> tuple[str | None, str | None]:
    query = parse_qs(urlsplit(uri).query)
    return query.get("start", [None])[0], query.get("end", [None])[0]


def token_matches_join_url(uri: str, join_url: str | None) -> bool:
    if not join_url:
        return False
    match = _TOKEN_PATTERN.match(uri)
    if not match:
        return False
    token = match.group(1).replace("%3D", "=").replace("%3d", "=").rstrip("=")
    expected = base64.urlsafe_b64encode(join_url.encode()).decode().rstrip("=")
    return token == expected


def slot_uri(join_url: str, start: str, end: str) -> str:
    """Rebuild a meeting-transcript URI for a payload whose read carried no window.
    The window is formatted like the connector's own, so provenance reads the same
    either way."""
    token = base64.urlsafe_b64encode(join_url.encode()).decode()
    window = [f"{_parse_iso(value).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')}" for value in (start, end)]
    return f"meeting-transcript:///events/{token}?start={quote(window[0], safe='')}&end={quote(window[1], safe='')}"


def occurrence_key(payload: dict) -> tuple:
    """The same meeting, recovered twice (inline and spilled), is one occurrence."""
    transcripts = payload.get("transcripts") or [{}]
    return (
        payload.get("meeting", {}).get("joinWebUrl"),
        transcripts[0].get("createdDateTime"),
    )


def choose_payload(row: dict, payloads: list[dict]) -> dict | None:
    """The payload for a manifest row: same subject, and the best slot overlap when
    a recurring series put several occurrences in the artifacts."""
    wanted = subject_key(row.get("subject"))
    candidates = [p for p in payloads if subject_key(p.get("meeting", {}).get("subject")) == wanted]
    if len(candidates) <= 1:
        return candidates[0] if candidates else None
    slot_start, slot_end = _parse_iso(row.get("start")), _parse_iso(row.get("end"))
    scored = []
    for payload in candidates:
        transcript = payload["transcripts"][0]
        scored.append(
            (
                _overlap(slot_start, slot_end, _parse_iso(transcript.get("createdDateTime")), _parse_iso(transcript.get("endDateTime"))),
                transcript.get("createdDateTime") or "",
                payload,
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][2]


def choose_uri(row: dict, payload: dict, uris: set[str]) -> tuple[str, str | None]:
    """The URI as read, preferring the window that holds this occurrence. Returns
    (uri, warning)."""
    join_url = payload.get("meeting", {}).get("joinWebUrl")
    same_meeting = [u for u in uris if token_matches_join_url(u, join_url)]
    slot_start, slot_end = _parse_iso(row.get("start")), _parse_iso(row.get("end"))
    windowed = [(u, *_parse_window(u)) for u in same_meeting if uri_window(u)[0]]
    if not windowed:
        if same_meeting:
            return slot_uri(join_url, row["start"], row["end"]), "read carried no window; slot taken from the manifest"
        return slot_uri(join_url, row["start"], row["end"]), "no URI found in the artifacts; slot taken from the manifest"

    best = max(
        windowed,
        key=lambda item: (
            _overlap(slot_start, slot_end, item[1], item[2]),
            item[1] or datetime.min.replace(tzinfo=timezone.utc),
        ),
    )
    overlap = _overlap(slot_start, slot_end, best[1], best[2])
    if overlap <= 0:
        return best[0], (
            f"window {best[1]}..{best[2]} does not overlap the manifest slot "
            f"{row['start']}..{row['end']}"
        )
    return best[0], None


def _parse_window(uri: str):
    start, end = uri_window(uri)
    return _parse_iso(start), _parse_iso(end)


# --- writing ------------------------------------------------------------------

def write_payload(payload: dict, raw_dir: Path, stem: str) -> tuple[Path, Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    payload_path = raw_dir / f"{stem}.json"
    vtt_path = raw_dir / f"{stem}.vtt"
    with payload_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with vtt_path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(payload["transcripts"][0].get("content", ""))
    return payload_path, vtt_path


def run(args) -> int:
    rows = json.loads(Path(args.manifest).expanduser().read_text(encoding="utf-8"))
    if args.project:
        project = Path(args.project).expanduser()
    elif args.session:
        project = None  # explicit sessions need no discovery
    else:
        project = default_project_dir()
    files = resolve_artifacts(project, args.session or [], args.since_minutes)
    if not files:
        raise SystemExit(f"No Claude Code session artifacts found in {project or 'the given sessions'}.")
    payloads, uris = collect(files)
    print(f"read {len(files)} artifact(s): {len(payloads)} payload(s), {len(uris)} transcript URI(s)")

    raw_dir = Path(args.raw_dir).expanduser()
    transcripts_dir = Path(args.transcripts_dir).expanduser()
    unresolved: list[str] = []
    claimed: set[tuple] = set()
    rebuilt = 0

    for row in rows:
        payload = choose_payload(row, payloads)
        if payload is None:
            unresolved.append(row.get("subject", "?"))
            print(f"!! no payload recovered for {row.get('subject')}", file=sys.stderr)
            continue
        claimed.add(occurrence_key(payload))
        uri, warning = choose_uri(row, payload, uris)
        if warning:
            print(f"!! {row.get('subject')}: {warning}", file=sys.stderr)

        date, hhmm = common.local_date_and_hhmm(row["start"])
        stem = f"{date}-{subject_key(row.get('subject'))}"
        payload_path, vtt_path = write_payload(payload, raw_dir, stem)
        rebuilt += 1

        cues = payload["transcripts"][0].get("content", "").count("-->")
        print(f"{row.get('subject')} | {cues} cues | slot {row['start']}..{row['end']} | {payload_path}")
        print(f"   webvtt {vtt_path}")

        if args.normalize:
            normalized = teams_transcript.normalize(payload, row.get("event_id"), uri)
            transcript_path = transcripts_dir / f"{stem}.json"
            common.dump_transcript(normalized, transcript_path)
            note_path = write_note.note_path_for(args.vault, normalized)
            print(f"   transcript {transcript_path}")
            print(f"   note {note_path}")
            print(f"   state teams.{row.get('event_id')} -> {note_path}")

    unclaimed = [p for p in payloads if occurrence_key(p) not in claimed]
    print(f"{rebuilt} of {len(rows)} manifest rows recovered")
    sys.stdout.flush()
    for payload in unclaimed:
        subject = payload.get("meeting", {}).get("subject")
        started = (payload.get("transcripts") or [{}])[0].get("createdDateTime")
        print(
            f"note: payload for '{subject}' ({started}) has no manifest row; not written",
            file=sys.stderr,
        )
    if unresolved:
        print(f"unrecovered: {', '.join(unresolved)}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True, help="JSON rows: subject, event_id, start, end")
    parser.add_argument("--project", default=None, help="Claude Code project dir (default: from the working directory)")
    parser.add_argument("--session", action="append", default=[], help="A session .jsonl, session dir, or spill file")
    parser.add_argument("--since-minutes", type=int, default=120, help="Session files modified within this window")
    parser.add_argument("--raw-dir", default="~/.scribe/raw", help="Where the payload JSON and WEBVTT go")
    parser.add_argument("--transcripts-dir", default="~/.scribe/transcripts", help="Where normalized JSON goes")
    parser.add_argument("--normalize", action="store_true", help="Also run teams_transcript.py's normalizer")
    parser.add_argument("--vault", default=DEFAULT_VAULT, help="Vault root, for predicting the note path")
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
