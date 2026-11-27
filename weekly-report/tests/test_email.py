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


def subject_facts(week: str, window: list[str], **extra: object) -> dict:
    facts = copy.deepcopy(FACTS)
    facts["week"], facts["window"] = week, window
    facts["team"] = {**(facts.get("team") or {}), "name": "Platform Integrations"}
    facts.update(extra)
    return facts


def test_subject_names_the_team_the_week_and_the_authors_week_number() -> None:
    facts = subject_facts("2026-W46", ["2026-11-09", "2026-11-13"],
                          start_week="2026-W46", week_tag_until="2026-12-31")
    assert render_email.subject(REPORT, facts) == "Platform Integrations: W46 (Alex week 1) Recap"


def test_subject_counts_weeks_from_the_start_week() -> None:
    facts = subject_facts("2026-W52", ["2026-12-21", "2026-12-25"],
                          start_week="2026-W46", week_tag_until="2026-12-31")
    assert render_email.subject(REPORT, facts) == "Platform Integrations: W52 (Alex week 7) Recap"


def test_subject_drops_the_week_number_after_the_tag_end_date() -> None:
    facts = subject_facts("2027-W01", ["2027-01-04", "2027-01-08"],
                          start_week="2026-W46", week_tag_until="2026-12-31")
    assert render_email.subject(REPORT, facts) == "Platform Integrations: W01 Recap"


def test_subject_has_no_week_number_without_a_start_week() -> None:
    assert render_email.subject(REPORT, subject_facts("2026-W46", ["2026-11-09", "2026-11-13"])) \
        == "Platform Integrations: W46 Recap"


def test_subject_without_a_team_is_the_week_alone() -> None:
    facts = subject_facts("2026-W46", ["2026-11-09", "2026-11-13"])
    facts["team"] = None
    assert render_email.subject(REPORT, facts) == "W46 Recap"


def test_the_draft_step_never_sends() -> None:
    assert "send" not in render_email.DRAFT_SCRIPT.lower()


IDEAS = ["Gateway with 3000 tools bloats agent context: search tools with find_tools (with Matt)",
         "Apps deploy from one MCP call, like artifact pages (with Andy)"]


def test_ideas_render_after_blocked_and_before_team() -> None:
    out = text(render(report={**REPORT, "ideas": IDEAS}))
    assert "Ideas (backlog, not committed)" in out
    assert IDEAS[0] in out and IDEAS[1] in out
    assert out.index("WAITING ON") < out.index("Ideas (backlog") < out.index("TEAM ·")


def test_no_ideas_hides_the_section() -> None:
    for report in ({**REPORT, "ideas": []}, {k: v for k, v in REPORT.items() if k != "ideas"}):
        assert "Ideas (backlog" not in text(render(report=report))


def test_more_than_three_ideas_is_refused() -> None:
    with pytest.raises(render_email.ReportError, match="ideas"):
        render(report={**REPORT, "ideas": IDEAS * 2})


@pytest.mark.parametrize("value", ["none", [""], [{"text": "x"}]])
def test_malformed_ideas_are_refused(value) -> None:
    with pytest.raises(render_email.ReportError, match="ideas"):
        render(report={**REPORT, "ideas": value})


def test_idea_text_is_escaped() -> None:
    out = render(report={**REPORT, "ideas": ['<b>x</b> & "y"']})
    assert "<b>x</b>" not in out and "&lt;b&gt;" in out


IN_FLIGHT = [
    {"title": "Gateway", "lines": ["Replaces the old gateway with one policy-checked service.",
                                        "One route switch, gated by a parity test."],
     "url": "https://example.invalid/pr/7", "ref": "hub#7"},
    {"title": "Catalog", "lines": ["One catalog for every tool."],
     "url": "https://example.invalid/pr/8", "ref": "lib#8"},
]


