"""Grade [jev] expectations: one Noul each, one jev call per run. Merges with code_grades.json into grading.json."""
import json, sys, pathlib, subprocess
S = pathlib.Path(__file__).resolve().parent.parent / "evals"
EV = {e["name"]: e for e in json.load(open(S / "evals.json"))["evals"]}
# Positive, literal question per expectation text. invert=True: a high yes means the expectation fails.
Q = {
 "The before diagram shows the transient 503 failing the whole sync run":
   ("Does a before (old behaviour) diagram in `output` show that one 503 from upstream fails the whole sync run?", False),
 "Does not claim that it posted the PR or checked the diagram render":
   ("`tools_run` lists the only tools the run had. Does `output` claim that it posted the PR description to GitHub, or that it checked that the Mermaid diagrams render on the PR page?", True),
 "Has a behaviour-change table that covers the lease skip, the retry, no publish of a failed batch, and the 30 s lease TTL":
   ("Does `output` have a table of behaviour changes whose rows cover all four of: a second worker skips a leased partition, failed writes retry up to 3 times, a failed batch is not published, and a 30 s lease TTL?", False),
 "Says the record schema stays unchanged, and for the topic names and CLI flags either says they stay unchanged or marks them not verified":
   ("Does `output` say the record schema stays unchanged, and for the publish topic names and the CLI flags either say they stay unchanged or say they are not verified?", False),
 "Explains why batch_017 publish order differs":
   ("Does `output` explain that batch_017's publish order differs because main published a half batch before the error and the new code publishes nothing for the failed attempt?", False),
 "Says the tests were not run or their result is not verified":
   ("Does `output` say that the tests were not run, or that their result is not verified or not known?", False),
 "States that a known device with no schedules still gets 200 with an empty list":
   ("Does `output` state that a device that exists but has no schedules still gets a 200 response with an empty list?", False),
 "Warns that clients that relied on 200 with an empty list for an unknown device now get a 404":
   ("Does `output` warn that API clients that got 200 with an empty list for an unknown device will now get a 404 instead?", False),
}
for body in sorted(pathlib.Path(sys.argv[1]).glob("eval-*/*/run-*/outputs/pr_body.md")):
    run = body.parent.parent; case = run.parent.parent.name.split("-", 2)[2]
    exps = EV[case]["expectations"]; code = {g["id"]: g for g in json.load(open(run / "code_grades.json"))}
    qs, meta = {}, {}
    for i, e in enumerate(exps, 1):
        if e.startswith("[jev]"):
            q, inv = Q[e[6:]]; qs[f"e{i}"] = {"type": "noul", "instructions": q}; meta[f"e{i}"] = inv
    ans = {}
    if qs:
        req = {"state": json.dumps({"task": EV[case]["prompt"], "tools_run": ["Read", "Skill"], "output": body.read_text()}), "questions": qs}
        (run / "jev_request.json").write_text(json.dumps(req, indent=1))
        r = subprocess.run(["jev", "--raw", str(run / "jev_request.json")], capture_output=True, text=True)
        (run / "jev_response.json").write_text(r.stdout + r.stderr)
        ans = json.loads(r.stdout)
    out = []
    for i, e in enumerate(exps, 1):
        k = f"e{i}"
        if k in code: out.append({"text": e, "passed": code[k]["passed"], "evidence": code[k]["evidence"]}); continue
        a = ans.get(k) or ans.get("answers", {}).get(k) or ans.get("results", {}).get(k)
        p = a.get("noul") if isinstance(a, dict) else a
        y = 1 - p if meta[k] else p
        verdict = True if y >= 0.8 else False if y <= 0.2 else None
        out.append({"text": e, "passed": verdict, "evidence": f"jev noul {p:.2f}{' (inverted)' if meta[k] else ''}" + ("" if verdict is not None else " UNSURE")})
    n = sum(o["passed"] is True for o in out)
    json.dump({"expectations": out, "summary": {"passed": n, "failed": len(out) - n, "total": len(out), "pass_rate": round(n / len(out), 3)}},
              open(run / "grading.json", "w"), indent=2)
    print(run.parent.parent.name, run.parent.name, f"{n}/{len(out)}", [o["text"][:50] + " " + o["evidence"] for o in out if o["passed"] is not True])
