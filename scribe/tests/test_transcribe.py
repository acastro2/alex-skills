"""Behaviour tests for transcribe.py, exercised through main() with a fake
ASR and a fake duration probe — no mlx import, no real audio decoding."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import scribe_common  # noqa: E402
import transcribe  # noqa: E402


def _dummy_audio(tmp_path: Path, name: str = "call.mp3") -> Path:
    path = tmp_path / name
    path.write_bytes(b"not really an mp3, just some bytes for sha256\x00\x01\x02")
    return path


def _fake_asr(segments: list[dict], language: str = "en"):
    def _asr(audio_path, model, lang):
        return {"text": " ".join(s["text"] for s in segments), "segments": segments, "language": language}

    return _asr


def _fake_probe(value):
    def _probe(audio_path):
        return value

    return _probe


# --- start-time resolution ---------------------------------------------------

def test_start_parsed_from_hidock_filename_in_local_tz_converts_to_utc(tmp_path):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"

    rc = transcribe.main(
        [str(audio), "-o", str(out)],
        asr=_fake_asr([{"id": 0, "seek": 0, "start": 0.0, "end": 1.0, "text": "Hello."}]),
        probe_duration=_fake_probe(60.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["start"] == "2026-09-02T20:00:56Z"
    assert data["provenance"]["hidock_file"] == "2026Sep02-150056-Rec17.hda"


def test_hidock_name_flag_used_when_audio_filename_is_generic(tmp_path):
    audio = _dummy_audio(tmp_path, "call.mp3")
    out = tmp_path / "out.json"

    rc = transcribe.main(
        [str(audio), "-o", str(out), "--hidock-name", "2026Sep02-150056-Rec17.hda"],
        asr=_fake_asr([{"id": 0, "seek": 0, "start": 0.0, "end": 1.0, "text": "Hello."}]),
        probe_duration=_fake_probe(60.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["start"] == "2026-09-02T20:00:56Z"
    assert data["provenance"]["hidock_file"] == "2026Sep02-150056-Rec17.hda"


def test_start_flag_overrides_filename_parsing(tmp_path):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"

    rc = transcribe.main(
        [str(audio), "-o", str(out), "--start", "2027-01-01T00:00:00Z"],
        asr=_fake_asr([{"id": 0, "seek": 0, "start": 0.0, "end": 1.0, "text": "Hello."}]),
        probe_duration=_fake_probe(60.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["start"] == "2027-01-01T00:00:00Z"


def test_no_date_in_filename_and_no_start_exits_2(tmp_path, capsys):
    audio = _dummy_audio(tmp_path, "call.mp3")
    out = tmp_path / "out.json"

    rc = transcribe.main(
        [str(audio), "-o", str(out)],
        asr=_fake_asr([{"id": 0, "seek": 0, "start": 0.0, "end": 1.0, "text": "Hello."}]),
        probe_duration=_fake_probe(60.0),
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert "start time" in captured.err.lower()
    assert not out.exists()


# --- paragraph grouping -------------------------------------------------------

def test_paragraph_gap_starts_a_new_turn(tmp_path):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"
    segments = [
        {"id": 0, "seek": 0, "start": 0.0, "end": 5.0, "text": "First segment."},
        {"id": 1, "seek": 0, "start": 6.9, "end": 9.0, "text": "Still close."},
        {"id": 2, "seek": 0, "start": 12.0, "end": 14.0, "text": "New topic starts."},
    ]

    rc = transcribe.main(
        [str(audio), "-o", str(out), "--paragraph-gap", "2.0"],
        asr=_fake_asr(segments),
        probe_duration=_fake_probe(20.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    turns = data["turns"]
    assert len(turns) == 2
    assert turns[0]["start"] == 0.0
    assert turns[0]["text"] == "First segment. Still close."
    assert turns[1]["start"] == 12.0
    assert turns[1]["text"] == "New topic starts."
    assert all(t["speaker"] is None for t in turns)
    assert data["speakers"] == []


def test_running_turn_over_90_seconds_forces_a_split(tmp_path):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"
    # Gaps stay well under the 2.0s paragraph-gap threshold throughout, so
    # only the 90-second running-turn cap can be responsible for a split.
    segments = [
        {"id": 0, "seek": 0, "start": 0.0, "end": 40.0, "text": "Part one."},
        {"id": 1, "seek": 0, "start": 40.5, "end": 80.0, "text": "Part two."},
        {"id": 2, "seek": 0, "start": 80.5, "end": 95.0, "text": "Part three."},
    ]

    rc = transcribe.main(
        [str(audio), "-o", str(out), "--paragraph-gap", "2.0"],
        asr=_fake_asr(segments),
        probe_duration=_fake_probe(100.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    turns = data["turns"]
    assert len(turns) == 2
    assert turns[0]["start"] == 0.0
    assert turns[0]["text"] == "Part one. Part two."
    assert turns[1]["start"] == 80.5
    assert turns[1]["text"] == "Part three."


# --- hallucination guard -------------------------------------------------------

def test_repeat_hallucination_guard_drops_third_and_later_and_reports_count(tmp_path):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"
    segments = [
        {"id": 0, "seek": 0, "start": 0.0, "end": 1.0, "text": "Thank you."},
        {"id": 1, "seek": 0, "start": 1.0, "end": 2.0, "text": "thank you!"},
        {"id": 2, "seek": 0, "start": 2.0, "end": 3.0, "text": "THANK YOU"},
        {"id": 3, "seek": 0, "start": 3.0, "end": 4.0, "text": "thank you."},
        {"id": 4, "seek": 0, "start": 4.0, "end": 5.0, "text": "Actual content."},
    ]

    rc = transcribe.main(
        [str(audio), "-o", str(out), "--paragraph-gap", "100"],
        asr=_fake_asr(segments),
        probe_duration=_fake_probe(5.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["provenance"]["dropped_repeats"] == 2
    assert data["provenance"]["segment_count"] == 3
    turn_text = data["turns"][0]["text"]
    assert turn_text.count("hank you") == 2
    assert "Actual content." in turn_text


def test_empty_segment_after_strip_is_dropped_without_counting_as_repeat(tmp_path):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"
    segments = [
        {"id": 0, "seek": 0, "start": 0.0, "end": 1.0, "text": "Hello."},
        {"id": 1, "seek": 0, "start": 1.0, "end": 2.0, "text": "   "},
        {"id": 2, "seek": 0, "start": 2.0, "end": 3.0, "text": "World."},
    ]

    rc = transcribe.main(
        [str(audio), "-o", str(out), "--paragraph-gap", "100"],
        asr=_fake_asr(segments),
        probe_duration=_fake_probe(3.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["provenance"]["dropped_repeats"] == 0
    assert data["provenance"]["segment_count"] == 2
    assert data["turns"][0]["text"] == "Hello. World."


# --- provenance and end computation -------------------------------------------

def test_provenance_fields_and_end_from_probed_duration(tmp_path):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"
    expected_sha256 = hashlib.sha256(audio.read_bytes()).hexdigest()
    segments = [{"id": 0, "seek": 0, "start": 0.0, "end": 1.0, "text": "Hello."}]

    rc = transcribe.main(
        [str(audio), "-o", str(out), "--model", "mlx-community/whisper-large-v3-turbo", "--language", "en"],
        asr=_fake_asr(segments, language="en"),
        probe_duration=_fake_probe(125.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    provenance = data["provenance"]
    assert provenance["audio_sha256"] == expected_sha256
    assert provenance["asr_model"] == "mlx-community/whisper-large-v3-turbo"
    assert provenance["asr_language"] == "en"
    assert provenance["duration_s"] == 125.0
    assert provenance["segment_count"] == 1
    assert provenance["dropped_repeats"] == 0
    assert provenance["hidock_file"] == "2026Sep02-150056-Rec17.hda"

    # start is 2026-09-02T20:00:56Z; end = start + 125s.
    assert data["start"] == "2026-09-02T20:00:56Z"
    assert data["end"] == "2026-09-02T20:03:01Z"


def test_end_falls_back_to_last_segment_end_when_probe_returns_none(tmp_path):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"
    segments = [
        {"id": 0, "seek": 0, "start": 0.0, "end": 10.0, "text": "First."},
        {"id": 1, "seek": 0, "start": 20.0, "end": 42.5, "text": "Second."},
    ]

    rc = transcribe.main(
        [str(audio), "-o", str(out)],
        asr=_fake_asr(segments),
        probe_duration=_fake_probe(None),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["provenance"]["duration_s"] == 42.5
    assert data["start"] == "2026-09-02T20:00:56Z"
    assert data["end"] == "2026-09-02T20:01:38Z"


# --- contract shape ------------------------------------------------------------

def test_output_matches_transcript_contract_and_schema_version(tmp_path, capsys):
    audio = _dummy_audio(tmp_path, "2026Sep02-150056-Rec17.mp3")
    out = tmp_path / "out.json"
    segments = [{"id": 0, "seek": 0, "start": 0.0, "end": 1.0, "text": "Hello."}]

    rc = transcribe.main(
        [str(audio), "-o", str(out), "--title", "Call with Jane"],
        asr=_fake_asr(segments),
        probe_duration=_fake_probe(10.0),
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))

    assert data["schema"] == scribe_common.SCHEMA_VERSION
    assert data["source"] == "hidock"
    assert data["title"] == "Call with Jane"
    assert set(data.keys()) == {
        "schema", "source", "title", "start", "end", "speakers", "turns", "provenance",
    }
    assert isinstance(data["turns"], list)
    for turn in data["turns"]:
        assert set(turn.keys()) == {"start", "speaker", "text"}
    provenance_keys = {
        "hidock_file", "audio_sha256", "asr_model", "asr_language",
        "duration_s", "segment_count", "dropped_repeats",
    }
    assert set(data["provenance"].keys()) == provenance_keys

    # Output path goes to stdout, everything else stays on stderr — a
    # caller shells out and takes stdout as the file location.
    captured = capsys.readouterr()
    assert captured.out.strip() == str(out)
