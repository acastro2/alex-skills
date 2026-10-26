"""The rules. Each one is a pure function over a skill's text bundle.

Every rule answers "would a reader of this file be misled?" Text that a model loads and
trusts has to resolve, match its own counts, and not tell two different stories. These are
cheap checks for the failures that already happened, not a style guide.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from .model import Finding
from .text import SkillText

try:
    import yaml
except ImportError:  # pragma: no cover - the gate must say so, not guess
    yaml = None

NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024
NAME_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL
)
ALLOWED_KEYS = frozenset(
    {
        "name",
        "description",
        "license",
        "compatibility",
        "metadata",
        "allowed-tools",
        "disable-model-invocation",
        "version",
    }
)


def _found(ctx: SkillText, rule: str, name: str, line: int | None, message: str) -> Finding:
    return Finding(rule=rule, skill=ctx.skill, file=name, line=line, message=message)


# --- frontmatter ---------------------------------------------------------------


def check_frontmatter(ctx: SkillText) -> list[Finding]:
    """What a host reads before it loads the skill: the name, the trigger text, the flags.

    A bad key is the expensive one here: a typo'd `disable-model-invocation` loads silently
    and the skill fires when it should not.
    """
    if "SKILL.md" not in ctx.texts:
        return [_found(ctx, "frontmatter", "SKILL.md", None, "SKILL.md is missing")]
    if yaml is None:
        raise RuntimeError("PyYAML is unavailable")

    text = ctx.texts["SKILL.md"]
    match = FRONTMATTER_RE.match(text)
    if not match:
        return [_found(ctx, "frontmatter", "SKILL.md", 1, "missing or malformed frontmatter")]
    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        detail = str(error).splitlines()[0]
        return [_found(ctx, "frontmatter", "SKILL.md", 1, f"invalid YAML: {detail}")]
    if not isinstance(frontmatter, dict):
        return [_found(ctx, "frontmatter", "SKILL.md", 1, "frontmatter must be a mapping")]

    out: list[Finding] = []
    for key in sorted(frontmatter, key=str):
        if key in ALLOWED_KEYS:
            continue
        close = difflib.get_close_matches(str(key), sorted(ALLOWED_KEYS), n=1)
        hint = f", did you mean {close[0]!r}?" if close else ""
        out.append(_found(ctx, "frontmatter", "SKILL.md", 2, f"unknown frontmatter key {key!r}{hint}"))

    name = frontmatter.get("name")
    description = frontmatter.get("description")

    if not isinstance(name, str) or not name.strip():
        out.append(_found(ctx, "frontmatter", "SKILL.md", 2, "name must be a non-empty string"))
    elif name != ctx.skill:
        out.append(
            _found(
                ctx,
                "frontmatter",
                "SKILL.md",
                2,
                f"name {name!r} must equal directory {ctx.skill!r}",
            )
        )
    else:
        if len(name) > NAME_MAX_LENGTH:
            out.append(
                _found(
                    ctx,
                    "frontmatter",
                    "SKILL.md",
                    2,
                    f"name is {len(name)} characters, the maximum is {NAME_MAX_LENGTH}",
                )
            )
        elif not NAME_RE.fullmatch(name):
            out.append(
                _found(
                    ctx,
                    "frontmatter",
                    "SKILL.md",
                    2,
                    f"name {name!r} must be lowercase letters and digits, joined by single hyphens",
                )
            )

    if not isinstance(description, str) or not description.strip():
        out.append(_found(ctx, "frontmatter", "SKILL.md", 3, "description must be a non-empty string"))
    elif len(description) > DESCRIPTION_MAX_LENGTH:
        out.append(
            _found(
                ctx,
                "frontmatter",
                "SKILL.md",
                3,
                f"description is {len(description)} characters, the maximum is {DESCRIPTION_MAX_LENGTH}",
            )
        )

    if "disable-model-invocation" in frontmatter and not isinstance(
        frontmatter["disable-model-invocation"], bool
    ):
        out.append(
            _found(
                ctx,
                "frontmatter",
                "SKILL.md",
                2,
                "disable-model-invocation must be true or false without quotes",
            )
        )
    return out


# --- links and paths -----------------------------------------------------------


def _headings(text: str) -> list[str]:
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        match = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if match and not fenced:
            out.append(match.group(1))
    return out


def _anchor(heading: str) -> str:
    text = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s", "-", text)


def check_links(ctx: SkillText) -> list[Finding]:
    """A markdown link that resolves nowhere is the reader's dead end, and the model's too."""
    out: list[Finding] = []
    for name in ctx.texts:
        base = ctx.files[name].parent
        for lineno, line in ctx.prose_lines(name):
            for match in re.finditer(r"\[([^\]]*)\]\(([^)\s]+)\)", line):
                target = match.group(2)
                if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("//"):
                    continue
                path_part, _, fragment = target.partition("#")
                if path_part:
                    resolved = (base / path_part).resolve()
                    if not resolved.exists():
                        out.append(
                            _found(ctx, "links", name, lineno, f"link target does not exist: {target}")
                        )
                        continue
                else:
                    resolved = ctx.files[name].resolve()
                if fragment and resolved.suffix == ".md" and resolved.exists():
                    anchors = {_anchor(h) for h in _headings(resolved.read_text(encoding="utf-8"))}
                    if fragment not in anchors:
                        out.append(
                            _found(
                                ctx,
                                "links",
                                name,
                                lineno,
                                f"anchor not found in {resolved.name}: #{fragment}",
                            )
                        )
    return out


PATH_SPAN = re.compile(r"^(?:\./|\.\./|[a-z0-9][\w.-]*/)[\w./%-]*\.(?:py|md|json|sh)$")


def _resolve_bases(ctx: SkillText) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for base in ctx.policy.path_bases:
        path = Path(base).expanduser()
        if not path.is_absolute():
            path = ctx.skill_dir / path
        out.append((base, path.resolve()))
    return out


def check_repo_paths(ctx: SkillText) -> list[Finding]:
    """A backticked path is an instruction to read that file. If it does not resolve, the
    reader is told to read nothing.

    Declared bases are checked too: a base that no longer exists is the same failure one
    step earlier, and it hides the paths that relied on it.
    """
    out: list[Finding] = []
    bases = _resolve_bases(ctx)
    for base, path in bases:
        if not path.exists():
            out.append(
                _found(
                    ctx,
                    "repo-paths",
                    "SKILL.md",
                    1,
                    f"declared path base does not exist: {base}",
                )
            )

    for name in ctx.texts:
        base_dir = ctx.files[name].parent
        for lineno, line in ctx.prose_lines(name):
            for match in re.finditer(r"`([^`]+)`", line):
                span = match.group(1).strip()
                if any(ch in span for ch in "<>~$* "):
                    continue
                if not PATH_SPAN.match(span):
                    continue
                if span in ctx.policy.external_paths:
                    continue
                candidates = [base_dir / span, ctx.skill_dir / span, ctx.root / span]
                candidates += [path / span for _, path in bases]
                if any(candidate.exists() for candidate in candidates):
                    continue
                out.append(
                    _found(
                        ctx,
                        "repo-paths",
                        name,
                        lineno,
                        f"backticked path does not resolve: {span}",
                    )
                )
    return out


# --- prose shape ---------------------------------------------------------------


COUNT_WORDS = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
COUNT_LINE = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten)\b\s+\S+[^:]{0,60}:(\*\*)?\s*$", re.I
)
ITEM_RE = re.compile(r"^\s*(?:[-*]\s|\d+\.\s)")


def check_counted_lists(ctx: SkillText) -> list[Finding]:
    """Text that says "Three checks" and then lists four makes the reader distrust the rest."""
    out: list[Finding] = []
    for name in ctx.texts:
        lines = ctx.lines[name]
        for index, line in enumerate(lines):
            if ctx.fenced[name][index]:
                continue
            match = COUNT_LINE.search(line)
            if not match:
                continue
            want = COUNT_WORDS[match.group(1).lower()]
            cursor = index + 1
            while cursor < len(lines) and not lines[cursor].strip():
                cursor += 1
            if cursor >= len(lines) or not ITEM_RE.match(lines[cursor]):
                continue
            count = 0
            probe = cursor
            while probe < len(lines):
                if ITEM_RE.match(lines[probe]):
                    count += 1
                elif lines[probe].strip() and lines[probe][:1] in (" ", "\t"):
                    pass  # a wrapped continuation of the item above
                else:
                    break
                probe += 1
            if count != want:
                out.append(
                    _found(
                        ctx,
                        "counted-lists",
                        name,
                        index + 1,
                        f"line says '{match.group(1)}' but the list has {count} item(s)",
                    )
                )
    return out


def _normalize(sentence: str) -> str:
    text = re.sub(r"[`*_\[\]]", "", sentence.lower())
    return re.sub(r"\s+", " ", text).strip()


def check_duplicate_sentences(ctx: SkillText) -> list[Finding]:
    """The same long sentence in two files drifts: one gets fixed, the other keeps lying.

    Two files marked standalone are exempt on purpose: a reference that is read on its own
    must carry its own warning, and that is not drift.
    """
    out: list[Finding] = []
    seen: dict[str, tuple[str, int, str]] = {}
    for name in ctx.texts:
        for lineno, line in ctx.prose_lines(name):
            for raw in re.split(r"(?<=[.!?])\s+", line):
                normalized = _normalize(raw)
                if len(normalized) < 70:
                    continue
                if normalized not in seen:
                    seen[normalized] = (name, lineno, raw)
                    continue
                other_file, other_line, other_raw = seen[normalized]
                if other_file == name:
                    continue
                both_standalone = (
                    other_file in ctx.policy.standalone and name in ctx.policy.standalone
                )
                if both_standalone:
                    continue
                out.append(
                    _found(
                        ctx,
                        "duplicate-sentences",
                        name,
                        lineno,
                        f"same sentence as {other_file}:{other_line}: {other_raw[:80]}...",
                    )
                )
    return out


WEAK = re.compile(
    r"\b(should probably|if possible|try to|maybe|perhaps|ideally|as appropriate|where possible|if convenient)\b",
    re.I,
)
NEGATED = re.compile(r"(?:not|never|don't|do not|n't)\s+\w*\s*$", re.I)


def check_weak_modals(ctx: SkillText) -> list[Finding]:
    """A hedge turns an instruction into a suggestion, and a suggestion gets skipped."""
    out: list[Finding] = []
    for name in ctx.texts:
        for lineno, line in ctx.prose_lines(name):
            for match in WEAK.finditer(line):
                before = line[: match.start()]
                if NEGATED.search(before) or re.search(r"\b(don't|do not|never)\b[^.]{0,15}$", before):
                    continue
                out.append(
                    _found(
                        ctx,
                        "weak-modals",
                        name,
                        lineno,
                        f"weak modal in an instruction: {match.group(0)!r}",
                    )
                )
    return out


PLACEMENT = re.compile(
    r"\b(put|puts|copy|copies|install|installs|place|places|save|saves|drop|drops|move|moves)\b",
    re.I,
)
HOST_TREES = ("~/.config/opencode", "~/.pi")


def check_tool_paths(ctx: SkillText) -> list[Finding]:
    """A skill runs under Claude Code, OpenCode and Pi. An instruction that only works when
    the file sits in one host's tree is the bug this catches.

    It judges the instruction, not the mention: naming a real file under `~/.claude/` is a
    fact about Alex's machine, while telling the reader to copy a skill there is a
    portability bug.
    """
    out: list[Finding] = []
    for name in ctx.texts:
        for lineno, line in ctx.prose_lines(name):
            if "~/.claude/" not in line or not PLACEMENT.search(line):
                continue
            block = ctx.block_for(name, lineno)
            if any(tree in block for tree in HOST_TREES):
                continue
            out.append(
                _found(
                    ctx,
                    "tool-paths",
                    name,
                    lineno,
                    "instruction places content in one host's tree; name every host's tree",
                )
            )
    return out


def check_tables(ctx: SkillText) -> list[Finding]:
    """A table whose rows disagree on column count renders as noise, not a table."""
    out: list[Finding] = []
    for name in ctx.texts:
        lines = ctx.lines[name]
        index = 0
        while index < len(lines):
            if ctx.fenced[name][index] or not lines[index].lstrip().startswith("|"):
                index += 1
                continue
            block = []
            cursor = index
            while (
                cursor < len(lines)
                and not ctx.fenced[name][cursor]
                and "|" in lines[cursor]
                and lines[cursor].strip()
            ):
                block.append(cursor)
                cursor += 1
            if len(block) >= 3:
                # An escaped pipe is a cell value, not a column edge: `"PieChart"\|"ColumnChart"`
                # inside a code span is one cell and must not read as six columns.
                widths = {len(re.findall(r"(?<!\\)\|", lines[k])) for k in block}
                if len(widths) > 1:
                    out.append(
                        _found(
                            ctx,
                            "tables",
                            name,
                            index + 1,
                            f"table rows disagree on column count: {sorted(widths)}",
                        )
                    )
            index = cursor if cursor > index else index + 1
    return out


def check_backticks(ctx: SkillText) -> list[Finding]:
    """An unclosed inline-code span swallows the rest of the paragraph."""
    out: list[Finding] = []
    for name in ctx.texts:
        balance = 0
        opened_at = 0
        for index, line in enumerate(ctx.lines[name]):
            if ctx.fenced[name][index]:
                continue
            for char in line:
                if char == "`":
                    if balance == 0:
                        opened_at = index + 1
                    balance ^= 1
        if balance:
            out.append(
                _found(ctx, "backticks", name, opened_at, "unbalanced inline-code backticks")
            )
    return out


GUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        for j, right_char in enumerate(right, 1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def check_guid_typos(ctx: SkillText) -> list[Finding]:
    """A GUID typed once is often a typo of one typed five times, and a typo is a dead
    request ID in a run."""
    occurrences: dict[str, list[tuple[str, int]]] = {}
    for name in ctx.texts:
        for lineno, line in ctx.prose_lines(name):
            for match in GUID.finditer(line.lower()):
                occurrences.setdefault(match.group(0), []).append((name, lineno))

    repeated = [guid for guid, sites in occurrences.items() if len(sites) >= 2]
    out: list[Finding] = []
    for guid, sites in occurrences.items():
        if len(sites) > 1:
            continue
        for known in repeated:
            if _levenshtein(guid, known) <= 2:
                out.append(
                    _found(
                        ctx,
                        "guid-typos",
                        sites[0][0],
                        sites[0][1],
                        f"GUID {guid} is one or two edits from the repeated {known}; likely a typo",
                    )
                )
                break
    return out
