"""The org and the project list are resolved, not memorized."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_ado.py"
spec = importlib.util.spec_from_file_location("resolve_ado", SCRIPT)
resolve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolve)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


def test_org_comes_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_ORG", "example-org")
    assert resolve.org() == "example-org"


def test_org_falls_back_to_az_config(monkeypatch) -> None:
    monkeypatch.delenv("AZURE_DEVOPS_ORG", raising=False)
    monkeypatch.setattr(
        resolve.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a[0], 0, stdout="organization = https://dev.azure.com/example-org\n", stderr=""
        ),
    )
    monkeypatch.setattr(resolve, "CONFIG", Path("/nonexistent/ado.json"))
    assert resolve.org() == "example-org"


def test_org_error_lists_every_fix(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AZURE_DEVOPS_ORG", raising=False)

    def no_az(*args, **kwargs):
        raise OSError("no az")

    monkeypatch.setattr(resolve.subprocess, "run", no_az)
    monkeypatch.setattr(resolve, "CONFIG", tmp_path / "absent.json")
    with pytest.raises(SystemExit) as failure:
        resolve.org()
    message = str(failure.value)
    assert "AZURE_DEVOPS_ORG" in message and "az devops configure" in message


def test_projects_come_from_the_api_with_pat_auth() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get("Authorization")
        return FakeResponse({"value": [{"name": "Project One", "state": "wellFormed"}]})

    rows = resolve.projects("example-org", "token-123", open_url=opener)
    assert rows == [{"name": "Project One", "state": "wellFormed"}]
    assert "example-org/_apis/projects" in captured["url"]
    assert captured["auth"].startswith("Basic ")


def test_missing_pat_says_what_to_set(monkeypatch) -> None:
    monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
    with pytest.raises(SystemExit, match="AZURE_DEVOPS_PAT"):
        resolve.pat()
