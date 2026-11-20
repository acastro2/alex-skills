"""Behaviour tests for the gather `slack` source: docs/specs/gather-slack.md.

`opencode run` is the boundary. Fake stdout has the event shape captured live on 2026-11-20
(one JSON line per tool call, `part.state.output` is the MCP text); every message text here is
synthetic. Fetch logic is tested through an injected slack runner; the real runner is tested
with a fake `subprocess.run` and a fake session-delete function, so no test starts opencode.
"""
import importlib.util
import json
import re
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

if "gather" in sys.modules:
    gather = sys.modules["gather"]
else:
    _spec = importlib.util.spec_from_file_location(
        "gather", Path(__file__).resolve().parents[1] / "scripts" / "gather.py")
    gather = importlib.util.module_from_spec(_spec)
    sys.modules["gather"] = gather
    _spec.loader.exec_module(gather)

NOW = datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)
UID = "UME123"
PROFILE = "slack_slack_read_user_profile"
SEARCH = "slack_slack_search_public_and_private"
READ_CHANNEL = "slack_slack_read_channel"
READ_THREAD = "slack_slack_read_thread"
NO_MORE = "There are no more messages available."
OVERLAP = timedelta(minutes=15)
LINK = "https://example.slack.com/archives"


# --- fake opencode stdout ---------------------------------------------------------------------

def tool_event(tool, args, output, sid="ses_a", status="completed", truncated=False):
    state = {"status": status, "input": args}
    if status == "completed":
        state["output"] = output
        state["metadata"] = {"truncated": truncated, "content": [{"type": "text", "text": output}]}
    else:
        state["error"] = output
    return json.dumps({"type": "tool_use", "sessionID": sid,
                       "part": {"type": "tool", "tool": tool, "state": state}})


def oc_stream(events, sid="ses_a"):
    head = [json.dumps({"type": "step_start", "sessionID": sid, "part": {"type": "step-start"}})]
    tail = [json.dumps({"type": "text", "sessionID": sid, "part": {"type": "text", "text": "DONE"}})]
    return "\n".join(head + events + tail) + "\n"


def profile_json(uid=UID):
    return json.dumps({"result": f"User ID: {uid}\nName: Test User"})


def hit(cid, path, name="chan", extra=""):
    return {"cid": cid, "name": name, "link": f"{LINK}/{cid}/{path}{extra}"}


def search_json(hits, info=NO_MORE):
    md = "\n\n".join(
        f"### Result {i} of {len(hits)}\nChannel: {h['name']} (ID: {h['cid']})\nParticipants: a, b\n"
        f"From: a\nTime: 2026-11-20 10:54:00 CST\nPermalink: {h['link']}\nText: synthetic {i}"
        for i, h in enumerate(hits, 1))
    return json.dumps({"results": md, "pagination_info": info})


def read_json(text="synthetic messages", info=NO_MORE):
    return json.dumps({"messages": text, "pagination_info": info})


def cursor_info(c):
    return f"For the next page of results use cursor `{c}`"


class World:
    """Answers each slack call. `dm`, `mentions`, `own` are the hits of the three searches."""

    def __init__(self, dm=(), mentions=(), own=(), uid=UID):
        self.dm, self.mentions, self.own, self.uid = list(dm), list(mentions), list(own), uid
        self.rounds = []
        self.closed = False

    def close(self):
        self.closed = True

    def respond(self, tool, args):
        if tool == PROFILE:
            return profile_json(self.uid), False
        if tool == SEARCH:
            hits = self.dm if "channel_types" in args else self.mentions if args["keywords"] else self.own
            return search_json(hits), False
        return read_json(f"{tool} {json.dumps(args, sort_keys=True)}"), False

    def __call__(self, calls, allowed):
        self.rounds.append((calls, allowed))
        return oc_stream([tool_event(c["tool"], c["args"], self.respond(c["tool"], c["args"])[0])
                          for c in calls])

    def calls(self, tool):
        return [c["args"] for calls, _ in self.rounds for c in calls if c["tool"] == tool]


def run_slack(tmp_path, runner, now=NOW, **kw):
    return gather.run(["slack"], root=tmp_path, now=now, runner=None, me=None, slack_runner=runner, **kw)


