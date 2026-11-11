"""Run every eval with the live skill and with a baseline. Each run is its own process group.

Usage:
  python3 run_iteration.py <iteration-dir> [--runs N] [--old-home DIR]

Without --old-home the baseline is no skill (config without_skill).
With --old-home the baseline is a snapshot installed as the project skill
DIR/.claude/skills/pr-change-description-v1 (config old_skill); its runs use a cwd under DIR.
Both baselines deny Skill(pr-change-description), so the live skill cannot load.
"""
import argparse, json, os, pathlib, subprocess, time, concurrent.futures as cf

import shutil
EVALS = pathlib.Path(__file__).resolve().parent.parent / "evals"
EV = json.load(open(EVALS / "evals.json"))["evals"]
MODEL = "claude-opus-5-5"
DENY = ["--disallowedTools", "Skill(pr-change-description)"]

ap = argparse.ArgumentParser()
ap.add_argument("iteration")
ap.add_argument("--runs", type=int, default=1)
ap.add_argument("--old-home")
a = ap.parse_args()
IT = pathlib.Path(a.iteration).expanduser().resolve()
BASE = "old_skill" if a.old_home else "without_skill"
# Copy fixtures to a neutral path. Why: with the fixtures inside the skill folder, a baseline run that
# was denied the skill read ../SKILL.md from disk (iteration-2, 2026-11-11).
FIX = IT / "fixtures"
shutil.copytree(EVALS / "files", FIX, dirs_exist_ok=True)
for ev in EV:
    ev["prompt"] = ev["prompt"].replace("{FIXTURES}", str(FIX))


def run(ev, cfg, k):
    d = IT / f"eval-{ev['id']}-{ev['name']}" / cfg / f"run-{k}"
    (d / "outputs").mkdir(parents=True, exist_ok=True)
    json.dump({"eval_id": ev["id"], "eval_name": ev["name"], "prompt": ev["prompt"], "assertions": ev["expectations"]},
              open(d.parent.parent / "eval_metadata.json", "w"), indent=2)
    cwd = d
    if cfg == "old_skill":
        cwd = pathlib.Path(a.old_home).expanduser().resolve() / "cwd" / f"{IT.name}-{ev['name']}-{k}"
        cwd.mkdir(parents=True, exist_ok=True)
    cmd = ["claude", "-p", ev["prompt"], "--model", MODEL, "--strict-mcp-config", "--tools", "Skill,Read",
           "--output-format", "stream-json", "--verbose", *([] if cfg == "with_skill" else DENY)]
    t0 = time.time()
    with open(d / "transcript.jsonl", "w") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=cwd, start_new_session=True)
        try:
            p.wait(timeout=900)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, 9)
            p.wait()
    wall = time.time() - t0
    res = {}
    for line in open(d / "transcript.jsonl"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "result":
            res = e
    (d / "outputs" / "pr_body.md").write_text(res.get("result", ""))
    u = res.get("usage", {})
    tok = sum(u.get(x, 0) for x in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    json.dump({"total_tokens": tok, "duration_ms": res.get("duration_ms"), "total_duration_seconds": round(wall, 1),
               "cost_usd": res.get("total_cost_usd"), "exit": p.returncode}, open(d / "timing.json", "w"), indent=2)
    return f"{ev['name']}/{cfg}/run-{k}: exit={p.returncode} {round(wall)}s"


jobs = [(e, c, k) for e in EV for c in ("with_skill", BASE) for k in range(1, a.runs + 1)]
with cf.ThreadPoolExecutor(8) as ex:
    for r in cf.as_completed([ex.submit(run, *j) for j in jobs]):
        print(r.result(), flush=True)
