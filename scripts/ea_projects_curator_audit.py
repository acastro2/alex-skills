#!/usr/bin/env python3
"""Audit the ea-projects-curator skill package and print one violation count.

WHY THIS EXISTS
---------------
`/autoresearch_goal` improves ea-projects-curator against a mechanical metric. This is
that metric: a deterministic case runner over the skill's prose (SKILL.md and the three
references, which are the loop's scope) plus its one script (references/render_page.py,
read-only). It prints a single integer: the number of violations found. Zero is the
target.

    python3 scripts/ea_projects_curator_audit.py                  # prints the count
    python3 scripts/ea_projects_curator_audit.py --report OUT.md  # count + details
    python3 scripts/ea_projects_curator_audit.py --list           # case ids

DESIGN RULES (keep the metric honest)
-------------------------------------
- Every violation must be fixable by editing the four prose files. render_page.py,
  curated.json, example-content.json, the tests and this script are read-only.
- No network. The only write is the optional report file.
- A case fires only on evidence it names (file + line + reason). No vibes.
- A case that would need renderer edits to fix does not belong here; it belongs in
  the canary guard (ea-projects-curator/tests/test_invariants.py).
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO / "ea-projects-curator"
PROSE_FILES = {
    "SKILL.md": SKILL_DIR / "SKILL.md",
    "references/recap.md": SKILL_DIR / "references" / "recap.md",
    "references/brought-docs.md": SKILL_DIR / "references" / "brought-docs.md",
    "references/write-shapes.md": SKILL_DIR / "references" / "write-shapes.md",
}
RENDERER = SKILL_DIR / "references" / "render_page.py"


class V:
    """One violation: case id, file, 1-based line (or None), message."""

    __slots__ = ("case", "file", "line", "message")

    def __init__(self, case: str, file: str, line: int | None, message: str):
        self.case = case
        self.file = file
        self.line = line
        self.message = message

    def __str__(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        return f"{where} — {self.message}"


class Ctx:
    def __init__(self) -> None:
        self.texts: dict[str, str] = {}
        self.lines: dict[str, list[str]] = {}
        self.in_fence: dict[str, list[bool]] = {}
        for name, path in PROSE_FILES.items():
            text = path.read_text(encoding="utf-8")
            self.texts[name] = text
            self.lines[name] = text.splitlines()
            flags: list[bool] = []
            fenced = False
            for ln in self.lines[name]:
                if re.match(r"^\s*(```|~~~)", ln):
                    flags.append(True)
                    fenced = not fenced
                else:
                    flags.append(fenced)
            self.in_fence[name] = flags
        self.renderer = RENDERER.read_text(encoding="utf-8") if RENDERER.exists() else ""

    def prose_lines(self, name: str):
        """(lineno, line) outside fenced code blocks."""
        for i, ln in enumerate(self.lines[name]):
            if not self.in_fence[name][i]:
                yield i + 1, ln

    def block_for(self, name: str, lineno: int) -> str:
        """Blank-line-delimited block (fence-aware, but fences count as content)."""
        lines = self.lines[name]
        start = end = lineno - 1
        while start > 0 and lines[start - 1].strip():
            start -= 1
        while end + 1 < len(lines) and lines[end + 1].strip():
            end += 1
        return "\n".join(lines[start : end + 1])

    def inline_spans(self, name: str) -> list[tuple[int, str]]:
        """(start_line, content) for every inline-code span outside fences. A span left
        open at end of line continues on the next line, which is how the prose wraps
        `render_page.py` and `--check-only` across two lines."""
        spans: list[tuple[int, str]] = []
        buf: str | None = None
        start = 0
        for i, ln in enumerate(self.lines[name]):
            if self.in_fence[name][i]:
                continue
            for ch in ln:
                if ch == "`":
                    if buf is None:
                        buf, start = "", i + 1
                    else:
                        spans.append((start, buf))
                        buf = None
                elif buf is not None:
                    buf += ch
            if buf is not None:
                buf += "\n"
        return spans


def gh_slug(heading: str) -> str:
    h = heading.strip().lower()
    h = re.sub(r"[^\w\s-]", "", h)
    return re.sub(r"\s", "-", h)


def headings(text: str) -> list[str]:
    out = []
    fenced = False
    for ln in text.splitlines():
        if re.match(r"^\s*(```|~~~)", ln):
            fenced = not fenced
            continue
        m = re.match(r"^#{1,6}\s+(.*?)\s*$", ln)
        if m and not fenced:
            out.append(m.group(1))
    return out


ANCHOR_CACHE: dict[str, set[str]] = {}


def anchors_for(path: Path) -> set[str]:
    key = str(path)
    if key not in ANCHOR_CACHE:
        ANCHOR_CACHE[key] = {gh_slug(h) for h in headings(path.read_text(encoding="utf-8"))}
    return ANCHOR_CACHE[key]


# ---------------------------------------------------------------- cases


def case_frontmatter(ctx: Ctx) -> list[V]:
    out = []
    text = ctx.texts["SKILL.md"]
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return [V("frontmatter", "SKILL.md", 1, "no YAML frontmatter block")]
    try:
        import yaml  # type: ignore

        fm = yaml.safe_load(m.group(1))
    except Exception as err:  # noqa: BLE001
        return [V("frontmatter", "SKILL.md", 1, f"frontmatter does not parse: {err}")]
    if not isinstance(fm, dict):
        return [V("frontmatter", "SKILL.md", 1, "frontmatter is not a mapping")]
    if fm.get("name") != "ea-projects-curator":
        out.append(V("frontmatter", "SKILL.md", 2, f"name must be ea-projects-curator, got {fm.get('name')!r}"))
    if not str(fm.get("description", "")).strip():
        out.append(V("frontmatter", "SKILL.md", 3, "description is empty"))
    return out


def case_links(ctx: Ctx) -> list[V]:
    out = []
    for name in ctx.texts:
        base = PROSE_FILES[name].parent
        for lineno, ln in ctx.prose_lines(name):
            for m in re.finditer(r"\[([^\]]*)\]\(([^)\s]+)\)", ln):
                target = m.group(2)
                if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("//"):
                    continue
                path_part, _, frag = target.partition("#")
                if path_part:
                    resolved = (base / path_part).resolve()
                    if not resolved.exists():
                        out.append(V("links", name, lineno, f"link target does not exist: {target}"))
                        continue
                else:
                    resolved = PROSE_FILES[name].resolve()
                if frag and resolved.suffix == ".md":
                    if frag not in anchors_for(resolved):
                        out.append(V("links", name, lineno, f"anchor not found in {resolved.name}: #{frag}"))
    return out


PATH_SPAN = re.compile(r"^(?:\./|\.\./|[a-z0-9][\w.-]*/)[\w./%-]*\.(?:py|md|json|sh)$")


def case_repo_paths(ctx: Ctx) -> list[V]:
    """Backticked repo-relative paths must resolve to real files."""
    out = []
    for name in ctx.texts:
        base = PROSE_FILES[name].parent
        for lineno, ln in ctx.prose_lines(name):
            for m in re.finditer(r"`([^`]+)`", ln):
                span = m.group(1).strip()
                if any(ch in span for ch in "<>~$* "):
                    continue
                if not PATH_SPAN.match(span):
                    continue
                for candidate in (base / span, SKILL_DIR / span, REPO / span):
                    if candidate.exists():
                        break
                else:
                    out.append(V("repo-paths", name, lineno, f"backticked path does not resolve: {span}"))
    return out


def _flag_window(text: str, script: str) -> str:
    """Text after the script name, up to the next .py mention, so one command's flags
    are never checked against another script's name in the same line."""
    out = []
    pos = 0
    while True:
        at = text.find(script, pos)
        if at < 0:
            return " ".join(out)
        rest = text[at + len(script):]
        cut = rest.find(".py")
        window = rest[:cut] if cut >= 0 else rest
        out.append(window)
        pos = at + len(script)


