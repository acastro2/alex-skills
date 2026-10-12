"""The optional "Portfolio movement" panel in render_page.py.

Pins four behaviours: the shipped example renders the panel in its slot, a page without
moves carries no empty section, and a bad stage or a non-move (from == to) is a named
error that says which key is wrong. Renders through the CLI, like test_invariants.py,
so the tests see exactly what a weekly run sees.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
RENDERER = SKILL_DIR / "references" / "render_page.py"
EXAMPLE = SKILL_DIR / "references" / "example-content.json"


def example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def render(tmp_path: Path, content: dict) -> subprocess.CompletedProcess:
    src = tmp_path / "content.json"
    src.write_text(json.dumps(content), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(RENDERER), str(src), str(tmp_path / "canvas.json")],
        capture_output=True, text=True, check=False,
    )


def page_text(tmp_path: Path, content: dict) -> str:
    run = render(tmp_path, content)
    assert run.returncode == 0, f"render failed:\n{run.stderr}"
    check = subprocess.run(
        [sys.executable, str(RENDERER), "--check-only", str(tmp_path / "canvas.json")],
        capture_output=True, text=True, check=False,
    )
    assert check.returncode == 0, f"--check-only rejected the canvas:\n{check.stderr}"
    text = subprocess.run(
        [sys.executable, str(RENDERER), "--text", str(tmp_path / "canvas.json")],
        capture_output=True, text=True, check=False,
    )
    assert text.returncode == 0, text.stderr
    return text.stdout


def test_example_renders_the_panel_between_open_questions_and_artifacts(tmp_path: Path) -> None:
    content = example()
    moves = content.get("portfolio_moves") or []
    assert len(moves) >= 2, "example-content.json must exercise portfolio_moves"
    text = page_text(tmp_path, content)
    assert "Portfolio movement" in text
    for m in moves:
        assert m["title"] in text, f"move {m['title']!r} missing from the page text"
    order = [text.index(h) for h in ("Open questions and risks", "Portfolio movement", "Artifacts referenced")]
    assert order == sorted(order), "Portfolio movement is out of its slot"


def test_linked_title_opens_in_a_new_tab_and_chips_drop_the_sort_prefix(tmp_path: Path) -> None:
    content = example()
    content["portfolio_moves"] = [
        {"title": "Linked row", "from": "1. Exploring", "to": "2. Committed", "url": "https://example.invalid/row"},
        {"title": "Plain row", "from": "4. Delivered", "to": "5. Stopped"},
    ]
    assert render(tmp_path, content).returncode == 0
    html = json.loads((tmp_path / "canvas.json").read_text(encoding="utf-8"))[0]["innerHTML"]
    panel = html.split("Portfolio movement", 1)[1].split("Artifacts referenced", 1)[0]
    assert 'href="https://example.invalid/row" target="_blank" rel="noopener noreferrer"' in panel
    assert panel.count("<a ") == 1, "only the move with a url gets a link"
    for label in (">Exploring<", ">Committed<", ">Delivered<", ">Stopped<"):
        assert label in panel, f"chip {label} missing"
    assert "2. Committed" not in panel
    # Solid chips are light-on-dark and need a print theme class; outline chips do not.
    assert panel.count('class="aw-avatar"') == 2


@pytest.mark.parametrize("moves", ["absent", []], ids=["absent", "empty"])
def test_no_moves_renders_no_section(tmp_path: Path, moves) -> None:
    content = example()
    if moves == "absent":
        content.pop("portfolio_moves", None)
    else:
        content["portfolio_moves"] = moves
    text = page_text(tmp_path, content)
    assert "Portfolio movement" not in text
    assert "Artifacts referenced" in text


GOOD = {"title": "Row", "from": "1. Exploring", "to": "2. Committed"}


@pytest.mark.parametrize(
    ("moves", "expected"),
    [
        ([dict(GOOD, to="2. In Analysis")], "portfolio_moves[0].to must be one of"),
        ([GOOD, dict(GOOD, **{"from": "Exploring"})], "portfolio_moves[1].from must be one of"),
        ([GOOD, dict(GOOD, to="1. Exploring")], "portfolio_moves[1].from and portfolio_moves[1].to are both"),
        ([{k: v for k, v in GOOD.items() if k != "title"}], "portfolio_moves[0] is missing required key 'title'"),
        ([dict(GOOD, url="")], "portfolio_moves[0].url is empty"),
        ([GOOD] * 9, "portfolio_moves has 9"),
    ],
    ids=["bad-stage-to", "bad-stage-from", "from-equals-to", "missing-title", "empty-url", "over-8"],
)
def test_bad_moves_are_named_errors(tmp_path: Path, moves, expected: str) -> None:
    content = example()
    content["portfolio_moves"] = copy.deepcopy(moves)
    run = render(tmp_path, content)
    assert run.returncode == 1
    assert "RENDER FAILED" in run.stderr and expected in run.stderr, run.stderr
