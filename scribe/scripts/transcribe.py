#!/usr/bin/env python3
"""Transcribe a local HiDock call recording into scribe.transcript/1 JSON.

Input is a mono 48 kHz MP3 saved from a HiDock P1 as `<stem>.mp3`. ASR runs
via mlx-whisper (Apple Silicon); mlx_whisper decodes audio itself through
ffmpeg (Homebrew, must be on PATH), and duration comes from ffprobe.

Usage:
    python3 transcribe.py <audio> -o <out.json> \\
        [--model mlx-community/whisper-large-v3-turbo] [--language en] \\
        [--diarization-model mlx-community/Nemotron-3-Diarization] \\
        [--start ISO8601] [--tz America/Chicago] [--title TEXT] \\
        [--hidock-name 2026Sep02-150056-Rec17.hda] [--paragraph-gap 2.0] \\
        [--allow-download]

Start time: taken from --start if given; otherwise parsed from
--hidock-name, or from the audio filename stem, whichever matches the
HiDock device-clock pattern `YYYYMonDD-HHMMSS-RecNN` (interpreted as local
time in --tz and converted to UTC). Exits 2 if neither is available.

Duration/end: from ffprobe; falls back to the last kept ASR segment's end
if ffprobe fails.

Turns: ASR segments are grouped into paragraphs, starting a new turn when
the gap since the previous segment's end reaches --paragraph-gap seconds,
when the speaker changes, or when the running turn would exceed 90 seconds.
Each segment takes the label of the diarization span it overlaps most; a
segment with no overlapping span stays unlabeled (speaker null). Without
diarization spans, every turn is unlabeled and `speakers` is [].

Hallucination guard: a run of 3+ consecutive segments with the same
normalized text (lowercase, punctuation stripped) keeps only the first two
and drops the rest; empty-after-strip segments are dropped outright.

On success prints only the written path to stdout; stats go to stderr.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import scribe_common as common

DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
DEFAULT_DIARIZATION_MODEL = "mlx-community/Nemotron-3-Diarization"
DEFAULT_LANGUAGE = "en"
MAX_TURN_SECONDS = 90.0
MIN_SPEAKER_OVERLAP_SECONDS = 0.1

_HIDOCK_NAME_PATTERN = re.compile(
    r"^(?P<year>\d{4})(?P<mon>[A-Za-z]{3})(?P<day>\d{2})-"
    r"(?P<hh>\d{2})(?P<mm>\d{2})(?P<ss>\d{2})-Rec\d+$"
)
_MONTH_ABBR = {
    abbr: i
    for i, abbr in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        start=1,
    )
}
_PUNCT_PATTERN = re.compile(r"[^\w\s]")


# --- seams: real ASR and subprocess boundaries ------------------------------

def asr(audio_path: str, model: str, language: str) -> dict:
    """Default ASR: mlx_whisper. Imported lazily so tests never import mlx."""
    import mlx_whisper

    return mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model,
        language=language,
        condition_on_previous_text=False,
        word_timestamps=False,
    )


def probe_duration(audio_path: str) -> float | None:
    """Default duration probe: ffprobe via subprocess. None if it fails."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def diarize(audio_path: str, model: str) -> list[dict]:
    """Default diarizer: mlx-audio over an ffmpeg-decoded 16 kHz mono WAV.

    Lazily imported so tests never import mlx. Returns spans with display
    labels ("speaker 0", ...) in the model's arrival order.
    """
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # Xet transfer bug, 2026-09-24

    from mlx_audio.vad import load

    with tempfile.TemporaryDirectory(prefix="scribe-diar-") as tmp:
        wav_path = os.path.join(tmp, "audio.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path,
             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav_path],
            check=True,
            capture_output=True,
        )
        diarizer = load(model, strict=True)
        result = diarizer.generate(wav_path)

    return [
        {"start": float(seg.start), "end": float(seg.end), "speaker": f"speaker {seg.speaker}"}
        for seg in getattr(result, "segments", []) or []
    ]


# --- start-time resolution ---------------------------------------------------

