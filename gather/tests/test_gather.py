"""Behaviour tests for gather: the contracts in gather/references/spec.md.

The `claude` subprocess is the boundary. A fake runner turns the requested calls into
stream-json with the same line shapes as real `claude -p --output-format stream-json`
runs (captured 2026-11-13); every message text here is synthetic.
"""
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gather.py"
spec = importlib.util.spec_from_file_location("gather", SCRIPT)
gather = importlib.util.module_from_spec(spec)
sys.modules["gather"] = gather
spec.loader.exec_module(gather)

ME = "me@example.com"
NOW = datetime(2026, 11, 13, 18, 0, tzinfo=timezone.utc)
SEARCH = "mcp__claude_ai_Microsoft_365__chat_message_search"


def chat_page(n, start=0, more=None):
    """Real connector shape: JSON objects back to back, paging hint as the last object."""
    objs = [
        json.dumps({"id": f"m{start + i}", "chatId": "19:c1@thread.v2", "summary": f"synthetic {start + i}",
                    "createdDateTime": "2026-11-13T10:00:00.000Z", "from": {"email": ME}})
        for i in range(n)
    ]
    if more is not None:
        objs.append(json.dumps({"moreResults": True, "nextOffset": more}))
    return "".join(objs)


def stream(uses):
    """uses: list of (tool_name, input, result_text, is_error). Returns stream-json stdout."""
    lines = [json.dumps({"type": "system", "subtype": "init", "model": "claude-haiku-5-5", "tools": [SEARCH]})]
    for i, (name, args, text, err) in enumerate(uses):
        tid = f"toolu_{i}"
        lines.append(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": tid, "name": name, "input": args}]}}))
        block = {"type": "tool_result", "tool_use_id": tid, "content": [{"type": "text", "text": text}]}
        if err:
            block["is_error"] = True
        lines.append(json.dumps({"type": "user", "message": {"content": [block]}}))
    lines.append(json.dumps({"type": "result", "subtype": "success", "result": "DONE"}))
    return "\n".join(lines) + "\n"


class FakeRunner:
    """Answers each requested call with respond(tool, args) -> (text, is_error)."""

    def __init__(self, respond, extra_uses=()):
        self.respond = respond
        self.extra_uses = list(extra_uses)
        self.rounds = []

    def __call__(self, calls, allowed):
        self.rounds.append((calls, allowed))
        uses = [(c["tool"], c["args"], *self.respond(c["tool"], c["args"])) for c in calls]
        return stream(uses + self.extra_uses)


def raw_records(root, source):
    return [json.loads(p.read_text()) for p in sorted((root / "raw" / source).rglob("*.json"))]


def read_state(root):
    p = root / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


# --- raw record + pairing ---------------------------------------------------------------

def test_raw_record_holds_the_tool_result_text_byte_for_byte(tmp_path):
    page = chat_page(3)
    runner = FakeRunner(lambda tool, args: (page, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    recs = raw_records(tmp_path, "teams_mine")
    assert len(recs) == 1
    r = recs[0]
    assert r["content"] == page
    assert r["tool"] == SEARCH
    assert r["provenance"] == "verbatim"
    assert r["source"] == "teams_mine"
    assert r["args"]["sender"] == ME


def test_results_pair_to_their_own_call_by_id_not_by_order():
    text = "\n".join([
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "A", "name": SEARCH, "input": {"offset": 0}},
            {"type": "tool_use", "id": "B", "name": SEARCH, "input": {"offset": 25}}]}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "B", "content": [{"type": "text", "text": "second"}]},
            {"type": "tool_result", "tool_use_id": "A", "content": "first"}]}}),
    ])
    calls = gather.parse_stream(text, allowed={SEARCH})
    by_offset = {c["args"]["offset"]: c["content"] for c in calls}
    assert by_offset == {0: "first", 25: "second"}


# --- guard --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["mcp__claude_ai_Microsoft_365__outlook_create_draft", "Bash"])
def test_a_tool_outside_the_allowlist_aborts_the_source_and_stores_nothing(tmp_path, bad):
    runner = FakeRunner(lambda tool, args: (chat_page(2), False),
                        extra_uses=[(bad, {"x": 1}, "ok", False)])
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"].startswith("aborted: guard")
    assert raw_records(tmp_path, "teams_mine") == []
    assert "teams_mine" not in read_state(tmp_path).get("cursors", {})


