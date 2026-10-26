"""Tests for the cookie cache: everything that runs before a browser is involved.

The browser half needs Playwright and a human login, so it is not covered here. Everything
that decides whether a cached cookie is reused, where it is stored, and what reaches stdout
is.
"""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cookie_auth.py"
spec = importlib.util.spec_from_file_location("cookie_auth", SCRIPT)
cookie_auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cookie_auth)

SITE = "https://example.internal/sites/team"
COOKIES = {
    "FedAuth": {"value": "secret-a", "domain": "example.internal", "path": "/"},
    "rtFa": {"value": "secret-b", "domain": "example.internal", "path": "/"},
}


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BROWSER_COOKIE_AUTH_HOME", str(tmp_path / "cache"))


def test_cache_round_trip() -> None:
    cookie_auth.save_cookies("sharepoint", SITE, COOKIES)
    cached = cookie_auth.get_cached_cookies("sharepoint", SITE)
    assert cached is not None
    assert cached["FedAuth"]["value"] == "secret-a"


def test_cache_file_and_directory_are_private() -> None:
    path = cookie_auth.save_cookies("sharepoint", SITE, COOKIES)
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert oct(path.parent.stat().st_mode & 0o777) == "0o700"


def test_expired_cache_is_ignored() -> None:
    path = cookie_auth.cache_file("sharepoint")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"url": SITE, "timestamp": time.time() - 10 * 3600, "cookies": COOKIES})
    )
    assert cookie_auth.get_cached_cookies("sharepoint", SITE, ttl_hours=1) is None


def test_another_url_is_ignored() -> None:
    cookie_auth.save_cookies("sharepoint", "https://other.internal/", COOKIES)
    assert cookie_auth.get_cached_cookies("sharepoint", SITE) is None


def test_incomplete_cookie_set_is_ignored() -> None:
    cookie_auth.save_cookies("sharepoint", SITE, {"FedAuth": COOKIES["FedAuth"]})
    assert cookie_auth.get_cached_cookies("sharepoint", SITE, ("FedAuth", "rtFa")) is None


def test_corrupt_cache_is_ignored() -> None:
    path = cookie_auth.cache_file("sharepoint")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json")
    assert cookie_auth.get_cached_cookies("sharepoint", SITE) is None


def test_separate_services_do_not_collide() -> None:
    cookie_auth.save_cookies("wiki", SITE, COOKIES)
    assert cookie_auth.get_cached_cookies("sharepoint", SITE) is None
    assert cookie_auth.get_cached_cookies("wiki", SITE) is not None


def test_slug_cannot_escape_the_cache_directory() -> None:
    path = cookie_auth.cache_file("../../etc/passwd")
    root = Path(cookie_auth._root()).resolve()
    assert path.resolve().parent == root
    with pytest.raises(ValueError):
        cookie_auth._slug("!!!")


def test_cli_never_prints_cookie_values(capsys) -> None:
    cookie_auth.save_cookies("sharepoint", SITE, COOKIES)
    assert cookie_auth.main(["sharepoint", SITE]) == 0
    out = capsys.readouterr().out
    assert "FedAuth" in out
    assert "secret-a" not in out and "secret-b" not in out


def test_make_session_carries_the_cached_cookies() -> None:
    pytest.importorskip("requests")
    cookie_auth.save_cookies("sharepoint", SITE, COOKIES)
    session = cookie_auth.make_session("sharepoint", SITE)
    assert session.cookies.get("FedAuth") == "secret-a"
