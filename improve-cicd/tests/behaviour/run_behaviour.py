"""Run every improve-cicd behaviour eval with the skill and without it. Each run is its own process group.

Usage:
  python3 -I run_behaviour.py <iteration> [--runs N] [--only a,b] [--model M] [--timeout S] [--dry-run]

with_skill:    prompt starts "Use my improve-cicd skill. "
without_skill: no skill line; Skill(improve-cicd) and Read of the skill folder are denied.
"""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claude_stream import final_result, skills_invoked  # noqa: E402

LIVE = Path(__file__).resolve().parents[2]
EVALS = LIVE / "evals" / "behaviour"
# Absolute paths need a leading // in Claude Code permission syntax; LIVE already starts with "/".
DENY = ["--disallowedTools", f"Skill(improve-cicd),Read(/{LIVE}/**)"]
TOOLS = "Skill,Read"
CONFIGS = ("with_skill", "without_skill")

ap = argparse.ArgumentParser()
ap.add_argument("iteration")
ap.add_argument("--runs", type=int, default=3)
ap.add_argument("--timeout", type=int, default=600)
ap.add_argument("--model", default="claude-opus-5-5")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--only", default=None, help="comma list of eval names; default all")
a = ap.parse_args()

if not (EVALS / "evals.json").is_file():
    print(f"missing {EVALS / 'evals.json'}", file=sys.stderr)
    sys.exit(2)
EV = json.load(open(EVALS / "evals.json"))["evals"]
if a.only is not None:
    wanted = [n.strip() for n in a.only.split(",") if n.strip()]
    known = {e["name"] for e in EV}
    for n in wanted:
        if n not in known:
            print(f"unknown eval: {n}", file=sys.stderr)
            sys.exit(2)
    EV = [e for e in EV if e["name"] in wanted]

IT = Path(a.iteration).expanduser().resolve()
FIX = IT / "fixtures"
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

if not a.dry_run:
    # Neutral path: with fixtures inside the skill folder a denied baseline could read the skill from disk.
    shutil.copytree(EVALS / "files", FIX, dirs_exist_ok=True)


def prompt_of(ev, cfg):
    line = "Use my improve-cicd skill. " if cfg == "with_skill" else ""
    return ev["prompt"].replace("{SKILL_LINE}", line).replace("{FIXTURES}", str(FIX))


def plan(ev, cfg, k):
    d = IT / f"eval-{ev['id']}-{ev['name']}" / cfg / f"run-{k}"
    cwd = IT / "cwd" / f"{ev['name']}-{cfg}-{k}"
    cmd = ["claude", "-p", prompt_of(ev, cfg), "--model", a.model, "--strict-mcp-config", "--tools", TOOLS,
           "--output-format", "stream-json", "--verbose", *([] if cfg == "with_skill" else DENY)]
    return d, cwd, cmd


def run(ev, cfg, k):
    d, cwd, cmd = plan(ev, cfg, k)
    (d / "outputs").mkdir(parents=True, exist_ok=True)
    cwd.mkdir(parents=True, exist_ok=True)
    json.dump({"eval_id": ev["id"], "eval_name": ev["name"], "prompt": prompt_of(ev, "with_skill"),
               "assertions": ev["expectations"], "tools": TOOLS.split(",")},
              open(d.parent.parent / "eval_metadata.json", "w"), indent=2)
    t0 = time.time()
    with open(d / "transcript.jsonl", "w") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=cwd, env=env, start_new_session=True)
        try:
            p.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, 9)
            p.wait()
    wall = time.time() - t0
    lines = open(d / "transcript.jsonl").read().splitlines()
    res = final_result(lines)
    (d / "outputs" / "reply.md").write_text(res.get("result", "") or "")
    json.dump(skills_invoked(lines), open(d / "skills_loaded.json", "w"), indent=2)
    json.dump({"duration_ms": res.get("duration_ms"), "cost_usd": res.get("total_cost_usd"),
               "exit": p.returncode, "total_seconds": round(wall, 1)}, open(d / "timing.json", "w"), indent=2)
    return f"{ev['name']}/{cfg}/run-{k}: exit={p.returncode} {round(wall)}s"


jobs = [(e, c, k) for e in EV for c in CONFIGS for k in range(1, a.runs + 1)]
if a.dry_run:
    for ev, cfg, k in jobs:
        d, cwd, cmd = plan(ev, cfg, k)
        print(f"[{ev['name']}/{cfg}/run-{k}] cwd={cwd} cmd={cmd}")
    print(f"{len(jobs)} runs", file=sys.stderr)
    sys.exit(0)

with cf.ThreadPoolExecutor(6) as ex:
    for r in cf.as_completed([ex.submit(run, *j) for j in jobs]):
        print(r.result(), flush=True)
