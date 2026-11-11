"""The collector's counting rules: the week window, which board lines count, and which notes
fall inside the week."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import collect  # noqa: E402

WED = dt.date(2026, 11, 11)
WINDOW = (dt.date(2026, 11, 9), dt.date(2026, 11, 13))

BOARD = """- [ ] my own line above the marker ⏫
<!-- BARD:START — bard owns everything below this line. -->
# BARD List
#### 👥 Personal
- [ ] 👥 Pack the old laptop `(x)` 🔺
- [x] 👥 Personal thing done `(x)` 🔼 ✅ 2026-11-10
## Open
### 🔥 This week
- [ ] 🔐 Rotate the token `(slack:2026-11-11)` 🔺
### ⏳ Waiting on others
- [ ] 🐙 Admin access with the access team `(slack:2026-11-11)` 🔼
## Done
- [x] ☁️ Shipped the thing `(abc)` ⏫ ✅ 2026-11-12
- [x] ☁️ Last week's thing `(abc)` ⏫ ✅ 2026-11-06
"""


def test_week_window_midweek_and_weekend() -> None:
    assert collect.week_window(WED) == WINDOW
    assert collect.week_window(dt.date(2026, 11, 9)) == WINDOW
    assert collect.week_window(dt.date(2026, 11, 15)) == WINDOW  # Sunday reports the week that ended
    assert collect.iso_week_label(WINDOW[0]) == "2026-W46"


def test_board_reads_below_marker_skips_personal_and_old_done() -> None:
    board = collect.parse_board(BOARD, WINDOW, ["Personal"])
    assert [o["line"].split()[0] for o in board["open"]] == ["🔐", "🐙"]
    assert board["open"][0]["horizon"] == "🔥 This week" and board["open"][0]["priority"] == "🔺"
    assert board["open"][1]["horizon"] == "⏳ Waiting on others"
    assert [d["date"] for d in board["done"]] == ["2026-11-12"]


def test_exclusion_is_a_whole_word_and_covers_sub_headings() -> None:
    text = (
        "#### 👥 Personal\n##### Move\n- [ ] 👥 Book the movers 🔼\n"
        "### 📅 Personalization rollout\n- [ ] ☁️ Ship the flag ⏫\n"
    )
    board = collect.parse_board(text, WINDOW, ["Personal"])
    assert [o["line"] for o in board["open"]] == ["☁️ Ship the flag ⏫"]


def test_personal_tag_is_dropped_from_done_and_archive() -> None:
    done = "## Done\n- [x] 👥 Pack the laptop #personal `(x)` 🔺 ✅ 2026-11-10\n- [x] 👥 Send the plan `(x)` ⏫ ✅ 2026-11-10\n"
    assert [d["line"] for d in collect.parse_board(done, WINDOW, ["Personal"])["done"]] == ["👥 Send the plan `(x)` ⏫ ✅ 2026-11-10"]
    archive = "- [x] 👥 Remove my files #personal ⏫ ✅ 2026-11-11\n- [x] ☁️ Ship it ⏫ ✅ 2026-11-11\n"
    assert [d["line"] for d in collect.parse_archive(archive, WINDOW)] == ["☁️ Ship it ⏫ ✅ 2026-11-11"]


def pr(url: str, state: str, closed: str = "") -> dict:
    return {"repository": {"nameWithOwner": "o/r"}, "number": 1, "title": url, "state": state,
            "url": url, "closedAt": closed or "0001-01-01T00:00:00Z"}


def test_prs_keep_open_and_closed_this_week_only() -> None:
    raw = [pr("open", "open"), pr("merged-now", "merged", "2026-11-12T10:00:00Z"),
           pr("merged-sept", "merged", "2026-09-03T10:00:00Z"), pr("dropped", "closed", "2026-11-10T10:00:00Z")]
    kept = collect.select_prs(raw, WINDOW)
    assert [(p["title"], p["state"], p["closed"]) for p in kept] == [
        ("open", "open", None), ("merged-now", "merged", "2026-11-12"), ("dropped", "closed", "2026-11-10")]


def test_pr_search_reports_a_full_page_as_truncated() -> None:
    class Done:
        returncode, stderr = 0, ""
        def __init__(self, n: int) -> None:
            self.stdout = json.dumps([pr(f"u{i}", "open") for i in range(n)])
    def run(cmd, **_):
        full = "--author" in cmd and "--updated=2026-11-09..2026-11-13" in cmd
        return Done(collect.PR_LIMIT if full else 3)
    out = collect.github_prs(WINDOW, [], run=run)
    assert out["truncated"] == ["authored --updated"]


def test_pr_merged_this_week_counts_even_if_updated_later() -> None:
    class Done:
        returncode, stderr = 0, ""
        def __init__(self, rows: list[dict]) -> None:
            self.stdout = json.dumps(rows)
    late = pr("merged-fri", "merged", "2026-11-13T20:00:00Z")
    def run(cmd, **_):
        merged_search = "--author" in cmd and "--merged-at=2026-11-09..2026-11-13" in cmd
        return Done([late] if merged_search else [])
    out = collect.github_prs(WINDOW, [], run=run)
    assert [p["title"] for p in out["authored"]] == ["merged-fri"]


def test_bard_fresh_compares_with_the_real_day_not_the_report_week(tmp_path: Path, capsys) -> None:
    (tmp_path / "Bard").mkdir()
    (tmp_path / "Todo.md").write_text(BOARD)
    now = dt.datetime.now(collect.TZ).isoformat(timespec="minutes")
    (tmp_path / "Bard" / ".bard-state.json").write_text(json.dumps({"last_run": now}))
    assert collect.main(["--vault", str(tmp_path), "--date", "2026-10-28", "--no-github"]) == 0
    assert json.loads(capsys.readouterr().out)["bard_fresh"] is True


def test_archive_counts_only_the_window() -> None:
    text = "- [x] a ⏫ ✅ 2026-11-09\n- [x] b ⏫ ✅ 2026-11-14\n- [ ] c 🔼\n"
    assert [d["line"] for d in collect.parse_archive(text, WINDOW)] == ["a ⏫ ✅ 2026-11-09"]


def test_note_day_uses_chicago_time() -> None:
    assert collect.note_day("2026-11-14T03:00:00Z") == dt.date(2026, 11, 13)  # Friday evening in Chicago
    assert collect.note_day("2026-11-11T09:08:00-06:00") == WED
    assert collect.note_day("not a date") is None


def test_bard_notes_in_window_skip_hubs(tmp_path: Path) -> None:
    def note(name: str, kind: str, ts: str) -> None:
        (tmp_path / f"{name}.md").write_text(f'---\ntype: {kind}\ntitle: {name}\ntimestamp: {ts}\nup: "[[Hub]]"\n---\nbody\n')
    note("In", "decision", "2026-11-10T15:00:00Z")
    note("Old", "lesson", "2026-11-05T15:00:00Z")
    note("Hub", "hub", "2026-11-10T15:00:00Z")
    notes = collect.bard_notes(tmp_path, WINDOW)
    assert [n["title"] for n in notes] == ["In"]
    assert notes[0]["up"] == "[[Hub]]"
