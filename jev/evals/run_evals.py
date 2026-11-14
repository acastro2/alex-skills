#!/usr/bin/env python3
"""Run the jev behavior evals: each prompt, under each guide version, N times.

    python3 -I run_evals.py --guide new=/path/SKILL.md --guide old=/path/SKILL.md \
        --out ~/.agents/skill-workspace/alex-skills/jev/iteration-1 --runs 2

Each run gets its own empty folder holding the guide at the same relative path
(`guide/SKILL.md`), so nothing in the path tells the model which version it reads.
`claude -p` runs with --strict-mcp-config and Read as the only tool, in its own
process group, and is killed with the group on timeout. The script counts the
ask_jev calls (```json blocks) in code; judgment expectations are graded separately
with Jev (see ../references/eval-grading.md).
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
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

WRAPPER = (
    "Read guide/SKILL.md first and follow it. The ask_jev tool is not connected here: do not "
    "try to call it, write the calls instead. Write each ask_jev call as its own ```json block "
    "holding one object with \"state\" and \"questions\" (one block per call; use no other json "
    "blocks). Where a value is known only after an earlier call, write a placeholder such as "
    "\"<value the earlier call returned>\".\n\nTask:\n"
)


def run_one(prompt: str, guide: str, model: str, timeout: int) -> dict:
    work = tempfile.mkdtemp(prefix="evalrun-")
    os.makedirs(os.path.join(work, "guide"))
    shutil.copy(guide, os.path.join(work, "guide", "SKILL.md"))
    cmd = ["claude", "-p", WRAPPER + prompt, "--model", model, "--strict-mcp-config",
           "--tools", "Read", "--output-format", "json", "--no-session-persistence"]
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
    return {"output": text, "calls": len(re.findall(r"(?:```|~~~)json\s*\n", text, re.I)),
            "cost_usd": data.get("total_cost_usd"), "duration_ms": data.get("duration_ms"),
            "num_turns": data.get("num_turns")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", action="append", required=True, help="label=/path/to/SKILL.md")
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()
    evals = json.load(open(os.path.join(HERE, "evals.json")))["evals"]
    guides = dict(g.split("=", 1) for g in args.guide)
    jobs = [(e, label, path, r) for e in evals for label, path in guides.items() for r in range(1, args.runs + 1)]
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
