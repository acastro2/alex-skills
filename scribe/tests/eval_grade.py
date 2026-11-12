"""Grade every run: `code` checks by regex over the reply, `jev` checks as one Noul each in one
jev call per run (jev/references/eval-grading.md). invert=True means a high yes fails the check.
Writes grading.json (text, passed, evidence) per run, in the layout aggregate_benchmark reads.

Usage: python3 eval_grade.py <iteration-dir>
"""
import json, pathlib, re, subprocess, sys

EVALS = pathlib.Path(__file__).resolve().parent.parent / "evals"
EV = {e["name"]: e for e in json.load(open(EVALS / "evals.json"))["evals"]}


def grade(run: pathlib.Path) -> None:
    case = run.parent.parent.name.split("-", 2)[2]
    ev, reply = EV[case], (run / "outputs" / "reply.md").read_text()
    qs = {f"e{i}": {"type": "noul", "instructions": c["q"]} for i, c in enumerate(ev["checks"], 1) if c["type"] == "jev"}
    ans = {}
    if qs:
        req = {"state": json.dumps({"task": ev["prompt"], "tools_run": ["Read", "Skill"], "output": reply}), "questions": qs}
        (run / "jev_request.json").write_text(json.dumps(req, indent=1))
        r = subprocess.run(["jev", "--raw", str(run / "jev_request.json")], capture_output=True, text=True)
        (run / "jev_response.json").write_text(r.stdout + r.stderr)
        body = json.loads(r.stdout)
        ans = body.get("answers", body)
    out = []
    for i, c in enumerate(ev["checks"], 1):
        inv = c.get("invert", False)
        if c["type"] == "code":
            hit = re.search(c["regex"], reply) is not None
            ok = hit != inv
            out.append({"text": c["text"], "passed": ok, "evidence": f"regex {'found' if hit else 'not found'}: {c['regex']}"})
            continue
        a = ans.get(f"e{i}", {})
        p = a.get("noul") if isinstance(a, dict) else a
        y = 1 - p if inv else p
        verdict = True if y >= 0.8 else False if y <= 0.2 else None
        out.append({"text": c["text"], "passed": verdict,
                    "evidence": f"jev noul {p:.2f}{' (inverted)' if inv else ''}" + ("" if verdict is not None else " UNSURE")})
    n = sum(o["passed"] is True for o in out)
    json.dump({"expectations": out, "summary": {"passed": n, "failed": len(out) - n, "total": len(out),
               "pass_rate": round(n / len(out), 3)}}, open(run / "grading.json", "w"), indent=2)
    misses = [f"{o['text'][:60]} [{o['evidence']}]" for o in out if o["passed"] is not True]
    print(f"{run.parent.parent.name} {run.parent.name}: {n}/{len(out)}", *misses, sep="\n   ")


for reply in sorted(pathlib.Path(sys.argv[1]).glob("eval-*/*/run-*/outputs/reply.md")):
    grade(reply.parent.parent)
