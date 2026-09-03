#!/usr/bin/env python3
"""Normalize a Microsoft Teams meeting-transcript payload into scribe.transcript/1 JSON.

Input is the JSON the M365 MCP `read_resource` returns for a
`meeting-transcript:///events/...` URI. Shape:

    {"meeting": {"subject": ...}, "transcripts": [{"createdDateTime", "endDateTime", "content"}]}

`content` is WEBVTT with `<v Speaker Name>text</v>` cues, one cue per breath,
blocks separated by `\\r\\n\\r\\n` (also accepts `\\n\\n`).

Usage:
    python3 teams_transcript.py <raw.json> -o <out.json> [--event-id ID] [--transcript-uri URI] [--merge]

--merge joins several transcripts that all fall inside the occurrence window (the
recording was stopped and restarted) into one, in createdDateTime order, with the
cue clock kept continuous across the gap.

NEVER trust `meeting.startDateTime` for the occurrence window: on a recurring
series it reports the SERIES start, not this occurrence's start. Use
transcripts[0].createdDateTime/endDateTime instead.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import parse_qs, urlsplit

import scribe_common as common

_CUE_TAG_PATTERN = re.compile(r"<v ([^>]+)>(.*?)</v>", re.DOTALL)
_STRAY_V_TAG_PATTERN = re.compile(r"</?v[^>]*>")
_VTT_TIMESTAMP_PATTERN = re.compile(r"^(\d+):(\d+):(\d+)\.(\d+)$")


def _parse_vtt_timestamp(ts: str) -> float:
    m = _VTT_TIMESTAMP_PATTERN.match(ts.strip())
    if not m:
        raise ValueError(f"unrecognized VTT timestamp: {ts!r}")
    hours, minutes, seconds, millis = m.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / (10 ** len(millis))


def parse_cues(content: str) -> list[dict]:
    """Parse WEBVTT content into cues with start seconds relative to the first cue."""
    normalized = content.replace("\r\n", "\n")
    raw_cues = []
    for block in normalized.split("\n\n"):
        block = block.strip()
        if not block or block.startswith("WEBVTT"):
            continue
        lines = [ln for ln in block.split("\n") if ln.strip()]
        ts_line = next((ln for ln in lines if "-->" in ln), None)
        if not ts_line:
            continue
        start_text = ts_line.split("-->")[0].strip()
        text = " ".join(ln for ln in lines if "-->" not in ln)
        m = _CUE_TAG_PATTERN.match(text)
        if m:
            speaker, utterance = m.group(1).strip(), m.group(2).strip()
        else:
            speaker = "UNKNOWN"
            utterance = _STRAY_V_TAG_PATTERN.sub("", text).strip()
        if utterance:
            raw_cues.append((_parse_vtt_timestamp(start_text), speaker, utterance))

    if not raw_cues:
        return []
    first_start = raw_cues[0][0]
    return [
        {"start": start - first_start, "speaker": speaker, "text": utterance}
        for start, speaker, utterance in raw_cues
    ]


def occurrence_window(transcript_uri: str | None) -> tuple[str | None, str | None]:
    """The ?start=&end= params on the meeting-transcript URI are the calendar
    slot of this occurrence. They name the meeting better than the first cue
    (which lands a few seconds before or after the slot), so the note uses them."""
    if not transcript_uri:
        return None, None
    params = parse_qs(urlsplit(transcript_uri).query)
    start = params.get("start", [None])[0]
    end = params.get("end", [None])[0]
    return start, end


def _merge_transcripts(transcripts: list[dict]) -> tuple[dict, list[dict]]:
    """Concatenate restarted transcript segments into one cue list. Each segment's
    cues restart at zero, so later segments are shifted by the wall-clock gap
    between the first segment's start and their own."""
    ordered = sorted(transcripts, key=lambda t: t.get("createdDateTime") or "")
    first_start = _parse_iso(ordered[0]["createdDateTime"])
    cues: list[dict] = []
    for seg in ordered:
        offset = (_parse_iso(seg["createdDateTime"]) - first_start).total_seconds()
        for cue in parse_cues(seg.get("content", "")):
            cues.append({**cue, "start": cue["start"] + offset})
    merged = {
        "createdDateTime": ordered[0].get("createdDateTime"),
        "endDateTime": ordered[-1].get("endDateTime"),
        "segments": len(ordered),
    }
    return merged, cues


def _parse_iso(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize(raw: dict, event_id: str | None, transcript_uri: str | None, merge: bool = False) -> dict:
    transcripts = raw.get("transcripts") or []
    if not transcripts:
        sys.exit("No transcript in payload; meeting was probably not recorded.")
    if len(transcripts) > 1 and not merge:
        sys.exit(
            f"{len(transcripts)} transcripts present in payload — either the caller omitted "
            "the ?start=&end= window on the meeting-transcript:/// URI and got the whole "
            "recurring series, or the recording was stopped and restarted. Re-fetch with the "
            "occurrence window, or pass --merge if all segments belong to this one meeting."
        )

    if len(transcripts) > 1:
        transcript, cues = _merge_transcripts(transcripts)
    else:
        transcript = transcripts[0]
        cues = parse_cues(transcript.get("content", ""))
    turns = common.merge_consecutive_turns(cues)
    speakers = sorted({turn["speaker"] for turn in turns})

    provenance: dict = {"cue_count": len(cues)}
    if transcript.get("segments"):
        provenance["merged_segments"] = transcript["segments"]
    if event_id:
        provenance["teams_event_id"] = event_id
    if transcript_uri:
        provenance["transcript_uri"] = transcript_uri
    provenance["transcript_start"] = transcript.get("createdDateTime")
    provenance["transcript_end"] = transcript.get("endDateTime")
    slot_start, slot_end = occurrence_window(transcript_uri)

    print(
        f"occurrence {transcript.get('createdDateTime')} -> {transcript.get('endDateTime')}: "
        f"{len(cues)} cues, {len(turns)} turns, {len(speakers)} speakers",
        file=sys.stderr,
    )
    print(f"speakers: {', '.join(speakers)}", file=sys.stderr)

    return {
        "schema": common.SCHEMA_VERSION,
        "source": "teams",
        "title": raw.get("meeting", {}).get("subject"),
        # Slot start names the meeting; the real end keeps duration honest.
        "start": slot_start or transcript.get("createdDateTime"),
        "end": transcript.get("endDateTime") or slot_end,
        "speakers": speakers,
        "turns": [{"start": t["start"], "speaker": t["speaker"], "text": t["text"]} for t in turns],
        "provenance": provenance,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_json", help="Path to the raw M365 meeting-transcript payload")
    parser.add_argument("-o", "--out", required=True, help="Path to write the normalized transcript JSON")
    parser.add_argument("--event-id", default=None, help="Teams calendar event id, recorded in provenance")
    parser.add_argument("--transcript-uri", default=None, help="meeting-transcript:/// URI, recorded in provenance")
    parser.add_argument("--merge", action="store_true", help="Join restarted transcript segments of one meeting")
    args = parser.parse_args()

    with open(args.raw_json, encoding="utf-8") as fh:
        raw = json.load(fh)

    normalized = normalize(raw, args.event_id, args.transcript_uri, merge=args.merge)
    common.dump_transcript(normalized, args.out)


if __name__ == "__main__":
    main()