def raw_records(root, source="slack"):
    return [json.loads(p.read_text()) for p in sorted((root / "raw" / source).rglob("*.json"))]


def read_state(root):
    p = root / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


# --- raw record -------------------------------------------------------------------------------

def test_raw_record_content_is_the_tool_output_byte_for_byte(tmp_path):
    world = World(dm=[hit("D1", "p1763600000000100", "dm")])
    ledger = run_slack(tmp_path, world)
    assert ledger["slack"].startswith("fetched")
    recs = raw_records(tmp_path)
    by_tool = {r["tool"]: r for r in recs}
    dm_search = next(r for r in recs if r["tool"] == SEARCH and "channel_types" in r["args"])
    assert dm_search["content"] == search_json([hit("D1", "p1763600000000100", "dm")])
    assert by_tool[PROFILE]["content"] == profile_json()
    for r in recs:
        assert r["source"] == "slack" and r["provenance"] == "verbatim"
    read = next(r for r in recs if r["tool"] == READ_CHANNEL)
    assert read["content"] == read_json(f"{READ_CHANNEL} {json.dumps(read['args'], sort_keys=True)}")


# --- guard and spill --------------------------------------------------------------------------

def test_a_tool_outside_the_allowlist_aborts_the_source_and_stores_nothing(tmp_path):
    def runner(calls, allowed):
        events = [tool_event(c["tool"], c["args"], profile_json()) for c in calls]
        return oc_stream(events + [tool_event("slack_slack_send_message", {"text": "x"}, "{}")])

    ledger = run_slack(tmp_path, runner)
    assert ledger["slack"] == "aborted: guard slack_slack_send_message"
    assert raw_records(tmp_path) == []
    assert "slack" not in read_state(tmp_path).get("cursors", {})
    assert gather.exit_code(ledger) == 3


def test_a_cut_tool_output_is_error_spill_and_nothing_is_stored(tmp_path):
    def runner(calls, allowed):
        (c,) = calls
        return oc_stream([tool_event(c["tool"], c["args"], profile_json(), truncated=True)])

    ledger = run_slack(tmp_path, runner)
    assert ledger["slack"] == "error: spill"
    assert raw_records(tmp_path) == []


def test_a_failed_tool_call_is_error_tool_error(tmp_path):
    def runner(calls, allowed):
        (c,) = calls
        return oc_stream([tool_event(c["tool"], c["args"], "channel_not_found", status="error")])

    assert run_slack(tmp_path, runner)["slack"] == "error: tool error"


def test_only_the_tools_a_round_needs_are_allowed(tmp_path):
    world = World(dm=[hit("D1", "p1763600000000100")])
    run_slack(tmp_path, world)
    allowed = [a for _, a in world.rounds]
    assert allowed[0] == [PROFILE]
    assert allowed[1] == [SEARCH]
    assert allowed[2] == [READ_CHANNEL]


# --- the user id ------------------------------------------------------------------------------

def test_no_user_id_in_the_profile_is_error_no_slack_user_id(tmp_path):
    world = World()
    world.respond = lambda tool, args: (json.dumps({"result": "no id here"}), False)
    ledger = run_slack(tmp_path, world)
    assert ledger["slack"] == "error: no slack user id"
    assert gather.exit_code(ledger) == 1
    assert "slack" not in read_state(tmp_path).get("cursors", {})


# --- search and read arguments ----------------------------------------------------------------

def test_searches_use_the_day_before_the_window_start(tmp_path):
    # Slack `after:` leaves out the date typed, so a window that starts on the 10th needs the 9th
    world = World()
    run_slack(tmp_path, world, since=datetime(2026, 11, 10, 0, 30, tzinfo=timezone.utc))
    base = {"limit": 20, "include_context": False, "natural_language_query": "", "sort": "timestamp"}
    assert sorted(world.calls(SEARCH), key=lambda a: a["filters"]) == sorted([
        {**base, "keywords": [], "filters": "after:2026-11-09", "channel_types": "im,mpim"},
        {**base, "keywords": [f"<@{UID}>"], "filters": "after:2026-11-09"},
        {**base, "keywords": [], "filters": f"from:<@{UID}> after:2026-11-09"},
    ], key=lambda a: a["filters"])


