#!/usr/bin/env python3
"""Resolve the Azure DevOps org and its live projects at run time.

A skill that memorizes an org name and a project list works for one person and lies for
everyone else. This resolves both:

    python3 scripts/resolve_ado.py org        # prints the org name
    python3 scripts/resolve_ado.py projects   # prints the org's well-formed projects as JSON

Org, in this order:
  1. `$AZURE_DEVOPS_ORG`
  2. `az devops configure -l` (`organization = https://dev.azure.com/<org>`)
  3. `org` in `~/.config/ado-ticket-writer.json`
  4. stop, with the three fixes named

Projects always come from the API, never from a list in the prose. Whether a project accepts
new work is a human decision the run asks for, not something the API can answer.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

CONFIG = Path(os.environ.get("ADO_CONFIG", Path.home() / ".config" / "ado-ticket-writer.json"))
API_VERSION = "7.1"


def org() -> str:
    from_env = os.environ.get("AZURE_DEVOPS_ORG", "").strip()
    if from_env:
        return from_env

    try:
        completed = subprocess.run(
            ["az", "devops", "configure", "-l"], capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        completed = None
    if completed and completed.returncode == 0:
        for line in completed.stdout.splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "organization" and value.strip():
                return value.strip().rstrip("/").rsplit("/", 1)[-1]

    if CONFIG.exists():
        try:
            configured = json.loads(CONFIG.read_text()).get("org", "")
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"{CONFIG} is not readable JSON: {error}")
        if configured:
            return str(configured).strip()

    raise SystemExit(
        "No Azure DevOps org. Set AZURE_DEVOPS_ORG, run `az devops configure -d organization="
        "https://dev.azure.com/<org>`, or add {\"org\": \"<org>\"} to " + str(CONFIG)
    )


def pat() -> str:
    token = os.environ.get("AZURE_DEVOPS_PAT", "").strip()
    if not token:
        raise SystemExit("Set AZURE_DEVOPS_PAT to a token with vso.work (and vso.work_write to change items)")
    return token


def projects(org_name: str, token: str, open_url=urllib.request.urlopen) -> list[dict]:
    """The org's well-formed projects, straight from the API."""
    request = urllib.request.Request(
        f"https://dev.azure.com/{org_name}/_apis/projects"
        f"?stateFilter=wellFormed&api-version={API_VERSION}"
    )
    credentials = base64.b64encode(f":{token}".encode()).decode()
    request.add_header("Authorization", f"Basic {credentials}")
    request.add_header("Accept", "application/json")
    with open_url(request, timeout=30) as response:
        payload = json.loads(response.read())
    return [
        {"name": item.get("name", ""), "state": item.get("state", "")}
        for item in payload.get("value", [])
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve the ADO org and its live projects.")
    parser.add_argument("what", choices=("org", "projects"))
    args = parser.parse_args(argv)

    if args.what == "org":
        print(org())
        return 0

    print(json.dumps(projects(org(), pat()), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
