"""Tests for Bard's state file.

The state file is the only thing that stops a sweep from redoing work, so every rule here is
one of the ways a sweep silently repeats: a watermark that moves back, a rounded day
boundary, a seen-set that loses a note, a write that leaves the old file in place.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "state.py"
spec = importlib.util.spec_from_file_location("bard_state", SCRIPT)
state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state_module)

StateError = state_module.StateError


def test_missing_file_reads_as_defaults(tmp_path: Path) -> None:
    state = state_module.load(tmp_path / "missing.json")
    assert state == {"last_run": None, "watermark": None, "scribe_seen": []}


def test_malformed_file_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json")
    with pytest.raises(StateError, match="not readable JSON"):
        state_module.load(path)


def test_record_run_writes_all_three_keys(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = state_module.record_run(path, "2026-10-25T15:00:00Z", ["Scribe/A.md"], now="2026-10-25T18:00:00+00:00")
    assert state["watermark"] == "2026-10-25T15:00:00Z"
    assert state["last_run"] == "2026-10-25T18:00:00+00:00"
    assert state["scribe_seen"] == ["Scribe/A.md"]
    assert json.loads(path.read_text()) == state


def test_watermark_cannot_move_backwards(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state_module.record_run(path, "2026-10-25T15:00:00Z")
    before = path.read_text()
    with pytest.raises(StateError, match="never moves it back"):
        state_module.record_run(path, "2026-10-24T09:00:00Z")
    assert path.read_text() == before, "a refused run must not touch the file"


def test_rounded_day_boundary_is_refused(tmp_path: Path) -> None:
    with pytest.raises(StateError, match="rounded day boundary"):
        state_module.record_run(tmp_path / "state.json", "2026-10-25T00:00:00Z")


def test_date_only_watermark_is_refused(tmp_path: Path) -> None:
    with pytest.raises(StateError, match="date without a time"):
        state_module.record_run(tmp_path / "state.json", "2026-10-25")


def test_watermark_needs_a_timezone(tmp_path: Path) -> None:
    with pytest.raises(StateError, match="needs a timezone"):
        state_module.record_run(tmp_path / "state.json", "2026-10-25T15:00:00")


def test_same_watermark_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state_module.record_run(path, "2026-10-25T15:00:00Z")
    state = state_module.record_run(path, "2026-10-25T15:00:00Z")
    assert state["watermark"] == "2026-10-25T15:00:00Z"


def test_scribe_seen_only_grows_and_does_not_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state_module.record_run(path, "2026-10-24T15:00:00Z", ["Scribe/A.md", "Scribe/B.md"])
    state = state_module.record_run(path, "2026-10-25T15:00:00Z", ["Scribe/B.md", "Scribe/C.md"])
    assert state["scribe_seen"] == ["Scribe/A.md", "Scribe/B.md", "Scribe/C.md"]


def test_seen_helper_returns_a_set(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state_module.record_run(path, "2026-10-25T15:00:00Z", ["Scribe/A.md"])
    assert state_module.seen(path) == {"Scribe/A.md"}


def test_write_is_atomic(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state_module.record_run(path, "2026-10-25T15:00:00Z", ["Scribe/A.md"])
    assert not (tmp_path / "state.json.tmp").exists()


def test_cli_show_and_record(tmp_path: Path, capsys) -> None:
    path = tmp_path / "state.json"
    code = state_module.main(["record", str(path), "--watermark", "2026-10-25T15:00:00Z", "--seen", "Scribe/A.md"])
    assert code == 0
    first = json.loads(capsys.readouterr().out)
    assert first["scribe_seen"] == ["Scribe/A.md"]

    assert state_module.main(["show", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == first


def test_cli_reports_a_refusal_with_exit_one(tmp_path: Path, capsys) -> None:
    path = tmp_path / "state.json"
    code = state_module.main(["record", str(path), "--watermark", "2026-10-25T00:00:00Z"])
    assert code == 1
    assert "STATE FAILED" in capsys.readouterr().err
    assert not path.exists(), "a refused first run must not create the file"
