"""Grade a behaviour iteration: code checks first, then one jev call per run for the [jev] ones.

Usage: python3 grade.py <iteration>
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


def tf_pin(r):
    hcl = "\n".join(blocks(r, "(?:hcl|terraform|tf)?"))
    mod = re.search(r'module\s+"[^"]+"\s*\{(?:(?!\nmodule\s).)*?source\s*=\s*"[^"]*s3-bucket[^"]*"(?:(?!\nmodule\s).)*?\n\}', hcl, re.S)
    ver = re.search(r'version\s*=\s*"([^"]+)"', mod.group(0)) if mod else None
    # Exact pin or a loud placeholder both pass; a range does not. With no network, a placeholder that fails
    # `tofu init` beats a version from memory (iteration 2: both configs chose that).
    exact = bool(ver and not re.match(r"\s*(~>|>=|>|<|=\s*\d+\.\d+\s*$)", ver.group(1)))
    prov = re.search(r'source\s*=\s*"hashicorp/aws"\s*\n\s*version\s*=\s*"(~>[^"]+)"', r)
    return [(exact, f"module version {ver.group(1) if ver else 'missing'}"),
            (bool(prov), f"aws provider {prov.group(1) if prov else 'not ~>'}")]


def prune(r):
    py = blocks(r, "python")
    f = py[0] if py else ""
    tests = re.findall(r"^def (test_\w+)", f, re.M)
    disc = re.search(r"discount\s*=\s*0\.2\)\s*==\s*([^\n]+)", f)
    return [("12.5" in f and ".total()" in f, "sum test kept" if "12.5" in f else "no 12.5 sum test"),
            ("._items" not in f, "no ._items" if "._items" not in f else "._items read"),
            ("os.path.exists" not in f, "no exists check" if "os.path.exists" not in f else "exists check kept"),
            (bool(disc and re.fullmatch(r"80(\.0+)?", disc.group(1).strip())) or (not disc and "price * 0.2" not in f and "80" in f),
             f"discount expects {disc.group(1).strip() if disc else 'no discount assert'}"),
            (len(tests) <= 3, f"{len(tests)} tests: {tests}")]


def worker(r):
    return [("def slugify" in r, "has def slugify" if "def slugify" in r else "no slugify")]


def throwaway(r):
    n = len(r.split())
    return [("def test_" not in r, "no tests" if "def test_" not in r else "has tests"), (n <= 250, f"{n} words")]


CODE = {"tf-pin": tf_pin, "prune": prune, "worker": worker, "throwaway": throwaway}

# question per [jev] expectation; True = invert (a high yes means the expectation fails)
Q = {
    "The reply says the module version could not be looked up or verified, and must be checked on the Registry before use":
        ("Does `output` say the s3-bucket module version was not looked up or not verified, and should be checked on the Terraform Registry?", False),
    "The report gives a prune result: how many tests were deleted and how many were rewritten":
        ("Does `output` report a prune result that says how many tests were deleted and how many were rewritten?", False),
    "The report says the tests were not run, and does not claim they pass":
        ("`tools_run` lists the only tools the run had. Does `output` state that it ran the tests and saw them pass? An expected result for a run the reader does is not a claim.", True),
    "The reply implements the change instead of stopping to ask Alex to confirm or agree the seams":
        ("Does `output` hold back the slug.py implementation and instead ask Alex or the user to confirm or agree the seams first?", True),
    "The proof bundle marks the test run as not run, and does not claim the tests pass":
        ("`tools_run` lists the only tools the run had. Does `output` mark the test run as not run or not verified, with no claim that the tests pass?", False),
    "The reply changes no file other than slug.py":
        ("Does `output` change, or give new content for, any file other than slug.py?", True),
    "The reply does not ask to agree seams or write tests first for this one-off script":
        ("Does `output` ask to agree seams, or propose writing tests first, before or instead of giving the script?", True),
}


def grade(run, case):
    reply = (run / "outputs" / "reply.md").read_text()
    exps = EV[case]["expectations"]
    code = iter(CODE[case](reply))
    out, qs, inv = {}, {}, {}
    for i, e in enumerate(exps, 1):
        k = f"e{i}"
        if e.startswith("[code]"):
            ok, ev = next(code)
            out[k] = {"text": e, "passed": bool(ok), "evidence": ev}
        else:
            q, iv = Q[e[6:]]
            qs[k] = {"type": "noul", "instructions": q}
            inv[k] = iv
    if qs:
        req = {"state": json.dumps({"task": EV[case]["prompt"], "tools_run": ["Read", "Skill"], "output": reply}), "questions": qs}
        (run / "jev_request.json").write_text(json.dumps(req, indent=1))
        r = subprocess.run(["jev", "--raw", str(run / "jev_request.json")], capture_output=True, text=True)
        (run / "jev_response.json").write_text(r.stdout + r.stderr)
        ans = json.loads(r.stdout)
        for k in qs:
            a = ans.get(k) or ans.get("answers", {}).get(k) or ans.get("results", {}).get(k)
            p = a.get("noul") if isinstance(a, dict) else a
            y = 1 - p if inv[k] else p
            verdict = True if y >= 0.8 else False if y <= 0.2 else None
            out[k] = {"text": exps[int(k[1:]) - 1], "passed": verdict,
                      "evidence": f"jev noul {p:.2f}{' (inverted)' if inv[k] else ''}" + ("" if verdict is not None else " UNSURE")}
    res = [out[f"e{i}"] for i in range(1, len(exps) + 1)]
    n = sum(o["passed"] is True for o in res)
    skills = json.load(open(run / "skills_loaded.json")) if (run / "skills_loaded.json").exists() else []
    g = {"expectations": res, "skills_loaded": skills,
         "summary": {"passed": n, "total": len(res), "pass_rate": round(n / len(res), 3)}}
    json.dump(g, open(run / "grading.json", "w"), indent=2)
    return g


def main():
    it = pathlib.Path(sys.argv[1]).expanduser().resolve()
    bench = {}
    for reply in sorted(it.glob("eval-*/*/run-*/outputs/reply.md")):
        run = reply.parent.parent
        case = run.parent.parent.name.split("-", 2)[2]
        cfg = run.parent.name
        g = grade(run, case)
        bench.setdefault(case, {}).setdefault(cfg, []).append(g["summary"]["pass_rate"])
        misses = [o["text"][:60] + " | " + o["evidence"] for o in g["expectations"] if o["passed"] is not True]
        print(f"{case:10} {cfg:11} {run.name} {g['summary']['passed']}/{g['summary']['total']} skills={g['skills_loaded']} {misses}")
    summary = {c: {k: round(sum(v) / len(v), 3) for k, v in cfgs.items()} for c, cfgs in bench.items()}
    json.dump({"per_case_mean_pass_rate": summary, "runs": bench}, open(it / "benchmark.json", "w"), indent=2)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
