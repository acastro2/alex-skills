"""Grade the [code] expectations. Writes code_grades.json per run; [jev] ones are left for Jev."""
import json, os, re, subprocess, sys, pathlib
MERMAID_DIR = os.environ.get("MERMAID_DIR")  # dir with mermaid_parse.mjs and node_modules (see its header)
S = pathlib.Path(__file__).resolve().parent.parent / "evals"
EV = {e["name"]: e for e in json.load(open(S / "evals.json"))["evals"]}
def mermaid(t): return re.findall(r"```mermaid\n(.*?)```", t, re.S)
def words(t): return len(re.findall(r"\S+", re.sub(r"```.*?```", "", t, flags=re.S)))
def fixture_nums(case):
    txt = "".join(p.read_text() for p in (S / "files" / case).iterdir())
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*", txt)}
def unknown_nums(t, case):
    known = fixture_nums(case)
    found = {n.replace(",", "") for n in re.findall(r"(?<![\w.#,])\d[\d,]*(?:\.\d+)?", t)}
    return sorted(n for n in found if "." not in n and int(n) >= 11 and n not in known)
def heading(t, pat): return [l for l in t.splitlines() if l.startswith("#") and re.search(pat, l, re.I)]
def check(text, case, exp):
    global CUR
    m = mermaid(text)
    x = exp.lower()
    if "1 or 2 mermaid" in x: return 1 <= len(m) <= 2, f"{len(m)} mermaid blocks"
    if "at least 4 mermaid" in x: return len(m) >= 4, f"{len(m)} mermaid blocks"
    if "at least 1 mermaid" in x: return len(m) >= 1, f"{len(m)} mermaid blocks"
    if "no mermaid" in x: return len(m) == 0, f"{len(m)} mermaid blocks"
    if "'6 passed'" in x: return "6 passed" in text, "found" if "6 passed" in text else "missing"
    if "no review-path" in x:
        h = heading(text, r"review path|behaviou?r change"); return not h, f"headings: {h}"
    if "at most" in x and "words" in x:
        lim = int(re.search(r"at most (\d+)", x).group(1)); w = words(text); return w <= lim, f"{w} words outside code blocks"
    if "every number" in x:
        u = unknown_nums(text, case); return not u, f"numbers not in fixtures: {u}"
    if "sequencediagram with an alt" in x:
        ok = any(b.lstrip().startswith("sequenceDiagram") and re.search(r"^\s*alt\b", b, re.M) for b in m); return ok, f"{ok}"
    if "subgraph" in x: ok = any("subgraph" in b for b in m); return ok, f"{ok}"
    if "commit hashes" in x:
        hs = ["a1c3e5f","b2d4f60","c3e5a71","d4f6b82","e5a7c93","f6b8da4"]; n = sum(h in text for h in hs); return n >= 5, f"{n}/6 hashes"
    if "412 passed and 359" in x: ok = "412 passed" in text and "359 passed" in text; return ok, f"{ok}"
    if "1312 and 418" in x: ok = bool(re.search(r"1,?312", text)) and "418" in text; return ok, f"{ok}"
    if "6120" in x: ok = bool(re.search(r"6,?120", text)); return ok, f"{ok}"
    if "pgbouncer" in x: ok = "pgbouncer" in text.lower(); return ok, f"{ok}"
    if "clock skew" in x: ok = "clock skew" in text.lower(); return ok, f"{ok}"
    if "2.4.1" in x: return "2.4.1" in text, ""
    if "#318" in x: return "#318" in text, ""
    if "'n passed'" in x:
        h = re.findall(r"\d+\s+(?:tests?\s+)?passed", text); return not h, f"pass counts found: {h}"
    if "table that mentions 404" in x:
        rows = [l for l in text.splitlines() if l.strip().startswith("|") and "404" in l]; return bool(rows), f"{len(rows)} table rows with 404"
    if "mermaid block parses" in x:
        if not MERMAID_DIR: return False, "not checked: set MERMAID_DIR"
        out = subprocess.run(["node", "mermaid_parse.mjs", CUR], cwd=MERMAID_DIR, capture_output=True, text=True).stdout
        r = re.search(r"(\d+)/(\d+) parse(.*)", out); zw = "\u200b```" in text
        return r.group(1) == r.group(2) and not zw, r.group(0)[:200] + (" | U+200B before a fence" if zw else "")
    raise ValueError(exp)
for run in sorted(pathlib.Path(sys.argv[1]).glob("eval-*/*/run-*/outputs/pr_body.md")):
    case = run.parts[-5].split("-", 2)[2]; text = run.read_text(); out = []
    CUR = str(run.resolve())
    for i, e in enumerate(EV[case]["expectations"], 1):
        if e.startswith("[code]"):
            ok, ev = check(text, case, e); out.append({"id": f"e{i}", "text": e, "passed": bool(ok), "evidence": "code: " + ev})
    json.dump(out, open(run.parent.parent / "code_grades.json", "w"), indent=2)
    print(run.parts[-5], run.parts[-4], f"{sum(o['passed'] for o in out)}/{len(out)}", [o["id"] + ":" + o["evidence"] for o in out if not o["passed"]])
