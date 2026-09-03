"""Behaviour tests for teams_transcript.py, exercised through the CLI."""
import json


def test_parses_cues_merges_consecutive_speakers_and_uses_occurrence_window(
    run_script, fixtures_dir, tmp_path
):
    out_path = tmp_path / "out.json"
    result = run_script(
        "teams_transcript.py",
        str(fixtures_dir / "teams_raw_basic.json"),
        "-o",
        str(out_path),
        "--event-id",
        "evt-123",
        "--transcript-uri",
        "meeting-transcript:///events/evt-123",
    )

    assert result.returncode == 0, result.stderr
    normalized = json.loads(out_path.read_text(encoding="utf-8"))

    assert normalized["schema"] == "scribe.transcript/1"
    assert normalized["source"] == "teams"
    assert normalized["title"] == "Architecture Advisory Board"

    # Series-start trap: transcripts[0].createdDateTime, never meeting.startDateTime.
    assert normalized["start"] == "2026-08-26T20:01:12Z"
    assert normalized["start"] != "2026-01-05T20:00:00Z"
    assert normalized["end"] == "2026-08-26T21:26:40Z"

    assert normalized["speakers"] == ["Ana Silva", "Bruno Costa"]

    # 8 cues, alternating Ana/Bruno with consecutive-speaker runs of 2, merge to 5 turns.
    turns = normalized["turns"]
    assert len(turns) == 5
    assert [t["speaker"] for t in turns] == [
        "Ana Silva",
        "Bruno Costa",
        "Ana Silva",
        "Bruno Costa",
        "Ana Silva",
    ]
    assert turns[0]["text"] == "Hi everyone, let's start the meeting."
    assert turns[1]["text"] == "Sounds good. I have the agenda ready."
    assert turns[3]["text"] == "First topic is SC compliance. We need to review it."

    # start is seconds since the first cue, not wall-clock.
    assert turns[0]["start"] == 0.0
    assert turns[1]["start"] == 5.5

    assert normalized["provenance"]["cue_count"] == 8
    assert normalized["provenance"]["teams_event_id"] == "evt-123"
    assert normalized["provenance"]["transcript_uri"] == "meeting-transcript:///events/evt-123"

    assert "occurrence 2026-08-26T20:01:12Z -> 2026-08-26T21:26:40Z" in result.stderr
    assert "8 cues, 5 turns, 2 speakers" in result.stderr
    assert "speakers: Ana Silva, Bruno Costa" in result.stderr


def test_accepts_lf_lf_block_separator(run_script, fixtures_dir, tmp_path):
    out_path = tmp_path / "out.json"
    result = run_script(
        "teams_transcript.py",
        str(fixtures_dir / "teams_raw_lf_separator.json"),
        "-o",
        str(out_path),
    )

    assert result.returncode == 0, result.stderr
    normalized = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(normalized["turns"]) == 5
    assert normalized["turns"][0]["text"] == "Hi everyone, let's start the meeting."


def test_provenance_omits_optional_keys_when_not_given(run_script, fixtures_dir, tmp_path):
    out_path = tmp_path / "out.json"
    result = run_script(
        "teams_transcript.py",
        str(fixtures_dir / "teams_raw_basic.json"),
        "-o",
        str(out_path),
    )

    assert result.returncode == 0, result.stderr
    normalized = json.loads(out_path.read_text(encoding="utf-8"))
    assert "teams_event_id" not in normalized["provenance"]
    assert "transcript_uri" not in normalized["provenance"]
    assert normalized["provenance"]["cue_count"] == 8


def test_multiple_transcripts_exits_nonzero_without_guessing(run_script, fixtures_dir, tmp_path):
    out_path = tmp_path / "out.json"
    result = run_script(
        "teams_transcript.py",
        str(fixtures_dir / "teams_raw_two_transcripts.json"),
        "-o",
        str(out_path),
    )

    assert result.returncode != 0
    assert "?start=" in result.stderr
    assert "series" in result.stderr.lower()
    assert not out_path.exists()


def test_empty_transcripts_exits_nonzero(run_script, fixtures_dir, tmp_path):
    out_path = tmp_path / "out.json"
    result = run_script(
        "teams_transcript.py",
        str(fixtures_dir / "teams_raw_empty_transcripts.json"),
        "-o",
        str(out_path),
    )

    assert result.returncode != 0
    assert "not recorded" in result.stderr
    assert not out_path.exists()


def test_calendar_slot_from_transcript_uri_wins_over_first_cue_time(run_script, fixtures_dir, tmp_path):
    out = tmp_path / "out.json"
    uri = "meeting-transcript:///events/TOKEN?start=2026-08-26T20%3A00%3A00.000Z&end=2026-08-26T21%3A00%3A00.000Z"
    result = run_script(
        "teams_transcript.py", str(fixtures_dir / "teams_raw_basic.json"), "-o", str(out), "--transcript-uri", uri
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["start"] == "2026-08-26T20:00:00.000Z"
    assert data["end"] == data["provenance"]["transcript_end"]
    assert data["provenance"]["transcript_start"] != data["start"]
    assert data["provenance"]["transcript_uri"] == uri


def test_merge_joins_restarted_segments_with_continuous_clock(run_script, fixtures_dir, tmp_path):
    out = tmp_path / "out.json"
    result = run_script(
        "teams_transcript.py", str(fixtures_dir / "teams_raw_two_transcripts.json"), "-o", str(out), "--merge"
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["provenance"]["merged_segments"] == 2
    starts = [turn["start"] for turn in data["turns"]]
    assert starts == sorted(starts)
    assert starts[-1] > 60  # the second segment is shifted by the real gap, not restarted at zero
