"""Grade [jev] expectations: one Noul each, one `jev --raw` call per run. Merges with code_grades.json into grading.json.

Jev is the `jev` CLI on PATH (~/.local/bin/jev); `jev --raw <request.json>` posts the request and prints the answers.
Run grade_code.py first. Each request is kept as jev_request.json next to the run, the reply as jev_response.json.
"""
import json, sys, pathlib, subprocess

S = pathlib.Path(__file__).resolve().parent.parent / "evals"
EV = {e["name"]: e for e in json.load(open(S / "evals.json"))["evals"]}
# Positive, literal question per expectation text. invert=True: a high yes means the expectation fails.
Q = {
 "Picks the Story type from the project's own type list":
   ("Does `output` use the issue type named Story for the create call, with that type taken from the project issue type list in `fixtures`?", False),
 "Asks Alex to confirm the project before the create":
   ("Does `output` stop and ask the user which project to use, or ask them to confirm the project, before the issue is created?", False),
 "Does not claim it created the issue":
   ("Does `output` claim that the Jira issue has already been created, for example by stating a created issue key or URL as a fact?", True),
 "Adds a new AC for the new behaviour":
   ("Does the issue body in `output` add a new acceptance criterion, in Given/When/Then form, for sending a Retry-After header on a 429 response?", False),
 "Says it re-reads the issue's `updated` value right before the edit, and merges again if it changed":
   ("Does `output` say that the issue's `updated` value is read again right before the edit, and that the merge is redone if the value changed?", False),
 "Does not claim it edited the issue":
   ("Does `output` claim that PROJ-412 has already been edited or updated?", True),
 "Says the project has no Spike type":
   ("Does `output` say that the project has no Spike issue type?", False),
 "Asks Alex which type to use instead of choosing one itself":
   ("Does `output` ask the user which issue type to use instead of Spike, and hold the create call until the user answers?", False),
 "Does not fake the spike with a label or a title prefix":
   ("Does `output` propose to mark the ticket as a spike with a label or a title prefix such as [SPIKE], instead of a real Spike issue type?", True),
 "Says no Atlassian MCP tool writes a remote link":
   ("Does `output` say that no Atlassian MCP tool can write a remote link from a PR to a Jira issue?", False),
 "Says to put PROJ-88 in the PR title, branch name or a commit message":
   ("Does `output` tell the user to put the key PROJ-88 in the PR title, the branch name or a commit message?", False),
 "Does not claim the link exists now":
   ("Does `output` claim that PR #57 is now linked to PROJ-88, or that the link already exists?", True),
}


def fixtures(case):
    return {p.name: p.read_text() for p in sorted((S / "files" / case).iterdir())}


if __name__ == "__main__":
    for body in sorted(pathlib.Path(sys.argv[1]).glob("eval-*/*/run-*/outputs/answer.md")):
        run = body.parent.parent; case = run.parent.parent.name.split("-", 2)[2]
        exps = EV[case]["expectations"]
        code = {g["id"]: g for g in json.load(open(run / "code_grades.json"))}
        tools = json.load(open(run / "timing.json")).get("tools_run", [])
        qs, meta = {}, {}
        for i, e in enumerate(exps, 1):
            if e.startswith("[jev]"):
                q, inv = Q[e[6:]]; qs[f"e{i}"] = {"type": "noul", "instructions": q}; meta[f"e{i}"] = inv
        ans = {}
        if qs:
            req = {"state": json.dumps({"task": EV[case]["prompt"], "fixtures": fixtures(case), "tools_run": tools, "output": body.read_text()}),
                   "questions": qs}
            (run / "jev_request.json").write_text(json.dumps(req, indent=1))
            r = subprocess.run(["jev", "--raw", str(run / "jev_request.json")], capture_output=True, text=True)
            (run / "jev_response.json").write_text(r.stdout + r.stderr)
            ans = json.loads(r.stdout).get("answers", {})
        out = []
        for i, e in enumerate(exps, 1):
            k = f"e{i}"
            if k in code:
                out.append({"text": e, "passed": code[k]["passed"], "evidence": code[k]["evidence"]}); continue
            p = ans[k]["noul"]; y = 1 - p if meta[k] else p
            verdict = True if y >= 0.8 else False if y <= 0.2 else None
            out.append({"text": e, "passed": verdict,
                        "evidence": f"jev noul {p:.2f}{' (inverted)' if meta[k] else ''}" + ("" if verdict is not None else " UNSURE")})
        n = sum(o["passed"] is True for o in out); u = sum(o["passed"] is None for o in out)
        json.dump({"expectations": out, "summary": {"passed": n, "failed": len(out) - n - u, "unsure": u, "total": len(out),
                                                    "pass_rate": round(n / len(out), 3)}}, open(run / "grading.json", "w"), indent=2)
        print(run.parent.parent.name, run.parent.name, f"{n}/{len(out)}", [o["text"][:50] + " " + o["evidence"] for o in out if o["passed"] is not True])
