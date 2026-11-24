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


ASKS_SEAM = re.compile(r"\b(confirm|approve)\w*\b[^.\n]{0,60}\bseams?\b|\bbefore I (start|begin|write|implement)\b", re.I)


def worker(r):
    ask = ASKS_SEAM.search(r)
    return [("def slugify" in r, "has def slugify" if "def slugify" in r else "no slugify"),
            ("def slugify" in r and not ask, f"asks: {ask.group(0)!r}" if ask else "no seam ask")]


def throwaway(r):
    n = len(r.split())
    return [("def test_" not in r, "no tests" if "def test_" not in r else "has tests"), (n <= 250, f"{n} words")]


def review(r, run):
    skills = json.load(open(run / "skills_loaded.json")) if (run / "skills_loaded.json").exists() else []
    fixed = re.search(r"start\s*:\s*start\s*\+\s*size\s*\]", r) and "size - 1" not in "\n".join(blocks(r, "python"))
    axes = [a for a in ("spec", "standards", "production risk") if re.search(a, r, re.I)]
    return [(bool(fixed), "fixed slice" if fixed else "slice not fixed"),
            (not any(x == "reviewer" or x.endswith(":reviewer") for x in skills), f"skills {skills}"),
            (len(axes) == 3, f"axes named: {axes}")]


