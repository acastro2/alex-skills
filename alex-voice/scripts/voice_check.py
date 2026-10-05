#!/usr/bin/env python3
"""Score a draft against Alex's measured voice fingerprint.

usage: voice_check.py FILE --register {blog,docs,comms,exec,chat,spoken}
Exit 1 only when a blocker is found (em dash, banned phrase, stock closer,
shorthand, lowercase standalone i). Everything else is a warning.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Alex works async and never offers a call or meeting. "I was on a call" is fine.
CALL_OFFER = (
    r"\b(jump|hop|get) on a (quick )?call\b|\b(book|schedule|set up|grab) (a|some|those) (quick )?(calls?|meetings?)\b"
    r"|\bschedule some time\b|\blet['’]?s sync\b|\b(talk|chat|speak|discuss)( about)?( it| this| that)? (on|over) a (quick )?call\b"
)

BANNED = [
    (r"—", "em dash"),
    (r"here['’]?s the (thing|deal)", "here's the thing/deal"),
    (r"\bbut here['’]?s\b", "but here's..."),
    (r"\bthe truth is\b", "the truth is"),
    (r"\blet me be direct\b", "let me be direct"),
    (r"\bfull disclosure\b", "full disclosure"),
    (r"\bi['’]?ll be honest\b", "I'll be honest"),
    (r"\bspoiler alert\b", "spoiler alert"),
    (r"\blet['’]?s (dive|unpack|explore)\b", "let's dive/unpack/explore"),
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
    (r"\bit['’]?s (important|worth) (to note|noting)\b", "it's important to note"),
    (r"\bin today['’]?s\b", "in today's..."),
    (r"\bever.evolving\b", "ever-evolving"),
    (r"\b(elevate|empower|foster)(s|ed|ing)?\b", "elevate/empower/foster"),
    (r"\blitmus\b", "litmus"),
    (r"\bcutting.edge\b", "cutting-edge"),
    (r"\bhere['’]?s what\b", "here's what..."),
    (r"\bthis is where\b", "this is where..."),
    (r"\banything else\b", "stock closer: anything else"),
    (r"\bhappy to help\b", "stock closer: happy to help"),
    (r"\bhope this helps\b", "stock closer: hope this helps"),
    (r"\bfeel free to reach out\b", "stock closer: feel free to reach out"),
    (CALL_OFFER, "call offer (Alex works async, never offer a call or meeting)"),
    (r"(?<![\w-])(quick q|wtv|plx|imho|imo|gimme|tho|ty|np|idk)(?![\w-])", "abbreviated word (quick q, wtv, plx, imho, imo, gimme, tho, ty, np, idk)"),
]


# Warnings: (pattern, label, registers where it does not apply)
WARN_PHRASES = [
    (r"\b(i|we)['’]ll\b|\b(you|we)['’]re\b|\bi['’]ve\b", "contraction Alex rarely types (I'll, we'll, you're, we're, I've)", ()),
    (r"\blets\b(?! (you|me|us|him|her|them|it|the|a|users|people|teams)\b)|\bwhats\b|\bits (a|not|the|ok|fine|just|been|going)\b", "typing slip (lets, whats, its for it is): Alex does not imitate typos", ()),
    (r"\bok so\b", "machine habit: 'ok so'", ()),
    (r"\bhelp me\b", "machine habit: 'help me'", ()),
    (r"\bi want you to\b", "machine habit: 'I want you to'", ()),
    (r"\bexplain to me\b", "machine habit: 'explain to me'", ()),
    # comms has its own tag-question rule; spoken scores tag questions as a rate
    (r"(?<!\bor )\bno\?", "machine habit: tag question 'no?'", ("comms", "spoken")),
]
# Habits from the old skill. Fine in a blog, wrong everywhere else.
OLD_SKILL_PHRASES = {
    "my bad": r"\bmy bad\b",
    "was my miss": r"\bwas my miss\b",
    "I promise": r"\bi promise\b",
    "cool, but": r"\bcool, but\b",
    "trust me": r"\btrust me\b",
    "don't get me wrong": r"\bdon['’]t get me wrong\b",
    "let me diagram that": r"\blet me diagram that\b",
    "etc!": r"\betc!",
    "one quick tip": r"\bone quick tip\b",
}
WARN_PHRASES += [(pat, f"old-skill phrase: '{name}'", ("blog",)) for name, pat in OLD_SKILL_PHRASES.items()]

# Case matters here: a lowercase "i" is a blocker, "I" is fine. Skips i.e., i-th, and words with i inside.
# A lone quoted 'i' (a character, not the pronoun) is ignored; 'i will go' and i'm are caught.
BANNED_CASE_SENSITIVE = [(r"(?<![\w./-])i(?!\w|\.\w|-\w|/\w|['’](?!\w))", "lowercase standalone i")]

# Banned patterns that do not apply in some registers (label: registers). "Anything else?"
# closes 9 of 24 of Alex's meetings, so it is a real spoken habit and a written AI tell.
BANNED_SKIP = {"stock closer: anything else": ("spoken",)}

MIN_WORDS_FOR_RATES = 100

# per 10k words unless noted; (low, high) targets measured from Alex's own writing
TARGETS = {
    "blog":   {"avg_sent": (14, 21), "p90_sent": (28, 42), "q": (30, 80), "bang": (15, 70), "paren": (60, 220), "the_start_pct": (0, 10), "one_line_para_pct": (0, 35), "lower_start_pct": (0, 2)},
    # docs and exec bands: provisional, fitted 2026-10-05 on the 10 drafts Alex picked as "would sign" (6 docs, 4 exec)
    "docs":   {"avg_sent": (8, 20), "p90_sent": (14, 36), "q": (0, 90), "bang": (0, 20), "paren": (20, 150), "the_start_pct": (0, 12), "one_line_para_pct": (0, 60), "lower_start_pct": (0, 10)},
    "comms":  {"avg_sent": (8, 18), "p90_sent": (14, 50), "bang": (0, 250), "paren": (0, 60), "the_start_pct": (0, 10), "lower_start_pct": (0, 2)},
    "exec":   {"avg_sent": (6, 20), "p90_sent": (14, 34), "q": (0, 30), "bang": (0, 10), "paren": (0, 80), "the_start_pct": (0, 15), "one_line_para_pct": (0, 60), "lower_start_pct": (0, 1)},
    "chat":   {},  # judged by line and count checks, not rates (rates fail on real bursts)
    # 100-299 words; punctuation is speech-to-text output, so it is not scored
    "spoken": {"avg_sent": (9, 24), "p90_sent": (18, 50), "the_start_pct": (0, 12), "tag_q": (0, 150)},
}

SPOKEN_LONG = {"avg_sent": (10, 18), "p90_sent": (18, 40), "the_start_pct": (0, 8), "tag_q": (15, 115), "opinion": (10, 80)}
SPOKEN_LONG_MIN_WORDS = 300


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


SKIPPED_IN = {label: skip for _, label, skip in WARN_PHRASES}


def hits(patterns: list[tuple[str, str]], text: str, flags: int) -> list[tuple[str, int]]:
    found = [(label, len(re.findall(pat, text, flags=flags))) for pat, label in patterns]
    return [(label, count) for label, count in found if count]


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
        "tag_q": per10k(r"\b(right|(?<!\bor )no|correct)\?|make(s)? sense\?"),
        "opinion": per10k(r"\b(i think|to me,|in my (honest |personal )?opinion|i do think)\b"),
        "the_start_pct": round(100 * sum(1 for s in sents if s.split()[0].lower() == "the") / max(len(sents), 1), 1),
        "lower_start_pct": round(100 * sum(1 for s in sents if s[0].islower()) / max(len(sents), 1), 1),
        "one_line_para_pct": round(100 * one_line / max(len(paras), 1), 1),
        "text": text,
        "lines": [line.strip() for line in text.splitlines() if line.strip()],
        "phrases": dict(hits([(pat, label) for pat, label, _ in WARN_PHRASES], text, re.I)),
        "banned": hits(BANNED, text, re.I) + hits(BANNED_CASE_SENSITIVE, text, 0),
    }


# Max count per draft; chat is judged by counts, not rates.
CHAT_CAPS = {"?": 3, "!": 2, "(": 2}


# Chat habits that are real but should not stack in one draft.
CHAT_MARKERS = [
    r"\b(right|(?<!\bor )no|correct)\?|\bmake(s)? sense\?",
    r"\bok so\b",
    r"\bsweet\b",
    r"\bamazing\b",
    r"\bwohoo\b",
    r"\b[a-z]*([a-z])\1{2,}[a-z]*\b",
    r"\b(shit|damn|wtf|sucks|crap)\b",
]


def chat_line_warnings(lines: list[str]) -> list[str]:
    warnings = []
    joined = "\n".join(lines)
    for mark, cap in CHAT_CAPS.items():
        if joined.count(mark) > cap:
            warnings.append(f"chat has {joined.count(mark)} '{mark}' (cap {cap})")
    markers = sum(len(re.findall(pat, joined, flags=re.I)) for pat in CHAT_MARKERS)
    if markers >= 2:
        warnings.append(f"chat has {markers} signature markers (budget 1)")
    for line in lines:
        count = len(line.split())
        if count > 30:
            warnings.append(f"chat line has {count} words: this is a channel post, use comms")
        elif count >= 3 and line.endswith(".") and not line.endswith(".."):
            warnings.append(f"chat line ends with a period: {line[:40]!r}")
    return warnings


def comms_warnings(text: str) -> list[str]:
    warnings = []
    questions = text.count("?")
    if questions > 1:
        warnings.append(f"comms has {questions} '?' (keep one at most)")
    tags = len(re.findall(r"\b(right|(?<!\bor )no)\?|\bmakes? sense\?", text, flags=re.I))
    if tags:
        warnings.append(f"tag question x{tags} (right? / make sense? / no?): state it instead")
    thinks = len(re.findall(r"\bi think\b", text, flags=re.I))
    if thinks >= 2:
        warnings.append(f"'I think' x{thinks}: say it plainly")
    return warnings


# Drafts ran 30% to 60% longer than Alex's real messages in the 2026-10 lineups, so length warns.
MAX_DRAFT_WORDS = {"chat": (40, "longer than about 94% of his chat replies"),
                   "comms": (60, "longer than 91% of his emails; fine only for a new thread, pushback, or handover")}
MAX_BLOG_PARAGRAPH_WORDS = 120


def length_warnings(stats: dict, register: str) -> list[str]:
    if register in MAX_DRAFT_WORDS:
        limit, why = MAX_DRAFT_WORDS[register]
        if stats["words"] > limit:
            return [f"draft is {stats['words']} words, {why}"]
    if register == "blog":
        long_paras = [len(p.split()) for p in re.split(r"\n\s*\n", stats["text"]) if len(p.split()) > MAX_BLOG_PARAGRAPH_WORDS]
        return [f"paragraph is {n} words; his paragraphs run about 60" for n in long_paras]
    return []


def report(stats: dict, register: str) -> tuple[list[str], list[str]]:
    blockers = [f"{label} x{count}" for label, count in stats["banned"] if register not in BANNED_SKIP.get(label, ())]
    warnings = [f"{label} x{count}" for label, count in stats["phrases"].items() if register not in SKIPPED_IN[label]]
    if register == "chat":
        warnings += chat_line_warnings(stats["lines"])
    if register == "comms":
        warnings += comms_warnings(stats["text"])
    warnings += length_warnings(stats, register)
    if stats["words"] < MIN_WORDS_FOR_RATES:
        return blockers, warnings
    bands = SPOKEN_LONG if register == "spoken" and stats["words"] >= SPOKEN_LONG_MIN_WORDS else TARGETS[register]
    for key, (low, high) in bands.items():
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
    if stats["words"] < MIN_WORDS_FOR_RATES:
        print("  short-form: rates not scored")
    if args.register == "spoken":
        print("  punctuation from speech-to-text, not calibrated")
    for item in blockers:
        print(f"  BLOCKER: {item}")
    for item in warnings:
        print(f"  warn: {item}")
    if not blockers and not warnings:
        print("  PASS: inside Alex's measured range")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
