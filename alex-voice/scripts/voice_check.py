#!/usr/bin/env python3
"""Score a draft against Alex's measured voice fingerprint.

usage: voice_check.py FILE --register {blog,docs,comms,exec,chat,spoken}
Exit 1 when a blocker is found (em dash or a banned phrase), else 0.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BANNED = [
    (r"—", "em dash"),
    (r"here'?s the (thing|deal)", "here's the thing/deal"),
    (r"\bbut here'?s\b", "but here's..."),
    (r"\bthe truth is\b", "the truth is"),
    (r"\blet me be direct\b", "let me be direct"),
    (r"\bfull disclosure\b", "full disclosure"),
    (r"\bi'?ll be honest\b", "I'll be honest"),
    (r"\bspoiler alert\b", "spoiler alert"),
    (r"\blet'?s (dive|unpack|explore)\b", "let's dive/unpack/explore"),
    (r"\bdive deep\b", "dive deep"),
    (r"\bdelv(e|ing)\b", "delve"),
    (r"\bleverag(e|es|ing)\b", "leverage"),
    (r"\butiliz(e|es|ing)\b", "utilize"),
    (r"\brobust\b", "robust"),
    (r"\bcomprehensive\b", "comprehensive"),
    (r"\bseamless(ly)?\b", "seamless"),
    (r"\bstreamlin(e|ed|ing)\b", "streamline"),
    (r"\bgame.?changer\b", "game-changer"),
    (r"\bparadigm\b", "paradigm"),
    (r"\bnavigat(e|ing) the\b", "navigate the..."),
    (r"\bit'?s (important|worth) (to note|noting)\b", "it's important to note"),
    (r"\bin today'?s\b", "in today's..."),
    (r"\bever.evolving\b", "ever-evolving"),
    (r"\b(elevate|empower|foster)(s|ed|ing)?\b", "elevate/empower/foster"),
    (r"\blitmus\b", "litmus"),
    (r"\bthis is where\b", "this is where..."),
    (r"\bquick q\b|\bwtv\b|\bplx\b|\bimho\b|\bgimme\b|\btho\b", "abbreviated word (quick q, wtv, plx, imho, gimme, tho)"),
]

# per 10k words unless noted; (low, high) targets measured from Alex's own writing
TARGETS = {
    "blog":   {"avg_sent": (14, 21), "p90_sent": (28, 42), "q": (30, 80), "bang": (15, 70), "paren": (60, 220), "the_start_pct": (0, 10), "one_line_para_pct": (0, 35), "lower_start_pct": (0, 2)},
    "docs":   {"avg_sent": (12, 20), "p90_sent": (24, 36), "q": (5, 40), "bang": (0, 20), "paren": (20, 150), "the_start_pct": (0, 12), "one_line_para_pct": (0, 60), "lower_start_pct": (0, 2)},
    "comms":  {"avg_sent": (12, 24), "p90_sent": (22, 46), "q": (10, 80), "bang": (40, 200), "paren": (0, 120), "the_start_pct": (0, 10), "one_line_para_pct": (0, 80), "lower_start_pct": (0, 2)},
    "exec":   {"avg_sent": (12, 20), "p90_sent": (22, 34), "q": (0, 30), "bang": (0, 10), "paren": (0, 80), "the_start_pct": (0, 15), "one_line_para_pct": (0, 60), "lower_start_pct": (0, 1)},
    "chat":   {"avg_sent": (4, 30), "p90_sent": (8, 55), "q": (80, 260), "bang": (60, 350), "paren": (0, 60), "the_start_pct": (0, 5), "one_line_para_pct": (40, 100), "lower_start_pct": (30, 100)},
    "spoken": {"avg_sent": (10, 20), "p90_sent": (20, 34), "q": (80, 220), "bang": (0, 40), "paren": (0, 20), "the_start_pct": (0, 5), "one_line_para_pct": (0, 100), "lower_start_pct": (0, 5)},
}


def strip_markup(text: str) -> str:
    text = re.sub(r"\A---.*?\n---\s*", "", text, flags=re.S)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"^\s*(#+|[-*]|\d+\.|>)\s*", "", text, flags=re.M)
    return text


def sentences(text: str) -> list[str]:
    flat = re.sub(r"[ \t]+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", flat)
    return [p.strip() for p in parts if len(p.strip().split()) >= 2]


def analyze(raw: str) -> dict:
    text = strip_markup(raw)
    words = re.findall(r"[A-Za-z'’]+", text)
    n = max(len(words), 1)
    sents = sentences(text)
    lens = sorted(len(s.split()) for s in sents) or [0]
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    one_line = sum(1 for p in paras if len(sentences(p)) <= 1)
    per10k = lambda pat: round(10000 * len(re.findall(pat, text, flags=re.I)) / n, 1)
    return {
        "words": len(words),
        "sentences": len(sents),
        "avg_sent": round(sum(lens) / len(lens), 1),
        "p90_sent": lens[int(len(lens) * 0.9)] if sents else 0,
        "q": per10k(r"\?"),
        "bang": per10k(r"!"),
        "paren": per10k(r"\("),
        "emdash": per10k(r"—"),
        "tag_q": per10k(r"\b(right|no|correct)\?|make(s)? sense\?"),
        "opinion": per10k(r"\b(i think|to me,|in my (honest |personal )?opinion|i do think)\b"),
        "the_start_pct": round(100 * sum(1 for s in sents if s.split()[0].lower() == "the") / max(len(sents), 1), 1),
        "lower_start_pct": round(100 * sum(1 for s in sents if s[0].islower()) / max(len(sents), 1), 1),
        "one_line_para_pct": round(100 * one_line / max(len(paras), 1), 1),
        "banned": [(label, len(re.findall(pat, text, flags=re.I))) for pat, label in BANNED if re.search(pat, text, flags=re.I)],
    }


def report(stats: dict, register: str) -> tuple[list[str], list[str]]:
    blockers = [f"{label} x{count}" for label, count in stats["banned"]]
    warnings = []
    for key, (low, high) in TARGETS[register].items():
        value = stats[key]
        if value < low:
            warnings.append(f"{key}={value} is LOW for {register} (target {low}-{high})")
        elif value > high:
            warnings.append(f"{key}={value} is HIGH for {register} (target {low}-{high})")
    return blockers, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--register", choices=sorted(TARGETS), default="blog")
    args = parser.parse_args(argv)

    stats = analyze(args.file.read_text(encoding="utf-8", errors="replace"))
    blockers, warnings = report(stats, args.register)

    print(f"voice_check {args.file.name} [{args.register}] words={stats['words']} sentences={stats['sentences']}")
    print(f"  avg_sent={stats['avg_sent']} p90_sent={stats['p90_sent']} ?/10k={stats['q']} !/10k={stats['bang']} (/10k={stats['paren']} emdash/10k={stats['emdash']}")
    print(f"  tag_q/10k={stats['tag_q']} opinion/10k={stats['opinion']} the_start%={stats['the_start_pct']} lower_start%={stats['lower_start_pct']} one_line_para%={stats['one_line_para_pct']}")
    if stats["words"] < 300:
        print("  note: under 300 words, rate warnings are unreliable; blockers still count")
    for item in blockers:
        print(f"  BLOCKER: {item}")
    for item in warnings:
        print(f"  warn: {item}")
    if not blockers and not warnings:
        print("  PASS: inside Alex's measured range")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