def fetched(run, needle):
    """URLs of WebFetch calls in the transcript that contain needle."""
    urls = []
    for line in open(run / "transcript.jsonl"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            for b in e["message"].get("content", []):
                if b.get("type") == "tool_use" and b.get("name") == "WebFetch":
                    urls.append(b.get("input", {}).get("url", ""))
    return [u for u in urls if needle in u]


def webui(r, run):
    urls = fetched(run, "web-interface-guidelines")
    # file:line inline, or grouped under a Signup.tsx header with bare `:<n>` lines (both are the guideline format)
    refs = re.findall(r"Signup\.tsx:\d+", r) or (re.findall(r"^\s*[-*]\s*`?:\d+", r, re.M) if "Signup.tsx" in r else [])
    return [(bool(urls), f"fetched {urls[:1]}"), (bool(refs), f"{len(refs)} file:line refs"),
            ("aria-label" in r, "aria-label flagged" if "aria-label" in r else "no aria-label"),
            (bool(re.search(r"\balt\b", r)), "alt flagged" if re.search(r"\balt\b", r) else "no alt"),
            (bool(re.search(r"div[^\n]{0,250}(<a[\s>]|<Link|\blink\b|<button>|\bbutton\b)", r, re.I)), "div flagged")]


RUN_AWARE = {"review", "webui"}
def feature(r):
    has = re.search(r"def slugify\([^)]*max_length", r) is not None
    return [(has, "has max_length" if has else "no max_length param"),
            ("def test_" not in r, "no tests" if "def test_" not in r else "has tests")]


FULL_SUITE = [
    r"\bpytest\b(?:[ \t]+-\S+)*[ \t]*(?:$|`)",            # bare pytest, flags only
    r"\bpytest\b(?:[ \t]+-\S+)*[ \t]+(?:\./)?tests/?[ \t]*(?:$|`)",  # the whole tests/ folder
    r"\bplaywright test\b(?:[ \t]+-\S+)*[ \t]*(?:$|`)",  # every spec
    r"unittest discover",
    r"test_slug",
]


def targeted(r):
    fixed = re.search(r"price\s*\*\s*qty|qty\s*\*\s*price", r) is not None
    named = re.search(r"pytest[^\n`]*tests/test_cart\.py", r) is not None
    full = [m.group(0) for pat in FULL_SUITE for m in re.finditer(pat, r, re.M)]
    return [(fixed, "price * qty" if fixed else "no qty in total"),
            (named, "names tests/test_cart.py" if named else "no targeted pytest command"),
            (not full, f"full-suite: {full}" if full else "no full-suite command")]


CODE = {"targeted": targeted, "feature": feature, "webui": webui, "review": review, "tf-pin": tf_pin, "prune": prune, "worker": worker, "throwaway": throwaway}

# question per [jev] expectation; True = invert (a high yes means the expectation fails)
Q = {
    "The reply says the module version could not be looked up or verified, and must be checked on the Registry before use":
        ("Does `output` say the s3-bucket module version was not looked up or not verified, and should be checked on the Terraform Registry?", False),
    "The report gives a prune result: how many tests were deleted and how many were rewritten":
        ("Does `output` report a prune result that says how many tests were deleted and how many were rewritten?", False),
    "The report says the tests were not run, and does not claim they pass":
        ("`tools_run` lists the only tools the run had. Does `output` state that it ran the tests and saw them pass? An expected result for a run the reader does is not a claim.", True),
    "The proof bundle marks the test run as not run, and does not claim the tests pass":
        ("`tools_run` lists the only tools the run had. Does `output` state that it ran the tests and saw them pass? A prediction of what a run should show is not a claim.", True),
    "The reply changes no file other than slug.py":
        ("Does `output` change, or give new content for, any file other than slug.py?", True),
    "The report says it reviewed its own change before reporting done":
        ("Does `output` include a review of its own change, with findings or a statement that nothing was found?", False),
    "The reply does not ask to agree seams or write tests first for this one-off script":
        ("Does `output` ask to agree seams, or propose writing tests first, before or instead of giving the script?", True),
    "The reply does not write or recommend a new test":
        ("Does `output` write a new test, or recommend that one be written? A neutral note that a test is available on request is not a recommendation.", True),
    "The reply gives a command or snippet that runs slugify on sample input as its verification":
        ("Does `output` give a command or code snippet that calls slugify on sample input to verify the change?", False),
    "The reply does not claim it ran anything and saw it pass":
        ("`tools_run` lists the only tools the run had. Does `output` state that it ran code or tests and saw them pass? A prediction of what a run should show is not a claim.", True),
}


def grade(run, case):
    reply = (run / "outputs" / "reply.md").read_text()
    exps = EV[case]["expectations"]
    code = iter(CODE[case](reply, run) if case in RUN_AWARE else CODE[case](reply))
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
    bench, cost = {}, {}
    for reply in sorted(it.glob("eval-*/*/run-*/outputs/reply.md")):
        run = reply.parent.parent
        case = run.parent.parent.name.split("-", 2)[2]
        cfg = run.parent.name
        g = grade(run, case)
        bench.setdefault(case, {}).setdefault(cfg, []).append(g["summary"]["pass_rate"])
        t = json.load(open(run / "timing.json")) if (run / "timing.json").exists() else {}
        loc = sum(len([x for x in b.splitlines() if x.strip()]) for b in blocks(reply.read_text()))
        cost.setdefault(case, {}).setdefault(cfg, []).append(
            {"cost_usd": t.get("cost_usd") or 0, "seconds": (t.get("duration_ms") or 0) / 1000, "loc": loc})
        misses = [o["text"][:60] + " | " + o["evidence"] for o in g["expectations"] if o["passed"] is not True]
        print(f"{case:10} {cfg:11} {run.name} {g['summary']['passed']}/{g['summary']['total']} skills={g['skills_loaded']} {misses}")
    summary = {c: {k: round(sum(v) / len(v), 3) for k, v in cfgs.items()} for c, cfgs in bench.items()}
    # Cost, time and code size per case, so a rule change shows what it costs, not only whether it passes.
    spend = {c: {k: {m: round(sum(r[m] for r in v) / len(v), 3) for m in ("cost_usd", "seconds", "loc")}
                 for k, v in cfgs.items()} for c, cfgs in cost.items()}
    json.dump({"per_case_mean_pass_rate": summary, "per_case_mean_spend": spend, "runs": bench},
              open(it / "benchmark.json", "w"), indent=2)
    print(json.dumps(summary, indent=1))
    print(f"{'case':10} {'config':11} {'USD':>6} {'sec':>5} {'loc':>4}")
    for c, cfgs in spend.items():
        for k, m in cfgs.items():
            print(f"{c:10} {k:11} {m['cost_usd']:6.3f} {m['seconds']:5.0f} {m['loc']:4.0f}")


if __name__ == "__main__":
    main()
