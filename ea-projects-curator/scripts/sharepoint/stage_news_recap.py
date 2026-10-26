#!/usr/bin/env python3
"""Stage a News draft. Alex publishes manually in SharePoint.

Canvas content is a separately generated JSON array: fill the content JSON, then run
`references/render_page.py <content.json> <canvas.json>`, from the skill root.
That script owns every tag, style and colour; see its docstring for the schema.

Use --dry-run to inspect the target without contacting SharePoint. Live writes verify
PromotedState and the title region.

The SharePoint title region is suppressed by default (`LayoutWebpartsContent =
[{"controlType":0}]`), because every Architecture Weekly page carries its title in the
navy band and the default region renders it a second time above the content. Verified
2026-09-18 against 2026-08-12-AAB-Recap.aspx, which stores exactly that value and shows
no title region. Pass --keep-title to opt out.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests
import sharepoint_api as sp


PRESETS = {
    "recap": {"folder": "Recaps", "slug": "AAB-Recap"},
    "ainews": {"folder": "AI Tech News", "slug": "AI-Tech-News"},
}
CSOM_CURRENT_TYPEID = "{3747adcd-a3c3-41b9-bfab-4a64dd2f1e0a}"


def mark_news_draft(session, site_url, item_id):
    # These fields silently ignore modern REST updates; use CSOM SystemUpdate.
    actions = (
        '<Method Name="SetFieldValue" Id="11" ObjectPathId="9"><Parameters>'
        '<Parameter Type="String">PromotedState</Parameter>'
        '<Parameter Type="Int32">1</Parameter></Parameters></Method>'
    )
    actions += '<Method Name="SystemUpdate" Id="13" ObjectPathId="9" />'
    xml = (
        '<Request xmlns="http://schemas.microsoft.com/sharepoint/clientquery/2009" '
        'SchemaVersion="15.0.0.0" LibraryVersion="16.0.0.0" ApplicationName="promote">'
        f'<Actions>{actions}</Actions><ObjectPaths>'
        f'<StaticProperty Id="1" TypeId="{CSOM_CURRENT_TYPEID}" Name="Current" />'
        '<Property Id="3" ParentId="1" Name="Web" />'
        '<Property Id="5" ParentId="3" Name="Lists" />'
        '<Method Id="7" ParentId="5" Name="GetByTitle"><Parameters>'
        '<Parameter Type="String">Site Pages</Parameter></Parameters></Method>'
        f'<Method Id="9" ParentId="7" Name="GetItemById"><Parameters>'
        f'<Parameter Type="Number">{item_id}</Parameter></Parameters></Method>'
        '</ObjectPaths></Request>'
    )
    r = session.post(
        f"{site_url}/_vti_bin/client.svc/ProcessQuery",
        data=xml.encode("utf-8"),
        headers={"Content-Type": "text/xml"},
    )
    r.raise_for_status()
    error = r.json()[0].get("ErrorInfo")
    if error:
        raise RuntimeError(f"CSOM promotion failed: {error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(PRESETS), default="recap")
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--canvas", required=True, help="path to a CanvasContent1 JSON array")
    parser.add_argument("--title", required=True)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--folder", help="folder relative to SitePages")
    parser.add_argument("--slug", help="filename slug after the date")
    parser.add_argument("--stage", action="store_true", help="stage a draft (the only operation)")
    parser.add_argument("--hide-title", dest="hide_title", action="store_true", default=True,
                        help="suppress the SharePoint title region so the band carries the "
                             "title (the default for every page)")
    parser.add_argument("--keep-title", dest="hide_title", action="store_false",
                        help="keep SharePoint's default title region above the content")
    parser.add_argument("--dry-run", action="store_true", help="show target without network or writes")
    args = parser.parse_args()
    if not sp.SITE_URL:
        parser.error("Set SHAREPOINT_SITE_URL")

    site_url = sp.SITE_URL
    site_path = urlparse(site_url).path.rstrip("/")
    preset = PRESETS[args.kind]
    folder = f"{site_path}/SitePages/{args.folder or preset['folder']}"
    target = f"{folder}/{args.date}-{args.slug or preset['slug']}.aspx"
    print(f"kind={args.kind} mode=stage target={target} PromotedState->1")
    if args.dry_run:
        print("dry run, nothing written")
        return

    canvas = Path(args.canvas).read_text()
    if not isinstance(json.loads(canvas), list):
        raise ValueError("CanvasContent1 must be a JSON array")
    session = sp.make_session()
    r = session.get(f"{site_url}/_api/sitepages/pages({args.id})")
    r.raise_for_status()
    page = r.json()["d"]
    first_published = page.get("FirstPublished")
    if page.get("PromotedState") == 2 or (first_published and not first_published.startswith("0001-")):
        raise ValueError("This News page was already published. Edit it manually in SharePoint.")

    refs = set(re.findall(r"SiteAssets/([A-Za-z0-9._-]+\.(?:png|jpg|jpeg|gif|svg))", canvas))
    if refs:
        r = session.get(f"{site_url}/_api/web/getfolderbyserverrelativeurl("
                        f"'{sp.api_path(site_path)}/SiteAssets')/files?$select=Name")
        r.raise_for_status()
        missing = refs - {item["Name"] for item in r.json()["d"]["results"]}
        if missing:
            raise ValueError(f"Upload missing SiteAssets images first: {', '.join(sorted(missing))}")

    digest = sp.get_request_digest(session, site_url)
    session.headers.update({"Content-Type": "application/json;odata=verbose", "X-RequestDigest": digest})
    r = session.get(f"{site_url}/_api/web/getfolderbyserverrelativeurl('{sp.api_path(folder)}')")
    if r.status_code == 404:
        r = session.post(f"{site_url}/_api/web/folders/addUsingPath(DecodedUrl='{sp.api_path(folder)}')")
    r.raise_for_status()

    fields = {"CanvasContent1": canvas, "Title": args.title}
    if args.hide_title:
        # The band already carries the page title. Pages left at the default (null) render
        # it twice.
        fields["LayoutWebpartsContent"] = '[{"controlType":0}]'
    current = sp.save_page(session, site_url, args.id, fields)
    print("savepage: OK")
    r = session.post(f"{site_url}/_api/web/getfilebyserverrelativeurl('{sp.api_path(current)}')"
                     "/checkin(comment='staged draft',checkintype=0)")
    r.raise_for_status()
    print("checkin(minor): OK")

    if current.lower() != target.lower():
        r = session.post(f"{site_url}/_api/web/getfilebyserverrelativeurl('{sp.api_path(current)}')"
                         f"/moveto(newurl='{sp.api_path(target)}',flags=1)")
        r.raise_for_status()
    mark_news_draft(session, site_url, args.id)
    r = session.get(f"{site_url}/_api/sitepages/pages({args.id})?$select=PromotedState,FirstPublished")
    r.raise_for_status()
    observed = r.json()["d"]
    print("verify PromotedState:", observed.get("PromotedState"), "FirstPublished:", observed.get("FirstPublished"))
    if observed.get("PromotedState") != 1:
        raise RuntimeError(f"Expected PromotedState=1; observed {observed.get('PromotedState')}")

    # Unlike PromotedState this is a plain field, but it is the difference between one
    # title on the page and two, so it gets verified rather than assumed.
    if args.hide_title:
        r = session.get(f"{site_url}/_api/sitepages/pages({args.id})?$select=LayoutWebpartsContent")
        r.raise_for_status()
        layout = r.json()["d"].get("LayoutWebpartsContent")
        print("verify LayoutWebpartsContent:", repr(layout))
        if not layout or "controlType" not in layout:
            raise RuntimeError("Title region not suppressed; the page would show two titles.")

    host = urlparse(site_url)
    print(f"DONE -> {host.scheme}://{host.netloc}{target}")
    print("STAGED as a News draft. Alex must publish it manually in SharePoint.")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, ValueError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