def test_a_dm_channel_is_read_from_the_window_start_epoch(tmp_path):
    since = datetime(2026, 11, 10, 8, 15, tzinfo=timezone.utc)
    world = World(dm=[hit("D1", "p1763600000000100", "dm"), hit("D1", "p1763600000000200", "dm"),
                      hit("D2", "p1763600000000300", "dm")],
                  mentions=[hit("C9", "p1763600000000400")])
    run_slack(tmp_path, world, since=since)
    oldest = str(int(since.timestamp()))
    assert world.calls(READ_CHANNEL) == [
        {"channel_id": "D1", "oldest": oldest, "limit": 100},
        {"channel_id": "D2", "oldest": oldest, "limit": 100},
    ]


def test_thread_targets_come_from_thread_ts_and_from_the_p_path_part_and_are_deduped(tmp_path):
    root_hit = hit("C1", "p1763657640123456")
    replied = hit("C1", "p1763657700000200", extra="?thread_ts=1763650000.000100&cid=C1")
    dm_reply = hit("D1", "p1763600000000500", "dm", extra="?thread_ts=1763500000.000300&cid=D1")
    dm_plain = hit("D1", "p1763600000000100", "dm")
    world = World(dm=[dm_plain, dm_reply], mentions=[root_hit, replied], own=[root_hit])
    run_slack(tmp_path, world)
    threads = [(a["channel_id"], a["message_ts"]) for a in world.calls(READ_THREAD)]
    assert sorted(threads) == [("C1", "1763650000.000100"), ("C1", "1763657640.123456"),
                               ("D1", "1763500000.000300")]
    assert all(a["limit"] == 100 for a in world.calls(READ_THREAD))


def test_a_round_holds_at_most_ten_calls(tmp_path):
    hits = [hit("C1", f"p17636576{i:02d}000000") for i in range(12)]
    world = World(mentions=hits)
    run_slack(tmp_path, world)
    assert len(world.calls(READ_THREAD)) == 12
    assert all(len(calls) <= 10 for calls, _ in world.rounds)


# --- paging -----------------------------------------------------------------------------------

def test_a_search_follows_its_cursor_until_no_more(tmp_path):
    seen = []

    def respond(tool, args):
        if tool == PROFILE:
            return profile_json(), False
        if tool != SEARCH:
            return read_json(), False
        if "channel_types" in args or not args["keywords"]:
            return search_json([]), False
        seen.append(args.get("cursor"))
        if args.get("cursor") is None:
            return search_json([hit("C1", "p1763657640123456")], cursor_info("abc==")), False
        return search_json([hit("C2", "p1763657640123457")], NO_MORE), False

    world = World()
    world.respond = respond
    ledger = run_slack(tmp_path, world)
    assert seen == [None, "abc=="]
    # profile + 3 searches + 1 more mention page + 2 thread reads; items are the search hits
    assert ledger["slack"] == "fetched 7 calls, 2 items"


def test_a_read_follows_its_cursor_too(tmp_path):
    pages = {None: read_json("first", cursor_info("c2")), "c2": read_json("second", NO_MORE)}

    def respond(tool, args):
        if tool == READ_CHANNEL:
            return pages[args.get("cursor")], False
        return World(dm=[hit("D1", "p1763600000000100", "dm")]).respond(tool, args)

    world = World()
    world.respond = respond
    run_slack(tmp_path, world)
    reads = [r["content"] for r in raw_records(tmp_path) if r["tool"] == READ_CHANNEL]
    assert reads == [pages[None], pages["c2"]]
    assert [a.get("cursor") for a in world.calls(READ_CHANNEL)] == [None, "c2"]


def test_a_chain_that_reaches_max_pages_is_capped_and_the_cursor_does_not_move(tmp_path):
    def respond(tool, args):
        if tool == PROFILE:
            return profile_json(), False
        return search_json([], cursor_info("again")), False

    world = World()
    world.respond = respond
    ledger = run_slack(tmp_path, world, max_pages=2)
    assert ledger["slack"] == "capped at 2 pages"
    state = read_state(tmp_path)
    assert state["cursors"]["slack"] == (NOW - timedelta(days=7)).isoformat()
    assert "slack" not in state.get("covered_from", {})
    assert len(world.calls(SEARCH)) == 6