def case_script_flags(ctx: Ctx) -> list[V]:
    """Flags shown next to render_page.py / voice_check.py must exist in those scripts."""
    out = []
    seen: set[tuple[str, int, str]] = set()

    render_flags = set(re.findall(r'"(--[\w-]+)"', ctx.renderer))
    voice_path = REPO / "alex-voice" / "scripts" / "voice_check.py"
    voice_src = voice_path.read_text(encoding="utf-8") if voice_path.exists() else ""
    registers = set(re.findall(r'"(\w+)":\s*\{', voice_src.split("TARGETS")[1])) if "TARGETS" in voice_src else set()

    def check(name: str, lineno: int, window: str) -> None:
        if "render_page.py" in window:
            for flag in re.findall(r"--[\w-]+", _flag_window(window, "render_page.py")):
                key = (name, lineno, flag)
                if flag not in render_flags and key not in seen:
                    seen.add(key)
                    out.append(V("script-flags", name, lineno, f"render_page.py flag not in the script: {flag}"))
        if "voice_check.py" in window:
            for m in re.finditer(r"--register\s+(\w+)", _flag_window(window, "voice_check.py")):
                key = (name, lineno, m.group(1))
                if registers and m.group(1) not in registers and key not in seen:
                    seen.add(key)
                    out.append(V("script-flags", name, lineno, f"voice_check.py register unknown: {m.group(1)}"))

    for name in ctx.texts:
        # command examples in fences and on their own line
        for i, ln in enumerate(ctx.lines[name]):
            check(name, i + 1, ln)
        # inline-code spans, including the ones that wrap across two lines
        for start_line, span in ctx.inline_spans(name):
            check(name, start_line, span)
    return out


