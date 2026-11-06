import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import evidence_dates
import evidence_links


def test_set_frontmatter_inserts_and_replaces():
    text = "---\ntitle: Example\n---\n\nBody\n"
    new, ok = evidence_dates.set_frontmatter(
        text, {"date": "2026-01-02", "date_precision": "day", "date_source": "body"}
    )
    assert ok is True
    assert "date: 2026-01-02" in new
    assert new.endswith("\n\nBody\n")

    replaced, ok = evidence_dates.set_frontmatter(new, {"date": "2026-02-03"})
    assert ok is True
    assert "date: 2026-02-03" in replaced
    assert "date: 2026-01-02" not in replaced


def test_set_related_merges_and_is_idempotent():
    text = '---\ntitle: Example\nrelated:\n  - "[[Bard/Old]]"\n---\n\nBody\n'
    first, ok = evidence_links.set_related(text, ["Bard/New"])
    assert ok is True
    assert "[[Bard/Old]]" in first
    assert "[[Bard/New]]" in first
    second, ok = evidence_links.set_related(first, ["Bard/New"])
    assert ok is True
    assert first == second


def test_hub_mapping_is_resolved():
    assert evidence_links.hub_link({"topic": "Security & Identity"}) == "Bard/Security & Identity"
    assert evidence_links.hub_link({"topic": "Org & Strategy"}) is None
    assert evidence_links.hub_link({"topic": None}) is None
