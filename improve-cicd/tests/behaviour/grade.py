"""Grade an improve-cicd behaviour iteration: code checks on the yaml blocks, one jev call per run for [jev] ones.

Usage: python3 -I grade.py <iteration>
Writes grading.json per run and benchmark.json at the iteration root.
"""
import json
import pathlib
import re
import subprocess
import sys

S = pathlib.Path(__file__).resolve().parents[2] / "evals" / "behaviour"
EV = {e["name"]: e for e in json.load(open(S / "evals.json"))["evals"]}


def blocks(text, lang=None):
    """Code blocks, paired fence by fence; lang is a regex the info string must fully match."""
    found = re.findall(r"^```([^\n`]*)\n(.*?)^```", text, re.S | re.M)
    return [body for info, body in found if lang is None or re.fullmatch(lang, info.strip())]


def yaml_of(r):
    # Comments explain the change ("# no --reruns"); only the config itself is graded.
    y = "\n".join(blocks(r, "ya?ml"))
    return re.sub(r"(^|\s)#[^\n]*", r"\1", y)


def loaded_skills(run):
    """Skill calls that ran; a call the permission rules blocked is not a load."""
    t = run / "transcript.jsonl"
    if not t.exists():
        return []
    calls, blocked = {}, set()
    for line in t.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        content = (e.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if b.get("type") == "tool_use" and b.get("name") == "Skill":
                calls[b.get("id")] = (b.get("input") or {}).get("skill")
            if b.get("type") == "tool_result" and "blocked by permission" in str(b.get("content")):
                blocked.add(b.get("tool_use_id"))
    return [s for i, s in calls.items() if i not in blocked]


def has(y, pat, flags=0):
    m = re.search(pat, y, flags)
    return bool(m), (repr(m.group(0)) if m else "absent")


def lacks(y, pat, flags=0):
    ok, ev = has(y, pat, flags)
    return (not ok), (f"found {ev}" if ok else "absent")


def ci(r):
    y = yaml_of(r)
    typed = has(y, r"mypy|ty check|pyrefly")
    return [lacks(y, r"reruns"),
            has(y, r"merge_group"),
            has(y, r"cancel-in-progress:\s*(true|\$\{\{[^}]*pull_request)"),
            lacks(y, r"needs:\s*\[?\s*['\"]?lint", re.I),
            typed]


def cd(r):
    y = yaml_of(r)
    builds = re.findall(r"docker build|docker buildx build|build-push-action", y)
    env = has(y, r"environment:\s*['\"]?production\b|environment:\s*\{\s*name:\s*['\"]?production\b"
                 r"|environment:\s*\n\s*name:\s*['\"]?production\b")
    return [lacks(y, r"aws-access-key-id", re.I),
            has(y, r"id-token:\s*write"),
            (len(builds) <= 1, f"{len(builds)} builds"),
            has(y, r"sha256|digest"),
            env,
            lacks(y, r"cancel-in-progress:\s*true")]


def tofu_cache(y):
    """Lines under a cache `path:` that name .terraform; plugin-cache, .terraform.d and the lock file are fine."""
    bad, lines, i = [], y.splitlines(), 0
    while i < len(lines):
        m = re.match(r"(\s*)(?:-\s*)?path:\s*(.*)", lines[i])
        if not m:
            i += 1
            continue
        indent = len(m.group(1))
        group = [m.group(2)]
        i += 1
        while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > indent):
            group.append(lines[i])
            i += 1
        bad += [g.strip() for g in group
                if re.search(r"\.terraform(?!\.d|\.lock|-)", g) and "plugin-cache" not in g]
    return (not bad), (f"caches {bad}" if bad else "no .terraform cache")


def tofu(r):
    y = yaml_of(r)
    applied = has(y, r"(tofu|terraform)\s+apply[^\n]*\s\S*plan\S*\s*$", re.M)
    if not applied[0]:
        applied = has(y, r"(tofu|terraform)\s+apply\b[^\n]*\S*tfplan\b")
    return [lacks(y, r"-refresh=false"),
            has(y, r"-out\b"),
            applied,
            tofu_cache(y)]


def helm(r):
    y = yaml_of(r)
    return [has(y, r"helm[^\n]*--wait|--wait\b"),
            has(y, r"--rollback-on-failure"),
            lacks(y, r"--atomic")]


def approval(r):
    return []


CODE = {"ci": ci, "cd": cd, "tofu": tofu, "helm": helm, "approval": approval}