def test_guard_error_names_the_tool():
    text = stream([("mcp__claude_ai_Microsoft_365__outlook_create_draft", {}, "ok", False)])
    with pytest.raises(gather.GuardError, match="outlook_create_draft"):
        gather.parse_stream(text, allowed={SEARCH})


# --- paging -------------------------------------------------------------------------

def test_paging_follows_next_offset_until_the_last_page(tmp_path):
    def respond(tool, args):
        off = args.get("offset", 0)
        return (chat_page(25, off, more=off + 25) if off < 50 else chat_page(4, off)), False

    runner = FakeRunner(respond)
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    offsets = [c["args"]["offset"] for calls, _ in runner.rounds for c in calls]
    assert offsets == [0, 25, 50]
    assert ledger["teams_mine"] == "fetched 3 calls, 54 items"
    assert len(raw_records(tmp_path, "teams_mine")) == 3


def test_paging_cap_is_reported_and_never_marks_the_window_covered(tmp_path):
    # a capped first run pins the cursor at its window start (no slide), but never claims coverage
    runner = FakeRunner(lambda tool, args: (chat_page(25, args.get("offset", 0), more=args.get("offset", 0) + 25), False))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME, max_pages=2)
    assert ledger["teams_mine"] == "capped at 2 pages"
    state = read_state(tmp_path)
    assert state["cursors"]["teams_mine"] == (NOW - timedelta(days=7)).isoformat()
    assert "teams_mine" not in state.get("covered_from", {})


# --- ledger -------------------------------------------------------------------------

EMPTY = "(mcp__claude_ai_Microsoft_365__chat_message_search completed with no output)"


def test_every_requested_source_gets_exactly_one_ledger_line_even_when_empty(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    ledger = gather.run(["teams_mine", "teams_chats"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger == {"teams_mine": "fetched 1 calls, 0 items", "teams_chats": "fetched 1 calls, 0 items"}
    files = list((tmp_path / "ledger").glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["sources"] == ledger


def test_a_tool_error_is_an_error_line_not_an_empty_fetch(tmp_path):
    runner = FakeRunner(lambda tool, args: ("MCP error -32602: Input validation error", True))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"].startswith("error:")
    assert "teams_mine" not in read_state(tmp_path).get("cursors", {})


def test_a_runner_crash_is_an_error_line_and_other_sources_still_run(tmp_path):
    def runner(calls, allowed):
        if calls[0]["args"].get("sender"):
            raise RuntimeError("claude exited 1")
        return stream([(c["tool"], c["args"], EMPTY, False) for c in calls])

    ledger = gather.run(["teams_mine", "teams_chats"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"].startswith("error:")
    assert ledger["teams_chats"] == "fetched 1 calls, 0 items"


# --- cursor -------------------------------------------------------------------------
# The cursor steps back 15 minutes (Alex, 2026-11-13): Teams and mail search can index a
# message after it was sent, and a cursor at the run start would skip it forever.
OVERLAP = timedelta(minutes=15)

def test_first_run_starts_seven_days_back_and_success_moves_the_cursor_to_run_start(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    first_after = runner.rounds[0][0][0]["args"]["afterDateTime"]
    assert datetime.fromisoformat(first_after.replace("Z", "+00:00")) == NOW - timedelta(days=7)
    assert read_state(tmp_path)["cursors"]["teams_mine"] == (NOW - OVERLAP).isoformat()

    later = NOW + timedelta(hours=5)
    runner2 = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=later, runner=runner2, me=ME)
    second_after = runner2.rounds[0][0][0]["args"]["afterDateTime"]
    assert datetime.fromisoformat(second_after.replace("Z", "+00:00")) == NOW - OVERLAP
    assert read_state(tmp_path)["cursors"]["teams_mine"] == (later - OVERLAP).isoformat()


def test_cursor_never_moves_backwards(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    gather.run(["teams_mine"], root=tmp_path, now=NOW - timedelta(days=1), runner=runner, me=ME)
    assert read_state(tmp_path)["cursors"]["teams_mine"] == (NOW - OVERLAP).isoformat()


# --- spill (real shape captured 2026-11-13) --------------------------------------------
# Over ~50 KB, the message's tool_result holds only a <persisted-output> preview; the line's
# `tool_use_result` holds the full text. The file named in the preview is deleted when the run
# ends, so it is never a source. Over MAX_MCP_OUTPUT_TOKENS the result is an error text.

def spill_stream(full, preview):
    lines = [
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "T", "name": SEARCH, "input": {"offset": 0}}]}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "T", "content": preview}]},
            "tool_use_result": {"content": full}}),
    ]
    return "\n".join(lines) + "\n"


