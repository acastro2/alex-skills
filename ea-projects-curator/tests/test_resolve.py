"""Resolver tests: identity comes from the environment, ids come from the API.

Both resolvers are the reason these skills are portable, so each source order gets a test and
each failure names what to fix.
"""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

import pytest

SHAREPOINT = Path(__file__).resolve().parents[1] / "scripts" / "sharepoint"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SHAREPOINT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode()

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return json.loads(self._body)


class FakeSession:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.urls: list[str] = []

    def get(self, url: str) -> FakeResponse:
        self.urls.append(url)
        return FakeResponse(self.payload)


def test_site_url_comes_from_the_environment(monkeypatch) -> None:
    resolve = load("resolve")
    monkeypatch.setenv("SHAREPOINT_SITE_URL", "https://example.sharepoint.com/sites/Architecture/")
    assert resolve.site_url() == "https://example.sharepoint.com/sites/Architecture"


def test_site_url_falls_back_to_the_config_file(tmp_path, monkeypatch) -> None:
    resolve = load("resolve")
    config = tmp_path / "curator.json"
    config.write_text(json.dumps({"site_url": "https://example.sharepoint.com/sites/X"}))
    monkeypatch.delenv("SHAREPOINT_SITE_URL", raising=False)
    monkeypatch.setattr(resolve, "CONFIG", config)
    assert resolve.site_url() == "https://example.sharepoint.com/sites/X"


def test_site_url_error_names_both_fixes(tmp_path, monkeypatch) -> None:
    resolve = load("resolve")
    monkeypatch.delenv("SHAREPOINT_SITE_URL", raising=False)
    monkeypatch.setattr(resolve, "CONFIG", tmp_path / "absent.json")
    with pytest.raises(SystemExit) as failure:
        resolve.site_url()
    assert "SHAREPOINT_SITE_URL" in str(failure.value)


def test_list_id_is_looked_up_by_title() -> None:
    resolve = load("resolve")
    session = FakeSession({"d": {"results": [{"Id": "abc-123", "Title": "EA Portfolio"}]}})
    resolved = resolve.list_id(session, "https://example.sharepoint.com/sites/X", "EA Portfolio")
    assert resolved == {"id": "abc-123", "title": "EA Portfolio"}
    assert "$filter=Title eq 'EA Portfolio'" in session.urls[0]


def test_a_missing_list_names_the_title() -> None:
    resolve = load("resolve")
    session = FakeSession({"d": {"results": []}})
    with pytest.raises(SystemExit, match="No list titled"):
        resolve.list_id(session, "https://example.sharepoint.com/sites/X", "Ghost")


def test_cookie_cache_is_shared_with_auth() -> None:
    """The port moved the cache out of the checkout; both modules must agree on where."""
    auth = load("auth")
    source = (SHAREPOINT / "sharepoint_api.py").read_text()
    assert "from auth import COOKIE_CACHE" in source, "sharepoint_api must import the path, not copy it"
    assert auth.COOKIE_CACHE.is_absolute()
    assert str(Path.home()) in str(auth.COOKIE_CACHE)


class ViewSession(FakeSession):
    def get(self, url: str) -> FakeResponse:
        self.urls.append(url)
        if "/views?" in url:
            return FakeResponse({"d": {"results": [
                {"Id": "view-1", "Title": "Current bets"},
                {"Id": "view-2", "Title": "Track record"},
            ]}})
        return FakeResponse(self.payload)


def test_view_ids_are_resolved_by_title() -> None:
    resolve = load("resolve")
    session = ViewSession({"d": {"results": []}})
    ids = resolve.view_ids(session, "https://example.sharepoint.com/sites/X", "abc", ("Track record",))
    assert ids == {"Track record": "view-2"}


def test_a_renamed_view_is_named_in_the_error() -> None:
    resolve = load("resolve")
    session = ViewSession({"d": {"results": []}})
    with pytest.raises(SystemExit, match="No view titled"):
        resolve.view_ids(session, "https://example.sharepoint.com/sites/X", "abc", ("Gone",))
