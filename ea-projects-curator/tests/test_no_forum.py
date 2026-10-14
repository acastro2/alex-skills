"""The no_forum mode and the blue info band in render_page.py (Alex, 2026-10-12).

A week with no forum renders the blue NO FORUM THIS WEEK band with the next agenda, and no forum
sections. Pins: the page renders without any forum key, a forum key on a no_forum page is a named
error (a no-forum week has no forum record to fill), and the delivery panel still renders.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
RENDERER = SKILL_DIR / "references" / "render_page.py"
EXAMPLE = SKILL_DIR / "references" / "example-content.json"
FORUM_KEYS = ("objective", "outcome", "tldr", "decisions", "actions", "topics",
              "open_questions", "speakers", "speakers_source", "artifacts")


def no_forum_page() -> dict:
    c = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for key in FORUM_KEYS:
        c.pop(key, None)
    c["no_forum"] = {
        "headline": "No forum met on October 7.",
        "text": "The next forum is Wednesday, October 14, 3:00 to 4:00pm Central.",
        "agenda": [{"title": "Central source of truth for secrets", "url": "https://example.com/rfc",
                    "note": "Decision."}],
    }
    return c


def render(tmp_path: Path, content: dict) -> subprocess.CompletedProcess:
    src = tmp_path / "content.json"
    src.write_text(json.dumps(content), encoding="utf-8")
    return subprocess.run([sys.executable, str(RENDERER), str(src), str(tmp_path / "canvas.json")],
                          capture_output=True, text=True, check=False)


def text_of(tmp_path: Path) -> str:
    run = subprocess.run([sys.executable, str(RENDERER), "--text", str(tmp_path / "canvas.json")],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    return run.stdout


def test_no_forum_page_renders_the_line_and_no_forum_sections(tmp_path):
    run = render(tmp_path, no_forum_page())
    assert run.returncode == 0, run.stderr
    text = text_of(tmp_path)
    assert "NO FORUM THIS WEEK" in text
    assert "No forum met on October 7." in text
    assert "Agenda" in text and "Central source of truth for secrets" in text
    for heading in ("Objective", "Decisions made", "Action items", "Topics discussed",
                    "Spoke in this session"):
        assert heading not in text
    assert "DELIVERED BY ENTERPRISE ARCHITECTURE" in text


def test_forum_key_on_a_no_forum_page_is_a_named_error(tmp_path):
    c = no_forum_page()
    c["decisions"] = [{"text": "x", "rationale": "y", "owner": "z"}]
    run = render(tmp_path, c)
    assert run.returncode != 0
    assert "decisions is set on a no_forum page" in run.stderr


def test_blank_no_forum_line_is_refused(tmp_path):
    c = no_forum_page()
    c["no_forum"]["headline"] = ""
    run = render(tmp_path, c)
    assert run.returncode != 0
    assert "no_forum.headline" in run.stderr


def test_agenda_item_needs_a_link(tmp_path):
    c = no_forum_page()
    c["no_forum"]["agenda"] = [{"title": "Item with no link"}]
    run = render(tmp_path, c)
    assert run.returncode != 0
    assert "no_forum.agenda[0]" in run.stderr


def test_info_tone_renders_the_navy_chip_with_a_print_class(tmp_path):
    run = render(tmp_path, no_forum_page())
    assert run.returncode == 0, run.stderr
    canvas = (tmp_path / "canvas.json").read_text(encoding="utf-8")
    assert "aw-infolabel" in canvas and "#183A63" in canvas
    assert "&#9888;" not in canvas.split("aw-infolabel", 1)[1][:400]