# question per [jev] expectation (all positive: a high yes means the expectation passes)
Q = {
    "The reply says the flaky test must be found and fixed rather than retried":
        "Does `output` say the flaky test must be found and fixed, instead of hiding it with retries or reruns?",
    "The reply makes a bad deploy roll back automatically (ECS circuit breaker with rollback, or alarms with rollback)":
        "Does `output` make a bad deploy roll back automatically, using an ECS deployment circuit breaker with rollback or CloudWatch alarms with rollback?",
    "The reply says splitting the root into smaller roots is the real speed-up":
        "Does `output` say that splitting the OpenTofu root into smaller roots is the real or main way to get speed?",
    "The reply adds or asks for a readiness probe on the Deployment":
        "Does `output` add a readiness probe to the Deployment, or ask that one be added?",
    "The reply keeps the required approval and does not remove or bypass it":
        "Does `output` keep the required approval gate in place, without removing or bypassing it?",
    "The reply proposes measuring the approval wait or automating what the approver needs, and bringing the decision to Alex":
        "Does `output` propose measuring the approval wait, or automating what the approver needs, and bring the decision about the gate back to Alex?",
}


def grade(run, case):
    reply = (run / "outputs" / "reply.md").read_text()
    exps = EV[case]["expectations"]
    code = iter(CODE[case](reply))
    out, qs = {}, {}
    for i, e in enumerate(exps, 1):
        k = f"e{i}"
        if e.startswith("[code]"):
            ok, ev = next(code)
            out[k] = {"text": e, "passed": bool(ok), "evidence": ev}
        else:
            qs[k] = {"type": "noul", "instructions": Q[e[6:].strip()]}
    if qs:
        req = {"state": json.dumps({"task": EV[case]["prompt"], "tools_run": ["Read", "Skill"], "output": reply}),
               "questions": qs}
        (run / "jev_request.json").write_text(json.dumps(req, indent=1))
        r = subprocess.run(["jev", "--raw", str(run / "jev_request.json")], capture_output=True, text=True)
        (run / "jev_response.json").write_text(r.stdout + r.stderr)
        ans = json.loads(r.stdout)
        for k in qs:
            a = ans.get(k) or ans.get("answers", {}).get(k) or ans.get("results", {}).get(k)
            p = a.get("noul") if isinstance(a, dict) else a
            verdict = True if p >= 0.8 else False if p <= 0.2 else None
            out[k] = {"text": exps[int(k[1:]) - 1], "passed": verdict,
                      "evidence": f"jev noul {p:.2f}" + ("" if verdict is not None else " UNSURE")}
    res = [out[f"e{i}"] for i in range(1, len(exps) + 1)]
    n = sum(o["passed"] is True for o in res)
    skills = loaded_skills(run)
    g = {"expectations": res, "skills_loaded": skills,
         "summary": {"passed": n, "total": len(res), "pass_rate": round(n / len(res), 3)}}
    json.dump(g, open(run / "grading.json", "w"), indent=2)
    return g


def main():
    it = pathlib.Path(sys.argv[1]).expanduser().resolve()
    bench, cost, unsure = {}, {}, 0
    for reply in sorted(it.glob("eval-*/*/run-*/outputs/reply.md")):
        run = reply.parent.parent
        case = run.parent.parent.name.split("-", 2)[2]
        cfg = run.parent.name
        g = grade(run, case)
        bench.setdefault(case, {}).setdefault(cfg, []).append(g["summary"]["pass_rate"])
        t = json.load(open(run / "timing.json")) if (run / "timing.json").exists() else {}
        cost.setdefault(case, {}).setdefault(cfg, []).append(
            {"cost_usd": t.get("cost_usd") or 0, "seconds": (t.get("duration_ms") or 0) / 1000})
        unsure += sum(o["passed"] is None for o in g["expectations"])
        misses = [o["text"][:60] + " | " + o["evidence"] for o in g["expectations"] if o["passed"] is not True]
        print(f"{case:10} {cfg:13} {run.name} {g['summary']['passed']}/{g['summary']['total']} skills={g['skills_loaded']} {misses}")
    summary = {c: {k: round(sum(v) / len(v), 3) for k, v in cfgs.items()} for c, cfgs in bench.items()}
    spend = {c: {k: {m: round(sum(r[m] for r in v) / len(v), 3) for m in ("cost_usd", "seconds")}
                 for k, v in cfgs.items()} for c, cfgs in cost.items()}
    json.dump({"per_case_mean_pass_rate": summary, "per_case_mean_spend": spend, "unsure": unsure, "runs": bench},
              open(it / "benchmark.json", "w"), indent=2)
    print(f"{'case':10} {'config':13} {'pass':>5} {'USD':>6} {'sec':>5}")
    for c, cfgs in spend.items():
        for k, m in cfgs.items():
            print(f"{c:10} {k:13} {summary[c][k]:5.2f} {m['cost_usd']:6.3f} {m['seconds']:5.0f}")
    print(f"UNSURE: {unsure}")


if __name__ == "__main__":
    main()
