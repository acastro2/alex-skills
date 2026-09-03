"""Behaviour tests for scribe_common's public functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import scribe_common  # noqa: E402


def test_clean_turns_drops_empty_before_merge_so_it_no_longer_keeps_same_speaker_apart():
    turns = [
        {"start": 0.0, "speaker": "Ana Silva", "text": "First part."},
        {"start": 1.0, "speaker": "Bruno Costa", "text": "uh"},
        {"start": 2.0, "speaker": "Ana Silva", "text": "Second part."},
    ]

    cleaned, glossary_replacements = scribe_common.clean_turns(turns, glossary=[])

    assert glossary_replacements == 0
    assert len(cleaned) == 1
    assert cleaned[0]["speaker"] == "Ana Silva"
    assert cleaned[0]["text"] == "First part. Second part."


def test_merge_consecutive_turns_never_merges_null_speakers():
    turns = [
        {"start": 0.0, "speaker": None, "text": "First unlabelled turn."},
        {"start": 1.0, "speaker": None, "text": "Second unlabelled turn."},
        {"start": 2.0, "speaker": None, "text": "Third unlabelled turn."},
    ]

    merged = scribe_common.merge_consecutive_turns(turns)

    assert len(merged) == 3
    assert [t["text"] for t in merged] == [
        "First unlabelled turn.",
        "Second unlabelled turn.",
        "Third unlabelled turn.",
    ]


def test_merge_consecutive_turns_still_merges_named_runs_around_null_speakers():
    turns = [
        {"start": 0.0, "speaker": "Ana Silva", "text": "Hello."},
        {"start": 1.0, "speaker": "Ana Silva", "text": "Let's begin."},
        {"start": 2.0, "speaker": None, "text": "inaudible"},
        {"start": 3.0, "speaker": None, "text": "more inaudible"},
        {"start": 4.0, "speaker": "Bruno Costa", "text": "Sounds good."},
        {"start": 5.0, "speaker": "Bruno Costa", "text": "Let's continue."},
    ]

    merged = scribe_common.merge_consecutive_turns(turns)

    assert len(merged) == 4
    assert merged[0]["speaker"] == "Ana Silva"
    assert merged[0]["text"] == "Hello. Let's begin."
    assert merged[1]["speaker"] is None
    assert merged[1]["text"] == "inaudible"
    assert merged[2]["speaker"] is None
    assert merged[2]["text"] == "more inaudible"
    assert merged[3]["speaker"] == "Bruno Costa"
    assert merged[3]["text"] == "Sounds good. Let's continue."
