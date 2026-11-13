"""The weekly email: the report's words in the designed template, with every number computed
from the facts. Seam: render(report, facts) -> HTML fragment, plus the CLI. The Outlook draft
step (osascript) is humble and checked by hand."""
from __future__ import annotations

import copy
import html
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import render_email  # noqa: E402

FIX = Path(__file__).parent / "fixtures" / "email"
REPORT = json.loads((FIX / "report.json").read_text())
FACTS = json.loads((FIX / "facts.json").read_text())


def text(markup: str) -> str:
    markup = re.sub(r"<head.*?</head>", "", markup, flags=re.S)
    markup = re.sub(r"<!--.*?-->", "", markup, flags=re.S)
    markup = re.sub(r"<[^>]+>", " ", markup)
    return re.sub(r"\s+", " ", html.unescape(markup)).strip()


def render(report: dict | None = None, facts: dict | None = None) -> str:
    return render_email.render(report or REPORT, facts or FACTS)


def day_bars(out: str) -> list[tuple[int, str]]:
    bars = re.findall(r"height:(\d+)px;background-color:(#[0-9A-Fa-f]{6})", out)
    return [(int(h), c.upper()) for h, c in bars][:5]


def test_renders_the_design_example_word_for_word() -> None:
    assert text(render()) == text((FIX / "design-example.html").read_text())


def test_output_is_a_document_outlook_applescript_accepts() -> None:
    # Proven 2026-11-13: a doctype or <!--[if mso]> comments give an empty draft, and a <style>
    # in the body shows up as visible text. A plain html/head/body document keeps the design.
    out = render()
    assert out.startswith("<html><head>")
    for banned in ("<!--", "<!doctype", "<title"):
        assert banned not in out.lower()
    head, body = out.split("</head>", 1)
    assert "prefers-color-scheme: dark" in head
    assert "<style" not in body


def test_dark_palette_hooks_survive_and_white_is_never_pure() -> None:
    out = render()
    assert 'class="bt-bar-hi"' in out
    assert 'class="bt-head' in out
    assert "#FFFFFF" not in out.upper()


def test_dark_surfaces_are_transparent_or_near_black() -> None:
    # 2026-11-13 swatch test: Outlook for Mac lifts every painted dark background to one
    # mid-dark level; only transparent and near-black #050505 pass unchanged. The card and
    # panel stay filled: the dark CSS follows the OS, so a light Outlook web pane on a dark
    # Mac gets it too, and light text on a transparent card there is unreadable.
    head = render().split("</head>", 1)[0].replace(" ", "")
    assert '[class~="bt-page"]{background-color:transparent' in head
    for rule in ('[class~="bt-card"]{', ".bt-card[data-ogsb]{", "[data-ogsb].bt-card{", '[class~="bt-panel"]{'):
        assert rule + "background-color:#050505" in head, rule
    assert '[class~="bt-head"]{background-color:#050505' in head
    assert "linear-gradient" not in head


def test_day_bars_scale_to_the_busiest_day() -> None:
    assert day_bars(render()) == [(24, "#3F9C84"), (36, "#3F9C84"), (24, "#3F9C84"),
                                  (72, "#0B6E5A"), (12, "#3F9C84")]


def test_a_day_with_no_merges_keeps_the_outlook_minimum_bar() -> None:
    facts = copy.deepcopy(FACTS)
    facts["team"]["prs"]["merged"] = [p for p in facts["team"]["prs"]["merged"] if p["closed"] != "2026-11-13"]
    assert day_bars(render(facts=facts))[4] == (2, "#3F9C84")
    assert "Thursday carried the week: 6 of 13 merges." in text(render(facts=facts))


def test_a_week_with_no_merges_has_flat_bars_and_says_so() -> None:
    facts = copy.deepcopy(FACTS)
    facts["team"]["prs"]["merged"] = []
    out = render(facts=facts)
    assert day_bars(out) == [(2, "#3F9C84")] * 5
    assert "No merges this week." in text(out)


def test_flow_bars_scale_to_the_larger_of_resolved_and_created() -> None:
    out = render()
    assert re.findall(r'width="(\d+)%" height="14"', out) == ["100", "83", "17"]


def test_backlog_line_follows_resolved_versus_created() -> None:
    facts = copy.deepcopy(FACTS)
    facts["team"]["jira"]["created"] += facts["team"]["jira"]["created"][:6]
    assert "Backlog grew by 2 tickets." in text(render(facts=facts))
    facts["team"]["jira"]["created"] = facts["team"]["jira"]["created"][:23]
    assert "Backlog held steady." in text(render(facts=facts))


def test_bulk_closes_are_a_note_and_never_counted_as_resolved() -> None:
    facts = copy.deepcopy(FACTS)
    facts["team"]["jira"]["bulk_runs"] = []
    facts["team"]["jira"]["resolved"] = [t for t in facts["team"]["jira"]["resolved"] if not t["bulk"]]
    out = text(render(facts=facts))
    assert "stale tickets closed" not in out
    assert "Resolved 23" in out


