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
    "references/ado-ea-portfolio-schema.md": SKILL_DIR / "references" / "ado-ea-portfolio-schema.md",
    "references/connections-pass.md": SKILL_DIR / "references" / "connections-pass.md",
    "references/board-schema.md": SKILL_DIR / "references" / "board-schema.md",
    "references/retrieval.md": SKILL_DIR / "references" / "retrieval.md",
    "references/newsletter.md": SKILL_DIR / "references" / "newsletter.md",
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
    ("SKILL.md", "1. Exploring"),
    ("SKILL.md", "2. Committed"),
    ("SKILL.md", "3. Delivering"),
    ("SKILL.md", "4. Delivered"),
    ("SKILL.md", "5. Stopped"),
    ("SKILL.md", "Board to AAB flow"),
    ("SKILL.md", "Never write or `$select` them"),
    ("SKILL.md", "AABItems"),
    ("SKILL.md", "portfolio_moves"),
    ("SKILL.md", "Delivered"),
    ("SKILL.md", "Stopped: <why>"),
    ("SKILL.md", "EARole"),
    ("SKILL.md", "Influences"),
    ("SKILL.md", "Security Hardening"),
    ("SKILL.md", "Platform Foundations"),
    ("SKILL.md", "Governance"),
    ("SKILL.md", "Business Initiatives"),
    ("SKILL.md", "Advisory Board"),
    # Connections pass (Alex, 2026-10-12): bounded creativity after the review tables
    ("SKILL.md", "Connections pass"),
    ("SKILL.md", "`I#`"),
    ("SKILL.md", "`advisor` tool"),
    ("SKILL.md", "at least two pieces of evidence from this run"),
    ("SKILL.md", "it never writes"),
    ("SKILL.md", "Act, Park or Drop"),
    ("SKILL.md", "`ideas`"),
    ("references/connections-pass.md", "at least two pieces of evidence from this run"),
    ("references/connections-pass.md", "no cap"),
    ("references/connections-pass.md", "The advisor is a reviewer, not a source."),
    ("references/connections-pass.md", "never writes an idea"),
    # exclusion screen gates
    ("SKILL.md", "Privileged / counsel-touched"),
    ("SKILL.md", "Vendor-sensitive naming"),
    ("SKILL.md", "Scope-claiming"),
    ("SKILL.md", "HR / personnel"),
    # review gate shape
    ("SKILL.md", "split by surface, never one merged list"),
    # decisions-first review (Alex, 2026-10-12)
    ("SKILL.md", "### 1. Needs you"),
    ("SKILL.md", "### 2. Check the words"),
    ("SKILL.md", "### 3. Routine"),
    ("SKILL.md", "No markdown tables anywhere in it"),
    ("SKILL.md", "Wrap every line at 100 characters"),
    ("SKILL.md", "the Answer line lists every Needs-you ID once"),
    ("SKILL.md", "A line he did not answer is not written"),
    ("SKILL.md", "every Stage (`Status`) move and every `System.State` move, each on its own line"),
    ("references/connections-pass.md", "Answer: act / park / drop"),
    ("SKILL.md", "A1, A2, ..."),
    ("SKILL.md", "D1, D2, ..."),
    ("SKILL.md", "E1, E2, ..."),
    ("SKILL.md", "W1, W2, ..."),
    # where EA work lives and the ADO control (decided 2026-10-09)
    ("SKILL.md", "Every epic in an EA area rolls up to exactly one EA Projects row"),
    ("SKILL.md", "Weekly epic update, on every active epic, every week"),
    ("SKILL.md", "Never move `System.State` on an item assigned to someone else"),
    ("SKILL.md", "ADO WEEKLY CONTROL"),
    ("SKILL.md", "evidence decides each week"),
    ("SKILL.md", "Progress number"),
    ("SKILL.md", "The number passes the exclusion screen first"),
    ("SKILL.md", "with the unit written once, right after X"),
    ("SKILL.md", "EA operations"),
    ("SKILL.md", "Planned absence"),
    ("SKILL.md", "Readership"),
    ("references/ado-ea-portfolio-schema.md", "is **never** derived from ADO"),
    ("references/ado-ea-portfolio-schema.md", "reporting change is official"),
    ("references/write-shapes.md", "validateOnly=true"),
    ("references/write-shapes.md", "No @-mentions"),
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
    ("references/retrieval.md", "fe9c1f44-8a0c-4f68-b0b1-bf8741eed4fd"),
    # moved out of SKILL.md 2026-10-12: SKILL.md must keep pointing at each reference
    ("SKILL.md", "references/board-schema.md"),
    ("SKILL.md", "references/retrieval.md"),
    ("SKILL.md", "references/newsletter.md"),
    ("SKILL.md", "never a saved query for the"),
    ("references/board-schema.md", "Never write or `$select` them"),
    ("references/board-schema.md", "never to all of them by default"),
    ("references/retrieval.md", "Auth preflight FIRST"),
    ("references/retrieval.md", "never a saved query"),
    ("references/newsletter.md", "OAuth only flow is enabled"),
    ("references/newsletter.md", "Never judge this page in edit mode"),
    ("references/newsletter.md", "Composition rule: the summary is a roll-up, nothing new"),
    ("references/newsletter.md", "moves_baseline"),
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
