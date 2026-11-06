import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evidence_catalog.py"
spec = importlib.util.spec_from_file_location("evidence_catalog", SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_vault(root: Path) -> Path:
    vault = root / "vault"
    e = vault / "Evidence"
    write(
        e / "Plans-Proposals" / "plan-codeql.md",
        """---
doc_type: plan
topic: "Security & Identity"
sensitivity: internal
---
# CodeQL · Plan

Created 2026-10-14. Make CodeQL useful: less noise, org-aware rules, an owner for every alert, a PR gate that stops the backlog from growing.
""",
    )
    write(
        e / "Sources" / "Architecture" / "Files" / "plan-codeql.md",
        """---
doc_type: plan
topic: "Security & Identity"
sensitivity: internal
---
# CodeQL mirror

A mirror copy.
""",
    )
    write(
        e / "Sources" / "Developer" / "itcc" / "_digest.md",
        """---
title: "itcc — digest"
type: developer-digest
source: "/Users/does-not-exist/Developer/itcc"
archived: 2026-10-28
---
# itcc

3 documents kept.
""",
    )
    write(
        e / "Sources" / "Developer" / "itcc" / "_originals" / "raw.md",
        "# raw\n\nThis must be excluded.\n",
    )
    write(e / "README.md", "# README\n\nNavigation only.\n")
    write(
        e / "Confidential" / "secret.md",
        """---
title: "Secret note"
doc_type: note
topic: "Security & Identity"
sensitivity: confidential
---
# Secret note

SECRET BODY MUST NOT BE USED.
""",
    )
    write(
        e / "ADRs" / "ADR-0001.md",
        """---
doc_type: adr
topic: "Security & Identity"
sensitivity: internal
title: "ADR-0001"
---
# ADR-0001

Date Proposed May 2025.
""",
    )
    write(
        e / "Templates" / "template.md",
        """---
doc_type: template
topic: "Delivery & Docs"
sensitivity: internal
title: "Template"
---
# Template

A blank template.
""",
    )
    return vault


def test_rows_flags_and_dates(tmp_path):
    vault = make_vault(tmp_path)
    rows, meta = catalog.collect_rows(vault)
    assert meta["row_count"] == 6
    by_path = {row["path"]: row for row in rows}
    assert "README.md" not in by_path
    assert not any("_originals" in path for path in by_path)

    plan = by_path["Plans-Proposals/plan-codeql.md"]
    assert plan["canonical"] is True
    assert plan["date"] == "2026-10-14"
    assert plan["date_source"] == "body"

    mirror = by_path["Sources/Architecture/Files/plan-codeql.md"]
    assert mirror["canonical"] is False
    assert mirror["duplicate_of"] == "Plans-Proposals/plan-codeql.md"

    digest = by_path["Sources/Developer/itcc/_digest.md"]
    assert digest["doc_type"] == "digest"
    assert digest["source_status"] == "missing"

    adr = by_path["ADRs/ADR-0001.md"]
    assert adr["date"] == "2025-05"
    assert adr["date_precision"] == "month"

    secret = by_path["Confidential/secret.md"]
    assert secret["sensitivity"] == "confidential"
    assert "SECRET BODY" not in secret["summary"]

    template = by_path["Templates/template.md"]
    assert template["date"] is None
    assert template["date_source"] == "none"


def test_build_is_idempotent_and_check_passes(tmp_path):
    vault = make_vault(tmp_path)
    assert catalog.build(vault) == 0
    first = (vault / "Evidence" / "catalog.jsonl").read_bytes()
    assert catalog.build(vault) == 0
    second = (vault / "Evidence" / "catalog.jsonl").read_bytes()
    assert first == second
    assert catalog.check(vault) == 0


def test_catalog_md_has_rows(tmp_path):
    vault = make_vault(tmp_path)
    assert catalog.build(vault) == 0
    text = (vault / "Evidence" / "CATALOG.md").read_text()
    assert "6 documents" in text
    assert "Developer digests" in text
    assert "ADR-0001" in text