def _normalize_iso_to_utc_z(value: str) -> str:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_hidock_datetime(name: str, tz_name: str) -> str | None:
    stem = Path(name).stem
    m = _HIDOCK_NAME_PATTERN.match(stem)
    if not m:
        return None
    month = _MONTH_ABBR.get(m.group("mon").capitalize())
    if month is None:
        return None
    try:
        naive = datetime(
            int(m.group("year")), month, int(m.group("day")),
            int(m.group("hh")), int(m.group("mm")), int(m.group("ss")),
        )
    except ValueError:
        return None
    local_dt = naive.replace(tzinfo=ZoneInfo(tz_name))
    return local_dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_start(args: argparse.Namespace) -> str | None:
    if args.start:
        return _normalize_iso_to_utc_z(args.start)
    for candidate in filter(None, [args.hidock_name, Path(args.audio).name]):
        parsed = _parse_hidock_datetime(candidate, args.tz)
        if parsed:
            return parsed
    return None


def _resolve_hidock_file(args: argparse.Namespace) -> str | None:
    if args.hidock_name:
        return args.hidock_name
    stem = Path(args.audio).stem
    if _HIDOCK_NAME_PATTERN.match(stem):
        return f"{stem}.hda"
    return None


# --- hallucination guard ----------------------------------------------------

def _normalize_for_repeat_check(text: str) -> str:
    return _PUNCT_PATTERN.sub("", text.lower()).strip()


def _filter_segments(segments: list[dict]) -> tuple[list[dict], int]:
    """Drop empty-after-strip segments, then drop the 3rd+ consecutive
    segment whose normalized text repeats the previous kept one."""
    kept: list[tuple[dict, str]] = []
    dropped = 0
    for seg in segments:
        raw_text = (seg.get("text") or "").strip()
        if not raw_text:
            continue
        normalized = _normalize_for_repeat_check(raw_text)
        run_len = 1
        for _, prev_normalized in reversed(kept):
            if prev_normalized == normalized:
                run_len += 1
            else:
                break
        if run_len >= 3:
            dropped += 1
            continue
        kept.append((seg, normalized))
    return [seg for seg, _ in kept], dropped


# --- speaker assignment -------------------------------------------------------

