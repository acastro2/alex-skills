#!/usr/bin/env python3
"""Audit ea-projects-curator: its five domain rules, on top of the shared skill rules.

    python3 ea-projects-curator/tests/ea_projects_curator_audit.py                  # prints the count
    python3 ea-projects-curator/tests/ea_projects_curator_audit.py --report OUT.md  # count + details
    python3 ea-projects-curator/tests/ea_projects_curator_audit.py --list           # case ids

The shared rules live in `skillcheck/` and run here through `check_skill`. Only the rules
that mean something for this skill alone stay in this file: the page content schema, the
palette, the flags of the two scripts it calls, its JSON examples, and the vocabulary it
retired. Everything here must be fixable by editing the prose or the renderer; nothing here
writes.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from skillcheck import Finding, Rule, check_skill  # noqa: E402  (path set above)
from skillcheck.text import SkillText  # noqa: E402

SKILL_DIR = REPO / "ea-projects-curator"
RENDERER = SKILL_DIR / "references" / "render_page.py"
VOICE = REPO / "alex-voice" / "scripts" / "voice_check.py"
EXAMPLE = SKILL_DIR / "references" / "example-content.json"


def _found(ctx: SkillText, rule: str, name: str, line: int | None, message: str) -> Finding:
    return Finding(rule=rule, skill=ctx.skill, file=name, line=line, message=message)


def _renderer() -> str:
    return RENDERER.read_text(encoding="utf-8") if RENDERER.exists() else ""


# --- script flags --------------------------------------------------------------


def _flag_window(text: str, script: str) -> str:
    """Text after the script name, up to the next .py mention, so one command's flags are
    never checked against another script's name in the same span."""
    out = []
    position = 0
    while True:
        at = text.find(script, position)
        if at < 0:
            return " ".join(out)
        rest = text[at + len(script) :]
        cut = rest.find(".py")
        out.append(rest[:cut] if cut >= 0 else rest)
        position = at + len(script)


def case_script_flags(ctx: SkillText) -> list[Finding]:
    """A flag shown next to a script must exist in that script."""
    renderer = _renderer()
    out: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()

    render_flags = set(re.findall(r'"(--[\w-]+)"', renderer))
    voice_src = VOICE.read_text(encoding="utf-8") if VOICE.exists() else ""
    registers = (
        set(re.findall(r'"(\w+)":\s*\{', voice_src.split("TARGETS")[1]))
        if "TARGETS" in voice_src
        else set()
    )

    def check(name: str, lineno: int, window: str) -> None:
        if "render_page.py" in window:
            for flag in re.findall(r"--[\w-]+", _flag_window(window, "render_page.py")):
                key = (name, lineno, flag)
                if flag not in render_flags and key not in seen:
                    seen.add(key)
                    out.append(
                        _found(ctx, "script-flags", name, lineno, f"render_page.py flag not in the script: {flag}")
                    )
        if "voice_check.py" in window:
            for match in re.finditer(r"--register\s+(\w+)", _flag_window(window, "voice_check.py")):
                key = (name, lineno, match.group(1))
                if registers and match.group(1) not in registers and key not in seen:
                    seen.add(key)
                    out.append(
                        _found(
                            ctx,
                            "script-flags",
                            name,
                            lineno,
                            f"voice_check.py register unknown: {match.group(1)}",
                        )
                    )

    for name in ctx.texts:
        for index, line in enumerate(ctx.lines[name]):
            check(name, index + 1, line)
        for start_line, span in ctx.inline_spans(name):
            check(name, start_line, span)
    return out


# --- JSON examples -------------------------------------------------------------


def _parses(body: str) -> str | None:
    """None when the block parses. Fragments like `"docs": {...}` are legal in the docs
    because they live inside a larger object, so try the wrapped form too."""
    last: ValueError | None = None
    for candidate in (body, "{" + body + "}"):
        try:
            json.loads(candidate)
            return None
        except ValueError as error:
            last = error
    return str(last)


def case_json_blocks(ctx: SkillText) -> list[Finding]:
    out: list[Finding] = []
    for name in ctx.texts:
        text = ctx.texts[name]
        for match in re.finditer(r"^[ \t]*```json[ \t]*\n(.*?)^[ \t]*```", text, re.S | re.M):
            lineno = text[: match.start()].count("\n") + 1
            error = _parses(match.group(1))
            if error:
                out.append(_found(ctx, "json-blocks", name, lineno, f"json block does not parse: {error}"))
    try:
        json.loads(EXAMPLE.read_text(encoding="utf-8"))
    except ValueError as error:
        out.append(
            _found(
                ctx,
                "json-blocks",
                "references/example-content.json",
                None,
                f"example content does not parse: {error}",
            )
        )
    return out


# --- content schema ------------------------------------------------------------

SCHEMA_KEY_RE = re.compile(r"`([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)(?:\[\])?`")


def schema_vocabulary(renderer: str) -> tuple[set[str], set[str]]:
    """(top-level required keys, every key name the renderer ever reads)."""
    match = re.search(r"def check_content\(.*?\n(?=# --- block builders)", renderer, re.S)
    body = match.group(0) if match else ""
    top = set(re.findall(r'need(?:_list)?\(\s*\w+,\s*"(\w+)"', body))
    return top, set(top) | set(re.findall(r'\[\s*"(\w+)"\s*\]', renderer))


