#!/usr/bin/env python3
"""Validate top-level skills in this repository."""
from __future__ import annotations

import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
RELATIVE_PATH_RE = re.compile(
    r"(?<![.\w])(\.\./[^\s`'\"<>()\[\]{}]+)"
)
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024
NAME_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
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


@dataclass(frozen=True)
class ValidationResult:
    checked: int
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def discover_skill_files(root: Path) -> list[Path]:
    """Return only SKILL.md files in immediate child directories."""
    return sorted(path for path in root.glob("*/SKILL.md") if path.is_file())


def parse_frontmatter(path: Path) -> tuple[dict | None, str, str | None]:
    """Return parsed frontmatter, full text, and an optional error."""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text, "missing or malformed frontmatter"

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        detail = str(error).splitlines()[0]
        return None, text, f"invalid YAML: {detail}"

    if not isinstance(frontmatter, dict):
        return None, text, "frontmatter must be a mapping"
    return frontmatter, text, None


def find_relative_paths(text: str) -> set[str]:
    """Return explicit parent-relative path tokens from skill text."""
    return set(RELATIVE_PATH_RE.findall(text))


def validate_repo(root: Path) -> ValidationResult:
    """Validate the flat skill layout under root."""
    if yaml is None:
        raise RuntimeError("PyYAML is unavailable")

    errors: list[str] = []
    skill_files = discover_skill_files(root)

    for skill_file in skill_files:
        display_path = skill_file.relative_to(root)
        frontmatter, text, frontmatter_error = parse_frontmatter(skill_file)
        if frontmatter_error:
            errors.append(f"{display_path}: {frontmatter_error}")
        else:
            for key in sorted(frontmatter, key=str):
                if key in ALLOWED_KEYS:
                    continue
                close = difflib.get_close_matches(str(key), sorted(ALLOWED_KEYS), n=1)
                hint = f", did you mean {close[0]!r}?" if close else ""
                errors.append(f"{display_path}: unknown frontmatter key {key!r}{hint}")

            name = frontmatter.get("name")
            description = frontmatter.get("description")

            if not isinstance(name, str) or not name.strip():
                errors.append(f"{display_path}: name must be a non-empty string")
            elif name != skill_file.parent.name:
                errors.append(
                    f"{display_path}: name {name!r} must equal directory "
                    f"{skill_file.parent.name!r}"
                )

            if isinstance(name, str) and name.strip():
                if len(name) > NAME_MAX_LENGTH:
                    errors.append(
                        f"{display_path}: name is {len(name)} characters, "
                        f"the maximum is {NAME_MAX_LENGTH}"
                    )
                elif not NAME_RE.fullmatch(name):
                    errors.append(
                        f"{display_path}: name {name!r} must be lowercase "
                        "letters and digits, joined by single hyphens"
                    )

            if not isinstance(description, str) or not description.strip():
                errors.append(
                    f"{display_path}: description must be a non-empty string"
                )
            elif len(description) > DESCRIPTION_MAX_LENGTH:
                errors.append(
                    f"{display_path}: description is {len(description)} characters, "
                    f"the maximum is {DESCRIPTION_MAX_LENGTH}"
                )

            if "disable-model-invocation" in frontmatter and not isinstance(
                frontmatter["disable-model-invocation"], bool
            ):
                errors.append(
                    f"{display_path}: disable-model-invocation must be true or "
                    "false without quotes"
                )

        for relative_path in sorted(find_relative_paths(text)):
            target = (skill_file.parent / relative_path).resolve()
            if not target.exists():
                errors.append(
                    f"{display_path}: relative path {relative_path!r} does not resolve"
                )

    return ValidationResult(len(skill_files), tuple(errors))


def main(root: Path = REPO_ROOT) -> int:
    if yaml is None:
        print("PyYAML is required. Install it with: pip install pyyaml", file=sys.stderr)
        return 2

    result = validate_repo(root)
    if result.passed:
        print(f"Checked {result.checked} skills: PASS")
        return 0

    print(f"Checked {result.checked} skills: {len(result.errors)} error(s)")
    for error in result.errors:
        print(f"  {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
