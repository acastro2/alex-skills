"""Run the projects-curator behavior evals: the live skill against a snapshot of the skill at a git ref.

Usage:
  python3 run_iteration.py <iteration-dir> [--runs N] [--cases a,b] [--configs with_skill,old_skill] [--ref HEAD]

Each run is one `claude -p` with --strict-mcp-config --tools "Skill,Read", in its own process group, in a neutral
cwd. No shell, no Atlassian MCP, so a run cannot touch Jira or Confluence.

Both configs are denied the real ledger (curated.json holds org facts) and this evals folder (it holds the
expectations). old_skill is also denied the live skill, and its prompt points at a snapshot of <ref> written
outside every skill source, so OpenCode never discovers it as a live skill.
"""
import argparse, json, os, pathlib, shutil, subprocess, time, uuid, concurrent.futures as cf

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
REPO = SKILL_DIR.parent
EVALS = SKILL_DIR / "evals"
MODEL = "claude-opus-5-5"
HOME = str(pathlib.Path.home())
LIVE = [f"/{HOME}/.agents/skills/projects-curator", f"/{HOME}/.claude/skills/projects-curator"]
DENY_BOTH = [x for p in LIVE for x in (f"Read({p}/curated.json)", f"Read({p}/evals/**)")]
DENY_OLD = ["Skill(projects-curator)", *[f"Read({p}/**)" for p in LIVE]]

ap = argparse.ArgumentParser()
ap.add_argument("iteration")
ap.add_argument("--runs", type=int, default=1)
ap.add_argument("--cases", default="", help="comma list of eval names; default all")
ap.add_argument("--configs", default="with_skill,old_skill")
ap.add_argument("--ref", default="HEAD", help="git ref for the old_skill snapshot")
a = ap.parse_args()
IT = pathlib.Path(a.iteration).expanduser().resolve()
EV = json.load(open(EVALS / "evals.json"))["evals"]

# Fixtures go to a neutral path, so a run never has a reason to read this evals folder.
FIX = IT / "fixtures"
shutil.copytree(EVALS / "files", FIX, dirs_exist_ok=True)

# Snapshot the skill at --ref. Only tracked files exist at a ref; the ledger never does.
SNAP = IT / "old-skill" / "projects-curator"
if "old_skill" in a.configs and not SNAP.exists():
    files = subprocess.run(["git", "ls-tree", "-r", "--name-only", a.ref, "projects-curator/"],
                           cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    for f in files:
        if "/evals/" in f or "/tests/" in f:
            continue
        out = SNAP / f.removeprefix("projects-curator/")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(subprocess.run(["git", "show", f"{a.ref}:{f}"], cwd=REPO, capture_output=True, check=True).stdout)


def prompt_for(ev, cfg):
    p = ev["prompt"].replace("{FIXTURES}", str(FIX))
    if cfg == "old_skill":
        p = (f"The projects-curator skill is installed at {SNAP}. Read {SNAP}/SKILL.md and the reference files it "
             f"points to under {SNAP}/references/, and follow it as the projects-curator skill.\n\n" + p)
    return p


def tool_uses(path):
    names, skills, reads, res = [], [], [], {}
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
                    if c["name"] == "Read":
                        reads.append(c.get("input", {}).get("file_path", ""))
        elif e.get("type") == "result":
            res = e
    return names, skills, reads, res


def run(ev, cfg, k):
    d = IT / f"eval-{ev['id']}-{ev['name']}" / cfg / f"run-{k}"
    (d / "outputs").mkdir(parents=True, exist_ok=True)
    json.dump({"eval_id": ev["id"], "eval_name": ev["name"], "prompt": ev["prompt"], "assertions": ev["expectations"]},
              open(d.parent.parent / "eval_metadata.json", "w"), indent=2)
    cwd = IT / "cwd" / uuid.uuid4().hex[:8]
    cwd.mkdir(parents=True, exist_ok=True)
    deny = DENY_BOTH + (DENY_OLD if cfg == "old_skill" else [])
    cmd = ["claude", "-p", prompt_for(ev, cfg), "--model", MODEL, "--strict-mcp-config", "--tools", "Skill,Read",
           "--output-format", "stream-json", "--verbose", "--disallowedTools", *deny]
    t0 = time.time()
    with open(d / "transcript.jsonl", "w") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=cwd, start_new_session=True)
        try:
            p.wait(timeout=900)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, 9)
            p.wait()
    wall = time.time() - t0
    names, skills, reads, res = tool_uses(d / "transcript.jsonl")
    (d / "outputs" / "answer.md").write_text(res.get("result", ""))
    u = res.get("usage", {})
    tok = sum(u.get(x, 0) for x in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    leaked = [r for r in reads if r.endswith("curated.json") and str(FIX) not in r]
    json.dump({"total_tokens": tok, "duration_ms": res.get("duration_ms"), "total_duration_seconds": round(wall, 1),
               "cost_usd": res.get("total_cost_usd"), "exit": p.returncode, "tools_run": names,
               "skills_called": skills, "reads": reads, "real_ledger_reads": leaked},
              open(d / "timing.json", "w"), indent=2)
    return f"{ev['name']}/{cfg}/run-{k}: exit={p.returncode} {round(wall)}s skills={skills} reads={len(reads)} ledger_leak={len(leaked)}"


jobs = [(e, c, k) for e in EV if not a.cases or e["name"] in a.cases.split(",")
        for c in a.configs.split(",") for k in range(1, a.runs + 1)]
with cf.ThreadPoolExecutor(6) as ex:
    for r in cf.as_completed([ex.submit(run, *j) for j in jobs]):
        print(r.result(), flush=True)
