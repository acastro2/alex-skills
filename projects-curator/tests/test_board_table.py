"""The board adapter: read the board table from a wiki page's HTML, and write approved cell
changes back without touching any other byte. Seam: page HTML in, rows or new HTML out."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import board_table  # noqa: E402

PAGE = (Path(__file__).parent / "fixtures" / "board.html").read_text()
COLUMNS = ["Title", "Stage", "Execution Link"]


def test_read_finds_the_board_table_by_its_header_and_ignores_other_tables() -> None:
    rows = board_table.read_board(PAGE, COLUMNS)
    assert [r["Title"] for r in rows] == ["Code Search for Agents", "Self-Healing Agent"]
    assert rows[0]["Stage"] == "3. Delivering"
    assert rows[0]["Execution Link"] == {"text": "T-1", "href": "https://tracker.test/browse/T-1"}
    assert rows[1]["Execution Link"] == ""


def test_no_changes_returns_the_page_byte_for_byte() -> None:
    assert board_table.apply_changes(PAGE, COLUMNS, []) == PAGE


def test_one_cell_change_touches_only_that_cell_and_keeps_its_ids() -> None:
    change = [{"row": "Self-Healing Agent", "column": "Stage", "value": "2. Committed"}]
    out = board_table.apply_changes(PAGE, COLUMNS, change)
    assert out == PAGE.replace('<p data-local-id="c4">1. Exploring</p>', '<p data-local-id="c4">2. Committed</p>')


def test_a_link_value_renders_an_anchor_and_text_is_escaped() -> None:
    changes = [{"row": "Self-Healing Agent", "column": "Execution Link",
                "value": {"text": "T-9", "href": "https://tracker.test/browse/T-9?a=1&b=2"}},
               {"row": "Code Search for Agents", "column": "Stage", "value": "3. Delivering <beta> & more"}]
    out = board_table.apply_changes(PAGE, COLUMNS, changes)
    assert '<p data-local-id="c6"><a href="https://tracker.test/browse/T-9?a=1&amp;b=2">T-9</a></p>' in out
    assert '<p data-local-id="b4">3. Delivering &lt;beta&gt; &amp; more</p>' in out
    assert board_table.read_board(out, COLUMNS)[1]["Execution Link"]["href"] == "https://tracker.test/browse/T-9?a=1&b=2"


def test_a_new_row_is_appended_to_the_board_table_only() -> None:
    new = [{"new_row": {"Title": "Self-Service App Deploy", "Stage": "1. Exploring", "Execution Link": ""}}]
    out = board_table.apply_changes(PAGE, COLUMNS, new)
    rows = board_table.read_board(out, COLUMNS)
    assert [r["Title"] for r in rows][-1] == "Self-Service App Deploy"
    assert out.count("<tr>") == PAGE.count("<tr>") + 1
    assert out.split('<table data-local-id="t1"')[0] == PAGE.split('<table data-local-id="t1"')[0]
    assert out.endswith('<p data-local-id="p9">Footer.</p>\n')


@pytest.mark.parametrize("columns", [["Title", "Stage"], ["Title", "Stage", "Execution Link", "Sponsor"]])
def test_no_table_with_exactly_these_columns_fails_loudly(columns: list[str]) -> None:
    with pytest.raises(board_table.BoardError, match="no board table"):
        board_table.read_board(PAGE, columns)


@pytest.mark.parametrize("change", [
    {"row": "Nope", "column": "Stage", "value": "x"},
    {"row": "Self-Healing Agent", "column": "Sponsor", "value": "x"},
    {"new_row": {"Title": "Only a title"}},
    {"new_row": {"Title": "Self-Healing Agent", "Stage": "1. Exploring", "Execution Link": ""}},
])
def test_a_change_that_does_not_fit_the_board_fails_and_writes_nothing(change: dict) -> None:
    with pytest.raises(board_table.BoardError):
        board_table.apply_changes(PAGE, COLUMNS, [change])
