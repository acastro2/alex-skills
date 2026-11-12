"""Run every ticket-writer eval with the live skill and with a no-skill baseline. Each run is its own process group.

Usage:
  python3 run_iteration.py <iteration-dir> [--runs N]

Baseline (config without_skill) denies Skill(ticket-writer) and Reads of the skill folder, so the live skill cannot load.
Every run uses --strict-mcp-config --tools "Skill,Read": no shell, no Atlassian MCP.
"""
import argparse, json, os, pathlib, shutil, subprocess, time, uuid, concurrent.futures as cf

EVALS = pathlib.Path(__file__).resolve().parent.parent / "evals"
EV = json.load(open(EVALS / "evals.json"))["evals"]
MODEL = "claude-opus-5-5"
# The Read denies matter: a baseline denied only the Skill tool read SKILL.md from disk (iteration-1, 2026-11-12).
# Both paths are denied because ~/.claude/skills/ticket-writer is a symlink to the repo folder. Checked: both return
# "File is in a directory that is denied by your permission settings"; other skills such as jev stay readable.
HOME = str(pathlib.Path.home())
DENY = ["--disallowedTools", "Skill(ticket-writer)",
        f"Read(/{HOME}/.agents/skills/ticket-writer/**)", f"Read(/{HOME}/.claude/skills/ticket-writer/**)"]

ap = argparse.ArgumentParser()
ap.add_argument("iteration")
ap.add_argument("--runs", type=int, default=1)
ap.add_argument("--configs", default="with_skill,without_skill", help="comma list; use to rerun one config")
a = ap.parse_args()
IT = pathlib.Path(a.iteration).expanduser().resolve()
# Copy fixtures to a neutral path. Why: with the fixtures inside the skill folder, a baseline run that
# was denied the skill could read ../SKILL.md from disk.
FIX = IT / "fixtures"
shutil.copytree(EVALS / "files", FIX, dirs_exist_ok=True)
for ev in EV:
    ev["prompt"] = ev["prompt"].replace("{FIXTURES}", str(FIX))


def tool_uses(path):
    """Return (tool names in order, Skill inputs, tool_result texts that say blocked, final result event)."""
    names, skills, blocked, res = [], [], [], {}
    for line in open(path):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            for c in e.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    names.append(c["name"])
                    if c["name"] == "Skill":
                        skills.append(c.get("input", {}).get("skill", ""))
        elif e.get("type") == "user":
            for c in e.get("message", {}).get("content", []) if isinstance(e.get("message", {}).get("content"), list) else []:
                if c.get("type") == "tool_result" and "blocked by permission" in json.dumps(c.get("content", "")):
                    blocked.append(json.dumps(c.get("content", ""))[:200])
        elif e.get("type") == "result":
            res = e
    return names, skills, blocked, res


def run(ev, cfg, k):
    d = IT / f"eval-{ev['id']}-{ev['name']}" / cfg / f"run-{k}"
    (d / "outputs").mkdir(parents=True, exist_ok=True)
    json.dump({"eval_id": ev["id"], "eval_name": ev["name"], "prompt": ev["prompt"], "assertions": ev["expectations"]},
              open(d.parent.parent / "eval_metadata.json", "w"), indent=2)
    # Neutral cwd. Why: the run folder name holds the config (with_skill / without_skill), and a baseline run
    # read it from its working directory and said it was a baseline (iteration-1 first pass, 2026-11-12).
    cwd = IT / "cwd" / uuid.uuid4().hex[:8]
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
    names, skills, blocked, res = tool_uses(d / "transcript.jsonl")
    (d / "outputs" / "answer.md").write_text(res.get("result", ""))
    u = res.get("usage", {})
    tok = sum(u.get(x, 0) for x in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    json.dump({"total_tokens": tok, "duration_ms": res.get("duration_ms"), "total_duration_seconds": round(wall, 1),
               "cost_usd": res.get("total_cost_usd"), "exit": p.returncode,
               "tools_run": names, "skills_called": skills, "blocked": blocked,
               "ticket_writer_loaded": "ticket-writer" in skills and not blocked},
              open(d / "timing.json", "w"), indent=2)
    return f"{ev['name']}/{cfg}/run-{k}: exit={p.returncode} {round(wall)}s skills={skills} blocked={len(blocked)}"


jobs = [(e, c, k) for e in EV for c in a.configs.split(",") for k in range(1, a.runs + 1)]
with cf.ThreadPoolExecutor(8) as ex:
    for r in cf.as_completed([ex.submit(run, *j) for j in jobs]):
        print(r.result(), flush=True)
