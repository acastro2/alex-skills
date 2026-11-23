#!/usr/bin/env python3
"""Grade the search eval runs: `code` expectations by counting json blocks, the rest with Jev.

    python3 -I grade.py --selftest                # offline known answers: must print SELFTEST PASS
    python3 -I grade.py prepare ~/.agents/skill-workspace/alex-skills/search/iteration-N
    # orchestrator: send each run's jev-request.json to ask_jev, save the reply as jev-response.json
    python3 -I grade.py apply ~/.agents/skill-workspace/alex-skills/search/iteration-N

Jev is an MCP tool the orchestrator calls by hand, not a local CLI, so grading has two
phases. `prepare` writes jev-request.json next to each run. `apply` reads jev-response.json
(either {"answers": {...}} or the answers dict itself, each answer {"noul": float}) and
writes grading.json. Bands from ../../jev/references/eval-grading.md: yes >= 0.80 passes,
yes <= 0.20 fails, the middle is unsure (None). A run with no jev-response.json is graded on
its code expectations only, with a warning.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

FENCE = re.compile(r"(?:```|~~~)json\s*\n(.*?)(?:```|~~~)", re.S | re.I)
PASS_AT = 0.80
FAIL_AT = 0.20


def split_output(output: str) -> dict:
    """The calls and the prose apart: mixed together, Jev misread one for the other."""
    return {"calls": FENCE.findall(output), "explanation": FENCE.sub("", output).strip()}


def code_verdict(output: str, bounds: list[int]) -> tuple[bool, str]:
    """True when the number of json blocks is within bounds [min, max], inclusive."""
    n = len(split_output(output)["calls"])
    lo, hi = bounds
    return lo <= n <= hi, f"code: {n} json blocks, want {lo}..{hi}"


def band_verdict(noul: float, invert: bool) -> tuple[bool | None, float]:
    """Map a Noul score to pass (True), fail (False) or unsure (None). Returns (verdict, yes)."""
    yes = 1 - noul if invert else noul
    if yes >= PASS_AT:
        return True, yes
    if yes <= FAIL_AT:
        return False, yes
    return None, yes


def load_evals() -> dict[int, dict]:
    return {e["id"]: e for e in json.load(open(os.path.join(HERE, "evals.json")))["evals"]}


def run_dirs(root: str) -> list[str]:
    return sorted(glob.glob(os.path.join(os.path.expanduser(root), "eval-*", "*", "run-*")))


def eval_id(run_dir: str) -> int:
    return int(re.search(r"eval-(\d+)-", run_dir).group(1))


def prepare(root: str) -> int:
    evals = load_evals()
    for run_dir in run_dirs(root):
        ev = evals[eval_id(run_dir)]
        res = json.load(open(os.path.join(run_dir, "result.json")))
        questions = {f"e{i}": {"type": "noul", "instructions": x["jev"]}
                     for i, x in enumerate(ev["expectations"]) if "jev" in x}
        if not questions:
            print(f"{run_dir}: no jev expectations, nothing to send")
            continue
        state = {"task": ev["prompt"], **split_output(res.get("output", ""))}
        body = {"state": json.dumps(state), "questions": questions}
        json.dump(body, open(os.path.join(run_dir, "jev-request.json"), "w"), indent=1)
        print(f"{run_dir}: wrote jev-request.json ({len(questions)} questions)")
    return 0


def read_answers(run_dir: str) -> dict | None:
    path = os.path.join(run_dir, "jev-response.json")
    if not os.path.isfile(path):
        return None
    data = json.load(open(path))
    return data["answers"] if isinstance(data, dict) and "answers" in data else data


def grade_run(run_dir: str, ev: dict) -> dict | None:
    res = json.load(open(os.path.join(run_dir, "result.json")))
    answers = read_answers(run_dir)
    rows = []
    for i, x in enumerate(ev["expectations"]):
        if "code" in x:
            ok, evidence = code_verdict(res.get("output", ""), x["code"]["calls"])
            rows.append({"text": x["text"], "passed": ok, "evidence": evidence})
        elif "jev" in x and answers is not None:
            a = answers.get(f"e{i}")
            if a is None:
                rows.append({"text": x["text"], "passed": None, "evidence": f"no answer for e{i}"})
                continue
            verdict, yes = band_verdict(a["noul"], bool(x.get("invert")))
            inv = " (inverted)" if x.get("invert") else ""
            rows.append({"text": x["text"], "passed": verdict,
                         "evidence": f"jev yes={yes:.2f}{inv} (noul {a['noul']:.2f})"})
    if answers is None and any("jev" in x for x in ev["expectations"]):
        print(f"WARNING {run_dir}: no jev-response.json, graded code expectations only")
        return None
    firm = [r for r in rows if r["passed"] is not None]
    summary = {"passed": sum(r["passed"] for r in firm), "failed": sum(not r["passed"] for r in firm),
               "unsure": len(rows) - len(firm), "total": len(rows)}
    summary["pass_rate"] = round(summary["passed"] / len(firm), 2) if firm else None
    out = {"expectations": rows, "summary": summary}
    json.dump(out, open(os.path.join(run_dir, "grading.json"), "w"), indent=1)
    return out


def apply(root: str) -> int:
    evals = load_evals()
    totals: dict[str, list[int]] = {}
    for run_dir in run_dirs(root):
        label = run_dir.split(os.sep)[-2]
        name = os.path.basename(run_dir)
        g = grade_run(run_dir, evals[eval_id(run_dir)])
        if g is None:
            ev = evals[eval_id(run_dir)]
            res = json.load(open(os.path.join(run_dir, "result.json")))
            rows = []
            for x in ev["expectations"]:
                if "code" in x:
                    ok, evidence = code_verdict(res.get("output", ""), x["code"]["calls"])
                    rows.append({"text": x["text"], "passed": ok, "evidence": evidence})
            g = {"expectations": rows, "summary": {"passed": sum(r["passed"] for r in rows),
                 "total": len(rows), "unsure": 0}}
        s = g["summary"]
        t = totals.setdefault(label, [0, 0, 0])
        t[0] += s["passed"]; t[1] += s["total"]; t[2] += s["unsure"]
        fails = [r["text"][:60] + " [" + r["evidence"] + "]" for r in g["expectations"] if r["passed"] is not True]
        print(f"eval {eval_id(run_dir)} {label} {name}: {s['passed']}/{s['total']}"
              + (f"  not passed: {fails}" if fails else ""))
    for label, (p, n, u) in totals.items():
        print(f"TOTAL {label}: {p}/{n} passed, {u} unsure")
    return 0


def selftest() -> int:
    failures = 0

    def check(name: str, got, want) -> None:
        nonlocal failures
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: want {want}, got {got}")

    one = "Plan first.\n```json\n{\"query\": \"Series A Brazil\"}\n```\nThat is the call."
    two = "```json\n{\"a\": 1}\n```\nand\n```json\n{\"b\": 2}\n```"
    none = "No call. I would tell the user it is a script task."
    check("a1 one block vs [1,1]", code_verdict(one, [1, 1])[0], True)
    check("a2 two blocks vs [1,1]", code_verdict(two, [1, 1])[0], False)
    check("a3 zero blocks vs [0,1]", code_verdict(none, [0, 1])[0], True)

    check("b1 noul 0.9 invert false", band_verdict(0.9, False)[0], True)
    check("b2 noul 0.5 invert false", band_verdict(0.5, False)[0], None)
    check("b3 noul 0.1 invert false", band_verdict(0.1, False)[0], False)
    check("b4 noul 0.9 invert true", band_verdict(0.9, True)[0], False)
    check("b5 noul 0.5 invert true", band_verdict(0.5, True)[0], None)
    check("b6 noul 0.1 invert true", band_verdict(0.1, True)[0], True)

    sp = split_output(one)
    check("c1 one json body kept as call", len(sp["calls"]), 1)
    check("c2 call body holds the json", "Series A Brazil" in sp["calls"][0], True)
    check("c3 explanation has no json fence", "```" in sp["explanation"], False)
    check("c4 explanation keeps the prose", sp["explanation"], "Plan first.\n\nThat is the call.")

    print("SELFTEST", "PASS" if not failures else f"FAIL ({failures} checks wrong)")
    return 1 if failures else 0


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["prepare", "apply"])
    ap.add_argument("root")
    args = ap.parse_args()
    return prepare(args.root) if args.command == "prepare" else apply(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