def test_in_flight_renders_after_done_and_before_next() -> None:
    report = {**REPORT, "in_flight": IN_FLIGHT, "diagrams_url": "https://example.invalid/deep-dive"}
    out = render(report=report)
    words = text(out)
    assert "In flight" in words
    for item in IN_FLIGHT:
        assert item["title"] in words and item["ref"] in words and item["url"] in out
        for line in item["lines"]:
            assert line in words
    assert "https://example.invalid/deep-dive" in out
    assert words.index("Done") < words.index("In flight") < words.index("Next")


def test_no_in_flight_hides_the_section() -> None:
    for report in ({**REPORT, "in_flight": []}, {k: v for k, v in REPORT.items() if k != "in_flight"}):
        assert "In flight" not in text(render(report=report))


def test_more_than_three_in_flight_items_is_refused() -> None:
    with pytest.raises(render_email.ReportError, match="in_flight"):
        render(report={**REPORT, "in_flight": IN_FLIGHT * 2})


def test_more_than_three_lines_in_one_in_flight_item_is_refused() -> None:
    item = {**IN_FLIGHT[0], "lines": ["a", "b", "c", "d"]}
    with pytest.raises(render_email.ReportError, match="in_flight"):
        render(report={**REPORT, "in_flight": [item]})


@pytest.mark.parametrize("value", ["none", [{"title": "x"}], [{"title": "", "lines": ["a"]}]])
def test_malformed_in_flight_is_refused(value) -> None:
    with pytest.raises(render_email.ReportError, match="in_flight"):
        render(report={**REPORT, "in_flight": value})


def test_in_flight_text_is_escaped() -> None:
    item = {"title": "<b>x</b>", "lines": ['& "y"']}
    out = render(report={**REPORT, "in_flight": [item]})
    assert "<b>x</b>" not in out and "&lt;b&gt;" in out


# The combined weekly email (Alex, 2026-11-25): the deep dive merged into the email. Features,
# not PR titles; repo bars from the facts; In flight diagrams as table boxes (Outlook drops SVG).
def merged(repo: str, n: int) -> dict:
    return {"repo": f"org/{repo}", "number": n, "title": f"feat: internal title {n}", "state": "merged",
            "url": f"https://github.com/org/{repo}/pull/{n}", "closed": "2026-11-11"}


SHIPPED = [{"theme": "Production", "headline": "Production runs like Development.",
            "features": [{"text": "Teams ship to production the same way as development",
                          "refs": [{"ref": "hub#1", "url": "https://github.com/org/hub/pull/1"}]}]}]
DIAGRAM = [[{"label": "Skill authors"}, {"arrow": "→"}, {"label": "One catalog", "tone": "hi"},
            {"arrow": "→"}, {"label": "Cursor"}]]


def combined_facts() -> dict:
    facts = copy.deepcopy(FACTS)
    facts["github"]["authored"] = [merged("hub", 1), merged("hub", 2), merged("canon", 3)]
    facts["team"]["jira"]["moved"] = {"items": [{"key": "K-9", "summary": "moved thing", "status": "In Progress",
                                                  "assignee": "Kim", "url": "https://j/browse/K-9", "mine": False}],
                                      "missing": 0}
    return facts


def combined_report() -> dict:
    return {**REPORT, "shipped": SHIPPED,
            "in_flight": [{"title": "Catalog", "lines": ["Publish once."], "diagram": DIAGRAM}]}


def test_shipped_renders_features_with_refs_never_pr_titles() -> None:
    out = render(report=combined_report(), facts=combined_facts())
    words = text(out)
    assert "Shipped this week" in words and "Production runs like Development." in words
    assert "Teams ship to production the same way as development" in words
    assert "https://github.com/org/hub/pull/1" in out and "hub#1" in words
    assert "internal title" not in out


def test_repo_bars_come_from_the_facts() -> None:
    words = text(render(report=combined_report(), facts=combined_facts()))
    assert "hub 2" in words and "canon 1" in words


def test_in_flight_diagram_is_a_table_of_boxes_not_svg() -> None:
    out = render(report=combined_report(), facts=combined_facts())
    words = text(out)
    for label in ("Skill authors", "One catalog", "Cursor", "→"):
        assert label in words
    assert "<svg" not in out.lower() and "<img" not in out.lower()


