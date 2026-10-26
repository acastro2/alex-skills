"""The one shape every rule returns."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from .text import SkillText


@dataclass(frozen=True)
class Finding:
    """One rule violation, in the terms a reader needs: where, which rule, why."""

    rule: str
    skill: str
    file: str
    line: int | None
    message: str

    def text(self) -> str:
        where = f"{self.skill}/{self.file}"
        if self.line is not None:
            where = f"{where}:{self.line}"
        return f"{where} - {self.rule} - {self.message}"


@dataclass(frozen=True)
class Rule:
    """One check. Pure: a text bundle in, findings out. No globals, no I/O beyond reads."""

    id: str
    check: Callable[[SkillText], list[Finding]]
    why: str
