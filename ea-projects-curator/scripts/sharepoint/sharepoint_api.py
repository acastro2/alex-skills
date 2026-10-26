#!/usr/bin/env python3
"""
SharePoint REST API helper for site pages.

Handles request digest, cookie auth, and common page operations.
Usage: python3 sharepoint_api.py <command> [args...]
"""

import json
import sys
import os
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

# Suppress SSL warnings from corporate proxy
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRIPT_DIR = Path(__file__).parent
SITE_URL = os.environ.get("SHAREPOINT_SITE_URL", "").rstrip("/")


def load_cookies() -> dict:
    """Load cookies from cache file."""
    cache = SCRIPT_DIR / ".cookies.json"
    if not cache.exists():
        print("ERROR: No cached cookies. Run auth.py first.", file=sys.stderr)
        sys.exit(1)
    data = json.loads(cache.read_text())
    return data.get("cookies", {})


def make_session() -> requests.Session:
    """Create a requests session with SharePoint cookies."""
    cookies = load_cookies()
    s = requests.Session()
    s.verify = False
    for name, info in cookies.items():
        if isinstance(info, dict):
            s.cookies.set(name, info["value"], domain=info.get("domain", ""), path=info.get("path", "/"))
        else:
            s.cookies.set(name, info)
    s.headers.update({
        "Accept": "application/json;odata=verbose",
    })
    return s


def get_request_digest(session: requests.Session, site_url: str) -> str:
    """Fetch the X-RequestDigest needed for write operations."""
    r = session.post(f"{site_url}/_api/contextinfo")
    r.raise_for_status()
    return r.json()["d"]["GetContextWebInformation"]["FormDigestValue"]


def list_pages(site_url: str, top: int = 20):
    """List site pages."""
    s = make_session()
    r = s.get(f"{site_url}/_api/sitepages/pages?$top={top}&$orderby=Modified desc")
    r.raise_for_status()
    pages = r.json().get("d", {}).get("results", [])
    result = []
    for p in pages:
        result.append({
            "id": p.get("Id"),
            "title": p.get("Title"),
            "name": p.get("FileName") or p.get("Name"),
            "url": p.get("AbsoluteUrl") or p.get("Url"),
            "modified": p.get("Modified"),
            "author": p.get("AuthorByline"),
            "promotedState": p.get("PromotedState"),
        })
    return result


def get_page(site_url: str, page_id: int):
    """Get a specific page by ID."""
    s = make_session()
    r = s.get(f"{site_url}/_api/sitepages/pages({page_id})")
    r.raise_for_status()
    return r.json().get("d", {})


def create_page(site_url: str, title: str, layout: str = "Article"):
    """Create a new modern site page."""
    s = make_session()
    digest = get_request_digest(s, site_url)
    s.headers.update({
        "Content-Type": "application/json;odata=verbose",
        "X-RequestDigest": digest,
    })

    payload = {
        "__metadata": {"type": "SP.Publishing.SitePage"},
        "Title": title,
        "PageLayoutType": layout,
        "PromotedState": 0,
    }

    r = s.post(f"{site_url}/_api/sitepages/pages", json=payload)
    r.raise_for_status()
    return r.json().get("d", {})


def api_path(server_relative: str) -> str:
    """Encode URL characters and escape apostrophes inside an OData literal."""
    return quote(server_relative, safe="/'").replace("'", "''")


def save_page(session, site_url: str, page_id: int, fields: dict) -> str:
    """Save a checked-out draft, preserving content not included in fields."""
    r = session.get(f"{site_url}/_api/sitepages/pages({page_id})")
    r.raise_for_status()
    page = r.json()["d"]
    path = urlparse(page["Url"]).path
    if not path.startswith("/"):
        path = f"{urlparse(site_url).path.rstrip('/')}/{path}"

    digest = get_request_digest(session, site_url)
    session.headers.update({
        "Content-Type": "application/json;odata=verbose",
        "X-RequestDigest": digest,
    })
    if not page.get("IsPageCheckedOutToCurrentUser"):
        r = session.post(f"{site_url}/_api/web/getfilebyserverrelativeurl('{api_path(path)}')/checkout")
        r.raise_for_status()
    payload = {
        "__metadata": {"type": "SP.Publishing.SitePage"},
        **{key: page[key] for key in ("Title", "CanvasContent1", "LayoutWebpartsContent") if key in page},
        **fields,
    }
    r = session.post(f"{site_url}/_api/sitepages/pages({page_id})/savepage", json=payload)
    r.raise_for_status()
    return path