PREVIEW = ("<persisted-output>\nOutput too large (93.8KB). Full output saved to: /gone/tool-results/x.txt\n\n"
           "Preview (first 2KB):\n{\"id\":\"m0\"...\n</persisted-output>")


def test_a_spilled_result_is_stored_complete_from_tool_use_result():
    full = chat_page(25) * 3
    (call,) = gather.parse_stream(spill_stream(full, PREVIEW), allowed={SEARCH})
    assert call["content"] == full


def test_a_spilled_result_with_list_shaped_tool_use_result_is_joined():
    full = chat_page(30)
    text = spill_stream(full, PREVIEW).replace(json.dumps({"content": full}), json.dumps([{"type": "text", "text": full}]))
    (call,) = gather.parse_stream(text, allowed={SEARCH})
    assert call["content"] == full


def test_a_spill_without_the_full_text_fails_the_source_instead_of_storing_the_preview(tmp_path):
    runner = FakeRunner(lambda tool, args: (PREVIEW, False))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"].startswith("error: spill")
    assert raw_records(tmp_path, "teams_mine") == []


def test_a_result_over_the_token_cap_is_an_error_even_though_is_error_is_unset(tmp_path):
    cap = ("Error: result (96,003 characters) exceeds maximum allowed tokens. Output has been saved to "
           "/gone/tool-results/x.txt.\nFormat: JSON with schema: {issues: {nodes: [{...}]}}")
    runner = FakeRunner(lambda tool, args: (cap, False))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"].startswith("error: spill")
    assert raw_records(tmp_path, "teams_mine") == []


# --- added after the live run 2026-11-13 ----------------------------------------------------

def test_sharepoint_author_is_the_display_name_because_the_mail_matches_nothing(tmp_path):
    # live: author=<mail> returned no output; author="<display name>" found Alex's doc
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["sharepoint"], root=tmp_path, now=NOW, runner=runner, me=ME, me_name="Doe, Jane")
    assert runner.rounds[0][0][0]["args"]["author"] == "Doe, Jane"


