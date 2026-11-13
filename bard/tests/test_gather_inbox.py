"""bard's view of the gather store: what is new, and what each source's last fetch said."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gather_inbox.py"
spec = importlib.util.spec_from_file_location("gather_inbox", SCRIPT)
inbox = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inbox)


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def raw(root: Path, rel: str, provenance: str = "verbatim") -> None:
    source = rel.split("/")[1]
    write(root / rel, {"source": source, "tool": "t", "args": {}, "run_id": "r", "fetched_at": "x",
                       "provenance": provenance, "content": "synthetic"})


def make_store(root: Path) -> None:
    raw(root, "raw/mail/2026-11-12/20261112T100000-aaaaaa-1.json")
    raw(root, "raw/mail/2026-11-13/20261113T100000-bbbbbb-1.json")
    raw(root, "raw/jira/2026-11-13/20261113T100000-bbbbbb-1.json")
    raw(root, "raw/slack/2026-11-13/20261113T110000-cccccc-1.json", provenance="model-copied")
    write(root / "ledger/20261112T100000-aaaaaa.json",
          {"run_id": "20261112T100000-aaaaaa", "sources": {"mail": "fetched 1 calls, 3 items", "jira": "fetched 6 calls, 4 items"}})
    write(root / "ledger/20261113T100000-bbbbbb.json",
          {"run_id": "20261113T100000-bbbbbb", "sources": {"mail": "error: claude exited 1", "teams_channels": "not fetched: x"}})
    write(root / "ledger/20261113T110000-cccccc.json",
          {"run_id": "20261113T110000-cccccc", "sources": {"slack": "fetched 1 calls, 2 items"}})


def test_lists_only_files_not_yet_seen_grouped_by_source(tmp_path: Path) -> None:
    make_store(tmp_path)
    out = inbox.listing(tmp_path, seen={"raw/mail/2026-11-12/20261112T100000-aaaaaa-1.json"})
    assert out["available"] is True
    assert out["unseen"] == {
        "jira": ["raw/jira/2026-11-13/20261113T100000-bbbbbb-1.json"],
        "mail": ["raw/mail/2026-11-13/20261113T100000-bbbbbb-1.json"],
        "slack": ["raw/slack/2026-11-13/20261113T110000-cccccc-1.json"],
    }


def test_the_latest_ledger_line_per_source_wins_so_a_failed_last_fetch_shows(tmp_path: Path) -> None:
    make_store(tmp_path)
    out = inbox.listing(tmp_path, seen=set())
    assert out["ledger"] == {
        "mail": "error: claude exited 1",
        "jira": "fetched 6 calls, 4 items",
        "teams_channels": "not fetched: x",
        "slack": "fetched 1 calls, 2 items",
    }
    # mail failed last, teams_channels was not built, and the rest never ran: all are gaps
    assert sorted(out["fallback"]) == ["calendar", "github", "mail", "sharepoint", "teams_channels",
                                       "teams_chats", "teams_mine"]


def test_a_source_gather_never_ran_is_a_gap_not_silence(tmp_path: Path) -> None:
    write(tmp_path / "ledger/20261113T100000-aaaaaa.json", {"sources": {"mail": "fetched 2 calls, 5 items"}})
    out = inbox.listing(tmp_path, seen=set())
    assert "mail" not in out["fallback"]
    assert {"teams_chats", "jira", "slack"} <= set(out["fallback"])


def test_model_copied_files_are_flagged_as_not_quotable(tmp_path: Path) -> None:
    make_store(tmp_path)
    out = inbox.listing(tmp_path, seen=set())
    assert out["model_copied"] == ["raw/slack/2026-11-13/20261113T110000-cccccc-1.json"]


def test_no_store_means_every_lane_falls_back(tmp_path: Path) -> None:
    out = inbox.listing(tmp_path / "missing", seen=set())
    assert out == {"available": False, "unseen": {}, "ledger": {}, "fallback": [], "model_copied": [],
                   "fetched_at": {}, "covered_from": {}}


def test_cli_reads_seen_from_the_bard_state_file(tmp_path: Path, capsys) -> None:
    store = tmp_path / "gather"
    make_store(store)
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"gather_seen": ["raw/mail/2026-11-12/20261112T100000-aaaaaa-1.json",
                                                 "raw/mail/2026-11-13/20261113T100000-bbbbbb-1.json"]}))
    assert inbox.main(["list", "--root", str(store), "--state", str(state)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "mail" not in out["unseen"]


def test_a_fetched_source_whose_last_run_is_older_than_max_age_is_a_gap(tmp_path: Path) -> None:
    write(tmp_path / "ledger/20261110T100000-aaaaaa.json",
          {"started_at": "2026-11-10T10:00:00+00:00", "sources": {"mail": "fetched 2 calls, 5 items"}})
    write(tmp_path / "ledger/20261113T090000-bbbbbb.json",
          {"started_at": "2026-11-13T09:00:00+00:00", "sources": {"jira": "fetched 6 calls, 4 items"}})
    from datetime import datetime, timezone
    out = inbox.listing(tmp_path, seen=set(), now=datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc), max_age_hours=24)
    assert "mail" in out["fallback"]
    assert "jira" not in out["fallback"]
    assert out["fetched_at"]["mail"] == "2026-11-10T10:00:00+00:00"


def test_a_source_whose_gather_history_starts_after_the_bard_watermark_is_a_gap(tmp_path: Path) -> None:
    # /code-review 2026-11-13: bard's watermark 14 days back, gather's first window only 7
    write(tmp_path / "ledger/20261113T090000-aaaaaa.json",
          {"started_at": "2026-11-13T09:00:00+00:00", "sources": {"mail": "fetched 2 calls, 5 items",
                                                                   "jira": "fetched 6 calls, 4 items"}})
    write(tmp_path / "state.json", {"cursors": {}, "covered_from": {"mail": "2026-11-06T09:00:00+00:00"}})
    out = inbox.listing(tmp_path, seen=set(), watermark="2026-10-30T09:00:00+00:00")
    assert "mail" in out["fallback"]
    assert "jira" not in out["fallback"], "snapshot sources hold every open item, so no history window"
    assert out["covered_from"]["mail"] == "2026-11-06T09:00:00+00:00"
    later = inbox.listing(tmp_path, seen=set(), watermark="2026-11-07T09:00:00+00:00")
    assert "mail" not in later["fallback"]


def test_a_window_source_with_no_covered_from_is_a_gap_when_a_watermark_is_given(tmp_path: Path) -> None:
    write(tmp_path / "ledger/20261113T090000-aaaaaa.json",
          {"started_at": "2026-11-13T09:00:00+00:00", "sources": {"mail": "fetched 2 calls, 5 items"}})
    out = inbox.listing(tmp_path, seen=set(), watermark="2026-11-07T09:00:00+00:00")
    assert "mail" in out["fallback"]


def test_cli_takes_the_watermark_from_the_bard_state(tmp_path: Path, capsys) -> None:
    store = tmp_path / "gather"
    write(store / "ledger/20261113T090000-aaaaaa.json",
          {"started_at": "2026-11-13T09:00:00+00:00", "sources": {"mail": "fetched 2 calls, 5 items"}})
    write(store / "state.json", {"covered_from": {"mail": "2026-11-06T09:00:00+00:00"}})
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"watermark": "2026-10-30T09:00:00+00:00", "gather_seen": []}))
    inbox.main(["list", "--root", str(store), "--state", str(state), "--max-age-hours", "100000"])
    assert "mail" in json.loads(capsys.readouterr().out)["fallback"]
