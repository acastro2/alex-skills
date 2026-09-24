"""Behaviour tests for hint_speakers.py.

Reading the transcript and deciding who spoke is a language judgement, so the model
does it and writes `<id>.speakers.json`. This module is the gatekeeper and applier:
it refuses anything that is not an attendee name, on a label that exists, with a
quoted piece of evidence, and never puts one name on two labels.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hint_speakers  # noqa: E402


def _turn(start, speaker, text):
    return {"start": start, "speaker": speaker, "text": text}


def _transcript(turns):
    return {
        "schema": "scribe.transcript/1",
        "source": "hidock",
        "title": None,
        "start": "2026-09-24T14:04:32Z",
        "end": None,
        "speakers": sorted({t["speaker"] for t in turns if t["speaker"]}),
        "turns": turns,
        "provenance": {"diarization_status": "ok"},
    }


_MAPPING = {
    "speaker 1": {
        "name": "Alexandre Castro",
        "evidence": '"i\'m alex i\'m the enterprise architect" at 00:00:35',
    }
}


def _validate(mapping, turns, candidates):
    return hint_speakers.validate(mapping, turns, candidates)


# --- applying a mapping the model produced ------------------------------------

def test_applies_an_evidenced_name_and_records_the_quote():
    turns = [_turn(5.0, "speaker 0", "Morning."), _turn(35.0, "speaker 1", "i'm alex")]

    accepted, refused = _validate(_MAPPING, turns, ["Alexandre Castro", "Greg Glazier"])

    assert refused == {}
    assert accepted["speaker 1"]["name"] == "Alexandre Castro"
    updated = hint_speakers.apply_hints(_transcript(turns), accepted)
    assert updated["turns"][1]["speaker"] == "speaker 1 (likely Alexandre Castro)"
    assert updated["turns"][0]["speaker"] == "speaker 0"
    assert updated["speakers"] == ["speaker 0", "speaker 1 (likely Alexandre Castro)"]
    assert "Alexandre Castro" in updated["provenance"]["speaker_hints"]
    assert "i'm alex" in updated["provenance"]["speaker_hints"]


def test_refuses_a_name_that_is_not_an_attendee():
    turns = [_turn(5.0, "speaker 1", "hello")]

    accepted, refused = _validate(_MAPPING, turns, ["Greg Glazier", "Kylee Dill"])

    assert accepted == {}
    assert "attendee" in refused["speaker 1"]


def test_refuses_a_label_that_is_not_in_the_transcript():
    turns = [_turn(5.0, "speaker 0", "hello")]

    accepted, refused = _validate(_MAPPING, turns, ["Alexandre Castro"])

    assert accepted == {}
    assert "speaker 1" in refused


def test_refuses_two_labels_claiming_the_same_name():
    turns = [_turn(5.0, "speaker 0", "hello"), _turn(9.0, "speaker 1", "hi")]
    mapping = {
        "speaker 0": {"name": "Alexandre Castro", "evidence": '"hey alex" at 00:00:05'},
        "speaker 1": {"name": "Alexandre Castro", "evidence": '"hi alex" at 00:00:09'},
    }

    accepted, refused = _validate(mapping, turns, ["Alexandre Castro"])

    assert accepted == {}
    assert len(refused) == 2


def test_refuses_an_entry_without_evidence():
    turns = [_turn(5.0, "speaker 1", "hello")]
    mapping = {"speaker 1": {"name": "Alexandre Castro", "evidence": ""}}

    accepted, refused = _validate(mapping, turns, ["Alexandre Castro"])

    assert accepted == {}
    assert "evidence" in refused["speaker 1"]


def test_apply_is_idempotent():
    turns = [_turn(35.0, "speaker 1", "i'm alex")]
    accepted, _ = _validate(_MAPPING, turns, ["Alexandre Castro"])
    once = hint_speakers.apply_hints(_transcript(turns), accepted)

    assert hint_speakers.apply_hints(once, accepted) == once


# --- the tool the session runs ------------------------------------------------

def test_main_reads_the_mapping_file_and_labels_the_json(tmp_path):
    path = tmp_path / "call.json"
    path.write_text(
        json.dumps(_transcript([_turn(5.0, "speaker 0", "Morning."), _turn(35.0, "speaker 1", "i'm alex")])),
        encoding="utf-8",
    )
    mapping = tmp_path / "call.speakers.json"
    mapping.write_text(json.dumps(_MAPPING), encoding="utf-8")

    rc = hint_speakers.main(
        [str(path), "--attendees", "Alexandre Castro, Greg Glazier", "--from-file", str(mapping)]
    )

    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["turns"][1]["speaker"] == "speaker 1 (likely Alexandre Castro)"
    assert data["provenance"]["speaker_hint_status"] == "ok"


def test_main_without_a_mapping_file_changes_nothing(tmp_path):
    path = tmp_path / "call.json"
    before = _transcript([_turn(5.0, "speaker 1", "hello")])
    path.write_text(json.dumps(before), encoding="utf-8")

    rc = hint_speakers.main([str(path), "--attendees", "Alexandre Castro"])

    assert rc == 0
    assert json.loads(path.read_text(encoding="utf-8"))["turns"] == before["turns"]