def test_jira_moves_show_when_the_facts_have_them() -> None:
    words = text(render(report=combined_report(), facts=combined_facts()))
    assert "Moved this week" in words and "K-9" in words and "In Progress" in words


def test_no_shipped_hides_the_section() -> None:
    assert "Shipped this week" not in text(render())


@pytest.mark.parametrize("value", ["none", [{"theme": "x", "headline": "y", "features": []}],
                                   [{"theme": "x", "headline": "y", "features": [{"text": "t", "refs": []}]}]])
def test_malformed_shipped_is_refused(value) -> None:
    with pytest.raises(render_email.ReportError, match="shipped"):
        render(report={**REPORT, "shipped": value}, facts=combined_facts())


def test_malformed_diagram_is_refused() -> None:
    report = combined_report()
    report["in_flight"][0]["diagram"] = [[{"nope": 1}]]
    with pytest.raises(render_email.ReportError, match="in_flight"):
        render(report=report, facts=combined_facts())


def test_shipped_without_done_renders_and_counts_features_in_the_header() -> None:
    report = {k: v for k, v in combined_report().items() if k != "done"}
    words = text(render(report=report, facts=combined_facts()))
    assert "1 done" in words and "Shipped this week" in words


def test_new_tickets_show_when_nothing_moved() -> None:
    facts = combined_facts()
    facts["team"]["jira"]["moved"] = {"items": [], "missing": 0}
    words = text(render(report=combined_report(), facts=facts))
    created = FACTS["team"]["jira"]["created"]
    assert created and created[0]["key"] in words


def test_moves_not_fetched_is_said_not_hidden() -> None:
    facts = combined_facts()
    del facts["team"]["jira"]["moved"]
    assert "Moved this week: not fetched" in text(render(report=combined_report(), facts=facts))


def test_malformed_moves_are_a_facts_error() -> None:
    facts = combined_facts()
    facts["team"]["jira"]["moved"] = {"items": ["str"], "missing": 0}
    with pytest.raises(render_email.ReportError, match="facts"):
        render(report=combined_report(), facts=facts)


def test_empty_shipped_is_treated_as_absent() -> None:
    assert "Shipped this week" not in text(render(report={**REPORT, "shipped": []}, facts=combined_facts()))


# Impeccable audit, 2026-11-27: the 880 px card had no phone layout, section titles were <p>,
# and the lighter repo bar became a hollow outline in dark mode.
def test_phone_rule_lets_the_card_fill_a_narrow_screen() -> None:
    head = render(report=combined_report(), facts=combined_facts()).split("</head>", 1)[0]
    rule = re.search(r"@media[^{]*max-width:\s*(\d+)px[^{]*\{(.*)", head, re.S)
    assert rule and int(rule.group(1)) <= 700
    assert "bt-card" in rule.group(2) and "100%" in rule.group(2)


def test_stat_and_bar_cells_stack_on_a_phone() -> None:
    out = render(report=combined_report(), facts=combined_facts())
    head = out.split("</head>", 1)[0]
    assert 'class="bt-stack' in out or "bt-stack" in out
    assert re.search(r"bt-stack[^}]*display:\s*block", head)


def test_section_titles_are_real_headings() -> None:
    out = render(report=combined_report(), facts=combined_facts())
    titles = re.findall(r"<h([23])[^>]*>(.*?)</h\1>", out, re.S)
    names = {re.sub(r"<[^>]+>", "", t).strip() for _, t in titles}
    for name in ("Decisions needed", "Shipped this week", "In flight", "Next", "Blocked"):
        assert name in names, name
    assert all("margin:0" in h.replace(" ", "") for h in re.findall(r"<h[23][^>]*>", out))


def test_lighter_repo_bar_keeps_a_fill_in_dark_mode() -> None:
    head = render(report=combined_report(), facts=combined_facts()).split("</head>", 1)[0]
    dark = head[head.index("prefers-color-scheme: dark"):]
    rule = re.search(r'\[class~="bt-bar"\][^{]*\{([^}]*)\}', dark)
    assert rule and "transparent" not in rule.group(1)