def update_page_content(site_url: str, page_id: int, canvas_content: str):
    """Save canvas content as a draft without publishing."""
    if not isinstance(json.loads(canvas_content), list):
        raise ValueError("CanvasContent1 must be a JSON array")
    save_page(make_session(), site_url, page_id, {"CanvasContent1": canvas_content})
    return {"success": True, "pageId": page_id, "published": False}


def update_page_title(site_url: str, page_id: int, title: str):
    """Save a title change as a draft without publishing."""
    save_page(make_session(), site_url, page_id, {"Title": title})
    return {"success": True, "pageId": page_id, "published": False}


def upload_asset(site_url: str, local_path: str, target_name: str = None,
                 folder: str = "SiteAssets", overwrite: bool = False):
    """Upload a local file into a library folder and return its server-relative URL."""
    source = Path(local_path)
    if not source.is_file():
        raise ValueError(f"Not a file: {local_path}")
    name = target_name or source.name
    folder_path = f"{urlparse(site_url).path.rstrip('/')}/{folder.strip('/')}"
    s = make_session()
    files_url = f"{site_url}/_api/web/getfolderbyserverrelativeurl('{api_path(folder_path)}')/files"
    r = s.get(f"{files_url}?$select=Name&$filter=Name eq '{api_path(name)}'")
    r.raise_for_status()
    if r.json()["d"]["results"] and not overwrite:
        # SharePoint keeps serving cached bytes when a name is reused, so a new name is the
        # only reliable way to replace an image on a page.
        raise ValueError(f"{name} already exists in {folder_path}; pass --overwrite to replace it")
    digest = get_request_digest(s, site_url)
    s.headers.update({"X-RequestDigest": digest, "Content-Type": "application/octet-stream"})
    r = s.post(f"{files_url}/add(overwrite=true,url='{api_path(name)}')", data=source.read_bytes())
    r.raise_for_status()
    uploaded = r.json()["d"]
    return {
        "success": True,
        "name": uploaded.get("Name"),
        "serverRelativeUrl": uploaded.get("ServerRelativeUrl"),
        "length": uploaded.get("Length"),
    }


def upload_asset_args(site_url: str, args: list):
    """Parse `upload-asset <local_path> [target_name] [--overwrite]`."""
    overwrite = "--overwrite" in args
    positional = [a for a in args if a != "--overwrite"]
    if not positional:
        raise IndexError("usage: upload-asset <local_path> [target_name] [--overwrite]")
    return upload_asset(
        site_url,
        positional[0],
        positional[1] if len(positional) > 1 else None,
        overwrite=overwrite,
    )


def delete_page(site_url: str, page_id: int):
    """Delete a page."""
    s = make_session()
    digest = get_request_digest(s, site_url)
    s.headers.update({
        "X-RequestDigest": digest,
        "X-HTTP-Method": "DELETE",
        "If-Match": "*",
    })

    r = s.post(f"{site_url}/_api/sitepages/pages({page_id})")
    r.raise_for_status()
    return {"success": True, "pageId": page_id, "deleted": True}


# ─── List view operations ───────────────────────────────────────────────────


def list_views(site_url: str, list_title: str):
    """List all views for a SharePoint list."""
    s = make_session()
    r = s.get(f"{site_url}/_api/web/lists/getbytitle('{list_title}')/views")
    r.raise_for_status()
    views = r.json().get("d", {}).get("results", [])
    return [
        {
            "id": v.get("Id"),
            "title": v.get("Title"),
            "defaultView": v.get("DefaultView"),
            "rowLimit": v.get("RowLimit"),
            "viewQuery": v.get("ViewQuery"),
        }
        for v in views
    ]


def get_view(site_url: str, list_title: str, view_title: str):
    """Get a specific view including its ViewFields."""
    s = make_session()
    r = s.get(
        f"{site_url}/_api/web/lists/getbytitle('{list_title}')/views/getbytitle('{view_title}')"
    )
    r.raise_for_status()
    view = r.json().get("d", {})

    # Also fetch ViewFields
    r2 = s.get(
        f"{site_url}/_api/web/lists/getbytitle('{list_title}')/views/getbytitle('{view_title}')/viewfields"
    )
    r2.raise_for_status()
    fields = r2.json().get("d", {}).get("Items", {}).get("results", [])

    return {
        "id": view.get("Id"),
        "title": view.get("Title"),
        "viewQuery": view.get("ViewQuery"),
        "rowLimit": view.get("RowLimit"),
        "defaultView": view.get("DefaultView"),
        "viewFields": fields,
    }


