"""One skill in, its findings out.

The rules are a registry, not a chain of calls, so a caller can add its own: the curator
skill supplies five domain rules that make no sense for any other skill, and it does that
through `extra_rules` rather than by copying the shared ones.
"""
from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable, Sequence

from .model import Finding, Rule
from .policy import Policy
from .rules import (
    check_backticks,
    check_counted_lists,
    check_duplicate_sentences,
    check_frontmatter,
    check_guid_typos,
    check_links,
    check_repo_paths,
    check_tables,
    check_tool_paths,
    check_weak_modals,
)
from .text import load_skill

RULES: tuple[Rule, ...] = (
    Rule("frontmatter", check_frontmatter, "the host reads this before it loads the skill"),
    Rule("links", check_links, "a dead link is a dead end for the reader"),
    Rule("repo-paths", check_repo_paths, "a backticked path is an instruction to read that file"),
    Rule("tables", check_tables, "rows that disagree on columns do not render as a table"),
    Rule("backticks", check_backticks, "an unclosed span swallows the paragraph"),
    Rule("counted-lists", check_counted_lists, "a stated count that is wrong costs trust"),
    Rule("duplicate-sentences", check_duplicate_sentences, "two copies drift, one gets fixed"),
    Rule("weak-modals", check_weak_modals, "a hedge turns an instruction into a suggestion"),
    Rule("tool-paths", check_tool_paths, "an install instruction that works in one host only"),
    Rule("guid-typos", check_guid_typos, "a near-miss GUID is a dead request ID"),
)


def check_skill(
    skill_dir: Path,
    root: Path | None = None,
    extra_rules: Sequence[Rule] = (),
    policy: Policy | None = None,
) -> list[Finding]:
    """Check one skill folder. Pass `extra_rules` to add a skill's own domain rules."""
    skill_dir = Path(skill_dir).resolve()
    ctx = load_skill(skill_dir, root or skill_dir.parent)
    if policy is not None:
        ctx.policy = policy
    findings: list[Finding] = []
    for rule in (*RULES, *extra_rules):
        findings.extend(rule.check(ctx))
    findings.sort(key=lambda f: (f.rule, f.file, f.line or 0))
    return findings


def discover_skills(root: Path) -> list[Path]:
    """Skill folders are the immediate children that hold a SKILL.md. Nothing recursive:
    a vendored skill inside another folder is not this repo's skill."""
    return sorted(path for path in Path(root).glob("*/SKILL.md") if path.is_file())


def check_repo(root: Path, extra_rules: Iterable[Rule] = ()) -> list[Finding]:
    findings: list[Finding] = []
    for skill_md in discover_skills(root):
        findings.extend(check_skill(skill_md.parent, root=root, extra_rules=tuple(extra_rules)))
    return findings
