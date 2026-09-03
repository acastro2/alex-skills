"""Behaviour tests for write_note.py, exercised through the CLI."""
from pathlib import Path


def _note_path(vault):
    return vault / "Scribe" / "Meetings" / "Transcripts" / "2026-08-26 1501 Architecture Advisory Board.md"


def test_builds_expected_path_and_frontmatter(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
        "--glossary",
        str(fixtures_dir / "glossary.md"),
        "--summary-file",
        str(fixtures_dir / "summary.md"),
        "--attendees",
        "Ana Silva,Bruno Costa,Carla Reyes",
        "--tags",
        "project/aab,quarterly",
    )

    assert result.returncode == 0, result.stderr
    expected_path = _note_path(vault)
    assert result.stdout.strip() == str(expected_path)
    assert expected_path.exists()

    content = expected_path.read_text(encoding="utf-8")

    assert 'type: transcript' in content
    assert 'title: "Architecture Advisory Board"' in content
    assert 'date: 2026-08-26T20:01:12Z' in content
    assert 'end: 2026-08-26T21:26:40Z' in content
    assert 'duration_min: 85' in content
    assert 'source: teams' in content
    assert 'speakers: ["Ana Silva", "Bruno Costa"]' in content
    assert 'attendees: ["Ana Silva", "Bruno Costa", "Carla Reyes"]' in content
    assert 'tags: ["scribe", "meeting", "source/teams", "project/aab", "quarterly"]' in content
    assert 'confidential: true' in content
    assert 'provenance:' in content
    assert '  teams_event_id: "AAMkAGI1AAA="' in content
    assert '  cue_count: 8' in content
    assert 'cleaned: true' in content
    assert 'glossary_replacements: 1' in content
    assert 'scribe_schema: scribe.transcript/1' in content
    assert content.startswith("---\n")
    assert "# Architecture Advisory Board" in content


def test_glossary_replacement_is_case_insensitive_and_word_bounded(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
        "--glossary",
        str(fixtures_dir / "glossary.md"),
    )

    assert result.returncode == 0, result.stderr
    content = _note_path(vault).read_text(encoding="utf-8")

    # "SC" => "SE" must fire on the standalone word but never inside "SCOPE".
    assert "The SE compliance topic is first." in content
    assert "SCOPE document" in content
    assert "SEOPE" not in content
    assert "glossary_replacements: 1" in content


def test_fillers_and_duplicate_words_are_cleaned_and_empty_turns_dropped(
    run_script, fixtures_dir, tmp_path
):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
    )

    assert result.returncode == 0, result.stderr
    content = _note_path(vault).read_text(encoding="utf-8")

    assert "Hi everyone, let's start the meeting." in content
    assert " um " not in content
    assert "The the" not in content
    # The lone filler-only turn ("uh") is dropped, then the Bruno turns on
    # either side of it merge into one: 3 turn paragraphs remain, not 4.
    assert content.count("**[") == 3
    assert "**[00:00:11] Ana Silva:** uh" not in content
    assert "We need to review the SCOPE document too. Let's move to the next item." in content
    # No glossary passed, so no replacements happened.
    assert "glossary_replacements: 0" in content


def test_empty_turn_no_longer_keeps_same_speaker_turns_apart(run_script, fixtures_dir, tmp_path):
    """Regression test for clean_turns order: drop-empty must run before
    re-merge, so a filler-only turn between two same-speaker turns does not
    keep them apart."""
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
    )

    assert result.returncode == 0, result.stderr
    content = _note_path(vault).read_text(encoding="utf-8")

    # Bruno's three original turns (agenda item, SCOPE review, next item), split
    # by Ana's now-dropped "uh", must all land in a single merged paragraph.
    bruno_lines = [line for line in content.splitlines() if line.startswith("**[") and "Bruno Costa" in line]
    assert len(bruno_lines) == 1
    assert "Sounds good." in bruno_lines[0]
    assert "SCOPE document" in bruno_lines[0]
    assert "next item" in bruno_lines[0]


def test_summary_file_inserted_verbatim_before_transcript_section(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
        "--summary-file",
        str(fixtures_dir / "summary.md"),
    )

    assert result.returncode == 0, result.stderr
    content = _note_path(vault).read_text(encoding="utf-8")

    summary_text = (fixtures_dir / "summary.md").read_text(encoding="utf-8").rstrip()
    assert summary_text in content
    assert content.index(summary_text) < content.index("## Transcript")
    assert 'description: "The board reviewed the SE compliance roadmap and agreed on next steps."' in content


