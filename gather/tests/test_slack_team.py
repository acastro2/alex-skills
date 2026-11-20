"""Behaviour tests for the gather `slack_team` source: the team's Slack channels, read in full.

`slack` covers only Alex's DMs, mentions and own posts. weekly-report's team section needs the
team channels too, so `slack_team` reads each configured channel from the window start and every
thread that has replies. Same runner, same store, same cursor rules as `slack`.
"""
import json
from datetime import datetime, timedelta, timezone

from test_slack import (NOW, NO_MORE, OVERLAP, READ_CHANNEL, READ_THREAD, PROFILE, SEARCH,
                        cursor_info, gather, oc_stream, raw_records, read_json, read_state,
                        tool_event)

CHANS = ["C0TEAM1", "C0TEAM2"]


def channel_md(cid, messages):
    """messages: [(ts, text, replies)] in the read_channel markdown shape seen live 2026-11-20."""
    parts = [f"Channel: #team (ID: {cid})\n"]
    for ts, text, replies in messages:
        block = (f"=== Message from A <a@example.com> (UA1) at 2026-11-19 10:00:00 CST === \n"
                 f"Message TS: {ts}\n{text}")
        if replies:
            block += f"\nThread: {replies} replies (latest: 2026-11-19 11:00:00 CST)"
        parts.append(block)
    return "\n\n".join(parts)


class TeamWorld:
    def __init__(self, channels=None, threads=None):
        self.channels = channels or {}
        self.threads = threads or {}
        self.rounds = []
        self.closed = False

    def close(self):
        self.closed = True

    def respond(self, tool, args):
        if tool == READ_CHANNEL:
            pages = self.channels.get(args["channel_id"], [([], NO_MORE)])
            idx = 0 if "cursor" not in args else int(args["cursor"])
            msgs, info = pages[idx]
            return read_json(channel_md(args["channel_id"], msgs), info)
        if tool == READ_THREAD:
            return read_json(f"thread {args['channel_id']} {args['message_ts']}")
        raise AssertionError(f"slack_team must not call {tool}")

    def __call__(self, calls, allowed):
        self.rounds.append((calls, allowed))
        return oc_stream([tool_event(c["tool"], c["args"], self.respond(c["tool"], c["args"]))
                          for c in calls])

    def calls(self, tool):
        return [c["args"] for calls, _ in self.rounds for c in calls if c["tool"] == tool]


def run_team(tmp_path, runner, now=NOW, channels=CHANS, **kw):
    return gather.run(["slack_team"], root=tmp_path, now=now, runner=None, me=None,
                      slack_runner=runner, slack_channels=channels, **kw)


def test_slack_team_is_a_default_source():
    assert "slack_team" in gather.SOURCES


def test_each_channel_is_read_from_the_window_start_epoch(tmp_path):
    since = datetime(2026, 11, 16, 6, 0, tzinfo=timezone.utc)
    world = TeamWorld()
    run_team(tmp_path, world, since=since)
    oldest = str(int(since.timestamp()))
    assert world.calls(READ_CHANNEL) == [{"channel_id": c, "oldest": oldest, "limit": 100} for c in CHANS]


def test_no_search_and_no_profile_call(tmp_path):
    world = TeamWorld()
    run_team(tmp_path, world)
    tools = {c["tool"] for calls, _ in world.rounds for c in calls}
    assert tools <= {READ_CHANNEL, READ_THREAD}
    assert PROFILE not in tools and SEARCH not in tools


def test_a_channel_read_follows_its_cursor_until_no_more(tmp_path):
    world = TeamWorld(channels={"C0TEAM1": [([("1.1", "a", 0)], cursor_info("1")),
                                            ([("1.2", "b", 0)], NO_MORE)]})
    ledger = run_team(tmp_path, world)
    reads = [a for a in world.calls(READ_CHANNEL) if a["channel_id"] == "C0TEAM1"]
    assert [a.get("cursor") for a in reads] == [None, "1"]
    assert ledger["slack_team"].startswith("fetched")


def test_only_messages_with_replies_get_a_thread_read_once(tmp_path):
    world = TeamWorld(channels={
        "C0TEAM1": [([("1795000000.000100", "no replies", 0), ("1795000000.000200", "has replies", 3)],
                     cursor_info("1")),
                    ([("1795000000.000200", "has replies", 3)], NO_MORE)],
        "C0TEAM2": [([("1795000000.000300", "one reply", 1)], NO_MORE)]})
    run_team(tmp_path, world)
    threads = sorted((a["channel_id"], a["message_ts"]) for a in world.calls(READ_THREAD))
    assert threads == [("C0TEAM1", "1795000000.000200"), ("C0TEAM2", "1795000000.000300")]
    assert all(a["limit"] == 100 for a in world.calls(READ_THREAD))


def test_items_count_channel_messages_and_records_are_stored_verbatim(tmp_path):
    world = TeamWorld(channels={"C0TEAM1": [([("1.1", "a", 0), ("1.2", "b", 0)], NO_MORE)],
                                "C0TEAM2": [([("1.3", "c", 0)], NO_MORE)]})
    ledger = run_team(tmp_path, world)
    assert ledger["slack_team"] == "fetched 2 calls, 3 items"
    recs = raw_records(tmp_path, "slack_team")
    assert len(recs) == 2 and {r["source"] for r in recs} == {"slack_team"}
    expected = world.respond(READ_CHANNEL, {"channel_id": "C0TEAM1", "oldest": "0", "limit": 100})
    assert any(r["content"] == expected for r in recs)


def test_no_channels_configured_is_not_fetched_and_makes_no_call(tmp_path):
    world = TeamWorld()
    ledger = run_team(tmp_path, world, channels=[])
    assert ledger["slack_team"].startswith("not fetched:")
    assert "slack_team_channels" in ledger["slack_team"]
    assert world.rounds == []


def test_a_capped_channel_chain_keeps_the_cursor(tmp_path):
    world = TeamWorld(channels={"C0TEAM1": [([("1.1", "a", 0)], cursor_info("1")),
                                            ([("1.2", "b", 0)], cursor_info("0"))]})
    ledger = run_team(tmp_path, world, max_pages=2)
    assert ledger["slack_team"] == "capped at 2 pages"
    assert "slack_team" not in read_state(tmp_path).get("covered_from", {})


def test_the_cursor_moves_to_run_start_minus_fifteen_minutes_on_fetched(tmp_path):
    run_team(tmp_path, TeamWorld())
    state = read_state(tmp_path)
    assert state["cursors"]["slack_team"] == (NOW - OVERLAP).isoformat()
    assert state["covered_from"]["slack_team"] == (NOW - timedelta(days=7)).isoformat()


def test_cli_reads_channels_from_the_gather_config(tmp_path, monkeypatch):
    cfg = tmp_path / "gather.json"
    cfg.write_text(json.dumps({"slack_team_channels": ["C0TEAM1"]}))
    monkeypatch.setenv("GATHER_CONFIG", str(cfg))
    world = TeamWorld()
    monkeypatch.setattr(gather, "claude_runner", lambda root: (_ for _ in ()).throw(AssertionError("no claude")))
    monkeypatch.setattr(gather, "opencode_runner", lambda root, **kw: world)
    assert gather.main(["run", "--sources", "slack_team", "--root", str(tmp_path / "store")]) == 0
    assert [a["channel_id"] for a in world.calls(READ_CHANNEL)] == ["C0TEAM1"]
