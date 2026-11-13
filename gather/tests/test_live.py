"""Opt-in live check: real `claude -p` against Teams. Costs about USD 0.02 per call.

Run with GATHER_LIVE=1. Read-only: the run allows one search tool and get_me.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gather.py"

pytestmark = pytest.mark.skipif(os.environ.get("GATHER_LIVE") != "1", reason="set GATHER_LIVE=1 to run live")


def test_teams_mine_seven_days_live_writes_raw_and_leaves_no_session(tmp_path):
    root = tmp_path / "store"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "run", "--sources", "teams_mine", "--since", "7d", "--root", str(root)],
        capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    raws = sorted((root / "raw" / "teams_mine").rglob("*.json"))
    assert raws, "no raw file written"
    assert any(json.loads(p.read_text())["content"] for p in raws), "every raw content is empty"

    ledger = json.loads(next((root / "ledger").glob("*.json")).read_text())
    assert ledger["sources"]["teams_mine"].startswith("fetched")

    # claude -p ran with cwd <root>/run; no session may be saved for that cwd
    encoded = re.sub(r"[^A-Za-z0-9]", "-", str((root / "run").resolve()))
    assert not (Path.home() / ".claude" / "projects" / encoded).exists()
