#!/usr/bin/env python3
"""Reach the Slack MCP from a host that has no Slack connector (OpenCode), through cursor-agent.

Why: Slack's MCP server only accepts registered partner clients (Claude Code, Cursor). OpenCode
is not one. cursor-agent is, and its `stream-json` output carries every tool result verbatim,
while Cursor's on-disk transcripts keep only the tool calls, not their results. So the payload
must come from stdout, captured here.

Read-only in three layers: a Cursor permission file in the bridge workspace that allows the
Slack read tools by name and denies the write tools, all shell, and all file writes (deny wins,
and without --force an unlisted tool is rejected headless); a prompt that names only read tools;
and a post-run check that fails the run if a write-looking tool ran. `--mode ask` is NOT used:
it rejects every MCP call, reads included (verified 2026-11-11). See references/slack.md.

Usage:
  slack_via_cursor.py --out /tmp/slack.json "Search Slack for messages to me after 2026-11-10"
  slack_via_cursor.py --out /tmp/slack.json --prompt-file brief.txt
Exit codes: 0 ok, 1 cursor-agent failed, 2 a tool reported an error or Slack is not connected,
3 a write-looking tool ran.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5-5-medium"
# Cursor stores MCP sign-in per workspace folder (~/.cursor/projects/<folder>/mcp-auth.json),
# so the bridge needs one fixed folder: a fresh temp folder would ask for sign-in every run.
DEFAULT_WORKSPACE = Path.home() / ".local/share/slack-via-cursor"
READ_TOOLS = [
    "slack_search_public_and_private", "slack_search_public", "slack_search_channels",
    "slack_search_users", "slack_read_channel", "slack_read_thread", "slack_read_canvas",
    "slack_read_user_profile",
]
WRITE_TOOLS = [
    "slack_send_message", "slack_send_message_draft", "slack_schedule_message",
    "slack_create_canvas", "slack_update_canvas",
]
CLI_PERMISSIONS = {
    "permissions": {
        "allow": [f"Mcp(slack:{t})" for t in READ_TOOLS],
        "deny": [f"Mcp(slack:{t})" for t in WRITE_TOOLS] + ["Shell(*)", "Write(**)"],
    }
}
# Cursor's own Slack client id, as published in Slack's "Connect to Cursor" docs.
MCP_CONFIG = {
    "mcpServers": {
        "slack": {
            "url": "https://mcp.slack.com/mcp",
            "auth": {"CLIENT_ID": "3660753192626.8903469228982"},
        }
    }
}
WRITE_WORDS = re.compile(
    r"send|schedule|draft|create|update|upload|complete_file|add_reaction|reactions_add|"
    r"write|delete|post|invite|archive",
    re.I,
)
READ_ONLY_PREAMBLE = (
    "You are a read-only fetcher for the Slack MCP server. Use ONLY Slack search and read "
    "tools (search messages, search channels, search users, read channel, read thread, read "
    "canvas, read user profile, list channels). Never send, schedule, draft, react, create, "
    "update, or upload anything. Do not summarize: call the tools, page until the request is "
    "covered, then reply with the one word DONE.\n\nRequest:\n"
)


def tool_name(entry: dict) -> str:
    """The stream names a call by its single `*ToolCall` key; MCP calls carry the real tool
    name in their args, under one of a few keys."""
    key = next((k for k in entry if k.endswith("ToolCall")), "unknown")
    args = entry.get(key, {}).get("args", {}) or {}
    for field in ("toolName", "name", "tool"):
        if isinstance(args.get(field), str):
            return f"{key}:{args[field]}"
    return key


def content_text(raw: object) -> str | None:
    """Built-in tools return a string. MCP tools return a list of blocks shaped
    `{"text": {"text": "..."}}` (seen 2026-11-11) or `{"type": "text", "text": "..."}` (MCP spec).
    Join the text verbatim; anything else is kept as JSON so nothing is lost."""
    if raw is None or isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts = []
        for block in raw:
            text = block.get("text") if isinstance(block, dict) else None
            if isinstance(text, dict):
                text = text.get("text")
            parts.append(text if isinstance(text, str) else json.dumps(block))
        return "\n".join(parts)
    return json.dumps(raw)


def parse_stream(lines: list[str]) -> dict:
    """Turn cursor-agent stream-json lines into one record: session, every completed tool call
    with its verbatim result, and the final result event."""
    out: dict = {"session_id": None, "model": None, "calls": [], "result": None, "bad_lines": 0}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            out["bad_lines"] += 1
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            out["session_id"] = event.get("session_id")
            out["model"] = event.get("model")
        elif kind == "tool_call" and event.get("subtype") == "completed":
            entry = event.get("tool_call", {})
            key = next((k for k in entry if k.endswith("ToolCall")), None)
            body = entry.get(key, {}) if key else {}
            result = body.get("result", {}) or {}
            success = result.get("success")
            raw = success.get("content") if isinstance(success, dict) else None
            failed = success is None or bool(isinstance(success, dict) and success.get("isError"))
            out["calls"].append(
                {
                    "call_id": event.get("call_id"),
                    "tool": tool_name(entry),
                    "args": body.get("args", {}),
                    "content": content_text(raw),
                    "error": result if failed else None,
                }
            )
        elif kind == "result":
            out["result"] = {
                "is_error": event.get("is_error"),
                "text": event.get("result"),
                "duration_ms": event.get("duration_ms"),
            }
    return out


def problems(record: dict) -> tuple[int, list[str]]:
    """Exit code and human lines for what went wrong. A write-looking call wins over errors."""
    notes: list[str] = []
    # Only real calls count: a getMcpTools lookup of a write tool only reads its schema.
    writes = [
        c for c in record["calls"]
        if c["tool"].startswith("mcpToolCall") and WRITE_WORDS.search(c["tool"].split(":")[-1])
    ]
    if writes:
        return 3, [
            f"write tool {'attempted, blocked' if 'permissionDenied' in json.dumps(c['error']) else 'ran'}: {c['tool']}"
            for c in writes
        ]
    errors = [c for c in record["calls"] if c["error"] is not None]
    notes += [f"tool error: {c['tool']}" for c in errors]
    blob = json.dumps(record["calls"])
    if "needsAuth" in blob:
        notes.append("an MCP server reports needsAuth: run `cursor-agent mcp login slack` in the bridge workspace")
    if "[truncated]" in blob:
        notes.append("a result contains '[truncated]': page smaller or read the thread directly")
    if record["result"] is None or record["result"].get("is_error"):
        notes.append("no successful result event")
    return (2 if notes else 0), notes


def ensure_workspace(workspace: Path) -> None:
    """Write the Slack MCP config once, and the permission file every run (it is the
    write block, so it must never drift). Sign-in is a separate, interactive step:
    `cd <workspace> && cursor-agent mcp enable slack && cursor-agent mcp login slack`."""
    config = workspace / ".cursor" / "mcp.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    if not config.exists():
        config.write_text(json.dumps(MCP_CONFIG, indent=2) + "\n")
    (workspace / ".cursor" / "cli.json").write_text(json.dumps(CLI_PERMISSIONS, indent=2) + "\n")


def run(prompt: str, model: str, timeout: int, workspace: Path) -> tuple[int, str, str]:
    ensure_workspace(workspace)
    cmd = [
        "cursor-agent", "-p", "--output-format", "stream-json",
        "--approve-mcps", "--trust", "--workspace", str(workspace), "--model", model,
        READ_ONLY_PREAMBLE + prompt,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=workspace)
    return proc.returncode, proc.stdout, proc.stderr


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", help="what to fetch from Slack")
    ap.add_argument("--prompt-file", type=Path)
    ap.add_argument("--out", type=Path, required=True, help="where to write the JSON record")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    args = ap.parse_args(argv)
    prompt = args.prompt_file.read_text() if args.prompt_file else args.prompt
    if not prompt:
        ap.error("give a prompt or --prompt-file")

    code, stdout, stderr = run(prompt, args.model, args.timeout, args.workspace)
    if code != 0:
        print(f"cursor-agent exited {code}: {stderr.strip()[-400:]}", file=sys.stderr)
        return 1
    record = parse_stream(stdout.splitlines())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2))
    exit_code, notes = problems(record)
    with_content = sum(1 for c in record["calls"] if c["content"])
    print(f"session {record['session_id']} model {record['model']}: "
          f"{len(record['calls'])} tool calls, {with_content} with content -> {args.out}")
    for note in notes:
        print(f"WARNING: {note}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
