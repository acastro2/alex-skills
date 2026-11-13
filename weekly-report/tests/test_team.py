"""The team section: how the team's product moved this week, kept apart from Alex's own work.
Seams: the `gh` subprocess (injected `run`), saved Jira search pages, and the Slack paste file."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import collect  # noqa: E402

WINDOW = (dt.date(2026, 11, 9), dt.date(2026, 11, 13))
TEAM = {"name": "Team", "org": "o", "repos": ["a", "b"]}


class Proc:
    returncode, stderr = 0, ""

    def __init__(self, rows: list[dict]) -> None:
        self.stdout = json.dumps(rows)


def gh_pr(repo: str, n: int, author: str = "dev", closed: str = "", draft: bool = False) -> dict:
    return {"repository": {"name": repo, "nameWithOwner": f"o/{repo}"}, "number": n, "title": f"{repo}#{n}",
            "author": {"login": author}, "url": f"https://x/{repo}/{n}", "isDraft": draft,
            "state": "merged" if closed else "open", "closedAt": closed or "0001-01-01T00:00:00Z"}


def test_team_prs_search_the_org_and_keep_only_team_repos() -> None:
    # A long --repo list makes GitHub search return 0 rows with exit 0, so the search must be
    # org-wide and the repo filter local.
    calls = []
    merged = [gh_pr("a", 1, closed="2026-11-10T10:00:00Z"), gh_pr("other", 2, closed="2026-11-10T10:00:00Z"),
              gh_pr("b", 3, author="alex", closed="2026-11-12T10:00:00Z")]
    open_ = [gh_pr("b", 4), gh_pr("a", 5, draft=True), gh_pr("other", 6)]

    def run(cmd, **_):
        calls.append(cmd)
        assert "--repo" not in cmd and "--owner" in cmd and cmd[cmd.index("--owner") + 1] == "o"
        return Proc(merged if any(c.startswith("--merged-at=") for c in cmd) else open_)

    out = collect.team_prs(WINDOW, TEAM, mine_urls={"https://x/b/3"}, run=run)
    assert [(p["repo"], p["number"], p["mine"]) for p in out["merged"]] == [("a", 1, False), ("b", 3, True)]
    assert out["merged"][0]["author"] == "dev" and out["merged"][0]["closed"] == "2026-11-10"
    assert [(p["repo"], p["number"], p["draft"]) for p in out["open"]] == [("b", 4, False), ("a", 5, True)]
    assert out["truncated"] == []
    assert any("--state" in c and "open" in c and "--updated=2026-11-09..2026-11-13" in c for c in calls)


def test_team_prs_name_a_full_page_as_truncated() -> None:
    page = [gh_pr("a", i, closed="2026-11-10T10:00:00Z") for i in range(collect.PR_LIMIT)]

    def run(cmd, **_):
        return Proc(page if any(c.startswith("--merged-at=") for c in cmd) else [])

    assert collect.team_prs(WINDOW, TEAM, mine_urls=set(), run=run)["truncated"] == ["team merged"]


def test_team_prs_raise_on_gh_failure() -> None:
    class Fail:
        returncode, stdout, stderr = 1, "", "HTTP 401"

    with pytest.raises(RuntimeError, match="401"):
        collect.team_prs(WINDOW, TEAM, mine_urls=set(), run=lambda cmd, **_: Fail())


def issue(key: str, kind: str, created: str, resolved: str | None, account: str | None = "dev-id") -> dict:
    return {"key": key, "webUrl": f"https://j/browse/{key}", "fields": {
        "summary": f"do {key}", "issuetype": {"name": kind}, "status": {"name": "Done" if resolved else "To Do"},
        "assignee": {"accountId": account, "displayName": "Dev"} if account else None,
        "created": created, "resolutiondate": resolved}}


def page(nodes: list[dict], total: int, more: bool) -> str:
    return json.dumps({"issues": {"totalCount": total, "nodes": nodes, "pageInfo": {"hasNextPage": more}},
                       "context": {"atlassianAccountId": "me-id"}})


def test_jira_pages_split_resolved_created_bugs_in_chicago_time() -> None:
    p1 = page([issue("T-1", "Story", "2026-10-01T09:00:00.000-0500", "2026-11-10T09:00:00.000-0600", "me-id"),
               issue("T-2", "Bug", "2026-11-11T09:00:00.000-0600", None, None)], total=4, more=True)
    p2 = page([issue("T-3", "Task", "2026-11-08T09:00:00.000-0600", "2026-11-14T04:00:00.000+0000"),  # Fri night in Chicago
               issue("T-4", "Task", "2026-11-08T09:00:00.000-0600", "2026-11-14T08:00:00.000-0600"),  # Saturday: out
               issue("T-1", "Story", "2026-10-01T09:00:00.000-0500", "2026-11-10T09:00:00.000-0600", "me-id")],
              total=4, more=False)
    out = collect.parse_jira([p1, p2], WINDOW)
    assert [i["key"] for i in out["resolved"]] == ["T-1", "T-3"]
    assert [i["key"] for i in out["created"]] == ["T-2"]
    assert [i["key"] for i in out["bugs"]] == ["T-2"]
    first = out["resolved"][0]
    assert first["mine"] is True and first["url"] == "https://j/browse/T-1" and first["resolved"] == "2026-11-10"
    assert out["created"][0]["assignee"] is None and out["created"][0]["mine"] is False
    assert out["total"] == 4 and out["missing"] == 0


def test_jira_reports_missing_issues_when_a_page_was_not_passed() -> None:
    p1 = page([issue("T-1", "Task", "2026-11-10T09:00:00.000-0600", None)], total=3, more=True)
    assert collect.parse_jira([p1], WINDOW)["missing"] == 2


def test_jira_later_pages_carry_no_total_count() -> None:
    # Seen live: only the first page of a paged search has `totalCount`.
    p1 = page([issue("T-1", "Task", "2026-11-10T09:00:00.000-0600", None)], total=2, more=True)
    p2 = json.loads(page([issue("T-2", "Task", "2026-11-10T09:00:00.000-0600", None)], total=0, more=False))
    del p2["issues"]["totalCount"]
    out = collect.parse_jira([p1, json.dumps(p2)], WINDOW)
    assert [i["key"] for i in out["created"]] == ["T-1", "T-2"] and out["missing"] == 0


def test_jira_flags_bulk_closes_apart_from_real_work() -> None:
    # Seen live: 188 tickets closed in 10 minutes by one backlog cleanup. A run of BULK_MIN or
    # more resolutions, each within a minute of the one before, is a bulk close.
    n = collect.BULK_MIN
    bulk = [issue(f"B-{i}", "Task", "2026-09-01T09:00:00.000-0500",
                  f"2026-11-12T15:{10 + i // 2:02d}:{(i % 2) * 30:02d}.000+0000") for i in range(n)]
    real = [issue("R-1", "Story", "2026-09-01T09:00:00.000-0500", "2026-11-12T18:00:00.000+0000"),
            issue("R-2", "Story", "2026-09-01T09:00:00.000-0500", "2026-11-10T18:00:00.000+0000")]
    out = collect.parse_jira([page(bulk + real, total=n + 2, more=False)], WINDOW)
    assert sorted(i["key"] for i in out["resolved"] if not i["bulk"]) == ["R-1", "R-2"]
    assert sum(i["bulk"] for i in out["resolved"]) == n
    assert out["bulk_runs"] == [{"start": "2026-11-12T15:10:00+00:00", "count": n}]


def test_jira_few_quick_closes_are_not_bulk() -> None:
    few = [issue(f"F-{i}", "Task", "2026-09-01T09:00:00.000-0500", f"2026-11-12T15:10:{i:02d}.000+0000")
           for i in range(collect.BULK_MIN - 1)]
    out = collect.parse_jira([page(few, total=len(few), more=False)], WINDOW)
    assert not any(i["bulk"] for i in out["resolved"]) and out["bulk_runs"] == []


def test_slack_paste_keeps_calls_verbatim_and_rejects_a_bad_shape() -> None:
    good = json.dumps({"calls": [{"tool": "slack_read_channel", "args": {"channel": "C1"}, "content": "raw text"}]})
    assert collect.parse_slack(good) == {"calls": 1, "items": [
        {"tool": "slack_read_channel", "args": {"channel": "C1"}, "content": "raw text"}]}
    with pytest.raises(ValueError):
        collect.parse_slack(json.dumps({"calls": [{"tool": "x"}]}))
    with pytest.raises(ValueError):
        collect.parse_slack(json.dumps({"calls": []}))


def test_main_puts_team_after_my_work_and_names_each_gap(tmp_path: Path, capsys, monkeypatch) -> None:
    vault = tmp_path / "vault"
    (vault / "Bard").mkdir(parents=True)
    (vault / "Todo.md").write_text("<!-- BARD:START -->\n")
    config = tmp_path / "weekly-report.json"
    config.write_text(json.dumps({"manager": "M", "team": TEAM}))
    monkeypatch.setattr(collect, "CONFIG", config)
    jira = tmp_path / "jira.txt"
    jira.write_text(page([issue("T-9", "Bug", "2026-11-10T09:00:00.000-0600", None)], total=1, more=False))

    assert collect.main(["--vault", str(vault), "--date", "2026-11-11", "--no-github", "--jira", str(jira)]) == 0
    facts = json.loads(capsys.readouterr().out)
    keys = list(facts)
    assert keys.index("team") > keys.index("github")
    team = facts["team"]
    assert team["name"] == "Team" and team["prs"] is None
    assert [i["key"] for i in team["jira"]["bugs"]] == ["T-9"]
    assert team["slack"] is None
    assert team["gaps"] == ["github: not fetched (--no-github)", "slack: not fetched", "datadog: not fetched"]


def test_bad_paste_files_become_gaps_and_keep_my_facts(tmp_path: Path, capsys, monkeypatch) -> None:
    vault = tmp_path / "vault"
    (vault / "Bard").mkdir(parents=True)
    (vault / "Todo.md").write_text("<!-- BARD:START -->\n## Done\n- [x] ☁️ Shipped it ⏫ ✅ 2026-11-12\n")
    config = tmp_path / "weekly-report.json"
    config.write_text(json.dumps({"team": TEAM}))
    monkeypatch.setattr(collect, "CONFIG", config)
    (tmp_path / "jira.txt").write_text("not json")
    (tmp_path / "slack.json").write_text(json.dumps({"calls": []}))
    short = tmp_path / "short.txt"
    short.write_text(page([issue("T-1", "Task", "2026-11-10T09:00:00.000-0600", None)], total=2, more=True))

    args = ["--vault", str(vault), "--date", "2026-11-11", "--no-github"]
    assert collect.main([*args, "--jira", str(tmp_path / "jira.txt"), "--slack", str(tmp_path / "slack.json")]) == 0
    facts = json.loads(capsys.readouterr().out)
    assert [d["date"] for d in facts["board"]["done"]] == ["2026-11-12"]
    gaps = facts["team"]["gaps"]
    assert facts["team"]["jira"] is None and gaps[1].startswith("jira: unreadable")
    assert facts["team"]["slack"] is None and gaps[2].startswith("slack: unreadable")

    assert collect.main([*args, "--jira", str(short)]) == 0
    gap = json.loads(capsys.readouterr().out)["team"]["gaps"][1]
    assert gap.startswith("jira: 1 issues missing") and "bulk" in gap


def test_main_without_team_config_has_no_team_block(tmp_path: Path, capsys, monkeypatch) -> None:
    (tmp_path / "Bard").mkdir()
    (tmp_path / "Todo.md").write_text("")
    monkeypatch.setattr(collect, "CONFIG", tmp_path / "missing.json")
    assert collect.main(["--vault", str(tmp_path), "--no-github"]) == 0
    assert json.loads(capsys.readouterr().out)["team"] is None


def test_team_merges_count_by_the_chicago_day() -> None:
    # closedAt is UTC. A 7 pm Friday merge in Chicago is 01:00 Saturday UTC: it belongs to Friday,
    # and a 7 pm Sunday merge before the week belongs to no day of it.
    merged = [gh_pr("a", 1, closed="2026-11-14T01:00:00Z"), gh_pr("a", 2, closed="2026-11-10T03:00:00Z"),
              gh_pr("a", 3, closed="2026-11-09T01:00:00Z")]
    calls = []

    def run(cmd, **_):
        calls.append(cmd)
        return Proc(merged if any(c.startswith("--merged-at=") for c in cmd) else [])

    out = collect.team_prs(WINDOW, TEAM, mine_urls=set(), run=run)
    assert [(p["number"], p["closed"]) for p in out["merged"]] == [(1, "2026-11-13"), (2, "2026-11-09")]
    assert any("--merged-at=2026-11-08..2026-11-14" in c for c in calls)
