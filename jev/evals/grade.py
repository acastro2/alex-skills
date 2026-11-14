#!/usr/bin/env python3
"""Grade the jev eval runs: `code:` expectations from the call count, the rest with Jev.

    python3 -I grade.py --selftest     # known answers first: must print SELFTEST PASS
    python3 -I grade.py ~/.agents/skill-workspace/alex-skills/jev/iteration-1

One Jev call per output, one Noul per judgment expectation, bands from
../references/eval-grading.md (0.80 pass, 0.20 fail, the middle is unsure). Writes
grading.json next to each result.json and prints a pass table per eval and version.
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Per eval: expectation index -> (Noul question, invert) or a Choice dict with the option
# that passes. Code expectations are absent here.
QUESTIONS = {
    1: {
        1: ("Is there one item in `calls` that asks both whether the ticket asks for a refund and which order it is for?", False),
        2: "code",  # graded by refers_to_other(): exact phrases, so code, not Jev
        3: ("Does the which-order question in `calls` offer an option meaning no order, neither, or not mentioned?", False),
        4: ("Does `explanation` say the which-order answer is used only when the refund answer passes?", False),
    },
    2: {
        1: ("Does `calls` include follow-up questions for at least two different incident types, for example a lost device or misdirected data as well as phishing?", False),
        2: ("Does `explanation` say the code uses only the follow-up answers for the incident type that was picked?", False),
    },
    3: {
        1: ("Does the state of the second item in `calls` hold only the clause the first call picked, or a placeholder for it, instead of all 40 clauses?", False),
        2: ("Does `explanation` say the second call needs the first call's answer to build its state?", False),
    },
    4: {
        1: ("Is there one item in `calls` that asks the dispute question, the which_line question, and the wants_document question?", False),
        2: ("Does the which_line question in `calls` offer an option meaning no line or none?", False),
        3: ("Does `explanation` say the old calls sent the same state, or that one call is cheaper or faster?", False),
    },
}
EXPECTED_CALLS = {1: 1, 2: 1, 3: 2, 4: 1}


FENCE = re.compile(r"(?:```|~~~)json\s*\n(.*?)(?:```|~~~)", re.S | re.I)
REFERS = re.compile(r"\b(if (the )?(answer|result)|answer above|question above|previous (question|answer|call)|"
                    r"first (question|answer|call)|if yes|if so)\b", re.I)


def split_output(output: str) -> dict:
    """The calls and the prose apart: mixed together, Jev misread one for the other."""
    return {"calls": FENCE.findall(output), "explanation": FENCE.sub("", output).strip()}


def refers_to_other(output: str) -> bool:
    """True when a question text inside a call points at another question or its answer."""
    return any(REFERS.search(c) for c in split_output(output)["calls"])


def ask_jev(state: dict, questions: dict, save_to: str | None = None) -> dict:
    body = json.dumps({"state": json.dumps(state), "questions": questions})
    if save_to:  # keep the request next to the run, so a reader can ask it again
        open(save_to, "w").write(body)
    out = subprocess.run(["jev", "-", "--raw"], input=body, capture_output=True, text=True, check=True).stdout
    return json.loads(out)["answers"]


def jev_verdicts(eid: int, task: str, output: str, save_to: str | None = None) -> dict[int, tuple[bool | None, float, bool]]:
    """Expectation index -> (verdict, raw noul, inverted), with the bands of eval-grading.md."""
    qs = {}
    for i, q in QUESTIONS[eid].items():
        if q == "code":
            continue
        if isinstance(q, dict):  # a Choice: passes when it picks q["pass"]
            qs[f"e{i}"] = {"type": "choice", "instructions": q["instructions"], "criteria": q["criteria"]}
        else:
            qs[f"e{i}"] = {"type": "noul", "instructions": q[0]}
    answers = ask_jev({"task": task, **split_output(output)}, qs, save_to)
    out = {}
    for i, q in QUESTIONS[eid].items():
        if q == "code":
            out[i] = (not refers_to_other(output), 1.0, False)
            continue
        a = answers[f"e{i}"]
        if isinstance(q, dict):
            conf = a.get("confidence", 0)
            firm = conf >= 0.80
            out[i] = ((a["choice"] == q["pass"]) if firm else None, conf, False)
        else:
            yes = 1 - a["noul"] if q[1] else a["noul"]
            out[i] = (True if yes >= 0.80 else False if yes <= 0.20 else None, a["noul"], q[1])
    return out


def grade(run_dir: str, eval_def: dict) -> dict:
    res = json.load(open(os.path.join(run_dir, "result.json")))
    eid = eval_def["id"]
    rows = []
    for i, text in enumerate(eval_def["expectations"]):
        if text.startswith("code:"):
            ok = res.get("calls") == EXPECTED_CALLS[eid]
            rows.append({"text": text, "passed": ok, "evidence": f"code: {res.get('calls')} json blocks"})
    verdicts = jev_verdicts(eid, eval_def["prompt"], res.get("output", ""),
                            os.path.join(run_dir, "jev-request.json"))
    for i, (verdict, p, invert) in verdicts.items():
        how = "code: phrase check" if QUESTIONS[eid][i] == "code" else f"jev {p:.2f}{' (inverted)' if invert else ''}"
        rows.append({"text": eval_def["expectations"][i], "passed": verdict, "evidence": how})
    firm = [r for r in rows if r["passed"] is not None]
    summary = {"passed": sum(r["passed"] for r in firm), "failed": sum(not r["passed"] for r in firm),
               "unsure": len(rows) - len(firm), "total": len(rows)}
    summary["pass_rate"] = round(summary["passed"] / len(firm), 2) if firm else None  # unsure is not a fail
    out = {"expectations": rows, "summary": summary}
    json.dump(out, open(os.path.join(run_dir, "grading.json"), "w"), indent=1)
    return out


# Hand-written outputs with known verdicts. Run before you trust a new grading pass.
KNOWN = [
    (1, "One call.\n```json\n{\"state\": \"{ticket}\", \"questions\": {\"refund\": {\"type\": \"noul\", \"instructions\": \"Does `ticket` ask for money back?\"}, \"order\": {\"type\": \"choice\", \"instructions\": \"For which order does `ticket` ask for money back?\", \"criteria\": {\"4471\": \"order 4471\", \"4502\": \"order 4502\", \"Neither\": \"no order\"}}}}\n```\nThe code checks `refund` first and reads `order` only when refund is 0.80 or more; otherwise it ignores `order`.",
     {1: True, 2: True, 3: True, 4: True}),
    (1, "Call 1:\n```json\n{\"state\": \"{ticket}\", \"questions\": {\"refund\": {\"type\": \"noul\", \"instructions\": \"Does `ticket` ask for money back?\"}}}\n```\nCall 2:\n```json\n{\"state\": \"{ticket}\", \"questions\": {\"order\": {\"type\": \"choice\", \"instructions\": \"If the answer above is yes, which order is it?\", \"criteria\": {\"4471\": \"order 4471\", \"4502\": \"order 4502\"}}}}\n```\nThe code sends both calls and logs the answers.",
     {1: False, 2: False, 3: False, 4: False}),
    (3, "Call 1 picks the clause from all 40.\n```json\n{\"state\": \"{complaint, clauses}\", \"questions\": {\"which\": {\"type\": \"choice\", \"instructions\": \"Which clause does `complaint` rely on?\"}}}\n```\nCall 2 sends only that clause:\n```json\n{\"state\": \"{complaint, clause: <value the earlier call returned>}\", \"questions\": {\"allows\": {\"type\": \"noul\", \"instructions\": \"Does `clause` allow ending with 30 days notice?\"}}}\n```\nThe second call needs the first answer to build its state.",
     {1: True, 2: True}),
    (3, "One call is enough.\n```json\n{\"state\": \"{complaint, clauses: all 40 clauses}\", \"questions\": {\"which\": {\"type\": \"choice\", \"instructions\": \"Which clause does `complaint` rely on?\"}, \"allows\": {\"type\": \"noul\", \"instructions\": \"Does any clause in `clauses` allow ending with 30 days notice?\"}}}\n```\nThe code reads both answers.",
     {1: False, 2: False}),
]


def selftest() -> int:
    bad = unsure = 0
    for eid, output, expected in KNOWN:
        got = jev_verdicts(eid, "known-answer check", output)
        for i, want in expected.items():
            verdict, p, _ = got[i]
            wrong = verdict is not None and verdict != want  # unsure goes to the LLM grader, not a fail
            bad += wrong
            unsure += verdict is None
            tag = "  <-- WRONG" if wrong else "  (unsure: LLM grader)" if verdict is None else ""
            print(f"known eval {eid} e{i}: want {want}, got {verdict} ({p:.2f}){tag}")
    print("SELFTEST", "PASS" if not bad else f"FAIL ({bad} firm verdicts wrong)", f"- {unsure} unsure")
    return 1 if bad else 0


def main(root: str) -> int:
    evals = {e["id"]: e for e in json.load(open(os.path.join(HERE, "evals.json")))["evals"]}
    totals: dict[str, list[int]] = {}
    for run_dir in sorted(glob.glob(os.path.join(os.path.expanduser(root), "eval-*", "*", "run-*"))):
        eid = int(re.search(r"eval-(\d+)-", run_dir).group(1))
        label = run_dir.split(os.sep)[-2]
        g = grade(run_dir, evals[eid])
        s = g["summary"]
        t = totals.setdefault(label, [0, 0, 0])
        t[0] += s["passed"]; t[1] += s["total"]; t[2] += s["unsure"]
        fails = [r["text"][:60] + " [" + r["evidence"] + "]" for r in g["expectations"] if r["passed"] is not True]
        print(f"eval {eid} {label} {run_dir[-5:]}: {s['passed']}/{s['total']}" + (f"  not passed: {fails}" if fails else ""))
    for label, (p, n, u) in totals.items():
        print(f"TOTAL {label}: {p}/{n} passed, {u} unsure")
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest() if sys.argv[1:] == ["--selftest"] else main(sys.argv[1]))
