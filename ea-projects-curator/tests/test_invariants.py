"""Canary guard for the ea-projects-curator skill package.

These tests pin the rules that must survive any edit: the exclusion screen gates, the
review-table convention, the status and theme vocabularies, the stage-never-publish
rule, the page naming pattern, the ledger keys, and the per-tool script-path
convention. They are intentionally about presence, not wording: a rule may be reworded,
but it may not disappear.

Run as the /autoresearch guard:

    python3 -m pytest scripts/tests ea-projects-curator/tests -q

The renderer smoke tests here are read-only: they render the shipped example to a
temporary file and check the renderer's own validation passes. render_page.py is not in
any loop's scope, so a failure here is a stop signal, not something to edit.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO = SKILL_DIR.parent
PROSE = {
    "SKILL.md": SKILL_DIR / "SKILL.md",
    "references/recap.md": SKILL_DIR / "references" / "recap.md",
    "references/brought-docs.md": SKILL_DIR / "references" / "brought-docs.md",
    "references/write-shapes.md": SKILL_DIR / "references" / "write-shapes.md",
}
RENDERER = SKILL_DIR / "references" / "render_page.py"
EXAMPLE = SKILL_DIR / "references" / "example-content.json"


def read(name: str) -> str:
    return PROSE[name].read_text(encoding="utf-8")


# (file, phrase) — presence required, verbatim.
INVARIANTS = [
    # the three overriding rules (SKILL.md)
    ("SKILL.md", "Never invent."),
    ("SKILL.md", "Never write unconfirmed."),
    ("SKILL.md", "is Alex's column"),
    # lifecycle and vocabulary
    ("SKILL.md", "1. Proposed"),
    ("SKILL.md", "2. In Analysis"),
    ("SKILL.md", "3. Decision-Ready"),
    ("SKILL.md", "4. In Progress"),
    ("SKILL.md", "5. Verifying"),
    ("SKILL.md", "6. Closed"),
    ("SKILL.md", "Delivered"),
    ("SKILL.md", "Killed"),
    ("SKILL.md", "Superseded"),
    ("SKILL.md", "Security Hardening"),
    ("SKILL.md", "Platform Foundations"),
    ("SKILL.md", "Modernization Enablement"),
    ("SKILL.md", "Business Initiatives"),
    ("SKILL.md", "Business Owner"),
    ("SKILL.md", "Process Owner"),
    ("SKILL.md", "Advisory Board"),
    # exclusion screen gates
    ("SKILL.md", "Privileged / counsel-touched"),
    ("SKILL.md", "Vendor-sensitive naming"),
    ("SKILL.md", "Scope-claiming"),
    ("SKILL.md", "HR / personnel"),
    # review gate shape
    ("SKILL.md", "one table per surface, never one merged list"),
    ("SKILL.md", "A1, A2, ..."),
    ("SKILL.md", "D1, D2, ..."),
    ("SKILL.md", "E1, E2, ..."),
    # AAB control
    ("SKILL.md", "Never create an AAB Intake item"),
    ("SKILL.md", "Never infer a date from cadence"),
    ("SKILL.md", "Scheduling is Alex's"),
    ("SKILL.md", "YYYY-MM-DD-AAB-Recap.aspx"),
    # newsletter and stage-never-publish
    ("SKILL.md", "PromotedState=1"),
    ("SKILL.md", "PromotedState=2"),
    ("SKILL.md", "What Enterprise Architecture shipped"),
    ("SKILL.md", "never publish the recap yourself"),
    ("SKILL.md", "Never change list or site permissions"),
    ("SKILL.md", "no @-mentions"),
    # identity and ledger
    ("SKILL.md", "d2c0a30a-dab4-40a7-bc63-7268736473f2"),
    ("SKILL.md", "80c68e54-eadf-4cf3-946a-3c0e432056a5"),
    ("SKILL.md", "fe9c1f44-8a0c-4f68-b0b1-bf8741eed4fd"),
    ("SKILL.md", "not_doing"),
    ("SKILL.md", "open_items"),
    ("SKILL.md", "curated.json"),
    # renderer pipeline
    ("SKILL.md", "references/render_page.py"),
    ("SKILL.md", "example-content.json"),
    # recap gates
    ("references/recap.md", "The recap prompt (Alex's wording"),
    ("references/recap.md", "voice_check.py"),
    ("references/recap.md", "exclusion screen applies"),
    ("references/recap.md", "docs-reviewer"),
    ("references/recap.md", "Never link an unpublished doc"),
    # brought documents gates
    ("references/brought-docs.md", "Content screen"),
    ("references/brought-docs.md", "Sharing-scope gate"),
    ("references/brought-docs.md", "An Accepted ADR is never edited"),
    # write shapes safety
    ("references/write-shapes.md", "Never change permissions"),
    ("references/write-shapes.md", "Append-only"),
]


@pytest.mark.parametrize(("name", "phrase"), INVARIANTS, ids=[f"{n}::{p[:24]}" for n, p in INVARIANTS])
def test_invariant_present(name: str, phrase: str) -> None:
    text = read(name)
    assert phrase in text, f"{name} lost the invariant {phrase!r}"


def test_frontmatter_still_names_the_skill() -> None:
    text = read("SKILL.md")
    assert re.match(r"^---\n.*?name: ea-projects-curator\n.*?\n---\n", text, re.S), "frontmatter name changed"


def test_renderer_hex_literals_live_only_in_the_palette() -> None:
    """A bare hex in a builder is drift; every colour is a named constant."""
    src = RENDERER.read_text(encoding="utf-8")
    body = src.split("# --- validation", 1)[1]
    offenders = [
        f"line {i + 1}: {ln.strip()}"
        for i, ln in enumerate(body.splitlines())
        if re.search(r"#[0-9A-Fa-f]{6}", ln)
    ]
    assert not offenders, "bare hex outside the palette block: " + "; ".join(offenders)


def test_renderer_example_renders_and_validates(tmp_path: Path) -> None:
    canvas = tmp_path / "canvas.json"
    run = subprocess.run(
        [sys.executable, str(RENDERER), str(EXAMPLE), str(canvas)],
        capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, f"example-content.json no longer renders:\n{run.stderr}"
    check = subprocess.run(
        [sys.executable, str(RENDERER), "--check-only", str(canvas)],
        capture_output=True, text=True, check=False,
    )
    assert check.returncode == 0, f"--check-only rejected the rendered canvas:\n{check.stderr}"
    text = subprocess.run(
        [sys.executable, str(RENDERER), "--text", str(canvas)],
        capture_output=True, text=True, check=False,
    )
    assert text.returncode == 0 and "What Enterprise Architecture shipped" in text.stdout, \
        "--text no longer returns the rendered page text"


def test_every_prose_file_is_non_empty() -> None:
    for name, path in PROSE.items():
        assert path.exists(), f"{name} is missing"
        assert len(path.read_text(encoding="utf-8").split()) > 200, f"{name} looks gutted"