def _parses(body: str) -> str | None:
    """None when the block parses. Fragments like `"docs": {...}` are legal in the docs
    (they live inside a larger object), so try the wrapped form too."""
    for candidate in (body, "{" + body + "}"):
        try:
            json.loads(candidate)
            return None
        except ValueError as err:
            last = err
    return str(last)


def case_json_blocks(ctx: Ctx) -> list[V]:
    out = []
    for name in ctx.texts:
        text = ctx.texts[name]
        for m in re.finditer(r"^[ \t]*```json[ \t]*\n(.*?)^[ \t]*```", text, re.S | re.M):
            body = m.group(1)
            lineno = text[: m.start()].count("\n") + 1
            err = _parses(body)
            if err:
                out.append(V("json-blocks", name, lineno, f"json block does not parse: {err}"))
    example = SKILL_DIR / "references" / "example-content.json"
    try:
        json.loads(example.read_text(encoding="utf-8"))
    except ValueError as err:
        out.append(V("json-blocks", "references/example-content.json", None, f"example content does not parse: {err}"))
    return out


SCHEMA_KEY_RE = re.compile(r"`([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)(?:\[\])?`")


def schema_vocabulary(ctx: Ctx) -> tuple[set[str], set[str]]:
    """(top-level required keys, every key name the renderer ever reads)."""
    m = re.search(r"def check_content\(.*?\n(?=# --- block builders)", ctx.renderer, re.S)
    body = m.group(0) if m else ""
    top = set(re.findall(r'need(?:_list)?\(\s*\w+,\s*"(\w+)"', body))
    vocab = set(top) | set(re.findall(r'\[\s*"(\w+)"\s*\]', ctx.renderer))
    return top, vocab


def case_schema_keys(ctx: Ctx) -> list[V]:
    """A dotted key that starts with a real schema key but names a field the renderer
    never reads is documentation drift (e.g. `exec_summary.footnote`). Tokens that do
    not start with a schema key at all (`page.goto`, `author.email`) are not our subject."""
    out = []
    top, vocab = schema_vocabulary(ctx)
    for name in ctx.texts:
        for lineno, ln in ctx.prose_lines(name):
            for m in SCHEMA_KEY_RE.finditer(ln):
                token = m.group(1)
                segs = token.split(".")
                if segs[0] not in top:
                    continue
                unknown = [s for s in segs[1:] if s not in vocab]
                if unknown:
                    out.append(V("schema-keys", name, lineno,
                                 f"key {token} names a field the renderer never reads: {unknown}"))
    return out


HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def case_palette(ctx: Ctx) -> list[V]:
    """Every colour the prose mentions must be a named palette constant."""
    out = []
    assigned = set()
    for m in re.finditer(r'=\s*("(#(?:[0-9A-Fa-f]{6}))")', ctx.renderer):
        assigned.add(m.group(2).lower())
    for m in re.finditer(r'"(#[0-9A-Fa-f]{6})"', ctx.renderer):
        assigned.add(m.group(1).lower())
    if not assigned:
        out.append(V("palette", "references/render_page.py", None, "no palette constants found; the parser went blind"))
    for name in ctx.texts:
        for lineno, ln in ctx.prose_lines(name):
            for m in HEX.finditer(ln):
                if m.group(0).lower() not in assigned:
                    out.append(V("palette", name, lineno, f"colour not in the render_page.py palette: {m.group(0)}"))
    return out


