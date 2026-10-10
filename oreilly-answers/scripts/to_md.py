"""Turn ask.js results into Markdown.

  to_md.py RAW_DIR                 print one Markdown document for every q*.json in RAW_DIR
  to_md.py --check FILE QUESTION   print one status line; non-zero exit if the run failed
"""
import json, re, sys
from pathlib import Path


MARK = "Was this response helpful?"


def load(p):
    d = json.loads(Path(p).read_text())
    v = d.get("value") or {}
    if v:
        # Older captures used {t, h} links and had no "complete" flag; normalise both.
        v["links"] = [{"title": l.get("title", l.get("t", "")), "href": l.get("href", l.get("h", ""))} for l in v.get("links", [])]
        v.setdefault("complete", MARK in v.get("text", ""))
    return v, d


def answer_body(text, q):
    # The page repeats the question in curly quotes; the answer runs from there to the feedback prompt.
    start = text.find("”", text.find("“")) + 1
    end = text.find(MARK)
    body = text[start:end if end > 0 else len(text)]
    # Answers renders each paragraph twice: once with "Citation N" runs, once clean. Keep the clean one.
    keep = [l.rstrip() for l in body.splitlines() if l.strip() and "Citation" not in l]
    return "\n\n".join(keep).strip()


def sources(links):
    seen, out = set(), []
    for l in links:
        key = l["href"].split("#")[0]
        if not key or key in seen or not l["title"]:
            continue
        seen.add(key)
        out.append(f"- [{l['title']}]({key})")
    return "\n".join(out)


def check(p, q):
    v, d = load(p)
    ok = d.get("ok") and v.get("q", "").strip() == q.strip() and v.get("complete")
    print(f"{Path(p).name}: {'ok' if ok else 'FAILED'} | asked={v.get('q','')[:60]!r} | complete={v.get('complete')} | {len(v.get('text',''))} chars")
    sys.exit(0 if ok else 1)


def render(raw_dir):
    files = sorted(Path(raw_dir).glob("q*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    print("# O'Reilly Answers\n\nAI answers over the O'Reilly library. Treat each as a lead: check any load-bearing claim against the cited book.\n")
    for p in files:
        v, _ = load(p)
        if not v:
            print(f"## {p.stem}: run failed\n")
            continue
        print(f"## Q: {v['q']}\n\n*Answers URL: {v['url']}*{'' if v.get('complete') else '  **(incomplete capture)**'}\n")
        print(answer_body(v["text"], v["q"]) + "\n")
        s = sources(v.get("links", []))
        if s:
            print("**Sources**\n\n" + s + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        check(sys.argv[2], sys.argv[3])
    else:
        render(sys.argv[1])
