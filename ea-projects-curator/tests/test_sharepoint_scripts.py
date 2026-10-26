"""Guards on the ported SharePoint helpers.

The scripts are the curator's own now, which means two things are worth pinning: the cookie
cache must never land in the checkout (this repo is public), and the offline regression
harness must stay offline.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SHAREPOINT = Path(__file__).resolve().parents[1] / "scripts" / "sharepoint"
REPO = Path(__file__).resolve().parents[2]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SHAREPOINT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cookie_cache_is_outside_the_repo() -> None:
    auth = load("auth")
    cache = auth.COOKIE_CACHE.resolve()
    assert REPO.resolve() not in cache.parents, f"cookie cache inside the repo: {cache}"
    assert cache.name == "cookies.json"


def test_saved_cookies_are_private(tmp_path, monkeypatch) -> None:
    auth = load("auth")
    monkeypatch.setattr(auth, "COOKIE_CACHE", tmp_path / "cookies.json")
    auth.save_cookies(
        "https://example.invalid/sites/team",
        {"FedAuth": {"value": "x", "domain": "example.invalid", "path": "/"},
         "rtFa": {"value": "y", "domain": "example.invalid", "path": "/"}},
    )
    assert oct(auth.COOKIE_CACHE.stat().st_mode & 0o777) == "0o600"


def test_ported_scripts_import_from_their_own_folder() -> None:
    """`stage_news_recap.py` does `import sharepoint_api`; both are in the same folder, so a
    run by path works without any path setup."""
    source = (SHAREPOINT / "stage_news_recap.py").read_text()
    assert "import sharepoint_api" in source
    assert (SHAREPOINT / "sharepoint_api.py").is_file()


def test_offline_harness_blocks_network() -> None:
    """`test_draft_only.py` claims the network and auth are blocked. That claim is the reason
    it is safe to run, so check it still names its blocks."""
    source = (SHAREPOINT / "test_draft_only.py").read_text()
    assert "Authentication and network connections are blocked" in source
