#!/usr/bin/env python3
"""Resolve the SharePoint site and the list ids this skill writes to.

Nothing here is memorized. The identity comes from the environment or one config file, and
every id comes from the API at run time, because an id in a document goes stale the day a
list is rebuilt and a copied id is worse than no id.

    python3 scripts/sharepoint/resolve.py                    # the two lists this skill uses
    python3 scripts/sharepoint/resolve.py --list "Other"     # any list by title
    python3 scripts/sharepoint/resolve.py --views "Current bets" --views "Track record"

List and view ids are resolved by title, never copied: a rebuilt list or view gets a new id,
and a copied id fails with a 404 that reads like a permissions problem.

Site URL, in this order:
  1. `$SHAREPOINT_SITE_URL`
  2. `site_url` in `~/.config/ea-projects-curator.json`
  3. stop, with the two fixes named

List ids are looked up by title on that site and printed as JSON, so a run can pass them on
without ever writing one down.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import sharepoint_api as sp  # noqa: E402  (path set above)

CONFIG = Path(os.environ.get("EA_CURATOR_CONFIG", Path.home() / ".config" / "ea-projects-curator.json"))
DEFAULT_LISTS = ("EA Portfolio", "AAB Intake")


def site_url() -> str:
    from_env = os.environ.get("SHAREPOINT_SITE_URL", "").strip().rstrip("/")
    if from_env:
        return from_env
    if CONFIG.exists():
        try:
            configured = json.loads(CONFIG.read_text()).get("site_url", "")
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"{CONFIG} is not readable JSON: {error}")
        if configured:
            return str(configured).strip().rstrip("/")
    raise SystemExit(
        "No SharePoint site. Set SHAREPOINT_SITE_URL, or add "
        '{"site_url": "https://<tenant>.sharepoint.com/sites/<site>"} to ' + str(CONFIG)
    )


def list_id(session, site: str, title: str) -> dict:
    """One list's id and title, looked up by title. Raises when the title is absent."""
    query = f"{site}/_api/web/lists?$filter=Title eq '{title.replace(chr(39), chr(39) * 2)}'&$select=Id,Title"
    response = session.get(query)
    response.raise_for_status()
    rows = response.json().get("d", {}).get("results", [])
    if not rows:
        raise SystemExit(f"No list titled {title!r} on {site}. Check the title, then retry.")
    return {"id": rows[0]["Id"], "title": rows[0]["Title"]}


def view_ids(session, site: str, list_guid: str, titles: tuple[str, ...]) -> dict:
    """View ids by title, for the list whose id was just resolved."""
    response = session.get(f"{site}/_api/web/lists(guid'{list_guid}')/views?$select=Id,Title")
    response.raise_for_status()
    by_title = {row["Title"]: row["Id"] for row in response.json().get("d", {}).get("results", [])}
    missing = [title for title in titles if title not in by_title]
    if missing:
        raise SystemExit(f"No view titled {missing} on list {list_guid}. Views get renamed too.")
    return {title: by_title[title] for title in titles}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve the SharePoint site, list and view ids.")
    parser.add_argument("--list", action="append", dest="lists", help="list title; repeat as needed")
    parser.add_argument("--views", action="append", default=[], help="view titles, on the first list")
    args = parser.parse_args(argv)

    site = site_url()
    session = sp.make_session()
    wanted = tuple(args.lists) if args.lists else DEFAULT_LISTS
    resolved = {title: list_id(session, site, title) for title in wanted}

    payload = {"site_url": site, "lists": resolved}
    if args.views:
        first = resolved[wanted[0]]["id"]
        payload["views"] = view_ids(session, site, first, tuple(args.views))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
