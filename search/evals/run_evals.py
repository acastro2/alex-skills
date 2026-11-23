#!/usr/bin/env python3
"""Run the search behavior evals: each prompt, under each guide version, N times.

    python3 -I run_evals.py --guide new=/path/exa-agent.md --guide old=/path/exa-agent.md \
        --out ~/.agents/skill-workspace/alex-skills/search/iteration-N --runs 2
    python3 -I run_evals.py --guide new=... --out ... --dry-run   # list the jobs, no claude call

Each run gets its own empty folder holding the guide at `guide/exa-agent.md`, so nothing
in the path tells the model which version it reads. `claude -p` runs with
--strict-mcp-config and Read as the only tool, in its own process group, and is killed
with the group on timeout. No Exa call is ever made: agent_run is not connected, and the
model writes each call as a json block. grade.py counts those blocks in code; judgment
expectations are graded with Jev (see README.md).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

WRAPPER = (
    "Read guide/exa-agent.md first and follow it. Today is 2026-11-23. The Exa agent_run tool "
    "is not connected here: do not try to call it, and do not call any other tool except Read. "
    "Write each agent_run call you would make as its own ```json block holding the arguments "
    "object (one block per call; use no other json blocks). If you would write a script, put it "
    "in a ```python or ```bash block and do not run it. Then write what you would tell the "
    "user.\n\nTask:\n"
)

JSON_FENCE = re.compile(r"(?:```|~~~)json\s*\n", re.I)


def count_json_blocks(text: str) -> int:
    return len(JSON_FENCE.findall(text))


def run_one(prompt: str, guide: str, model: str, timeout: int) -> dict:
    work = tempfile.mkdtemp(prefix="evalrun-")
    os.makedirs(os.path.join(work, "guide"))
    shutil.copy(guide, os.path.join(work, "guide", "exa-agent.md"))
    cmd = ["claude", "-p", WRAPPER + prompt, "--model", model, "--strict-mcp-config",
           "--tools", "Read", "--output-format", "json", "--no-session-persistence"]
    try:
        proc = subprocess.Popen(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            return {"error": "timeout"}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"error": (err or out)[-400:]}
    text = data.get("result", "")
    return {"output": text, "calls": count_json_blocks(text),
            "cost_usd": data.get("total_cost_usd"), "duration_ms": data.get("duration_ms"),
            "num_turns": data.get("num_turns")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", action="append", required=True, help="label=/path/to/exa-agent.md")
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", type=int, action="append", help="eval id to run; repeatable")
    ap.add_argument("--dry-run", action="store_true", help="print the job list and exit; no claude call")
    args = ap.parse_args()
    evals = json.load(open(os.path.join(HERE, "evals.json")))["evals"]
    if args.only:  # re-run a subset without paying for the rest
        evals = [e for e in evals if e["id"] in args.only]
    guides = dict(g.split("=", 1) for g in args.guide)
    for label, path in guides.items():
        if not os.path.isfile(path):
            print(f"guide not found: {label}={path}", file=sys.stderr)
            return 2
    jobs = [(e, label, path, r) for e in evals for label, path in guides.items()
            for r in range(1, args.runs + 1)]
    if args.dry_run:
        for e, label, _, r in jobs:
            print(f"eval {e['id']} {label} run {r}")
        print(f"dry run: {len(jobs)} jobs, no claude call")
        return 0
    with cf.ThreadPoolExecutor(args.jobs) as pool:
        futures = {pool.submit(run_one, e["prompt"], path, args.model, args.timeout): (e, label, r)
                   for e, label, path, r in jobs}
        for fut in cf.as_completed(futures):
            e, label, r = futures[fut]
            res = fut.result()
            d = os.path.join(os.path.expanduser(args.out), f"eval-{e['id']}-{e['name']}", label, f"run-{r}")
            os.makedirs(d, exist_ok=True)
            json.dump(res, open(os.path.join(d, "result.json"), "w"), indent=1)
            print(f"eval {e['id']} {label} run {r}: calls={res.get('calls')} error={res.get('error')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
