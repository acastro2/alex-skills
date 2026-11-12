"""voicememo_transcript.py: read the transcript Apple Voice Memos stores in the .m4a
(`moov/trak/udta/tsrp`, JSON) and write a normal scribe transcript JSON from it.
Exit 4 means the file has no Apple transcript: fall back to whisper (transcribe.py)."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scribe_common as common
import transcribe

CONTAINERS = {b"moov", b"trak", b"udta", b"mdia", b"minf", b"stbl"}
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
EXIT_NO_TRANSCRIPT = 4


def _boxes(data: bytes, start: int, end: int):
    """Yield (type, payload_start, payload_end) for each box in data[start:end]."""
    pos = start
    while pos + 8 <= end:
        size, kind = struct.unpack_from(">I4s", data, pos)
        header = 8
        if size == 1:
            if pos + 16 > end:
                return
            size = struct.unpack_from(">Q", data, pos + 8)[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            return
        yield kind, pos + header, pos + size
        pos += size


def _find(data: bytes, start: int, end: int, path: tuple[bytes, ...]) -> tuple[int, int] | None:
    for kind, lo, hi in _boxes(data, start, end):
        if kind == path[0]:
            if len(path) == 1:
                return lo, hi
            if kind in CONTAINERS:
                found = _find(data, lo, hi, path[1:])
                if found:
                    return found
    return None


def _find_anywhere(data: bytes, start: int, end: int, name: bytes) -> tuple[int, int] | None:
    """Find a box by type, descending through container boxes (moov, trak, udta, ...)."""
    for kind, lo, hi in _boxes(data, start, end):
        if kind == name:
            return lo, hi
        if kind in CONTAINERS:
            found = _find_anywhere(data, lo, hi, name)
            if found:
                return found
    return None


def read_tsrp(path: str | Path) -> dict | None:
    with open(path, "rb") as fh:
        data = fh.read()
    span = _find_anywhere(data, 0, len(data), b"tsrp")
    if span is None:
        return None
    try:
        return json.loads(data[span[0]:span[1]].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def read_duration(path: str | Path) -> float | None:
    with open(path, "rb") as fh:
        data = fh.read()
    span = _find(data, 0, len(data), (b"moov", b"mvhd"))
    if span is None:
        return None
    lo, hi = span
    version = data[lo]
    if version == 1 and hi - lo >= 32:
        timescale, duration = struct.unpack_from(">IQ", data, lo + 20)
    elif version == 0 and hi - lo >= 20:
        timescale, duration = struct.unpack_from(">II", data, lo + 12)
    else:
        return None
    return duration / timescale if timescale else None


def words(tsrp: dict) -> list[dict]:
    attributed = tsrp.get("attributedString", {})
    runs = attributed.get("runs", [])
    table = attributed.get("attributeTable", [])
    out = []
    for text, index in zip(runs[0::2], runs[1::2]):
        time_range = table[index].get("timeRange")
        if not time_range:
            continue
        out.append({"start": float(time_range[0]), "end": float(time_range[1]), "text": str(text).strip()})
    return out


def _utc(iso: str) -> datetime:
    parsed = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn an Apple Voice Memos transcript into scribe JSON.")
    parser.add_argument("m4a")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--voicememo-id", required=True)
    parser.add_argument("--start", required=True, help="ISO UTC start time")
    parser.add_argument("--title")
    parser.add_argument("--paragraph-gap", type=float, default=2.0)
    args = parser.parse_args(argv)

    tsrp = read_tsrp(args.m4a)
    if tsrp is None:
        print(f"no Apple transcript in {args.m4a}; fall back to whisper", file=sys.stderr)
        return EXIT_NO_TRANSCRIPT

    word_list = words(tsrp)
    if not word_list:
        print(f"no Apple transcript text in {args.m4a} yet; fall back to whisper", file=sys.stderr)
        return EXIT_NO_TRANSCRIPT
    duration = read_duration(args.m4a)
    start = _utc(args.start)
    end = start + timedelta(seconds=duration or 0.0)
    transcript_end = word_list[-1]["end"] if word_list else 0.0
    segments = [{**w, "speaker": None} for w in word_list]

    common.dump_transcript(
        {
            "schema": common.SCHEMA_VERSION,
            "source": "voicememo",
            "title": args.title,
            "start": start.strftime(TIME_FORMAT),
            "end": end.strftime(TIME_FORMAT),
            "speakers": [],
            "turns": transcribe._group_into_turns(segments, args.paragraph_gap),
            "provenance": {
                "transcript_source": "apple",
                "voicememo_id": args.voicememo_id,
                "audio_sha256": hashlib.sha256(Path(args.m4a).read_bytes()).hexdigest(),
                "locale": (tsrp.get("locale") or {}).get("identifier"),
                "word_count": len(word_list),
                "duration_s": round(duration, 1) if duration else None,
                "transcript_end_s": transcript_end,
                "coverage": round(transcript_end / duration, 2) if duration else None,
                "diarization_status": "skipped",
            },
        },
        args.output,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