def test_description_skips_heading_and_uses_first_sentence(run_script, fixtures_dir, tmp_path):
    """summary.md starts with '## Summary' then a sentence; description must be
    the sentence, not the heading."""
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
        "--summary-file",
        str(fixtures_dir / "summary.md"),
    )

    assert result.returncode == 0, result.stderr
    content = _note_path(vault).read_text(encoding="utf-8")
    assert 'description: "The board reviewed the SE compliance roadmap and agreed on next steps."' in content
    assert 'description: "## Summary"' not in content


def test_description_flag_overrides_summary_derived_description(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
        "--summary-file",
        str(fixtures_dir / "summary.md"),
        "--description",
        "Custom override description",
    )

    assert result.returncode == 0, result.stderr
    content = _note_path(vault).read_text(encoding="utf-8")
    assert 'description: "Custom override description"' in content
    assert 'description: "The board reviewed the SE compliance roadmap and agreed on next steps."' not in content


def test_description_falls_back_when_no_summary_file(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
    )

    assert result.returncode == 0, result.stderr
    content = _note_path(vault).read_text(encoding="utf-8")
    assert 'description: "Meeting transcript (teams)"' in content


def test_refuses_to_overwrite_without_force(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    first = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
    )
    assert first.returncode == 0, first.stderr
    note_path = _note_path(vault)
    original_mtime = note_path.stat().st_mtime_ns

    second = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
    )
    assert second.returncode != 0
    assert str(note_path) in second.stderr
    assert note_path.stat().st_mtime_ns == original_mtime

    third = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
        "--force",
    )
    assert third.returncode == 0, third.stderr


def test_dry_run_writes_nothing(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_basic.json"),
        "--vault",
        str(vault),
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert "# Architecture Advisory Board" in result.stdout
    assert not vault.exists()


def test_null_title_falls_back_to_untitled_meeting(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_null_title.json"),
        "--vault",
        str(vault),
    )

    assert result.returncode == 0, result.stderr
    expected_path = vault / "Scribe" / "Meetings" / "Transcripts" / "2026-08-26 1501 Untitled meeting.md"
    assert expected_path.exists()
    content = expected_path.read_text(encoding="utf-8")
    assert 'title: "Untitled meeting"' in content
    assert "# Untitled meeting" in content
    assert "end:" not in content
    assert "duration_min:" not in content


def test_null_speaker_turns_stay_separate_and_render_without_a_speaker_name(
    run_script, fixtures_dir, tmp_path
):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_hidock_null_speakers.json"),
        "--vault",
        str(vault),
    )

    assert result.returncode == 0, result.stderr
    expected_path = vault / "Scribe" / "Meetings" / "Transcripts" / "2026-08-26 1501 Unlabelled HiDock Recording.md"
    assert expected_path.exists()
    content = expected_path.read_text(encoding="utf-8")

    assert 'source: hidock' in content
    assert 'speakers: []' in content
    # Three null-speaker turns never merge, and none carries a speaker name/colon.
    assert content.count("**[") == 3
    assert "**[00:00:00]** First unlabelled turn." in content
    assert "**[00:00:03]** Second unlabelled turn." in content
    assert "**[00:00:06]** Third unlabelled turn." in content


def test_mixed_speakers_still_merges_named_runs_around_null_turns(run_script, fixtures_dir, tmp_path):
    vault = tmp_path / "vault"
    result = run_script(
        "write_note.py",
        str(fixtures_dir / "transcript_mixed_speakers.json"),
        "--vault",
        str(vault),
    )

    assert result.returncode == 0, result.stderr
    expected_path = vault / "Scribe" / "Meetings" / "Transcripts" / "2026-08-26 1501 Partly Labelled Recording.md"
    assert expected_path.exists()
    content = expected_path.read_text(encoding="utf-8")

    assert content.count("**[") == 4
    assert "**[00:00:00] Ana Silva:** Hello. Let's begin." in content
    assert "**[00:00:02]** inaudible" in content
    assert "**[00:00:03]** more inaudible" in content
    assert "**[00:00:04] Bruno Costa:** Sounds good. Let's continue." in content


def test_title_flag_overrides_transcript_title_in_heading_and_filename(fixtures_dir, tmp_path, run_script):
    result = run_script(
        "write_note.py", str(fixtures_dir / "transcript_null_title.json"),
        "--vault", str(tmp_path), "--title", "Call with Ana about SmartACH",
    )
    assert result.returncode == 0, result.stderr
    path = Path(result.stdout.strip())
    assert path.name.endswith(" Call with Ana about SmartACH.md")
    text = path.read_text(encoding="utf-8")
    assert 'title: "Call with Ana about SmartACH"' in text
    assert "# Call with Ana about SmartACH" in text