COUNT_WORDS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
COUNT_LINE = re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten)\b\s+\S+[^:]{0,60}:(\*\*)?\s*$", re.I)
ITEM_RE = re.compile(r"^\s*(?:[-*]\s|\d+\.\s)")


def case_counted_lists(ctx: Ctx) -> list[V]:
    """A 'Two <things>:' line must be followed by exactly two list items."""
    out = []
    for name in ctx.texts:
        lines = ctx.lines[name]
        for i, ln in enumerate(lines):
            if ctx.in_fence[name][i]:
                continue
            m = COUNT_LINE.search(ln)
            if not m:
                continue
            want = COUNT_WORDS[m.group(1).lower()]
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or not ITEM_RE.match(lines[j]):
                continue
            count = 0
            k = j
            while k < len(lines):
                if ITEM_RE.match(lines[k]):
                    count += 1
                elif lines[k].strip() and lines[k][:1] in (" ", "\t"):
                    pass  # wrapped continuation
                else:
                    break
                k += 1
            if count != want:
                out.append(V("counted-lists", name, i + 1,
                             f"line says '{m.group(1)}' but the list has {count} item(s)"))
    return out


def normalize_sentence(s: str) -> str:
    s = re.sub(r"[`*_\[\]]", "", s.lower())
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def case_duplicate_sentences(ctx: Ctx) -> list[V]:
    """Long sentences repeated across files are a single-source-of-truth defect."""
    out = []
    seen: dict[str, tuple[str, int, str]] = {}
    for name in ctx.texts:
        for lineno, ln in ctx.prose_lines(name):
            for raw in re.split(r"(?<=[.!?])\s+", ln):
                norm = normalize_sentence(raw)
                if len(norm) < 70:
                    continue
                if norm in seen:
                    other_file, other_line, other_raw = seen[norm]
                    if other_file != name:
                        out.append(V("duplicate-sentences", name, lineno,
                                     f"same sentence as {other_file}:{other_line}: {other_raw[:80]}..."))
                else:
                    seen[norm] = (name, lineno, raw)
    return out


STALE_NAMES = [
    ("ImpactUSD", "column renamed to `Impact` (see the Columns table)"),
]

STALE_PHRASES = [
    (re.compile(r"\bboth views\b"), "the package defines four named views (set 2026-09-03); name the views"),
    (re.compile(r'"Impact":\s*"\s*\$'), "Impact example leads with money; outcome comes first, metric in parens"),
]


def case_stale_text(ctx: Ctx) -> list[V]:
    out = []
    for name in ctx.texts:
        for lineno, ln in ctx.prose_lines(name):
            for token, why in STALE_NAMES:
                if token in ln:
                    out.append(V("stale-text", name, lineno, f"stale name `{token}`: {why}"))
            for rx, why in STALE_PHRASES:
                if rx.search(ln):
                    out.append(V("stale-text", name, lineno, f"stale phrasing: {why}"))
    return out


def case_tool_paths(ctx: Ctx) -> list[V]:
    """A skill shared by Claude Code, Pi and OpenCode cannot hardcode one tool's tree."""
    out = []
    for name in ctx.texts:
        for lineno, ln in ctx.prose_lines(name):
            if "~/.claude/" not in ln:
                continue
            block = ctx.block_for(name, lineno)
            if "~/.config/opencode" in block or "~/.pi" in block:
                continue
            out.append(V("tool-paths", name, lineno,
                         "Claude-only path in a shared skill; name the tool's tree or all trees"))
    return out


WEAK = re.compile(r"\b(should probably|if possible|try to|maybe|perhaps|ideally|as appropriate|where possible|if convenient)\b", re.I)
NEGATED = re.compile(r"(?:not|never|don't|do not|n't)\s+\w*\s*$", re.I)


def case_weak_modals(ctx: Ctx) -> list[V]:
    out = []
    for name in ctx.texts:
        for lineno, ln in ctx.prose_lines(name):
            for m in WEAK.finditer(ln):
                before = ln[: m.start()]
                if NEGATED.search(before) or re.search(r"\b(don't|do not|never)\b[^.]{0,15}$", before):
                    continue
                out.append(V("weak-modals", name, lineno, f"weak modal in an instruction: {m.group(0)!r}"))
    return out


