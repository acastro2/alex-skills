"""Tests for the skill prose checker.

Each rule is a pure function over a text bundle, so most of these build a two-file skill in a
temp directory and assert one finding. The last test runs the checker on this repo, which
makes the gate itself the assertion: if a rule starts crying wolf, this fails here first.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from skillcheck import Policy, check_repo, check_skill

CLEAN_SKILL = """---
name: demo
description: A demo skill.
---

# Demo

Read `references/guide.md` before you start.
"""


def write_skill(tmp_path: Path, name: str = "demo", body: str = CLEAN_SKILL, **refs: str) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    if refs:
        reference = skill_dir / "references"
        reference.mkdir(parents=True, exist_ok=True)
        for filename, text in refs.items():
            name = filename.replace("_", "-")
            if not Path(name).suffix:
                name += ".md"
            (reference / name).write_text(text, encoding="utf-8")
    return skill_dir


def rules(findings) -> list[str]:
    return [finding.rule for finding in findings]


def test_clean_skill_passes(tmp_path: Path) -> None:
    skill_dir = write_skill(tmp_path, guide="# Guide\n\nNothing to see.\n")
    assert check_skill(skill_dir) == []


def test_frontmatter_flags_a_typoed_key(tmp_path: Path) -> None:
    body = "---\nname: demo\ndescription: Demo.\ndisable-model-invokation: true\n---\n\n# Demo\n"
    findings = check_skill(write_skill(tmp_path, body=body))
    assert rules(findings) == ["frontmatter"]
    assert "disable-model-invokation" in findings[0].message


def test_frontmatter_requires_the_directory_name(tmp_path: Path) -> None:
    body = "---\nname: other\ndescription: Demo.\n---\n\n# Demo\n"
    findings = check_skill(write_skill(tmp_path, body=body))
    assert "must equal directory" in findings[0].message


def test_broken_markdown_link_fails(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nSee [the guide](references/missing.md).\n"
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n"))
    assert rules(findings) == ["links"]


def test_link_anchor_must_exist(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nSee [the guide](references/guide.md#nope).\n"
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n"))
    assert rules(findings) == ["links"]


def test_unresolved_backticked_path_fails(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nRead `references/ghost.md` too.\n"
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n"))
    assert rules(findings) == ["repo-paths"]


def test_declared_base_resolves_a_path(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nRead `references/cli.md` too.\n"
    skill_dir = write_skill(tmp_path, body=body, guide="# Guide\n")
    (tmp_path / "other" / "references").mkdir(parents=True)
    (tmp_path / "other" / "references" / "cli.md").write_text("# CLI\n", encoding="utf-8")
    policy = Policy(path_bases=("../other",))
    assert check_skill(skill_dir, policy=policy) == []


def test_stale_declared_base_is_a_finding(tmp_path: Path) -> None:
    skill_dir = write_skill(tmp_path, guide="# Guide\n")
    findings = check_skill(skill_dir, policy=Policy(path_bases=("../gone",)))
    assert rules(findings) == ["repo-paths"]
    assert "declared path base does not exist" in findings[0].message


def test_external_path_is_not_checked(tmp_path: Path) -> None:
    span = "docs/knowledge/elsewhere.md"
    body = CLEAN_SKILL + f"\nRead `{span}` in the work repo.\n"
    skill_dir = write_skill(tmp_path, body=body, guide="# Guide\n")
    assert check_skill(skill_dir, policy=Policy(external_paths=frozenset({span}))) == []


def test_duplicate_sentence_between_two_files_fails(tmp_path: Path) -> None:
    sentence = (
        "This paragraph is long enough to count as a sentence for the duplicate check and it "
        "appears twice in this skill.\n"
    )
    body = CLEAN_SKILL + "\n" + sentence
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n\n" + sentence))
    assert rules(findings) == ["duplicate-sentences"]


def test_standalone_files_may_repeat_a_sentence(tmp_path: Path) -> None:
    sentence = (
        "This paragraph is long enough to count as a sentence for the duplicate check and it "
        "appears twice in this skill.\n"
    )
    body = CLEAN_SKILL + "\n" + sentence
    skill_dir = write_skill(tmp_path, body=body, guide="# Guide\n\n" + sentence)
    policy = Policy(standalone=frozenset({"SKILL.md", "references/guide.md"}))
    assert check_skill(skill_dir, policy=policy) == []


def test_install_instruction_in_one_host_tree_fails(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nCopy the folder to `~/.claude/skills/demo/` and restart.\n"
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n"))
    assert rules(findings) == ["tool-paths"]


def test_mentioning_a_host_path_is_not_a_finding(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nThe helper lives at `~/.claude/scripts/auth.py` and is already installed.\n"
    assert check_skill(write_skill(tmp_path, body=body, guide="# Guide\n")) == []


def test_install_instruction_naming_every_tree_passes(tmp_path: Path) -> None:
    body = (
        CLEAN_SKILL
        + "\nCopy the folder to `~/.claude/skills/demo/`, `~/.config/opencode/skills/demo/`, "
        "or the Pi skills folder depending on the host.\n"
    )
    assert check_skill(write_skill(tmp_path, body=body, guide="# Guide\n")) == []


def test_escaped_pipe_does_not_add_a_column(tmp_path: Path) -> None:
    body = CLEAN_SKILL + (
        "\n| Widget | Value | Notes |\n"
        "|---|---|---|\n"
        '| Chart | `"PieChart"\\|"ColumnChart"` | one cell |\n'
    )
    assert check_skill(write_skill(tmp_path, body=body, guide="# Guide\n")) == []


def test_wrong_table_columns_fail(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\n| A | B | C |\n|---|---|---|\n| one | two |\n"
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n"))
    assert rules(findings) == ["tables"]


def test_counted_list_must_match_its_count(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nThree checks:\n\n- one\n- two\n"
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n"))
    assert rules(findings) == ["counted-lists"]


def test_weak_modal_in_an_instruction_fails(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nMaybe run the checker first.\n"
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n"))
    assert rules(findings) == ["weak-modals"]


def test_negated_weak_modal_is_left_alone(tmp_path: Path) -> None:
    body = CLEAN_SKILL + "\nNever skip the checker, and do not maybe it either.\n"
    assert check_skill(write_skill(tmp_path, body=body, guide="# Guide\n")) == []


def test_guid_near_miss_is_flagged(tmp_path: Path) -> None:
    known = "12345678-1234-1234-1234-123456789abc"
    typo = "12345678-1234-1234-1234-123456789abd"
    body = CLEAN_SKILL + f"\nEpic {known} and epic {known} again.\nTicket {typo}.\n"
    findings = check_skill(write_skill(tmp_path, body=body, guide="# Guide\n"))
    assert rules(findings) == ["guid-typos"]


def test_this_repo_passes_its_own_gate() -> None:
    repo = Path(__file__).resolve().parents[2]
    findings = check_repo(repo)
    assert findings == [], "\n".join(finding.text() for finding in findings)
    assert len(list(repo.glob("*/SKILL.md"))) >= 30


@pytest.mark.parametrize("name", ["demo", "another-skill"])
def test_skill_name_matches_directories(tmp_path: Path, name: str) -> None:
    body = CLEAN_SKILL.replace("name: demo", f"name: {name}")
    assert check_skill(write_skill(tmp_path, name=name, body=body, guide="# Guide\n")) == []