def test_a_full_search_page_with_no_end_hint_is_capped(tmp_path):
    full = [hit("C1", f"p17636576{i:02d}000000") for i in range(20)]

    def respond(tool, args):
        if tool == PROFILE:
            return profile_json(), False
        if tool == SEARCH and args["keywords"]:
            return search_json(full, ""), False
        return World().respond(tool, args)

    world = World()
    world.respond = respond
    assert run_slack(tmp_path, world)["slack"] == "capped at 1 pages"


# --- cursor and state -------------------------------------------------------------------------

def test_the_cursor_moves_to_run_start_minus_fifteen_minutes_only_on_fetched(tmp_path):
    world = World()
    assert run_slack(tmp_path, world)["slack"].startswith("fetched")
    state = read_state(tmp_path)
    assert state["cursors"]["slack"] == (NOW - OVERLAP).isoformat()
    assert state["covered_from"]["slack"] == (NOW - timedelta(days=7)).isoformat()


def test_a_failed_run_leaves_the_cursor_where_it_was(tmp_path):
    run_slack(tmp_path, World())
    before = read_state(tmp_path)

    def broken(calls, allowed):
        raise RuntimeError("opencode exited 1")

    ledger = run_slack(tmp_path, broken, now=NOW + timedelta(hours=2))
    assert ledger["slack"] == "error: opencode failed"
    assert read_state(tmp_path) == before


def test_the_next_window_starts_at_the_cursor(tmp_path):
    run_slack(tmp_path, World())
    world = World()
    later = NOW + timedelta(days=1)
    run_slack(tmp_path, world, now=later)
    start = NOW - OVERLAP
    expected = f"after:{(start - timedelta(days=1)).strftime('%Y-%m-%d')}"
    assert {a["filters"].split()[-1] for a in world.calls(SEARCH)} == {expected}


def test_slack_does_not_start_a_get_me_call(tmp_path, monkeypatch):
    def claude(root):
        def runner(calls, allowed):
            raise AssertionError("claude -p must not run for slack")
        return runner

    world = World()
    monkeypatch.setattr(gather, "claude_runner", claude)
    monkeypatch.setattr(gather, "opencode_runner", lambda root, **kw: world)
    assert gather.main(["run", "--sources", "slack", "--root", str(tmp_path)]) == 0
    assert world.closed
    (ledger,) = list((tmp_path / "ledger").glob("*.json"))
    assert json.loads(ledger.read_text())["sources"]["slack"].startswith("fetched")


def test_slack_is_a_default_source():
    assert "slack" in gather.SOURCES


# --- the real runner: models and sessions -----------------------------------------------------

FIRST_MODEL, GO_MODEL = gather.SLACK_MODELS


def fake_opencode(outcomes):
    """Replaces subprocess.run. `outcomes` maps a model to (returncode, stdout, stderr) or an exception."""
    seen = []

    def fake_run(cmd, **kw):
        assert cmd[0] == "opencode"
        model = cmd[cmd.index("-m") + 1]
        seen.append({"cmd": cmd, "cwd": kw.get("cwd"), "model": model})
        out = outcomes[model]
        if isinstance(out, BaseException):
            raise out
        return subprocess.CompletedProcess(cmd, out[0], out[1], out[2])

    return fake_run, seen


PROFILE_ARGS = {"response_format": "detailed"}
def runner_for(root, delete, lister=lambda: [], **kw):
    return gather.opencode_runner(root, delete=delete, lister=lister, **kw)


CALL = [{"tool": PROFILE, "args": PROFILE_ARGS}]
GOOD = oc_stream([tool_event(PROFILE, PROFILE_ARGS, profile_json(), sid="ses_good")], sid="ses_good")