def _overlap_seconds(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _assign_speakers(segments: list[dict], spans: list[dict]) -> list[str | None]:
    """Label each segment with the speaker of the span it overlaps most."""
    labels: list[str | None] = []
    for seg in segments:
        best_label, best_overlap = None, 0.0
        for span in spans:
            overlap = _overlap_seconds(
                float(seg["start"]), float(seg["end"]), float(span["start"]), float(span["end"])
            )
            if overlap > best_overlap:
                best_label, best_overlap = span["speaker"], overlap
        labels.append(best_label if best_overlap >= MIN_SPEAKER_OVERLAP_SECONDS else None)
    return labels


# --- turn grouping -----------------------------------------------------------

def _group_into_turns(segments: list[dict], paragraph_gap: float) -> list[dict]:
    turns: list[dict] = []
    current: dict | None = None
    for seg in segments:
        start = float(seg["start"])
        end = float(seg["end"])
        text = str(seg["text"]).strip()
        speaker = seg.get("speaker")
        if current is None:
            current = {"start": start, "end": end, "speaker": speaker, "texts": [text]}
            continue
        gap = start - current["end"]
        prospective_duration = end - current["start"]
        speaker_changed = speaker != current["speaker"]
        if gap >= paragraph_gap or speaker_changed or prospective_duration > MAX_TURN_SECONDS:
            turns.append(current)
            current = {"start": start, "end": end, "speaker": speaker, "texts": [text]}
        else:
            current["texts"].append(text)
            current["end"] = end
    if current is not None:
        turns.append(current)
    return [
        {"start": t["start"], "speaker": t["speaker"], "text": " ".join(t["texts"]).strip()}
        for t in turns
    ]


# --- misc --------------------------------------------------------------------

def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(
    argv: list[str] | None = None,
    *,
    asr=asr,
    probe_duration=probe_duration,
    diarize=diarize,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="Path to the local audio file (mp3)")
    parser.add_argument("-o", "--out", required=True, help="Path to write the normalized transcript JSON")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="mlx-whisper model repo")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="Language code for ASR")
    parser.add_argument(
        "--diarization-model", default=DEFAULT_DIARIZATION_MODEL,
        help="mlx-audio diarization model repo",
    )
    parser.add_argument("--start", default=None, help="Recording start, ISO 8601 (overrides filename parsing)")
    parser.add_argument("--tz", default="America/Chicago", help="Local timezone of the HiDock device clock")
    parser.add_argument("--title", default=None, help="Transcript title")
    parser.add_argument(
        "--hidock-name", default=None,
        help="Original HiDock filename, e.g. 2026Sep02-150056-Rec17.hda; recorded in provenance",
    )
    parser.add_argument(
        "--paragraph-gap", type=float, default=2.0,
        help="Seconds of silence between segments that starts a new turn",
    )
    parser.add_argument(
        "--allow-download", action="store_true",
        help="Allow model downloads (whisper and diarization); default runs offline (HF_HUB_OFFLINE=1)",
    )
    args = parser.parse_args(argv)

    if not args.allow_download:
        os.environ["HF_HUB_OFFLINE"] = "1"

    start = _resolve_start(args)
    if start is None:
        print(
            "Could not determine a recording start time: no --start given, and neither "
            f"--hidock-name nor the audio filename {Path(args.audio).name!r} matches the "
            "HiDock pattern YYYYMonDD-HHMMSS-RecNN.",
            file=sys.stderr,
        )
        return 2

    result = asr(args.audio, args.model, args.language)
    segments = result.get("segments") or []
    language = result.get("language") or args.language

    kept_segments, dropped_repeats = _filter_segments(segments)
    if dropped_repeats:
        print(f"dropped {dropped_repeats} repeated segment(s) (hallucination guard)", file=sys.stderr)

    try:
        spans = diarize(args.audio, args.diarization_model)
        diarization_status = "ok"
    except ImportError as exc:
        spans = []
        diarization_status = "skipped"
        print(f"diarization skipped: {exc}", file=sys.stderr)
    except Exception as exc:
        spans = []
        diarization_status = "failed"
        print(f"diarization failed: {exc}", file=sys.stderr)

    labels = _assign_speakers(kept_segments, spans)
    labeled_segments = [
        {"start": seg["start"], "end": seg["end"], "text": seg["text"], "speaker": label}
        for seg, label in zip(kept_segments, labels)
    ]

    turns = _group_into_turns(labeled_segments, args.paragraph_gap)
    speakers = sorted({turn["speaker"] for turn in turns if turn["speaker"] is not None})

    duration = probe_duration(args.audio)
    if duration is None and kept_segments:
        duration = float(kept_segments[-1]["end"])

    end = None
    if duration is not None:
        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
        end = (start_dt + timedelta(seconds=duration)).strftime("%Y-%m-%dT%H:%M:%SZ")

    provenance = {
        "hidock_file": _resolve_hidock_file(args),
        "audio_sha256": _sha256_file(args.audio),
        "asr_model": args.model,
        "asr_language": language,
        "duration_s": duration,
        "segment_count": len(kept_segments),
        "dropped_repeats": dropped_repeats,
        "diarization_model": args.diarization_model,
        "diarization_status": diarization_status,
        "diarization_spans": len(spans),
    }

    transcript = {
        "schema": common.SCHEMA_VERSION,
        "source": "hidock",
        "title": args.title,
        "start": start,
        "end": end,
        "speakers": speakers,
        "turns": turns,
        "provenance": provenance,
    }

    common.dump_transcript(transcript, args.out)

    print(
        f"model={args.model} language={language} duration_s={duration} "
        f"segments_kept={len(kept_segments)} segments_dropped={dropped_repeats} "
        f"turns={len(turns)} diarization={diarization_status} "
        f"spans={len(spans)} speakers={len(speakers)}",
        file=sys.stderr,
    )
    print(str(Path(args.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
