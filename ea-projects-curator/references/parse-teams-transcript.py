#!/usr/bin/env python3
"""Turn a Teams meeting-transcript JSON blob into a readable speaker-labelled transcript.

Input is the file the harness saves when `read_resource` on a
`meeting-transcript:///events/...` URI exceeds the tool output limit (~114KB for an
85-minute meeting). Shape:

    {"meeting": {...}, "transcripts": [{"createdDateTime", "endDateTime", "content"}]}

`content` is WEBVTT with `<v Speaker Name>text</v>` cues, one cue per breath.

Usage:
    python3 parse-teams-transcript.py <raw.json> [out.txt]

Prints the occurrence window and speaker list to stderr so you can confirm you have the
right session before reading the transcript. NEVER trust `meeting.startDateTime` for
this: on a recurring series it reports the SERIES start, not the occurrence.
"""
import json
import re
import sys


def parse(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    subject = data.get("meeting", {}).get("subject", "(unknown meeting)")
    transcripts = data.get("transcripts") or []
    if not transcripts:
        sys.exit("No transcripts in payload. The meeting was probably never recorded.")
    if len(transcripts) > 1:
        print(
            f"WARNING: {len(transcripts)} transcripts present — you likely omitted the "
            "?start=/&end= params and got the whole series. Confirm which one you want.",
            file=sys.stderr,
        )

    out = []
    for t in transcripts:
        cues = []
        for block in t.get("content", "").split("\r\n\r\n"):
            block = block.strip()
            if not block or block.startswith("WEBVTT"):
                continue
            lines = [ln for ln in block.split("\r\n") if ln.strip()]
            ts_line = next((ln for ln in lines if "-->" in ln), None)
            if not ts_line:
                continue
            start = ts_line.split("-->")[0].strip()[:8]
            text = " ".join(ln for ln in lines if "-->" not in ln)
            m = re.match(r"<v ([^>]+)>(.*?)</v>", text, re.DOTALL)
            if m:
                speaker, utterance = m.group(1).strip(), m.group(2).strip()
            else:
                speaker = "UNKNOWN"
                utterance = re.sub(r"</?v[^>]*>", "", text).strip()
            if utterance:
                cues.append((start, speaker, utterance))

        # Merge consecutive cues from the same speaker; unmerged cues read as noise.
        merged = []
        for start, speaker, utterance in cues:
            if merged and merged[-1][1] == speaker:
                merged[-1][2] += " " + utterance
            else:
                merged.append([start, speaker, utterance])

        out.append((t, cues, merged))

    return subject, out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    raw, dest = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    subject, parsed = parse(raw)

    chunks = []
    for t, cues, merged in parsed:
        speakers = sorted({turn[1] for turn in merged})
        header = (
            f"{subject} - Transcript\n"
            f"Occurrence: {t.get('createdDateTime')} to {t.get('endDateTime')} (UTC)\n"
            f"Source: Microsoft Teams meeting transcript (verbatim, auto-generated)\n"
            f"{len(cues)} cues merged into {len(merged)} turns. Speakers: {', '.join(speakers)}\n"
            + "=" * 90
            + "\n\n"
        )
        body = "".join(f"[{s}] {spk}: {utt}\n\n" for s, spk, utt in merged)
        chunks.append(header + body)

        print(
            f"occurrence {t.get('createdDateTime')} -> {t.get('endDateTime')}: "
            f"{len(cues)} cues, {len(merged)} turns, {len(speakers)} speakers",
            file=sys.stderr,
        )
        print(f"speakers: {', '.join(speakers)}", file=sys.stderr)

    text = "\n".join(chunks)
    if dest:
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {len(text)} chars to {dest}", file=sys.stderr)
        print(
            "Reminder: Teams garbles proper nouns. Verify or omit, never publish a guess.",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