def test_the_runner_asks_opencode_for_the_exact_calls_in_a_private_cwd(tmp_path, monkeypatch):
    run, seen = fake_opencode({FIRST_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    out = runner_for(tmp_path, delete=lambda sid: None)(CALL, [PROFILE])
    assert out == GOOD
    cmd, cwd = seen[0]["cmd"], seen[0]["cwd"]
    assert cwd == tmp_path / "run-opencode"
    assert stat.S_IMODE(cwd.stat().st_mode) == 0o700
    assert cmd[cmd.index("--agent") + 1] == "gather-slack"
    assert "--archived" in cmd and cmd[cmd.index("--format") + 1] == "json"
    assert json.loads(cmd[-1][cmd[-1].index("["):]) == CALL
    config = (cwd / "opencode.jsonc").read_text()
    assert "slack_slack_send_message" not in config
    assert '"snapshots": false' in config and "20000000" in config
    assert "Pass each args object exactly as given. Add no keys." in config


def test_every_session_id_seen_in_stdout_is_deleted(tmp_path, monkeypatch):
    two = oc_stream([tool_event(PROFILE, {}, profile_json(), sid="ses_one")], sid="ses_one") + \
        oc_stream([tool_event(PROFILE, {}, profile_json(), sid="ses_two")], sid="ses_two")
    run, _ = fake_opencode({FIRST_MODEL: (0, two, "")})
    deleted = []
    monkeypatch.setattr(gather.subprocess, "run", run)
    runner = runner_for(tmp_path, delete=deleted.append)
    runner(CALL, [PROFILE])
    assert sorted(deleted) == ["ses_one", "ses_two"]


def test_a_session_is_deleted_when_the_run_exits_non_zero(tmp_path, monkeypatch):
    run, _ = fake_opencode({FIRST_MODEL: (1, GOOD, "boom"), GO_MODEL: (1, GOOD, "boom")})
    deleted = []
    monkeypatch.setattr(gather.subprocess, "run", run)
    with pytest.raises(RuntimeError):
        runner_for(tmp_path, delete=deleted.append)(CALL, [PROFILE])
    assert set(deleted) == {"ses_good"}


def test_a_failed_delete_goes_to_orphans_and_the_next_run_deletes_it_first(tmp_path, monkeypatch):
    run, _ = fake_opencode({FIRST_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)

    def refuse(sid):
        raise RuntimeError("delete failed")

    runner_for(tmp_path, delete=refuse)(CALL, [PROFILE])
    orphans = tmp_path / "run-opencode" / "orphans"
    assert orphans.read_text().split() == ["ses_good"]
    assert stat.S_IMODE(orphans.stat().st_mode) == 0o600

    deleted = []
    runner_for(tmp_path, delete=deleted.append)(CALL, [PROFILE])
    assert deleted[0] == "ses_good"
    assert not orphans.exists()


def test_a_model_failure_retries_once_on_opencode_go_and_keeps_it(tmp_path, monkeypatch):
    run, seen = fake_opencode({FIRST_MODEL: (1, "", "provider error"), GO_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    runner = runner_for(tmp_path, delete=lambda sid: None)
    assert runner(CALL, [PROFILE]) == GOOD
    assert runner(CALL, [PROFILE]) == GOOD
    assert [s["model"] for s in seen] == [FIRST_MODEL, GO_MODEL, GO_MODEL]
    assert any(n.startswith("slack: fell back to opencode-go: ") for n in runner.notes)


@pytest.mark.parametrize("failure", [
    subprocess.TimeoutExpired("opencode", 1),
    (0, json.dumps({"type": "error", "error": {"name": "ProviderError"}}) + "\n", ""),
])
def test_a_timeout_or_an_error_event_with_no_tool_parts_falls_back(tmp_path, monkeypatch, failure):
    run, seen = fake_opencode({FIRST_MODEL: failure, GO_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    runner = runner_for(tmp_path, delete=lambda sid: None)
    assert runner(CALL, [PROFILE]) == GOOD
    assert [s["model"] for s in seen] == [FIRST_MODEL, GO_MODEL]


def test_failing_on_both_models_is_error_opencode_failed(tmp_path, monkeypatch):
    run, _ = fake_opencode({FIRST_MODEL: (1, "", "a"), GO_MODEL: (1, "", "b")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    runner = runner_for(tmp_path, delete=lambda sid: None)
    ledger = gather.run(["slack"], root=tmp_path, now=NOW, runner=None, me=None, slack_runner=runner)
    assert ledger["slack"] == "error: opencode failed"
    log = next((tmp_path / "logs").glob("*.log")).read_text()
    assert "slack: fell back to opencode-go" in log


def test_runner_config_uses_v2_agent_keys_and_denies_everything_first():
    # proven live 2026-11-20 with `agents` + `system`; the V1 `agent`/`prompt` form was not
    cfg = json.loads(gather.opencode_config(["slack_slack_read_thread"]))
    agent = cfg["agents"][gather.SLACK_AGENT]
    assert "agent" not in cfg and "system" in agent
    assert agent["permissions"][0] == {"action": "*", "resource": "*", "effect": "deny"}
    assert agent["permissions"][1:] == [{"action": "slack_slack_read_thread", "resource": "*", "effect": "allow"}]
    assert cfg["tool_output"]["max_bytes"] >= 20000000


def test_the_profile_call_passes_response_format_concise_and_nothing_else(tmp_path):
    # live 2026-11-20: with {} the model added `user_id: ""` and the call failed
    world = World()
    run_slack(tmp_path, world)
    assert world.calls(PROFILE) == [{"response_format": "detailed"}]


def test_the_model_order_is_claude_agent_then_opencode_go():
    assert gather.SLACK_MODELS == ("claude-agent/haiku", "opencode-go/deepseek-v4.1-flash#high")


def test_the_config_allows_all_four_read_tools_and_is_written_once(tmp_path, monkeypatch):
    # rewriting it before each run raced OpenCode's config reload: "Agent not found" (live 2026-11-20)
    run, _ = fake_opencode({FIRST_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    runner = runner_for(tmp_path, delete=lambda sid: None)
    path = tmp_path / "run-opencode" / "opencode.jsonc"
    runner(CALL, [PROFILE])
    first = path.stat().st_ino
    runner([{"tool": SEARCH, "args": {}}], [SEARCH])
    assert path.stat().st_ino == first
    perms = json.loads(path.read_text())["agents"][gather.SLACK_AGENT]["permissions"]
    assert perms[0] == {"action": "*", "resource": "*", "effect": "deny"}
    assert {p["action"] for p in perms[1:]} == {PROFILE, SEARCH, READ_CHANNEL, READ_THREAD}
    assert all(p["effect"] == "allow" for p in perms[1:])


def test_a_stale_config_is_rewritten(tmp_path, monkeypatch):
    run, _ = fake_opencode({FIRST_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    path = tmp_path / "run-opencode" / "opencode.jsonc"
    gather.mkdir_private(path.parent)
    path.write_text("{}")
    runner_for(tmp_path, delete=lambda sid: None)(CALL, [PROFILE])
    assert json.loads(path.read_text()) == json.loads(gather.opencode_config())


def test_a_run_with_calls_asked_but_no_tool_parts_falls_back(tmp_path, monkeypatch):
    # live 2026-11-20: the Cursor model said "Tool not found" and made no tool call, exit 0
    no_tools = oc_stream([], sid="ses_none")
    run, seen = fake_opencode({FIRST_MODEL: (0, no_tools, ""), GO_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    runner = runner_for(tmp_path, delete=lambda sid: None)
    assert runner(CALL, [PROFILE]) == GOOD
    assert [s["model"] for s in seen] == [FIRST_MODEL, GO_MODEL]


def claude_project(home, cwd):
    return home / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(Path(cwd).resolve()))


@pytest.mark.parametrize("returncode", [0, 1])
def test_the_claude_project_folder_of_the_run_cwd_is_removed_after_every_attempt(tmp_path, monkeypatch, returncode):
    # claude-agent/haiku saves Claude Code sessions, tool results included, under ~/.claude/projects
    home = tmp_path / "home"
    monkeypatch.setattr(gather.Path, "home", lambda: home)
    root = tmp_path / "store"
    mine = claude_project(home, root / "run-opencode")
    sibling = home / ".claude" / "projects" / "-some-real-project"
    sibling.mkdir(parents=True)
    (sibling / "keep.jsonl").write_text("alex")

    def fake_run(cmd, **kw):
        (mine / "sub").mkdir(parents=True)
        (mine / "sub" / "session.jsonl").write_text("slack text")
        return subprocess.CompletedProcess(cmd, returncode, GOOD, "x")

    monkeypatch.setattr(gather.subprocess, "run", fake_run)
    runner = runner_for(root, delete=lambda sid: None)
    try:
        runner(CALL, [PROFILE])
    except RuntimeError:
        pass
    assert not mine.exists()
    assert (sibling / "keep.jsonl").read_text() == "alex"


def test_a_symlinked_project_folder_is_never_followed(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setattr(gather.Path, "home", lambda: home)
    root = tmp_path / "store"
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "keep.txt").write_text("alex")
    link = claude_project(home, root / "run-opencode")
    link.parent.mkdir(parents=True)
    link.symlink_to(target, target_is_directory=True)
    run, _ = fake_opencode({FIRST_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    runner_for(root, delete=lambda sid: None)(CALL, [PROFILE])
    assert (target / "keep.txt").read_text() == "alex"


# --- sessions that never reached stdout -------------------------------------------------------

def row(sid, directory):
    return {"id": sid, "directory": directory, "projectId": "p", "title": "t", "created": 1, "updated": 2}


def test_only_sessions_of_the_exact_run_directory_are_deleted(tmp_path, monkeypatch):
    # a non-git folder can share a project with other folders, so the listing alone decides nothing
    mine = str((tmp_path / "run-opencode").resolve())
    rows = [row("ses_mine", mine), row("ses_other", str(tmp_path / "elsewhere")),
            row("ses_prefix", mine + "-2"), row("ses_child", mine + "/sub")]
    run, _ = fake_opencode({FIRST_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    deleted = []
    runner = runner_for(tmp_path, delete=deleted.append, lister=lambda: rows)
    runner(CALL, [PROFILE])
    assert sorted(deleted) == ["ses_good", "ses_mine"]
    deleted.clear()
    runner.close()
    assert deleted == ["ses_mine"]


def test_the_first_call_deletes_listed_sessions_before_orphans(tmp_path, monkeypatch):
    run, _ = fake_opencode({FIRST_MODEL: (0, GOOD, "")})
    monkeypatch.setattr(gather.subprocess, "run", run)
    cwd = tmp_path / "run-opencode"
    gather.mkdir_private(cwd)
    (cwd / "orphans").write_text("ses_orphan\n")
    deleted = []
    runner_for(tmp_path, delete=deleted.append,
               lister=lambda: [row("ses_mine", str(cwd.resolve()))])(CALL, [PROFILE])
    assert deleted[:2] == ["ses_mine", "ses_orphan"]
    assert not (cwd / "orphans").exists()


def test_a_listed_session_that_cannot_be_deleted_goes_to_orphans(tmp_path):
    def refuse(sid):
        raise RuntimeError("delete failed")

    mine = str((tmp_path / "run-opencode").resolve())
    runner_for(tmp_path, delete=refuse, lister=lambda: [row("ses_mine", mine)]).close()
    assert (tmp_path / "run-opencode" / "orphans").read_text().split() == ["ses_mine"]


def test_a_list_failure_is_a_note_and_never_an_exception(tmp_path):
    def broken():
        raise RuntimeError("opencode session list exited 1")

    deleted = []
    runner = runner_for(tmp_path, delete=deleted.append, lister=broken)
    runner.close()
    assert deleted == []
    assert any("session list failed" in n for n in runner.notes)


def test_the_real_lister_runs_in_the_run_cwd_and_bad_json_is_a_note(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, **kw):
        seen.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, 0, "not json", "")

    monkeypatch.setattr(gather.subprocess, "run", fake_run)
    runner = gather.opencode_runner(tmp_path, delete=lambda sid: None)
    runner.close()
    (cmd, kw), = seen
    assert cmd[:3] == ["opencode", "session", "list"] and cmd[cmd.index("--format") + 1] == "json"
    assert kw["cwd"] == tmp_path / "run-opencode" and kw["timeout"] == 60
    assert any("session list failed" in n for n in runner.notes)


def test_cmd_run_closes_the_slack_runner_even_when_run_raises(tmp_path, monkeypatch):
    world = World()
    monkeypatch.setattr(gather, "opencode_runner", lambda root, **kw: world)
    monkeypatch.setattr(gather, "run", lambda *a, **kw: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        gather.main(["run", "--sources", "slack", "--root", str(tmp_path)])
    assert world.closed
