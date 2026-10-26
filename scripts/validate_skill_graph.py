#!/usr/bin/env python3
"""Validate every skill in this repository.

The rules live in `skillcheck/`. This file keeps the command name, the result shape, and the
exit codes that pre-commit, `AGENTS.md`, and the tests already call. It is an adapter, not a
second implementation: adding a rule means editing `skillcheck/rules.py` only.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from skillcheck import check_skill, discover_skills  # noqa: E402  (path set above)


@dataclass(frozen=True)
class ValidationResult:
    checked: int
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def validate_repo(root: Path = REPO_ROOT) -> ValidationResult:
    root = Path(root).resolve()
    skill_files = discover_skills(root)
    errors: list[str] = []
    for skill_md in skill_files:
        for finding in check_skill(skill_md.parent, root=root):
            errors.append(f"{finding.skill}/{finding.file}: {finding.message}")
    return ValidationResult(len(skill_files), tuple(errors))


def main(root: Path = REPO_ROOT) -> int:
    try:
        result = validate_repo(root)
    except RuntimeError as error:
        print(f"skillcheck: {error}", file=sys.stderr)
        return 2

    if result.passed:
        print(f"Checked {result.checked} skills: PASS")
        return 0

    print(f"Checked {result.checked} skills: {len(result.errors)} error(s)")
    for error in result.errors:
        print(f"  {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