def update_view_columns(site_url: str, list_title: str, view_title: str, columns: list[str]):
    """Set the visible columns and their order on a view.

    Removes all existing ViewFields, then adds the given columns in order.
    Column names should be internal field names.
    """
    s = make_session()
    digest = get_request_digest(s, site_url)
    s.headers.update({
        "X-RequestDigest": digest,
    })

    base = f"{site_url}/_api/web/lists/getbytitle('{list_title}')/views/getbytitle('{view_title}')/viewfields"

    # Remove all existing fields
    r = s.post(f"{base}/removeallviewfields")
    r.raise_for_status()

    # Add fields in order
    for col in columns:
        r = s.post(f"{base}/addviewfield('{col}')")
        r.raise_for_status()

    return {"success": True, "view": view_title, "columns": columns}


def update_view_query(site_url: str, list_title: str, view_title: str, caml_query: str):
    """Set the CAML ViewQuery (sort + filter) on a view.

    caml_query should be raw CAML XML, e.g.:
    <Where><Eq><FieldRef Name='Status'/><Value Type='Choice'>Parked</Value></Eq></Where>
    <OrderBy><FieldRef Name='Modified' Ascending='FALSE'/></OrderBy>
    """
    s = make_session()
    digest = get_request_digest(s, site_url)
    s.headers.update({
        "Content-Type": "application/json;odata=verbose",
        "X-RequestDigest": digest,
        "X-HTTP-Method": "MERGE",
        "If-Match": "*",
    })

    payload = {
        "__metadata": {"type": "SP.View"},
        "ViewQuery": caml_query,
    }

    r = s.post(
        f"{site_url}/_api/web/lists/getbytitle('{list_title}')/views/getbytitle('{view_title}')",
        json=payload,
    )
    r.raise_for_status()
    return {"success": True, "view": view_title, "viewQuery": caml_query}


def list_fields(site_url: str, list_title: str):
    """List all fields on a list (useful for finding internal names)."""
    s = make_session()
    r = s.get(
        f"{site_url}/_api/web/lists/getbytitle('{list_title}')/fields"
        "?$filter=Hidden eq false and ReadOnlyField eq false"
        "&$select=Title,InternalName,TypeAsString"
    )
    r.raise_for_status()
    fields = r.json().get("d", {}).get("results", [])
    return [
        {
            "title": f.get("Title"),
            "internalName": f.get("InternalName"),
            "type": f.get("TypeAsString"),
        }
        for f in fields
    ]


COMMANDS = {
    "list": lambda args: list_pages(SITE_URL, int(args[0]) if args else 20),
    "get": lambda args: get_page(SITE_URL, int(args[0])),
    "create": lambda args: create_page(SITE_URL, args[0], args[1] if len(args) > 1 else "Article"),
    "update-content": lambda args: update_page_content(SITE_URL, int(args[0]), args[1]),
    "update-title": lambda args: update_page_title(SITE_URL, int(args[0]), args[1]),
    "delete": lambda args: delete_page(SITE_URL, int(args[0])),
    "upload-asset": lambda args: upload_asset_args(SITE_URL, args),
    # List view commands
    "list-views": lambda args: list_views(SITE_URL, args[0]),
    "get-view": lambda args: get_view(SITE_URL, args[0], args[1]),
    "update-view-columns": lambda args: update_view_columns(SITE_URL, args[0], args[1], json.loads(args[2])),
    "update-view-query": lambda args: update_view_query(SITE_URL, args[0], args[1], args[2]),
    "list-fields": lambda args: list_fields(SITE_URL, args[0]),
}


if __name__ == "__main__":
    if not SITE_URL:
        print("ERROR: Set SHAREPOINT_SITE_URL environment variable", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: SHAREPOINT_SITE_URL=... python3 sharepoint_api.py <command> [args...]", file=sys.stderr)
        print(f"Commands: {', '.join(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    try:
        result = COMMANDS[cmd](args)
        print(json.dumps(result, indent=2, default=str))
    except requests.exceptions.HTTPError as e:
        print(json.dumps({
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "body": e.response.text[:500] if e.response is not None else None,
        }, indent=2), file=sys.stderr)
        sys.exit(1)
    except (ValueError, IndexError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