def case_tables(ctx: Ctx) -> list[V]:
    out = []
    for name in ctx.texts:
        lines = ctx.lines[name]
        i = 0
        while i < len(lines):
            if ctx.in_fence[name][i] or not lines[i].lstrip().startswith("|"):
                i += 1
                continue
            block = []
            j = i
            while j < len(lines) and not ctx.in_fence[name][j] and "|" in lines[j] and lines[j].strip():
                block.append(j)
                j += 1
            if len(block) >= 3:
                widths = {lines[k].count("|") for k in block}
                if len(widths) > 1:
                    out.append(V("tables", name, i + 1, f"table rows disagree on column count: {sorted(widths)}"))
            i = j if j > i else i + 1
    return out


def case_backticks(ctx: Ctx) -> list[V]:
    out = []
    for name in ctx.texts:
        balance = 0
        line_of_open = 0
        for i, ln in enumerate(ctx.lines[name]):
            if ctx.in_fence[name][i]:
                continue
            for ch in ln:
                if ch == "`":
                    if balance == 0:
                        line_of_open = i + 1
                    balance ^= 1
        if balance:
            out.append(V("backticks", name, line_of_open, "unbalanced inline-code backticks"))
    return out


GUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def case_guid_typos(ctx: Ctx) -> list[V]:
    """A GUID used once that is one or two edits from a repeated one is a typo."""
    out = []
    occurrences: dict[str, list[tuple[str, int]]] = {}
    for name in ctx.texts:
        for lineno, ln in ctx.prose_lines(name):
            for m in GUID.finditer(ln.lower()):
                occurrences.setdefault(m.group(0), []).append((name, lineno))
    repeated = [g for g, sites in occurrences.items() if len(sites) >= 2]
    for g, sites in occurrences.items():
        if len(sites) > 1:
            continue
        for r in repeated:
            if levenshtein(g, r) <= 2:
                out.append(V("guid-typos", sites[0][0], sites[0][1],
                             f"GUID {g} is one or two edits from the repeated {r}; likely a typo"))
                break
    return out


CASES = [
    ("frontmatter", "SKILL.md frontmatter parses, name and description intact", case_frontmatter),
    ("links", "relative markdown links and their anchors resolve", case_links),
    ("repo-paths", "backticked repo-relative paths resolve", case_repo_paths),
    ("script-flags", "flags shown next to a script exist in that script", case_script_flags),
    ("json-blocks", "json code blocks and example-content.json parse", case_json_blocks),
    ("schema-keys", "dotted backticked keys belong to the renderer schema", case_schema_keys),
    ("palette", "mentioned colours are named palette constants", case_palette),
    ("counted-lists", "'Two <things>:' lines match their list length", case_counted_lists),
    ("duplicate-sentences", "no long sentence repeated across files", case_duplicate_sentences),
    ("stale-text", "no renamed fields or stale phrasings", case_stale_text),
    ("tool-paths", "no Claude-only path in the shared skill", case_tool_paths),
    ("weak-modals", "no weak modals in instructions", case_weak_modals),
    ("tables", "markdown tables agree on column count", case_tables),
    ("backticks", "inline-code backticks balance per file", case_backticks),
    ("guid-typos", "no GUID that is a near-miss of a repeated one", case_guid_typos),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit ea-projects-curator; prints one violation count.")
    ap.add_argument("--report", metavar="PATH", help="write a markdown report of every violation")
    ap.add_argument("--list", action="store_true", help="list case ids and stop")
    args = ap.parse_args()

    if args.list:
        for cid, desc, _ in CASES:
            print(f"{cid}\t{desc}")
        return 0

    ctx = Ctx()
    violations: list[V] = []
    for _, _, fn in CASES:
        violations.extend(fn(ctx))
    violations.sort(key=lambda v: (v.case, v.file, v.line or 0))

    if args.report:
        lines = [f"# ea-projects-curator audit — {len(violations)} violation(s)",
                 f"_Generated {datetime.datetime.now().isoformat(timespec='seconds')}_", ""]
        by_case: dict[str, list[V]] = {}
        for v in violations:
            by_case.setdefault(v.case, []).append(v)
        for cid, desc, _ in CASES:
            found = by_case.get(cid, [])
            lines.append(f"## `{cid}` — {len(found)} violation(s)")
            lines.append(f"_{desc}_")
            lines.append("")
            if not found:
                lines.append("- clean")
            for v in found:
                lines.append(f"- {v}")
            lines.append("")
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(len(violations))
    return 0


if __name__ == "__main__":
    sys.exit(main())
