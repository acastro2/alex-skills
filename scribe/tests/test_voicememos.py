"""voicememos.py on a store built in the same Core Data shape as the real one."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pytest  # noqa: E402

import voicememos as vm  # noqa: E402


@pytest.fixture(autouse=True)
def _close_stores():
    yield
    while OPEN:
        OPEN.pop().close()

# 2026-11-12T15:42:07Z, the real memo's start, in Core Data seconds.
NOV12 = 816190927.0


OPEN: list[sqlite3.Connection] = []


def make_store(tmp_path: Path, rows: list[tuple]) -> Path:
    store = tmp_path / "Recordings"
    store.mkdir()
    con = sqlite3.connect(store / "CloudRecordings.db")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE ZCLOUDRECORDING (Z_PK INTEGER PRIMARY KEY, ZUNIQUEID TEXT, ZDATE REAL, "
                "ZDURATION REAL, ZCUSTOMLABEL TEXT, ZPATH TEXT, ZEVICTIONDATE REAL)")
    con.executemany("INSERT INTO ZCLOUDRECORDING (ZUNIQUEID, ZDATE, ZDURATION, ZCUSTOMLABEL, ZPATH, ZEVICTIONDATE) "
                    "VALUES (?,?,?,?,?,?)", rows)
    con.commit()  # rows stay in the -wal file until a checkpoint, like the live app
    OPEN.append(con)  # held open like the running app; a close would checkpoint mid-test
    for _, _, _, _, path, evicted in rows:
        if path and evicted is None:
            (store / path).write_bytes(b"m4a")
    return store


def test_core_data_dates_convert_to_utc() -> None:
    assert vm.core_data_to_iso(NOV12) == "2026-11-12T15:42:07Z"


def test_list_reads_wal_rows_and_flags_missing_audio(tmp_path: Path, capsys) -> None:
    store = make_store(tmp_path, [
        ("A", NOV12, 1669.0, "Weekly sync", "20261112 094207.m4a", None),
        ("B", NOV12 + 60, 120.0, "New Recording 3", "20261112 094307.m4a", 1.0),
        ("C", NOV12 + 120, 5.0, "too short", "c.m4a", None),
    ])
    assert vm.main(["list", "--json"], store=store) == 0
    memos = json.loads(capsys.readouterr().out)
    assert [m["id"] for m in memos] == ["A", "B"]
    assert memos[0]["title"] == "Weekly sync" and memos[0]["local"] is True
    assert memos[1]["title"] is None  # generic app label
    assert memos[1]["local"] is False and memos[1]["evicted"] is True


def test_since_filters_by_day(tmp_path: Path) -> None:
    memos = [vm.to_memo({"id": "A", "date": NOV12, "duration": 100, "label": "", "path": "a.m4a", "evicted": False}, tmp_path)]
    assert vm.select(memos, dt.date(2026, 11, 12), 30)
    assert not vm.select(memos, dt.date(2026, 11, 13), 30)


def test_live_store_is_never_written(tmp_path: Path) -> None:
    store = make_store(tmp_path, [("A", NOV12, 100.0, "x", "a.m4a", None)])
    before = {p.name: p.stat().st_mtime_ns for p in store.iterdir()}
    vm.main(["list"], store=store)
    assert {p.name: p.stat().st_mtime_ns for p in store.iterdir()} == before


def test_missing_store_exits_3(tmp_path: Path, capsys) -> None:
    assert vm.main(["list"], store=tmp_path / "nope") == 3
    assert "unreadable" in capsys.readouterr().err