def test_sharepoint_without_a_display_name_is_not_fetched_rather_than_a_false_zero(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    ledger = gather.run(["sharepoint"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["sharepoint"].startswith("not fetched")
    assert runner.rounds == []


def test_the_store_is_readable_by_the_owner_only(tmp_path):
    root = tmp_path / "store"
    runner = FakeRunner(lambda tool, args: (chat_page(1), False))
    gather.run(["teams_mine"], root=root, now=NOW, runner=runner, me=ME)
    assert root.stat().st_mode & 0o077 == 0
    for p in root.rglob("*"):
        assert p.stat().st_mode & 0o077 == 0, p


# --- jira (shapes captured live 2026-11-13, values synthetic) -------------------------------

ATL = "mcp__claude_ai_Atlassian__"


def jira_responder(seen):
    def respond(tool, args):
        seen.append((tool, args))
        if tool == ATL + "getAccessibleAtlassianResources":
            return json.dumps([
                {"id": "conf-only", "url": "https://x.atlassian.net", "scopes": ["read:page:confluence"]},
                {"id": "cloud-1", "url": "https://x.atlassian.net", "scopes": ["read:jira-work", "write:jira-work"]},
            ]), False
        if tool == ATL + "searchJiraIssuesUsingJql":
            if args.get("nextPageToken") == "t1":
                return json.dumps({"issues": {"nodes": [{"key": "P-3"}], "pageInfo": {"hasNextPage": False, "endCursor": None}}}), False
            return json.dumps({"issues": {"nodes": [{"key": "P-1"}, {"key": "P-2"}],
                                          "pageInfo": {"hasNextPage": True, "endCursor": "t1"}}}), False
        if tool == ATL + "getJiraIssue":
            return json.dumps({"issues": {"nodes": [{"key": args["issueIdOrKey"], "changelog": {"histories": []}}]}}), False
        raise AssertionError(tool)
    return respond


def test_jira_snapshots_every_open_assigned_issue_with_its_changelog(tmp_path):
    seen = []
    ledger = gather.run(["jira"], root=tmp_path, now=NOW, runner=FakeRunner(jira_responder(seen)), me=ME)
    searches = [a for t, a in seen if t.endswith("searchJiraIssuesUsingJql")]
    assert all(a["cloudId"] == "cloud-1" for a in searches)
    assert "assignee = currentUser()" in searches[0]["jql"] and "statusCategory != Done" in searches[0]["jql"]
    assert [a.get("nextPageToken") for a in searches] == [None, "t1"]
    issues = [a for t, a in seen if t.endswith("getJiraIssue")]
    assert sorted(a["issueIdOrKey"] for a in issues) == ["P-1", "P-2", "P-3"]
    assert all(a["expand"] == "changelog" for a in issues)
    assert ledger["jira"] == "fetched 6 calls, 3 items"
    assert len(raw_records(tmp_path, "jira")) == 6
    assert "jira" not in read_state(tmp_path)["cursors"]


def test_jira_without_a_jira_site_is_an_error_not_an_empty_fetch(tmp_path):
    runner = FakeRunner(lambda tool, args: (json.dumps([{"id": "c", "scopes": ["read:page:confluence"]}]), False))
    ledger = gather.run(["jira"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["jira"].startswith("error:")
    assert raw_records(tmp_path, "jira") == []


# --- found in self-review 2026-11-13 ---------------------------------------------------------

def test_a_since_later_than_the_cursor_does_not_move_the_cursor_past_the_unfetched_gap(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    later = NOW + timedelta(days=7)
    gather.run(["teams_mine"], root=tmp_path, now=later, runner=runner, me=ME, since=later - timedelta(days=1))
    assert read_state(tmp_path)["cursors"]["teams_mine"] == (NOW - OVERLAP).isoformat()


def test_a_since_earlier_than_the_cursor_still_moves_it(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    later = NOW + timedelta(hours=1)
    gather.run(["teams_mine"], root=tmp_path, now=later, runner=runner, me=ME, since=NOW - timedelta(days=2))
    assert read_state(tmp_path)["cursors"]["teams_mine"] == (later - OVERLAP).isoformat()


def test_exit_code_ignores_sources_not_built_yet_but_not_errors():
    unbuilt = f"not fetched: {gather.NOT_FETCHED['teams_channels']}"
    assert gather.exit_code({"mail": "fetched 1 calls, 0 items", "teams_channels": unbuilt}) == 0
    assert gather.exit_code({"mail": "error: boom", "teams_channels": unbuilt}) == 1
    assert gather.exit_code({"sharepoint": "not fetched: no display name from get_me"}) == 1
    assert gather.exit_code({"mail": "capped at 2 pages"}) == 1
    assert gather.exit_code({"mail": "aborted: guard Bash"}) == 3


# --- from the independent review 2026-11-13 ---------------------------------------------------

import subprocess as _sp


def test_the_real_runner_denies_every_tool_not_listed(tmp_path, monkeypatch):
    # live 2026-11-13: without --permission-mode dontAsk an unlisted MCP tool ran (user mode is auto)
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["env"] = cmd, kw["env"]
        return _sp.CompletedProcess(cmd, 0, stream([]), "")

    monkeypatch.setattr(gather.subprocess, "run", fake_run)
    gather.claude_runner(tmp_path)([{"tool": SEARCH, "args": {}}], [SEARCH])
    cmd = seen["cmd"]
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    assert cmd[cmd.index("--tools") + 1] == ""
    assert "--no-session-persistence" in cmd
    allowed = cmd[cmd.index("--allowedTools") + 1:]
    assert allowed[0] == SEARCH
    assert seen["env"]["MAX_MCP_OUTPUT_TOKENS"] == gather.MCP_OUTPUT_TOKENS
    assert seen["env"]["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"


def test_the_runner_cleans_up_even_when_claude_times_out(tmp_path, monkeypatch):
    monkeypatch.setattr(gather.Path, "home", lambda: tmp_path / "home")
    root = tmp_path / "store"
    proj = tmp_path / "home" / ".claude" / "projects"
    cwd_key = __import__("re").sub(r"[^A-Za-z0-9]", "-", str((root / "run").resolve()))

    def fake_run(cmd, **kw):
        (proj / cwd_key).mkdir(parents=True)
        raise _sp.TimeoutExpired(cmd, 1)

    monkeypatch.setattr(gather.subprocess, "run", fake_run)
    import pytest as _pt
    with _pt.raises(Exception):
        gather.claude_runner(root)([{"tool": SEARCH, "args": {}}], [SEARCH])
    assert not (proj / cwd_key).exists()


@pytest.mark.parametrize("text", ["Error: token expired, reauthenticate", "<html>login</html>", ""])
def test_a_result_that_is_neither_json_nor_the_known_empty_text_is_an_error(tmp_path, text):
    runner = FakeRunner(lambda tool, args: (text, False))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"] == "error: unexpected result"
    assert raw_records(tmp_path, "teams_mine") == []
    assert "teams_mine" not in read_state(tmp_path).get("cursors", {})


def test_a_guard_abort_stops_the_whole_run(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False),
                        extra_uses=[("mcp__claude_ai_Microsoft_365__outlook_create_draft", {}, "ok", False)])
    ledger = gather.run(["teams_mine", "teams_chats"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"].startswith("aborted: guard")
    assert ledger["teams_chats"] == "not fetched: run stopped after a guard abort"
    assert len(runner.rounds) == 1


def test_ledger_lines_never_carry_result_or_stderr_text(tmp_path):
    secret = "PRIVATE TEAMS TEXT"

    def crash(calls, allowed):
        raise RuntimeError(f"claude exited 1: {secret}")

    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=crash, me=ME)
    tool_err = gather.run(["teams_chats"], root=tmp_path, now=NOW,
                          runner=FakeRunner(lambda t, a: (f"MCP error: {secret}", True)), me=ME)
    assert secret not in ledger["teams_mine"] and secret not in tool_err["teams_chats"]
    assert ledger["teams_mine"].startswith("error:") and tool_err["teams_chats"].startswith("error:")
    for p in (tmp_path / "ledger").glob("*.json"):
        assert secret not in p.read_text()
    logs = list((tmp_path / "logs").glob("*"))
    assert logs and any(secret in p.read_text() for p in logs)
    assert all(p.stat().st_mode & 0o077 == 0 for p in logs)


def test_since_on_a_first_run_does_not_mark_the_seven_day_window_as_fetched(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME, since=NOW - timedelta(days=1))
    assert "teams_mine" not in read_state(tmp_path)["cursors"]


def test_a_full_page_with_no_end_hint_is_capped_not_complete(tmp_path):
    runner = FakeRunner(lambda tool, args: (chat_page(25), False))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"].startswith("capped")


def test_github_uses_its_last_good_run_minus_a_day_not_a_fixed_seven_days(tmp_path):
    calls = []

    def gh(argv):
        calls.append(argv)
        return "[]"

    gather.run(["github"], root=tmp_path, now=NOW, runner=None, me=ME, gh=gh)
    later = NOW + timedelta(days=10)
    calls.clear()
    gather.run(["github"], root=tmp_path, now=later, runner=None, me=ME, gh=gh)
    updated = [a for argv in calls for a in argv if a.startswith("--updated=")]
    assert updated == [f"--updated=>={(NOW - timedelta(days=1)):%Y-%m-%d}"]


def test_a_full_gh_page_is_capped(tmp_path):
    full = json.dumps([{"number": i} for i in range(100)])
    ledger = gather.run(["github"], root=tmp_path, now=NOW, runner=None, me=ME, gh=lambda argv: full)
    assert ledger["github"] == "capped at gh limit 100"


def test_cli_writes_a_ledger_even_when_get_me_fails(tmp_path, monkeypatch):
    def broken(root):
        def runner(calls, allowed):
            raise RuntimeError("claude exited 1")
        return runner

    monkeypatch.setattr(gather, "claude_runner", broken)
    code = gather.main(["run", "--sources", "mail", "--root", str(tmp_path)])
    assert code == 1
    (ledger,) = list((tmp_path / "ledger").glob("*.json"))
    assert json.loads(ledger.read_text())["sources"]["mail"].startswith("error:")


# --- personal GitHub account (Alex, 2026-11-13: never gather from acastro2) -------------------

def test_github_is_never_fetched_as_the_personal_account(tmp_path):
    calls = []

    def gh(argv):
        calls.append(argv)
        return "acastro2\n" if argv[:2] == ["api", "user"] else "[]"

    ledger = gather.run(["github"], root=tmp_path, now=NOW, runner=None, me=ME, gh=gh)
    assert ledger["github"] == "not fetched: active gh account is the personal one"
    assert [a for a in calls if a[0] == "search"] == []
    assert raw_records(tmp_path, "github") == []
    assert gather.exit_code(ledger) == 1


def test_github_records_carry_the_login_they_were_fetched_as(tmp_path):
    gh = lambda argv: "work-login\n" if argv[:2] == ["api", "user"] else "[]"
    gather.run(["github"], root=tmp_path, now=NOW, runner=None, me=ME, gh=gh)
    recs = raw_records(tmp_path, "github")
    assert recs and all(r["args"]["login"] == "work-login" for r in recs)


def test_a_round_where_the_model_made_the_wrong_number_of_calls_is_asked_again():
    # live 2026-11-13: one jira run failed `call mismatch`, the next identical run was clean
    attempts = []

    def runner(calls, allowed):
        attempts.append(1)
        if len(attempts) == 1:
            return stream([])
        return stream([(c["tool"], c["args"], EMPTY, False) for c in calls])

    (call,) = gather.run_round(runner, [{"tool": SEARCH, "args": {"offset": 0}}])
    assert call["content"] == EMPTY and len(attempts) == 2


# --- from /code-review 2026-11-13 ------------------------------------------------------------

def test_covered_from_records_the_start_of_the_first_fetched_window_and_never_moves_later(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert read_state(tmp_path)["covered_from"]["teams_mine"] == (NOW - timedelta(days=7)).isoformat()
    gather.run(["teams_mine"], root=tmp_path, now=NOW + timedelta(days=1), runner=runner, me=ME)
    assert read_state(tmp_path)["covered_from"]["teams_mine"] == (NOW - timedelta(days=7)).isoformat()


def test_covered_from_moves_earlier_when_a_since_run_reaches_further_back(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME, since=NOW - timedelta(days=30))
    assert read_state(tmp_path)["covered_from"]["teams_mine"] == (NOW - timedelta(days=30)).isoformat()


def test_a_failed_get_me_still_lets_jira_and_github_run(tmp_path, monkeypatch):
    def runner_for(root):
        def runner(calls, allowed):
            if calls[0]["tool"].endswith("get_me"):
                raise RuntimeError("claude exited 1")
            return FakeRunner(jira_responder([]))(calls, allowed)
        return runner

    monkeypatch.setattr(gather, "claude_runner", runner_for)
    monkeypatch.setattr(gather, "real_gh", lambda argv: "work\n" if argv[:2] == ["api", "user"] else "[]")
    gather.main(["run", "--sources", "mail,jira,github", "--root", str(tmp_path)])
    (ledger,) = list((tmp_path / "ledger").glob("*.json"))
    lines = json.loads(ledger.read_text())["sources"]
    assert lines["mail"] == "error: get_me failed"
    assert lines["jira"].startswith("fetched") and lines["github"].startswith("fetched")


def test_jira_issues_are_read_in_batches_not_one_claude_run_each(tmp_path):
    runner = FakeRunner(jira_responder([]))
    ledger = gather.run(["jira"], root=tmp_path, now=NOW, runner=runner, me=ME)
    issue_rounds = [calls for calls, _ in runner.rounds if calls[0]["tool"].endswith("getJiraIssue")]
    assert len(issue_rounds) == 1 and len(issue_rounds[0]) == 3
    assert ledger["jira"] == "fetched 6 calls, 3 items"


def test_a_json_page_with_a_trailing_connector_note_is_valid(tmp_path):
    # live 2026-11-13: outlook_email_search ends its JSON objects with a short plain-text note
    page = chat_page(3) + "\n\nE-mail bodies are trimmed in search results. Use read_resource for the full text."
    runner = FakeRunner(lambda tool, args: (page, False))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert ledger["teams_mine"] == "fetched 1 calls, 3 items"
    assert raw_records(tmp_path, "teams_mine")[0]["content"] == page


# --- from the second /code-review 2026-11-13 -------------------------------------------------

def test_a_capped_first_run_pins_its_window_start_so_the_next_run_does_not_slide(tmp_path):
    runner = FakeRunner(lambda tool, args: (chat_page(25, args.get("offset", 0), more=args.get("offset", 0) + 25), False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME, max_pages=2)
    runner2 = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW + timedelta(days=1), runner=runner2, me=ME)
    first_after = runner2.rounds[0][0][0]["args"]["afterDateTime"]
    assert datetime.fromisoformat(first_after.replace("Z", "+00:00")) == NOW - timedelta(days=7)


def test_a_null_next_offset_ends_paging():
    page = chat_page(3) + json.dumps({"moreResults": False, "nextOffset": None})
    assert gather.next_args({"offset": 0}, page) is None


def test_spilled_tool_results_are_removed_even_when_claude_exits_non_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(gather.Path, "home", lambda: tmp_path / "home")
    root = tmp_path / "store"
    key = __import__("re").sub(r"[^A-Za-z0-9]", "-", str((root / "run").resolve()))
    spill = tmp_path / "home" / ".claude" / "projects" / key / "sess" / "tool-results" / "x.txt"

    def fake_run(cmd, **kw):
        spill.parent.mkdir(parents=True)
        spill.write_text("PRIVATE")
        return _sp.CompletedProcess(cmd, 1, "", "boom")

    monkeypatch.setattr(gather.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        gather.claude_runner(root)([{"tool": SEARCH, "args": {}}], [SEARCH])
    assert not spill.exists()


def test_one_jira_issue_error_does_not_throw_away_the_rest(tmp_path):
    base = jira_responder([])

    def respond(tool, args):
        if tool.endswith("getJiraIssue") and args["issueIdOrKey"] == "P-2":
            return "Issue does not exist or you do not have permission to see it.", True
        return base(tool, args)

    ledger = gather.run(["jira"], root=tmp_path, now=NOW, runner=FakeRunner(respond), me=ME)
    assert ledger["jira"] == "partial: 5 calls, 3 items, 1 issue errors"
    assert gather.exit_code(ledger) == 1
    assert "jira" not in read_state(tmp_path).get("last_ok", {})
    keys = [r["args"].get("issueIdOrKey") for r in raw_records(tmp_path, "jira")]
    assert "P-1" in keys and "P-3" in keys and "P-2" not in keys


def test_a_jira_page_with_more_but_no_cursor_is_an_unexpected_result(tmp_path):
    def respond(tool, args):
        if tool.endswith("searchJiraIssuesUsingJql"):
            return json.dumps({"issues": {"nodes": [{"key": "P-1"}], "pageInfo": {"hasNextPage": True}}}), False
        return jira_responder([])(tool, args)

    ledger = gather.run(["jira"], root=tmp_path, now=NOW, runner=FakeRunner(respond), me=ME)
    assert ledger["jira"] == "error: unexpected result"


def test_a_corrupt_state_file_still_writes_a_ledger(tmp_path):
    (tmp_path / "state.json").write_text("{trunc")
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=FakeRunner(lambda t, a: (EMPTY, False)), me=ME)
    assert ledger == {"teams_mine": "error: state unreadable"}
    assert list((tmp_path / "ledger").glob("*.json"))
    assert (tmp_path / "state.json").read_text() == "{trunc", "never overwrite a state file it could not read"


# --- from /reviewer + third /code-review 2026-11-13 ------------------------------------------
DAY = timedelta(days=1)


def windows(runner):
    out = []
    for calls, _ in runner.rounds:
        a = calls[0]["args"]
        out.append((a.get("afterDateTime"), a.get("beforeDateTime"), a.get("offset")))
    return out


def z(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_a_window_is_fetched_in_day_chunks_oldest_first(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=runner, me=ME, chunk=DAY)
    start = NOW - timedelta(days=7)
    assert windows(runner) == [(z(start + k * DAY), z(min(start + (k + 1) * DAY, NOW)), 0) for k in range(7)]
    assert ledger["teams_mine"] == "fetched 7 calls, 0 items"


def test_a_capped_chunk_keeps_the_days_before_it_and_the_next_run_resumes_there(tmp_path):
    start = NOW - timedelta(days=7)
    third = z(start + 2 * DAY)

    def respond(tool, args):
        if args["afterDateTime"] == third:
            off = args.get("offset", 0)
            return chat_page(25, off, more=off + 25), False
        return EMPTY, False

    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=FakeRunner(respond), me=ME, chunk=DAY, max_pages=2)
    assert ledger["teams_mine"] == "capped at 2 pages"
    state = read_state(tmp_path)
    assert state["cursors"]["teams_mine"] == (start + 2 * DAY).isoformat()
    assert state["covered_from"]["teams_mine"] == start.isoformat()
    runner2 = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["teams_mine"], root=tmp_path, now=NOW + timedelta(hours=1), runner=runner2, me=ME, chunk=DAY)
    assert windows(runner2)[0][0] == third


def test_the_cli_fetches_in_one_day_chunks(tmp_path, monkeypatch):
    seen = FakeRunner(lambda tool, args: (EMPTY, False))
    monkeypatch.setattr(gather, "claude_runner", lambda root: seen)
    gather.main(["run", "--sources", "teams_mine", "--me", ME, "--me-name", "X", "--since", "3d", "--root", str(tmp_path)])
    spans = [(datetime.fromisoformat(b.replace("Z", "+00:00")) - datetime.fromisoformat(a.replace("Z", "+00:00")))
             for a, b, _ in windows(seen)]
    assert len(spans) == 3 and all(sp <= DAY for sp in spans)


def test_calendar_reaches_two_weeks_ahead_in_one_chain(tmp_path):
    runner = FakeRunner(lambda tool, args: (EMPTY, False))
    gather.run(["calendar"], root=tmp_path, now=NOW, runner=runner, me=ME, chunk=DAY)
    assert len(runner.rounds) == 1
    assert runner.rounds[0][0][0]["args"]["beforeDateTime"] == z(NOW + timedelta(days=14))


def test_more_results_false_ends_paging_even_with_a_next_offset():
    page = chat_page(3) + json.dumps({"moreResults": False, "nextOffset": 25})
    assert gather.next_args({"offset": 0}, page) is None


def test_a_jira_search_without_the_issues_envelope_is_an_unexpected_result(tmp_path):
    def respond(tool, args):
        if tool.endswith("searchJiraIssuesUsingJql"):
            return json.dumps({"data": {"issues": {"nodes": [{"key": "P-1"}]}}}), False
        return jira_responder([])(tool, args)

    ledger = gather.run(["jira"], root=tmp_path, now=NOW, runner=FakeRunner(respond), me=ME)
    assert ledger["jira"] == "error: unexpected result"


def test_a_bare_json_error_body_is_an_unexpected_result(tmp_path):
    body = json.dumps({"error": "InvalidAuthenticationToken", "message": "Access token has expired."})
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=FakeRunner(lambda t, a: (body, False)), me=ME)
    assert ledger["teams_mine"] == "error: unexpected result"


@pytest.mark.parametrize("bad", [{"cursors": None}, {"last_ok": []}, {"covered_from": "x"}])
def test_a_state_file_with_a_wrong_shaped_key_is_unreadable(tmp_path, bad):
    (tmp_path / "state.json").write_text(json.dumps(bad))
    ledger = gather.run(["teams_mine"], root=tmp_path, now=NOW, runner=FakeRunner(lambda t, a: (EMPTY, False)), me=ME)
    assert ledger == {"teams_mine": "error: state unreadable"}


def test_state_and_ledger_are_saved_after_each_source_so_a_crash_keeps_finished_work(tmp_path):
    def runner(calls, allowed):
        if calls[0]["args"].get("recipient"):
            raise KeyboardInterrupt
        return stream([(c["tool"], c["args"], EMPTY, False) for c in calls])

    with pytest.raises(KeyboardInterrupt):
        gather.run(["teams_mine", "teams_chats"], root=tmp_path, now=NOW, runner=runner, me=ME)
    assert "teams_mine" in read_state(tmp_path)["cursors"]
    (ledger,) = list((tmp_path / "ledger").glob("*.json"))
    assert json.loads(ledger.read_text())["sources"]["teams_mine"].startswith("fetched")


def test_prune_removes_raw_days_and_logs_older_than_the_limit(tmp_path):
    old_day, new_day = (NOW - timedelta(days=40)).strftime("%Y-%m-%d"), NOW.strftime("%Y-%m-%d")
    for d in (old_day, new_day):
        (tmp_path / "raw" / "mail" / d).mkdir(parents=True)
        (tmp_path / "raw" / "mail" / d / "r-1.json").write_text("{}")
    (tmp_path / "logs").mkdir()
    old_log = tmp_path / "logs" / f"{(NOW - timedelta(days=40)):%Y%m%dT%H%M%S}-aaaaaa.log"
    new_log = tmp_path / "logs" / f"{NOW:%Y%m%dT%H%M%S}-bbbbbb.log"
    old_log.write_text("x"); new_log.write_text("y")
    removed = gather.prune(tmp_path, older_than=timedelta(days=30), now=NOW)
    assert not (tmp_path / "raw" / "mail" / old_day).exists() and (tmp_path / "raw" / "mail" / new_day).exists()
    assert not old_log.exists() and new_log.exists()
    assert removed == 2
