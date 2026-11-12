"""Grade the [code] expectations. Writes code_grades.json per run; [jev] ones are left for grade_jev.py.

A hand verdict goes in <iteration>/overrides.json:
  {"<case>/<config>/run-<k>": {"e3": {"passed": true, "reason": "..."}}}
and replaces the code verdict, with the reason in the evidence.
"""
import json, re, sys, pathlib

S = pathlib.Path(__file__).resolve().parent.parent / "evals"
EV = {e["name"]: e for e in json.load(open(S / "evals.json"))["evals"]}
FILES = S / "files"
NEG = re.compile(r"\b(not|never|no|without|instead|rather|avoid|cannot|can't|isn't|doesn't|don't|won't|would fail|reject|invalid)\b|n't", re.I)


def norm(t): return t.replace("\\n", "\n")
def flat(t): return re.sub(r"\s+", " ", re.sub(r"[*`]", "", t)).strip()
def positive_lines(t, pat):
    """Lines that match pat and carry no negation word."""
    return [l.strip() for l in norm(t).splitlines() if re.search(pat, l, re.I) and not NEG.search(l)]


def title_ok(t):
    ms = re.findall(r"\[[A-Z][A-Z0-9-]+\] [^\n\"`]*", norm(t))
    ms = [m.strip().rstrip("*\\,") for m in ms if re.match(r"\[[A-Z][A-Z0-9-]+\] \S", m)]
    if not ms: return False, "no title matching the pattern"
    return len(ms[0]) <= 80, f"{len(ms[0])} chars: {ms[0]!r}"


def six_sections(t):
    kws = {"Intent": "intent", "Constraints": "constraints", "Technical Interface": r"technical|interface",
           "Logic": "logic", "Validation": "validation", "Resources": "resources"}
    miss = [k for k, p in kws.items() if not re.search(rf"(?im)^\s*#{{2,6}}\s+.*({p})", norm(t))]
    return not miss, f"missing: {miss}" if miss else "6/6 headings"


def gwt(t):
    n = norm(t)
    at_start = all(re.search(rf"(?m)^[\s>*\-\d.]*\**{w}\b", n) for w in ("Given", "When", "Then"))
    one_line = re.search(r"Given\b.*\bWhen\b.*\bThen\b", n)
    return bool(at_start or one_line), "line-start" if at_start else ("one line" if one_line else "missing")


def call_order(t):
    pos = {k: t.find(k) for k in ("getAccessibleAtlassianResources", "searchJiraIssuesUsingJql", "createJiraIssue")}
    ok = all(v >= 0 for v in pos.values()) and pos["getAccessibleAtlassianResources"] < pos["searchJiraIssuesUsingJql"] < pos["createJiraIssue"]
    return ok, f"first positions {pos}"


def mirrors(t):
    for m in re.finditer("customfield_10234", t):
        w = t[m.end(): m.end() + 300]
        if re.search(r"Given|AC-0\d|acceptance criteria", w, re.I): return True, "AC text or AC reference within 300 chars after: " + flat(t[m.start(): m.start() + 110])
    return False, "customfield_10234 " + ("present with no AC text or reference after it" if "customfield_10234" in t else "absent")


def content_markdown(t):
    m = re.search(r"contentFormat\W{0,6}markdown", t, re.I)
    return bool(m), m.group(0) if m else "no contentFormat markdown"


def keeps(case_file, pat_list):
    desc = json.load(open(FILES / "update-merge" / "current-issue.json"))["fields"]["description"]
    lines = [flat(l.lstrip("- ")) for l in desc.splitlines() if any(re.search(p, l) for p in pat_list)]
    return lines


def keeps_ac(t):
    lines = keeps("", [r"^- AC-00\d"])
    out = flat(norm(t)); miss = [l for l in lines if l not in out]
    return not miss, f"{len(lines) - len(miss)}/{len(lines)} AC lines verbatim" + (f"; missing {[m[:40] for m in miss]}" if miss else "")


def keeps_donot(t):
    lines = keeps("", [r"DO NOT"])
    out = flat(norm(t)); miss = [l for l in lines if l not in out]
    return not miss, f"{len(lines) - len(miss)}/{len(lines)} DO NOT lines verbatim"


def edit_not_create(t):
    edit = "editJiraIssue" in t
    creates = positive_lines(t, "createJiraIssue")
    return edit and not creates, f"editJiraIssue present={edit}; non-negated createJiraIssue lines={creates[:3]}"


def no_spike_create(t):
    hits = positive_lines(t, r"issueTypeName\W{0,6}spike")
    return not hits, f"issueTypeName Spike lines={hits[:3]}"


def names_check(t):
    f = [n for n in ("getJiraIssueRemoteIssueLinks", "getTeamworkGraphContext") if n in t]
    return bool(f), f"named: {f}"


def no_remote_write(t):
    hits = positive_lines(t, r"remotelink|createremote")
    return not hits, f"non-negated lines={hits[:3]}"


CHECKS = {
    "Title matches": title_ok, "Body has the six sections": six_sections, "Body has Given, When and Then": gwt,
    "Calls list": call_order, "Mirrors the ACs": mirrors, "Uses `contentFormat`": content_markdown,
    "Keeps both existing AC lines": keeps_ac, "Keeps the existing `DO NOT:`": keeps_donot,
    "Proposes `editJiraIssue`": edit_not_create, "Proposes no `createJiraIssue`": no_spike_create,
    "Names `getJiraIssueRemoteIssueLinks`": names_check, "Does not name a remote-link write call": no_remote_write,
}


def check(text, exp):
    body = exp[len("[code] "):]
    for k, fn in CHECKS.items():
        if body.startswith(k): return fn(text)
    raise ValueError(exp)


if __name__ == "__main__":
    it = pathlib.Path(sys.argv[1])
    ov = json.load(open(it / "overrides.json")) if (it / "overrides.json").exists() else {}
    for run in sorted(it.glob("eval-*/*/run-*/outputs/answer.md")):
        case = run.parts[-5].split("-", 2)[2]; key = f"{case}/{run.parts[-4]}/{run.parts[-3]}"
        text = run.read_text(); out = []
        for i, e in enumerate(EV[case]["expectations"], 1):
            if not e.startswith("[code]"): continue
            ok, ev = check(text, e); ev = "code: " + ev
            o = ov.get(key, {}).get(f"e{i}")
            if o: ok, ev = o["passed"], f"{ev} | override: {o['reason']}"
            out.append({"id": f"e{i}", "text": e, "passed": bool(ok), "evidence": ev})
        json.dump(out, open(run.parent.parent / "code_grades.json", "w"), indent=2)
        print(key, f"{sum(o['passed'] for o in out)}/{len(out)}", [o["id"] + ":" + o["evidence"][:140] for o in out if not o["passed"]])
