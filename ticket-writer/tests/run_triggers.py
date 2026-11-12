"""Trigger evals for ticket-writer, under the repo safe-run rules.

Usage:
  python3 run_triggers.py <out-dir> [--runs 2] [--indices 0,6] [--workers 8]

Why not skill-creator/vendor/claude/scripts/run_eval.py: it starts `claude -p` with no --strict-mcp-config, no --tools
and no process group, and it writes a temp command file under <repo>/.claude/commands. So a near miss such as
"transition PROJ-9 to Done" would run with the live Atlassian connector. This runner uses the live skill, which is
installed through the ~/.claude/skills symlink, and tests the real description.

Each query is one `claude -p` with --strict-mcp-config --tools "Skill,Read", in its own process group, in a neutral cwd
under <out-dir>/cwd/. Triggered = a Skill tool_use whose input skill is `ticket-writer`. A Read of a ticket-writer path
is recorded as well, but the verdict is the Skill call. Any tool other than Skill or Read is recorded as `other_tools`.
"""
import argparse, json, os, pathlib, subprocess, time, uuid, concurrent.futures as cf

EVALS = pathlib.Path(__file__).resolve().parent.parent / "evals"
MODEL = "claude-opus-5-5"
TIMEOUT = 180
THRESHOLD = 0.5

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--runs", type=int, default=2)
ap.add_argument("--indices", help="comma list of query indexes to run; default all")
ap.add_argument("--workers", type=int, default=8)
ap.add_argument("--rescore", action="store_true", help="no new runs: re-read the saved transcripts and rewrite results.json")
a = ap.parse_args()
OUT = pathlib.Path(a.out).expanduser().resolve()
Q = json.load(open(EVALS / "trigger-evals.json"))
idx = [int(i) for i in a.indices.split(",")] if a.indices else list(range(len(Q)))


def analyse(path):
    skills, reads, other = [], [], []
    for line in open(path):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        m = e.get("message")
        if e.get("type") != "assistant" or not isinstance(m, dict):
            continue
        for c in m.get("content", []):
            if not isinstance(c, dict) or c.get("type") != "tool_use":
                continue
            if c["name"] == "Skill":
                skills.append(c.get("input", {}).get("skill", ""))
            elif c["name"] == "Read":
                reads.append(c.get("input", {}).get("file_path", ""))
            else:
                other.append(c["name"])
    return skills, reads, other


def run(i, k):
    q = Q[i]
    d = OUT / f"q{i:02d}" / f"run-{k}"
    if a.rescore:
        old = json.load(open(d / "run.json"))
        return rescore(i, k, q, d, old["exit"], old["timed_out"], old["wall_s"])
    d.mkdir(parents=True, exist_ok=True)
    cwd = OUT / "cwd" / uuid.uuid4().hex[:8]
    cwd.mkdir(parents=True, exist_ok=True)
    cmd = ["claude", "-p", q["query"], "--model", MODEL, "--strict-mcp-config", "--tools", "Skill,Read",
           "--output-format", "stream-json", "--verbose"]
    t0 = time.time(); timed_out = False
    with open(d / "transcript.jsonl", "w") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=cwd, start_new_session=True)
        try:
            p.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(p.pid, 9)
            p.wait()
    return rescore(i, k, q, d, p.returncode, timed_out, round(time.time() - t0, 1))


def rescore(i, k, q, d, code, timed_out, wall):
    skills, reads, other = analyse(d / "transcript.jsonl")
    r = {"i": i, "run": k, "query": q["query"], "should_trigger": q["should_trigger"], "exit": code,
         "timed_out": timed_out, "wall_s": wall, "skills_called": skills,
         "triggered": "ticket-writer" in skills,
         "read_ticket_writer": [x for x in reads if "/skills/ticket-writer" in x], "other_tools": other}
    json.dump(r, open(d / "run.json", "w"), indent=2)
    return r


runs = []
with cf.ThreadPoolExecutor(a.workers) as ex:
    for f in cf.as_completed([ex.submit(run, i, k) for i in idx for k in range(1, a.runs + 1)]):
        r = f.result(); runs.append(r)
        print(f"q{r['i']:02d} run-{r['run']} triggered={r['triggered']} skills={r['skills_called']} other={r['other_tools']} exit={r['exit']} {r['wall_s']}s", flush=True)

res = []
for i in idx:
    rs = [r for r in runs if r["i"] == i]
    n = sum(r["triggered"] for r in rs); rate = n / len(rs); st = Q[i]["should_trigger"]
    res.append({"query": Q[i]["query"], "should_trigger": st, "runs": len(rs), "triggered": n, "trigger_rate": rate,
                "read_ticket_writer": sum(bool(r["read_ticket_writer"]) for r in rs),
                "other_tools": sorted({t for r in rs for t in r["other_tools"]}),
                "pass": rate >= THRESHOLD if st else rate < THRESHOLD})
tp = sum(r["triggered"] for r in runs if r["should_trigger"]); fp = sum(r["triggered"] for r in runs if not r["should_trigger"])
fn = sum(not r["triggered"] for r in runs if r["should_trigger"])
summary = {"total": len(res), "passed": sum(r["pass"] for r in res), "run_level": {"tp": tp, "fp": fp, "fn": fn},
           "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None}
json.dump({"skill_name": "ticket-writer", "model": MODEL, "results": res, "summary": summary}, open(OUT / "results.json", "w"), indent=2)
print(json.dumps(summary))