def test_no_decisions_says_none_this_week() -> None:
    report = {**REPORT, "decisions": []}
    out = text(render(report=report))
    assert "None this week." in out
    assert "Reply with the codes" not in out
    assert "0 decisions need you" in out


def test_reply_codes_name_the_picks() -> None:
    assert "for example 1A 2B 3A " in text(render())


def test_nothing_blocked_hides_the_section() -> None:
    out = text(render(report={**REPORT, "blocked": []}))
    assert "Blocked" not in out.replace("0 blocked", "")
    assert "WAITING ON" not in out


def test_stale_bard_data_turns_the_footer_amber() -> None:
    facts = {**FACTS, "bard_fresh": False}
    out = render(facts=facts)
    assert "#F2B84B" in out
    assert "Stale data, last run Nov 13, 10:00 AM CT" in text(out)
    assert "Fresh data" not in text(out)


def test_no_team_config_drops_the_team_section() -> None:
    out = text(render(facts={**FACTS, "team": None}))
    assert "TEAM ·" not in out
    assert "PRs merged" not in out


def test_report_text_is_escaped() -> None:
    report = copy.deepcopy(REPORT)
    report["next"] = ['<script>alert(1)</script> & "x"']
    out = render(report=report)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


@pytest.mark.parametrize("field,size", [("decisions", 6), ("next", 6)])
def test_over_the_limit_is_refused(field: str, size: int) -> None:
    report = copy.deepcopy(REPORT)
    report[field] = (report[field] * size)[:size]
    with pytest.raises(render_email.ReportError):
        render(report=report)


def test_more_than_seven_done_items_is_refused() -> None:
    report = copy.deepcopy(REPORT)
    report["done"][0]["items"] *= 3
    with pytest.raises(render_email.ReportError):
        render(report=report)


def test_cli_writes_the_fragment(tmp_path: Path) -> None:
    out = tmp_path / "w.email.html"
    code = render_email.main(["--report", str(FIX / "report.json"), "--facts", str(FIX / "facts.json"),
                              "--out", str(out)])
    assert code == 0
    assert text(out.read_text()) == text(render())


def test_cli_rejects_a_bad_report_with_exit_2(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "r.json"
    bad.write_text(json.dumps({**REPORT, "next": ["x"] * 6}))
    code = render_email.main(["--report", str(bad), "--facts", str(FIX / "facts.json"),
                              "--out", str(tmp_path / "o.html")])
    assert code == 2
    assert "next" in capsys.readouterr().err


def test_dark_media_rules_use_attribute_selectors_only() -> None:
    # Swatch 3, 2026-11-13: Outlook on the web rewrites class selectors, so a .bt-* rule in the
    # media block fires on a dark OS even when its own theme is light. An attribute selector is
    # not rewritten: it fires in Outlook for Mac and Apple Mail, and stays inert on the web,
    # whose dark theme is carried by the [data-ogsb] hooks instead.
    head = render().split("</head>", 1)[0]
    media = head[head.index("@media (prefers-color-scheme: dark)"):]
    media = media[:media.index("\n}") if "\n}" in media else media.index("}}") + 1]
    assert '[class~="bt-card"]' in media
    assert not re.search(r"(?<![\w\"=~-])\.bt-", media)
    assert "[data-ogsb] .bt-card" in head


def test_flow_bars_never_pass_100_percent() -> None:
    # Bugs opened or closed can outnumber resolved and created (a cleanup week).
    facts = copy.deepcopy(FACTS)
    facts["team"]["jira"]["bugs"] = facts["team"]["jira"]["bugs"] * 10
    widths = [int(w) for w in re.findall(r'width="(\d+)%" height="14"', render(facts=facts))]
    assert widths and max(widths) == 100


def test_unfetched_sources_never_show_as_zero() -> None:
    facts = copy.deepcopy(FACTS)
    facts["team"]["prs"] = None
    facts["team"]["jira"] = None
    out = text(render(facts=facts))
    assert "Merges not fetched." in out and "Tickets not fetched." in out
    assert "0 PRs merged" not in out and "Resolved 0" not in out


def test_a_capped_pr_search_is_named_in_the_footer() -> None:
    facts = copy.deepcopy(FACTS)
    facts["team"]["prs"]["truncated"] = ["team merged"]
    assert "capped" in text(render(facts=facts)).lower()


@pytest.mark.parametrize("field,value", [("next", [{"text": "x"}]), ("next", [""]), ("blocked", "none")])
def test_malformed_next_and_blocked_are_refused(field: str, value) -> None:
    with pytest.raises(render_email.ReportError, match=field):
        render(report={**REPORT, field: value})


def test_cli_creates_the_output_folder(tmp_path: Path) -> None:
    out = tmp_path / "Reports" / "Weekly" / "w.email.html"
    assert render_email.main(["--report", str(FIX / "report.json"), "--facts", str(FIX / "facts.json"),
                              "--out", str(out)]) == 0
    assert out.exists()