def case_schema_keys(ctx: SkillText) -> list[Finding]:
    """A dotted key that starts with a real schema key but names a field the renderer never
    reads is documentation drift (e.g. `exec_summary.footnote`). Tokens that do not start
    with a schema key at all (`page.goto`, `author.email`) are not our subject."""
    out: list[Finding] = []
    top, vocabulary = schema_vocabulary(_renderer())
    for name in ctx.texts:
        for lineno, line in ctx.prose_lines(name):
            for match in SCHEMA_KEY_RE.finditer(line):
                token = match.group(1)
                segments = token.split(".")
                if segments[0] not in top:
                    continue
                unknown = [s for s in segments[1:] if s not in vocabulary]
                if unknown:
                    out.append(
                        _found(
                            ctx,
                            "schema-keys",
                            name,
                            lineno,
                            f"key {token} names a field the renderer never reads: {unknown}",
                        )
                    )
    return out


# --- palette -------------------------------------------------------------------

HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def case_palette(ctx: SkillText) -> list[Finding]:
    """Every colour the prose mentions must be a named palette constant."""
    renderer = _renderer()
    out: list[Finding] = []
    assigned: set[str] = set()
    for match in re.finditer(r'=\s*"(#[0-9A-Fa-f]{6})"', renderer):
        assigned.add(match.group(1).lower())
    for match in re.finditer(r'"(#[0-9A-Fa-f]{6})"', renderer):
        assigned.add(match.group(1).lower())
    if not assigned:
        out.append(
            _found(
                ctx,
                "palette",
                "references/render_page.py",
                None,
                "no palette constants found; the parser went blind",
            )
        )
    for name in ctx.texts:
        for lineno, line in ctx.prose_lines(name):
            for match in HEX.finditer(line):
                if match.group(0).lower() not in assigned:
                    out.append(
                        _found(
                            ctx,
                            "palette",
                            name,
                            lineno,
                            f"colour not in the render_page.py palette: {match.group(0)}",
                        )
                    )
    return out


# --- retired vocabulary --------------------------------------------------------

STALE_NAMES = [("ImpactUSD", "column renamed to `Impact` (see the Columns table)")]
STALE_PHRASES = [
    (re.compile(r"\bboth views\b"), "the package defines four named views (set 2026-09-03); name the views"),
    (re.compile(r'"Impact":\s*"\s*\$'), "Impact example leads with money; outcome comes first, metric in parens"),
]


def case_stale_text(ctx: SkillText) -> list[Finding]:
    out: list[Finding] = []
    for name in ctx.texts:
        for lineno, line in ctx.prose_lines(name):
            for token, why in STALE_NAMES:
                if token in line:
                    out.append(_found(ctx, "stale-text", name, lineno, f"stale name `{token}`: {why}"))
            for pattern, why in STALE_PHRASES:
                if pattern.search(line):
                    out.append(_found(ctx, "stale-text", name, lineno, f"stale phrasing: {why}"))
    return out


DOMAIN_RULES = (
    Rule("json-blocks", case_json_blocks, "the worked example and every json block parse"),
    Rule("schema-keys", case_schema_keys, "a dotted key belongs to the renderer schema"),
    Rule("palette", case_palette, "a mentioned colour is a named palette constant"),
    Rule("script-flags", case_script_flags, "a shown flag exists in the script it names"),
    Rule("stale-text", case_stale_text, "no renamed field or retired phrasing"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit ea-projects-curator; prints one count.")
    parser.add_argument("--report", metavar="PATH", help="write a markdown report of every finding")
    parser.add_argument("--list", action="store_true", help="list rule ids and stop")
    args = parser.parse_args()

    if args.list:
        for rule in DOMAIN_RULES:
            print(f"{rule.id}\t{rule.why}")
        return 0

    findings = check_skill(SKILL_DIR, root=REPO, extra_rules=DOMAIN_RULES)

    if args.report:
        lines = [
            f"# ea-projects-curator audit — {len(findings)} finding(s)",
            f"_Generated {datetime.datetime.now().isoformat(timespec='seconds')}_",
            "",
        ]
        by_rule: dict[str, list[Finding]] = {}
        for finding in findings:
            by_rule.setdefault(finding.rule, []).append(finding)
        for rule in DOMAIN_RULES:
            found = by_rule.pop(rule.id, [])
            lines.extend([f"## `{rule.id}` — {len(found)} finding(s)", f"_{rule.why}_", ""])
            lines.extend(f"- {finding.text()}" for finding in found)
            lines.append("")
        for rule_id in sorted(by_rule):
            found = by_rule[rule_id]
            lines.extend([f"## `{rule_id}` — {len(found)} finding(s)", ""])
            lines.extend(f"- {finding.text()}" for finding in found)
            lines.append("")
        Path(args.report).write_text("\n".join(lines), encoding="utf-8")

    print(len(findings))
    for finding in findings:
        print(f"  {finding.text()}", file=sys.stderr)
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
