#!/usr/bin/env python3
"""Measure whether a skill loads when it should, and stays off when it should not.

Reads ``<skill>/evals/trigger-evals.json`` and runs every query through
``claude -p`` with the safe flags (no MCP, no shell, only Skill and Read), then
records which skill the model picked first.

Each case carries:

    query           what a user would type
    expect          the skill that should be picked, or null for "no skill"
    should_trigger  optional, kept for the older files that only have this

A case passes when every run picks ``expect``. The target skill is the folder
name, so a near-miss case proves both halves: the partner skill loads and the
target stays off.

Usage:

    python scripts/trigger_eval.py --skill scribe
    python scripts/trigger_eval.py --skill scribe --runs 3 --jobs 6 --out DIR
    python scripts/trigger_eval.py --self-test

The runner never writes to the repo. ``--out`` defaults to a directory under
``~/.agents/skill-workspace/alex-skills/``, because a workspace path that holds
the skill name leaks into the prompt and skews the result.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SAFE_FLAGS = ["--strict-mcp-config", "--tools", "Skill,Read"]
TIMEOUT_SECONDS = 240
ERROR = "error"


def pick_skill(stream: str) -> str | None:
    """Return the skill the model invoked first, or None.

    The stream is newline-delimited JSON. The marker is a tool_use block whose
    name is ``Skill`` and whose input carries the skill name.
    """
    marker = '"name":"Skill"'
    for line in stream.splitlines():
        if marker not in line:
            continue
        decoded = _decode_line(line)
        if decoded is not None:
            for block in _tool_use_blocks(decoded):
                if block.get("name") == "Skill":
                    name = (block.get("input") or {}).get("skill")
                    if isinstance(name, str) and name:
                        return name
            continue
        return _pick_by_regex(line)
    return None


def _decode_line(line: str) -> dict | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _tool_use_blocks(event: dict):
    message = event.get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block


def _pick_by_regex(line: str) -> str | None:
    """Fallback for a stream that is not one JSON document per line."""
    start = line.find('"name":"Skill"')
    if start < 0:
        return None
    tail = line[start:]
    key = '"skill":"'
    at = tail.find(key)
    if at < 0:
        return None
    rest = tail[at + len(key):]
    end = rest.find('"')
    return rest[:end] if end > 0 else None


def run_one(query: str, cwd: Path) -> str | None:
    """Run one query and return the first skill picked, or None.

    A failed call returns ``ERROR``. The quota limit ends the process without a
    skill call, which would read as "the skill did not load" and turn a billing
    problem into a routing finding.
    """
    command = ["claude", "-p", query, *SAFE_FLAGS, "--output-format", "stream-json", "--verbose"]
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    try:
        out, _ = process.communicate(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _kill_group(process)
        out, _ = process.communicate()
        return ERROR
    if process.returncode != 0:
        return ERROR
    return pick_skill(out)


def _kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()


def load_cases(path: Path, skill: str) -> list[dict]:
    """Read the card. A case without ``expect`` falls back to ``should_trigger``,
    which is how the older files were written."""
    cases = json.loads(path.read_text())
    if not isinstance(cases, list) or not cases:
        raise SystemExit(f"{path}: expected a non-empty JSON list")
    for case in cases:
        if "query" not in case:
            raise SystemExit(f"{path}: a case has no query")
        if "expect" not in case:
            case["expect"] = skill if case.get("should_trigger", True) else None
    return cases


def score(cases: list[dict], picks: dict[str, list]) -> list[dict]:
    rows = []
    for case in cases:
        got = picks[case["query"]]
        expected = case.get("expect")
        rows.append(
            {
                "query": case["query"],
                "expect": expected,
                "got": got,
                "pass": all(pick == expected for pick in got),
            }
        )
    return rows


def report(skill: str, rows: list[dict]) -> str:
    passed = sum(1 for row in rows if row["pass"])
    errored = sum(1 for row in rows for pick in row["got"] if pick == ERROR)
    lines = [
        f"# Trigger card: {skill}",
        "",
        f"{passed}/{len(rows)} cases pass.",
        "",
        "| Case | Expect | Runs | Pass |",
        "|---|---|---|---|",
    ]
    for row in rows:
        got = ", ".join("none" if pick is None else pick for pick in row["got"])
        expect = "none" if row["expect"] is None else row["expect"]
        lines.append(f"| {row['query']} | {expect} | {got} | {'yes' if row['pass'] else 'no'} |")
    if errored:
        lines += [
            "",
            f"{errored} run(s) failed to start (quota, auth, or crash). Those cases prove nothing",
            "and must be re-run.",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    if not args.skill:
        parser.error("--skill is required unless --self-test")

    root = Path(__file__).resolve().parent.parent
    cases_path = root / args.skill / "evals" / "trigger-evals.json"
    if not cases_path.is_file():
        raise SystemExit(f"missing {cases_path}")
    cases = load_cases(cases_path, args.skill)

    out = Path(
        args.out
        or Path.home() / ".agents" / "skill-workspace" / "alex-skills" / "trigger" / args.skill
    )
    out.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="neutral-"))

    jobs = [(case["query"], run) for case in cases for run in range(args.runs)]
    picks = {case["query"]: [] for case in cases}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [
            (query, pool.submit(run_one, query, workdir)) for query, _ in jobs
        ]
        for query, future in futures:
            picks[query].append(future.result())

    rows = score(cases, picks)
    (out / "runs.json").write_text(json.dumps(rows, indent=2) + "\n")
    (out / "report.md").write_text(report(args.skill, rows))
    print(report(args.skill, rows))
    return 0 if all(row["pass"] for row in rows) else 1


def self_test() -> int:
    line = (
        '{"type":"assistant","message":{"content":[{"type":"tool_use",'
        '"name":"Skill","input":{"skill":"grilling"}}]}}'
    )
    assert pick_skill(line) == "grilling"
    assert pick_skill("") is None
    assert pick_skill('{"message":{"content":[{"type":"text","text":"hi"}]}}') is None
    assert pick_skill('noise "name":"Skill","input":{"skill":"reviewer"} tail') == "reviewer"
    assert pick_skill('"name":"Skill","input":{"skill":"bard"}') == "bard"
    cases = [{"query": "a", "expect": "scribe"}, {"query": "b", "expect": "bard"}]
    rows = score(cases, {"a": ["scribe", "scribe"], "b": ["scribe", "bard"]})
    assert rows[0]["pass"] is True
    assert rows[1]["pass"] is False
    text = report("scribe", rows)
    assert "1/2 cases pass." in text
    print("self-test ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
