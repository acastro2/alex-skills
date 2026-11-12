"""Run every scribe eval with the live skill and with no skill. Each run is its own process group.

Usage: python3 eval_run.py <iteration-dir> [--runs N]

Safe-run rules (repo standard): `--strict-mcp-config --tools "Skill,Read"`, so a run can read
the fixtures but cannot run a script, reach M365, or write the vault. The baseline denies
Skill(scribe). Fixtures are copied to <iteration>/fixtures so no run reads them from inside the
skill folder (a baseline once read ../SKILL.md through a fixture path, 2026-11-11).
"""
import argparse, concurrent.futures as cf, json, os, pathlib, re, shutil, subprocess, time

EVALS = pathlib.Path(__file__).resolve().parent.parent / "evals"
MODEL = "claude-opus-5-5"
HOME = pathlib.Path.home()
# A typed `/scribe` loads the skill as a slash command, which Skill(scribe) does not block: iteration-1's
# first baseline read references/voicememos.md (2026-11-12). So the baseline drops the slash and is also
# denied every read of the skill's files.
DENY = ["--disallowedTools", "Skill(scribe)",
        f"Read({HOME}/.claude/skills/scribe/**)", f"Read({HOME}/.agents/skills/scribe/**)"]


def run(it: pathlib.Path, ev: dict, cfg: str, k: int) -> str:
    d = it / f"eval-{ev['id']}-{ev['name']}" / cfg / f"run-{k}"
    (d / "outputs").mkdir(parents=True, exist_ok=True)
    json.dump({"eval_id": ev["id"], "eval_name": ev["name"], "prompt": ev["prompt"],
               "assertions": [c["text"] for c in ev["checks"]]},
              open(d.parent.parent / "eval_metadata.json", "w"), indent=2)
    prompt = ev["prompt"] if cfg == "with_skill" else re.sub(r"^/scribe\b", "Scribe", ev["prompt"])
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--strict-mcp-config", "--tools", "Skill,Read",
           "--output-format", "stream-json", "--verbose", *([] if cfg == "with_skill" else DENY)]
    t0 = time.time()
    with open(d / "transcript.jsonl", "w") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=d, start_new_session=True)
        try:
            p.wait(timeout=900)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, 9)
            p.wait()
    res, skills = {}, []
    for line in open(d / "transcript.jsonl"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "result":
            res = e
        for c in (e.get("message", {}) or {}).get("content", []) if isinstance(e.get("message"), dict) else []:
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                skills.append(c.get("input", {}).get("skill") or c.get("input", {}).get("command"))
            if isinstance(c, dict) and c.get("type") == "tool_use" and "/skills/scribe/" in json.dumps(c.get("input", {})):
                skills.append("read:" + c["input"].get("file_path", "?").split("/skills/")[-1])
    (d / "outputs" / "reply.md").write_text(res.get("result", ""))
    u = res.get("usage", {})
    tok = sum(u.get(x, 0) for x in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    json.dump({"total_tokens": tok, "duration_ms": res.get("duration_ms"), "total_duration_seconds": round(time.time() - t0, 1),
               "cost_usd": res.get("total_cost_usd"), "exit": p.returncode, "skills_loaded": skills},
              open(d / "timing.json", "w"), indent=2)
    return f"{ev['name']}/{cfg}/run-{k}: exit={p.returncode} skills={skills} {round(time.time() - t0)}s"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("iteration")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--configs", default="with_skill,without_skill")
    a = ap.parse_args()
    it = pathlib.Path(a.iteration).expanduser().resolve()
    fix = it / "fixtures"
    shutil.copytree(EVALS / "files", fix, dirs_exist_ok=True)
    evs = json.load(open(EVALS / "evals.json"))["evals"]
    for ev in evs:
        ev["prompt"] = ev["prompt"].replace("{FIXTURES}", str(fix))
    cfgs = a.configs.split(",")
    jobs = [(ev, c, k) for ev in evs for c in cfgs for k in range(1, a.runs + 1)]
    with cf.ThreadPoolExecutor(6) as ex:
        for r in cf.as_completed([ex.submit(run, it, *j) for j in jobs]):
            print(r.result(), flush=True)


if __name__ == "__main__":
    main()
