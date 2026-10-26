"""Tests for the page content contract, called directly on dicts.

These used to be impossible without rendering HTML and matching strings: the contract lived
inside `render_page.py` as `need()` calls. Now `validate()` takes a dict and raises a named
error, so a test states the rule it means.

The valid fixture is the shipped `example-content.json`, not a hand-written stub: a rule this
file does not know about still breaks the test.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "references"))

import content_schema  # noqa: E402
from content_schema import ContentError, validate  # noqa: E402

EXAMPLE = json.loads((SKILL_DIR / "references" / "example-content.json").read_text(encoding="utf-8"))


def week() -> dict:
    return copy.deepcopy(EXAMPLE)


def test_the_shipped_example_is_valid() -> None:
    assert validate(week()) is None


def test_missing_key_names_its_path() -> None:
    content = week()
    del content["decisions"][0]["rationale"]
    with pytest.raises(ContentError, match=r"decisions\[0\] is missing required key 'rationale'"):
        validate(content)


def test_missing_top_level_key_is_named() -> None:
    content = week()
    del content["tldr"]
    with pytest.raises(ContentError, match="content is missing required key 'tldr'"):
        validate(content)


def test_exec_summary_needs_the_band() -> None:
    content = week()
    content["exec_summary"]["points"] = content["exec_summary"]["points"][:2]
    with pytest.raises(ContentError, match="needs at least 3 item"):
        validate(content)


def test_exec_summary_rejects_too_many_points() -> None:
    content = week()
    content["exec_summary"]["points"] = content["exec_summary"]["points"] * 2
    with pytest.raises(ContentError, match="do not widen the band"):
        validate(content)


def test_band_headline_has_a_ceiling() -> None:
    content = week()
    content["warning"] = {"headline": "x" * 91, "text": "Short."}
    with pytest.raises(ContentError, match="keep it under 90"):
        validate(content)


def test_band_text_has_a_ceiling() -> None:
    content = week()
    content["warning"] = {"headline": "Short.", "text": "x" * 401}
    with pytest.raises(ContentError, match="keep it under 400"):
        validate(content)


def test_band_tone_must_be_known() -> None:
    content = week()
    content["warning"] = {"headline": "Short.", "text": "Short.", "tone": "amber"}
    with pytest.raises(ContentError, match="tone must be one of"):
        validate(content)


def test_outcome_tag_must_be_known() -> None:
    content = week()
    content["outcome"]["tag"] = "Mostly done"
    with pytest.raises(ContentError, match="outcome.tag must be one of"):
        validate(content)


def test_topic_tag_must_be_known() -> None:
    content = week()
    content["topics"][0]["tag"] = "Done"
    with pytest.raises(ContentError, match=r"topics\[0\].tag must be one of"):
        validate(content)


def test_topic_point_must_be_text_or_lead_and_text() -> None:
    content = week()
    content["topics"][0]["points"] = [{"lead": "Only a lead"}]
    with pytest.raises(ContentError, match=r"topics\[0\].points\[0\] is missing required key 'text'"):
        validate(content)


def test_portfolio_moves_are_capped() -> None:
    content = week()
    move = {"title": "SASE", "from": "1. Exploring", "to": "2. Committed"}
    content["portfolio_moves"] = [move] * (content_schema.MOVES_MAX + 1)
    with pytest.raises(ContentError, match="the page carries at most 8"):
        validate(content)


def test_a_move_must_change_stage() -> None:
    content = week()
    content["portfolio_moves"] = [{"title": "SASE", "from": "2. Committed", "to": "2. Committed"}]
    with pytest.raises(ContentError, match="a move changes stage"):
        validate(content)


def test_a_move_needs_a_board_stage() -> None:
    content = week()
    content["portfolio_moves"] = [{"title": "SASE", "from": "Exploring", "to": "2. Committed"}]
    with pytest.raises(ContentError, match=r"portfolio_moves\[0\].from must be one of"):
        validate(content)


def test_artifact_needs_a_real_link() -> None:
    content = week()
    content["artifacts"] = [{"label": "Deck", "url": "http://insecure.example.com/x"}]
    with pytest.raises(ContentError, match="must be https:// or /sites/"):
        validate(content)


def test_shipped_evidence_needs_a_link() -> None:
    content = week()
    content["shipped"]["items"][0]["evidence"] = [{"label": "No link"}]
    with pytest.raises(ContentError, match="is missing required key 'url'"):
        validate(content)


def test_a_no_forum_week_may_not_carry_a_forum_record() -> None:
    content = week()
    content["no_forum"] = {"headline": "No forum this week.", "text": "Back next Wednesday."}
    with pytest.raises(ContentError, match="a week with no forum has no forum record"):
        validate(content)


def test_a_no_forum_week_needs_no_forum_fields() -> None:
    content = week()
    for key in ("objective", "outcome", "tldr", "decisions", "actions", "topics", "open_questions", "speakers", "speakers_source"):
        content.pop(key)
    content["no_forum"] = {"headline": "No forum this week.", "text": "Back next Wednesday."}
    assert validate(content) is None


def test_no_forum_notice_must_be_complete() -> None:
    content = week()
    for key in ("objective", "outcome", "tldr", "decisions", "actions", "topics", "open_questions", "speakers", "speakers_source"):
        content.pop(key)
    content["no_forum"] = {"headline": "No forum this week."}
    with pytest.raises(ContentError, match="no_forum is missing required key 'text'"):
        validate(content)


def test_open_questions_accept_a_string_or_an_object() -> None:
    content = week()
    content["open_questions"] = ["A plain string question.", {"text": "An object question.", "next": "Ask Chris."}]
    assert validate(content) is None


def test_open_question_object_needs_text() -> None:
    content = week()
    content["open_questions"] = [{"next": "Ask Chris."}]
    with pytest.raises(ContentError, match=r"open_questions\[0\] is missing required key 'text'"):
        validate(content)
