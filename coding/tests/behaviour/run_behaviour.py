"""Run every behaviour eval with the live skill and with a baseline skill. Each run is its own process group.

Usage:
  python3 run_behaviour.py <iteration> --baseline-skill DIR [--runs N] [--timeout S] [--model M] [--dry-run]

old_skill: the baseline folder is installed as <iteration>/old-cwd/<name>-<k>/.claude/skills/<basename>,
and Skill(coding) is denied so the live skill cannot load.
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

EVALS = Path(__file__).resolve().parents[2] / "evals" / "behaviour"
# Deny the live skill twice: the Skill tool, and Read on its folder. A baseline that could not load
# the skill read the live SKILL.md instead (iteration test-ban-2), which made the comparison meaningless.
LIVE = Path(__file__).resolve().parents[2]
DENY = ["--disallowedTools", f"Skill(coding),Read(/{LIVE}/**)"]

ap = argparse.ArgumentParser()
ap.add_argument("iteration")
ap.add_argument("--baseline-skill", required=True)
ap.add_argument("--runs", type=int, default=2)
ap.add_argument("--timeout", type=int, default=600)
ap.add_argument("--model", default="claude-opus-5-5")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--only", default=None, help="comma list of eval names to run; default all")
ap.add_argument("--baseline-config-dir", default=None,
                help="CLAUDE_CONFIG_DIR for old_skill runs, so the baseline loads the CLAUDE.md from before the edit")
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
BASE = Path(a.baseline_skill).expanduser().resolve()
FIX = IT / "fixtures"
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

if not a.dry_run:
    # Neutral path: with fixtures inside the skill folder a denied baseline could read the skill from disk.
    shutil.copytree(EVALS / "files", FIX, dirs_exist_ok=True)
for ev in EV:
    ev["prompt"] = ev["prompt"].replace("{FIXTURES}", str(FIX))


def tools_of(ev):
    return ev.get("tools", ["Skill", "Read"])


def plan(ev, cfg, k):
    d = IT / f"eval-{ev['id']}-{ev['name']}" / cfg / f"run-{k}"
    cwd = d if cfg == "with_skill" else IT / "old-cwd" / f"{ev['name']}-{k}"
    # Name the skill each config loads: a denied baseline does not fall back by itself (iteration 1).
    prompt = ev["prompt"].replace("{SKILL}", "coding" if cfg == "with_skill" else BASE.name)
    tools = tools_of(ev)
    extra = [t for t in tools if t not in ("Skill", "Read")]
    allowed = ["--allowedTools", ",".join(extra)] if extra else []
    cmd = ["claude", "-p", prompt, "--model", a.model, "--strict-mcp-config", "--tools", ",".join(tools),
           *allowed, "--output-format", "stream-json", "--verbose", *([] if cfg == "with_skill" else DENY)]
    return d, cwd, cmd


def run(ev, cfg, k):
    d, cwd, cmd = plan(ev, cfg, k)
    (d / "outputs").mkdir(parents=True, exist_ok=True)
    json.dump({"eval_id": ev["id"], "eval_name": ev["name"], "prompt": ev["prompt"], "assertions": ev["expectations"],
               "tools": tools_of(ev)},
              open(d.parent.parent / "eval_metadata.json", "w"), indent=2)
    if cfg == "old_skill":
        dest = cwd / ".claude" / "skills" / BASE.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(BASE, dest, dirs_exist_ok=True)
    cwd.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(d / "transcript.jsonl", "w") as out:
        run_env = env if cfg == "with_skill" or not a.baseline_config_dir else {**env, "CLAUDE_CONFIG_DIR": a.baseline_config_dir}
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=cwd, env=run_env, start_new_session=True)
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


jobs = [(e, c, k) for e in EV for c in ("with_skill", "old_skill") for k in range(1, a.runs + 1)]
if a.dry_run:
    for ev, cfg, k in jobs:
        d, cwd, cmd = plan(ev, cfg, k)
        print(f"[{ev['name']}/{cfg}/run-{k}] cwd={cwd} cmd={cmd}")
    sys.exit(0)

with cf.ThreadPoolExecutor(8) as ex:
    for r in cf.as_completed([ex.submit(run, *j) for j in jobs]):
        print(r.result(), flush=True)
