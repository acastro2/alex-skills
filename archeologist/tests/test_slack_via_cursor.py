"""The Slack bridge's parser and its failure checks, on a real cursor-agent stream and on
hand-built events in the same shape."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import slack_via_cursor as bridge  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "cursor_stream_needsauth.jsonl"


def call(name: str, content: str | None = "ok", key: str = "mcpToolCall") -> str:
    result = {"success": {"content": content}} if content is not None else {"error": {"message": "boom"}}
    return json.dumps(
        {
            "type": "tool_call",
            "subtype": "completed",
            "call_id": f"c-{name}",
            "tool_call": {key: {"args": {"toolName": name, "query": "x"}, "result": result}},
        }
    )


INIT = json.dumps({"type": "system", "subtype": "init", "session_id": "s1", "model": "m"})
DONE = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "DONE"})


def test_real_stream_reads_session_calls_and_result() -> None:
    record = bridge.parse_stream(FIXTURE.read_text().splitlines())
    assert record["session_id"] == "23b78ce4-9e57-4fbd-9c14-e5169e284d53"
    assert [c["tool"] for c in record["calls"]] == ["getMcpToolsToolCall", "getMcpToolsToolCall"]
    assert all(c["content"] for c in record["calls"])
    assert record["result"]["is_error"] is False


def test_real_stream_flags_needs_auth() -> None:
    code, notes = bridge.problems(bridge.parse_stream(FIXTURE.read_text().splitlines()))
    assert code == 2
    assert any("needsAuth" in n for n in notes)


def test_verbatim_content_survives_parsing() -> None:
    text = 'Ana: "can you send me the SAD by Friday?"'
    record = bridge.parse_stream([INIT, call("slack_search_public_and_private", text), DONE])
    assert record["calls"][0]["content"] == text
    assert record["calls"][0]["tool"] == "mcpToolCall:slack_search_public_and_private"
    assert bridge.problems(record) == (0, [])


def test_a_write_tool_fails_the_run_even_when_it_succeeded() -> None:
    record = bridge.parse_stream([INIT, call("slack_send_message"), DONE])
    code, notes = bridge.problems(record)
    assert code == 3
    assert notes == ["write tool ran: mcpToolCall:slack_send_message"]


def test_read_tools_are_not_mistaken_for_writes() -> None:
    reads = ["slack_read_channel", "slack_read_thread", "slack_search_users", "slack_read_canvas"]
    record = bridge.parse_stream([INIT, *[call(n) for n in reads], DONE])
    assert bridge.problems(record) == (0, [])


def test_tool_error_and_missing_result_are_reported() -> None:
    record = bridge.parse_stream([INIT, call("slack_read_thread", content=None)])
    code, notes = bridge.problems(record)
    assert code == 2
    assert "tool error: mcpToolCall:slack_read_thread" in notes
    assert "no successful result event" in notes


def test_truncated_marker_is_reported() -> None:
    record = bridge.parse_stream([INIT, call("slack_read_channel", "msg ... [truncated]"), DONE])
    assert any("[truncated]" in n for n in bridge.problems(record)[1])


def test_garbage_lines_are_counted_not_fatal() -> None:
    record = bridge.parse_stream([INIT, "not json", "", DONE])
    assert record["bad_lines"] == 1
    assert record["result"]["text"] == "DONE"


def test_workspace_config_is_written_once(tmp_path: Path) -> None:
    ws = tmp_path / "bridge"
    bridge.ensure_workspace(ws)
    config = ws / ".cursor" / "mcp.json"
    assert json.loads(config.read_text())["mcpServers"]["slack"]["url"] == "https://mcp.slack.com/mcp"
    config.write_text('{"mcpServers": {}}')
    bridge.ensure_workspace(ws)
    assert config.read_text() == '{"mcpServers": {}}'


def test_permission_file_denies_every_write_tool_and_is_rewritten(tmp_path: Path) -> None:
    ws = tmp_path / "bridge"
    bridge.ensure_workspace(ws)
    perms = ws / ".cursor" / "cli.json"
    perms.write_text("{}")
    bridge.ensure_workspace(ws)
    rules = json.loads(perms.read_text())["permissions"]
    for tool in bridge.WRITE_TOOLS:
        assert f"Mcp(slack:{tool})" in rules["deny"]
        assert bridge.WRITE_WORDS.search(tool)
    assert "Shell(*)" in rules["deny"] and "Write(**)" in rules["deny"]
    assert not any(bridge.WRITE_WORDS.search(t) for t in bridge.READ_TOOLS)


def mcp_event(blocks: list, is_error: bool = False) -> str:
    return json.dumps({"type": "tool_call", "subtype": "completed", "call_id": "m1", "tool_call": {
        "mcpToolCall": {"args": {"toolName": "slack_search_public_and_private"},
                        "result": {"success": {"content": blocks, "isError": is_error}}}}})


def test_mcp_block_content_is_joined_verbatim() -> None:
    blocks = [{"text": {"text": "first"}}, {"type": "text", "text": "second"}]
    record = bridge.parse_stream([INIT, mcp_event(blocks), DONE])
    assert record["calls"][0]["content"] == "first\nsecond"
    assert bridge.problems(record) == (0, [])


def test_mcp_is_error_counts_as_tool_error() -> None:
    record = bridge.parse_stream([INIT, mcp_event([{"text": {"text": "nope"}}], is_error=True), DONE])
    assert bridge.problems(record)[0] == 2


def test_blocked_write_and_schema_lookup_are_told_apart() -> None:
    lookup = call("slack_send_message", "{schema}", key="getMcpToolsToolCall")
    blocked = json.dumps({"type": "tool_call", "subtype": "completed", "call_id": "w", "tool_call": {
        "mcpToolCall": {"args": {"toolName": "slack_send_message"},
                        "result": {"permissionDenied": {"error": "Blocked by permissions configuration"}}}}})
    assert bridge.problems(bridge.parse_stream([INIT, lookup, DONE])) == (0, [])
    assert bridge.problems(bridge.parse_stream([INIT, lookup, blocked, DONE])) == (
        3, ["write tool attempted, blocked: mcpToolCall:slack_send_message"])
