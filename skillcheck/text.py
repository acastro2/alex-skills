"""The text bundle every rule reads.

A rule never opens a file. It reads one bundle built once per skill, which is why
`check_skill` is cheap to call and a rule is cheap to test: hand it a dict of texts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .policy import Policy


@dataclass
class SkillText:
    skill: str
    skill_dir: Path
    root: Path
    policy: Policy
    files: dict[str, Path] = field(default_factory=dict)
    texts: dict[str, str] = field(default_factory=dict)
    lines: dict[str, list[str]] = field(default_factory=dict)
    fenced: dict[str, list[bool]] = field(default_factory=dict)

    def add(self, name: str, path: Path) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        self.files[name] = path
        self.texts[name] = text
        self.lines[name] = text.splitlines()
        flags: list[bool] = []
        in_fence = False
        for line in self.lines[name]:
            if line.lstrip().startswith(("```", "~~~")):
                flags.append(True)
                in_fence = not in_fence
            else:
                flags.append(in_fence)
        self.fenced[name] = flags

    def prose_lines(self, name: str):
        """(1-based line number, line) for every line outside a fenced block."""
        for index, line in enumerate(self.lines[name]):
            if not self.fenced[name][index]:
                yield index + 1, line

    def block_for(self, name: str, lineno: int) -> str:
        """The blank-line-delimited block around a line, which is the unit a rule
        should judge: one paragraph, not one wrapped line."""
        lines = self.lines[name]
        start = end = lineno - 1
        while start > 0 and lines[start - 1].strip():
            start -= 1
        while end + 1 < len(lines) and lines[end + 1].strip():
            end += 1
        return "\n".join(lines[start : end + 1])

    def inline_spans(self, name: str) -> list[tuple[int, str]]:
        """(start line, content) for every inline-code span outside fences.

        A span left open at the end of a line continues on the next one, because the prose
        wraps long commands. A rule that checks a command's flags has to see the whole span,
        not the first wrapped line.
        """
        spans: list[tuple[int, str]] = []
        buffer: str | None = None
        start = 0
        for index, line in enumerate(self.lines[name]):
            if self.fenced[name][index]:
                continue
            for char in line:
                if char == "`":
                    if buffer is None:
                        buffer, start = "", index + 1
                    else:
                        spans.append((start, buffer))
                        buffer = None
                elif buffer is not None:
                    buffer += char
            if buffer is not None:
                buffer += "\n"
        return spans


def load_skill(skill_dir: Path, root: Path) -> SkillText:
    """Read a skill's SKILL.md and every reference markdown under it.

    References only: scripts and fixtures in the same folder are not prose, and a rule
    about prose that reads a .py file would report its comments as findings.
    """
    skill_dir = Path(skill_dir).resolve()
    ctx = SkillText(
        skill=skill_dir.name,
        skill_dir=skill_dir,
        root=Path(root).resolve(),
        policy=Policy.for_skill(skill_dir.name),
    )
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        ctx.add("SKILL.md", skill_md)
    references = skill_dir / "references"
    if references.is_dir():
        for path in sorted(references.rglob("*.md")):
            ctx.add(str(path.relative_to(skill_dir)), path)
    return ctx
