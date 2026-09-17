#!/usr/bin/env python3
"""m365 — read-only CLI for your own mail, calendar, Teams and SharePoint.

Read-only by construction: there is no command that writes, sends or deletes.
Auth: authorization code + PKCE with a loopback redirect, refresh token cached on disk.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import stat
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph Command Line Tools (public client)
TENANT = "2dc14abb-7941-4377-a7d2-59f436e42867"
SCOPES = [
    "User.Read", "Chat.Read", "ChannelMessage.Read.All", "Sites.Read.All",
    "Team.ReadBasic.All", "TeamMember.Read.All", "Channel.ReadBasic.All",
    "Mail.Read", "Calendars.Read", "OnlineMeetings.Read", "offline_access",
]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0"
GRAPH = "https://graph.microsoft.com/v1.0"
CACHE_PATH = Path(os.environ.get("M365_CACHE", Path.home() / ".m365-readonly" / "token.json"))


class CliError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


# ---------------------------------------------------------------- token cache


class TokenCache:
    """Filesystem seam. Owns one file, mode 0600."""

    def __init__(self, path: Path = CACHE_PATH):
        self.path = path

    def read(self) -> dict | None:
        return json.loads(self.path.read_text()) if self.path.exists() else None

    def write(self, tokens: dict) -> None:
        self.path.parent.mkdir(mode=0o700, exist_ok=True)
        self.path.touch(mode=0o600, exist_ok=True)
        self.path.write_text(json.dumps({
            "refresh_token": tokens.get("refresh_token"),
            "access_token": tokens["access_token"],
            "expires_at": time.time() + int(tokens.get("expires_in", 3600)) - 120,
        }, indent=2))
        os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)

    def clear(self) -> bool:
        if self.path.exists():
            self.path.unlink()
            return True
        return False


# ---------------------------------------------------------------------- auth


def post_form(url: str, form: dict) -> dict:
    """Network seam."""
    req = urllib.request.Request(url, data=urllib.parse.urlencode(form).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return {"__status": e.code, **json.loads(e.read() or b"{}")}
        except Exception:
            return {"__status": e.code, "error": "http_error"}


def access_token(cache: TokenCache, now=time.time, post=post_form) -> str:
    cached = cache.read()
    if cached is None:
        raise CliError("no_token", "not signed in - run: m365 login")
    if cached.get("access_token") and now() < cached.get("expires_at", 0):
        return cached["access_token"]
    r = post(f"{AUTHORITY}/token", {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": cached["refresh_token"],
        "scope": " ".join(SCOPES),
    })
    if "access_token" not in r:
        raise CliError("refresh_failed", r.get("error_description") or r.get("error") or "unknown")
    cache.write(r)
    return r["access_token"]


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


class _Callback(http.server.BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802
        _Callback.result = {k: v[0] for k, v in
                            urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}
        body = b"<html><body style='font-family:system-ui;padding:40px'><h2>Signed in.</h2></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def login(cache: TokenCache) -> None:
    probe = http.server.HTTPServer(("127.0.0.1", 0), _Callback)
    port = probe.server_address[1]
    probe.server_close()
    redirect_uri = f"http://localhost:{port}"
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)
    url = f"{AUTHORITY}/authorize?" + urllib.parse.urlencode({
        "client_id": CLIENT_ID, "response_type": "code", "redirect_uri": redirect_uri,
        "response_mode": "query", "scope": " ".join(SCOPES), "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    print(f"\nOpening your browser. If it does not open, paste this:\n\n{url}\n", flush=True)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    server = http.server.HTTPServer(("127.0.0.1", port), _Callback)
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()
    t.join(240)
    server.server_close()
    got = _Callback.result
    if got.get("state") != state:
        raise CliError("login_failed", "state mismatch or no callback")
    if "code" not in got:
        raise CliError("login_failed", got.get("error_description") or got.get("error") or "no code")
    tokens = post_form(f"{AUTHORITY}/token", {
        "grant_type": "authorization_code", "client_id": CLIENT_ID, "code": got["code"],
        "redirect_uri": redirect_uri, "code_verifier": verifier,
    })
    if "access_token" not in tokens:
        raise CliError("login_failed", tokens.get("error_description") or "token exchange failed")
    cache.write(tokens)
    print(f"signed in - token cached at {cache.path}")


# --------------------------------------------------------------------- graph


def http_json(method: str, url: str, token: str, body: dict | None = None):
    """Network seam. Returns (status, parsed)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"raw": raw.decode(errors="replace")[:200]}
        return e.code, parsed


class Graph:
    def __init__(self, token_fn, transport=http_json):
        self._token = token_fn
        self._transport = transport

    def get(self, path: str, params: dict | None = None) -> dict:
        url = path if path.startswith("http") else f"{GRAPH}{path}"
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        status, body = self._transport("GET", url, self._token())
        if status >= 400:
            err = (body.get("error") or {})
            raise CliError(err.get("code") or f"http_{status}",
                           err.get("message") or str(body)[:200])
        return body

    def post(self, path: str, payload: dict) -> dict:
        url = path if path.startswith("http") else f"{GRAPH}{path}"
        status, body = self._transport("POST", url, self._token(), payload)
        if status >= 400:
            err = (body.get("error") or {})
            raise CliError(err.get("code") or f"http_{status}",
                           err.get("message") or str(body)[:200])
        return body

    def search(self, entity: str, query: str, limit: int) -> list:
        out = self.post("/search/query", {"requests": [{
            "entityTypes": [entity], "query": {"queryString": query}, "from": 0, "size": limit}]})
        try:
            return out["value"][0]["hitsContainers"][0].get("hits", [])
        except (KeyError, IndexError):
            return []


# ------------------------------------------------------------------- commands


def _trim_message(m: dict) -> dict:
    return {
        "id": m.get("id"), "subject": m.get("subject"),
        "from": ((m.get("from") or {}).get("emailAddress") or {}).get("address"),
        "received": m.get("receivedDateTime"), "preview": (m.get("bodyPreview") or "")[:300],
        "unread": m.get("isRead") is False, "webLink": m.get("webLink"),
    }


def _trim_event(e: dict) -> dict:
    return {
        "id": e.get("id"), "subject": e.get("subject"),
        "start": (e.get("start") or {}).get("dateTime"), "end": (e.get("end") or {}).get("dateTime"),
        "organizer": ((e.get("organizer") or {}).get("emailAddress") or {}).get("name"),
        "online": bool(e.get("onlineMeeting")),
    }


def cmd_mail_search(g: Graph, a) -> dict:
    params = {"$top": a.limit, "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead,webLink"}
    if a.query:
        params["$search"] = f'"{a.query}"'
    else:
        params["$orderby"] = "receivedDateTime desc"
    if a.sender:
        params["$filter"] = f"contains(from/emailAddress/address,'{a.sender}')"
    if a.after:
        params = {k: v for k, v in params.items() if k != "$search"}
        params["$filter"] = (params.get("$filter", "") + f" and receivedDateTime ge {a.after}").strip(" and")
    return {"messages": [_trim_message(m) for m in g.get("/me/messages", params).get("value", [])]}


def cmd_mail_read(g: Graph, a) -> dict:
    m = g.get(f"/me/messages/{a.id}",
              {"$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,webLink"})
    m["body"] = ((m.get("body") or {}).get("content") or "")[:a.max_chars]
    return {"message": m}


def cmd_calendar_search(g: Graph, a) -> dict:
    params = {"$top": a.limit, "$select": "id,subject,start,end,organizer,onlineMeeting",
              "$orderby": "start/dateTime"}
    if a.after:
        params["$filter"] = f"start/dateTime ge '{a.after}'"
    if a.before:
        params["$filter"] = (params.get("$filter", "") + f" and start/dateTime le '{a.before}'").strip(" and")
    return {"events": [_trim_event(e) for e in g.get("/me/events", params).get("value", [])]}


def cmd_teams_chats(g: Graph, a) -> dict:
    return {"chats": g.get("/me/chats", {"$top": a.limit, "$select": "id,topic,chatType,lastUpdatedDateTime"}
                           ).get("value", [])}


def cmd_teams_messages(g: Graph, a) -> dict:
    raw = g.get(f"/me/chats/{a.chat}/messages", {"$top": a.limit}).get("value", [])
    return {"messages": [{"from": ((m.get("from") or {}).get("user") or {}).get("displayName"),
                          "when": m.get("createdDateTime"),
                          "text": (m.get("body") or {}).get("content", "")[:a.max_chars]}
                         for m in raw if (m.get("body") or {}).get("content")]}


def cmd_teams_search(g: Graph, a) -> dict:
    return {"hits": [{"id": h.get("hitId"), "summary": h.get("summary")}
                     for h in g.search("chatMessage", a.query, a.limit)]}


def cmd_sharepoint_search(g: Graph, a) -> dict:
    if a.sites:
        return {"sites": g.get("/sites", {"search": a.query, "$select": "id,displayName,webUrl",
                                          "$top": a.limit}).get("value", [])}
    hits = g.search("driveItem", a.query, a.limit)
    return {"documents": [{"name": h.get("resource", {}).get("name"),
                           "webUrl": h.get("resource", {}).get("webUrl"),
                           "site": (h.get("resource", {}).get("parentReference") or {}).get("siteId")}
                          for h in hits]}


def cmd_sharepoint_read(g: Graph, a) -> dict:
    if a.target.startswith("http") and "sharepoint.com" in a.target and "/:" not in a.target:
        enc = base64.urlsafe_b64encode(a.target.encode()).rstrip(b"=").decode()
        item = g.get(f"/shares/u!{enc}/driveItem")
    else:
        item = g.get(f"/drives/{a.drive}/items/{a.target}")
    return {"item": {"name": item.get("name"), "size": item.get("size"), "webUrl": item.get("webUrl"),
                     "downloadUrl": item.get("@microsoft.graph.downloadUrl"),
                     "lastModified": item.get("lastModifiedDateTime")}}


def cmd_doctor(g: Graph, a) -> dict:
    cache = TokenCache()
    cached = cache.read()
    out = {
        "cache": str(cache.path),
        "cache_present": cached is not None,
        "has_refresh_token": bool(cached and cached.get("refresh_token")),
        "access_token": "none",
        "auth": "missing",
    }
    if cached:
        left = int(cached.get("expires_at", 0) - time.time())
        out["access_token"] = f"valid {left}s" if left > 0 else "expired (refreshes on use)"
        try:
            me = g.get("/me", {"$select": "displayName,userPrincipalName"})
            out["auth"] = "ok"
            out["user"] = me.get("userPrincipalName")
            for label, path, params in [
                ("mail", "/me/messages", {"$top": 1}),
                ("calendar", "/me/events", {"$top": 1}),
                ("teams", "/me/chats", {"$top": 1}),
                ("sharepoint", "/sites", {"search": "a", "$top": 1}),
            ]:
                try:
                    g.get(path, params)
                    out[label] = "ok"
                except CliError as e:
                    out[label] = f"fail: {e.code}"
        except CliError as e:
            out["auth"] = f"fail: {e.code}"
    return out


# ----------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="m365", description="Read your own mail, calendar, Teams and SharePoint.")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", help="sign in and cache a refresh token")
    sub.add_parser("logout", help="delete the cached token")
    sub.add_parser("whoami", help="show the signed-in account")
    sub.add_parser("doctor", help="check auth and which surfaces respond")

    m = sub.add_parser("mail", help="mail")
    ms = m.add_subparsers(dest="sub", required=True)
    s = ms.add_parser("search"); s.add_argument("query", nargs="?"); s.add_argument("--sender")
    s.add_argument("--after"); s.add_argument("--limit", type=int, default=20)
    r = ms.add_parser("read"); r.add_argument("id"); r.add_argument("--max-chars", type=int, default=4000)

    c = sub.add_parser("calendar", help="calendar")
    cs = c.add_subparsers(dest="sub", required=True)
    s = cs.add_parser("search"); s.add_argument("--after"); s.add_argument("--before")
    s.add_argument("--limit", type=int, default=20)

    t = sub.add_parser("teams", help="Teams")
    ts = t.add_subparsers(dest="sub", required=True)
    s = ts.add_parser("chats"); s.add_argument("--limit", type=int, default=25)
    s = ts.add_parser("messages"); s.add_argument("chat"); s.add_argument("--limit", type=int, default=50)
    s.add_argument("--max-chars", type=int, default=400)
    s = ts.add_parser("search"); s.add_argument("query"); s.add_argument("--limit", type=int, default=25)

    sp = sub.add_parser("sharepoint", help="SharePoint")
    sps = sp.add_subparsers(dest="sub", required=True)
    s = sps.add_parser("search"); s.add_argument("query"); s.add_argument("--sites", action="store_true")
    s.add_argument("--limit", type=int, default=20)
    s = sps.add_parser("read"); s.add_argument("target"); s.add_argument("--drive")

    rq = sub.add_parser("request", help="raw read-only Graph GET")
    rq.add_argument("path"); rq.add_argument("--param", action="append", default=[])
    return p


HANDLERS = {
    ("mail", "search"): cmd_mail_search, ("mail", "read"): cmd_mail_read,
    ("calendar", "search"): cmd_calendar_search,
    ("teams", "chats"): cmd_teams_chats, ("teams", "messages"): cmd_teams_messages,
    ("teams", "search"): cmd_teams_search,
    ("sharepoint", "search"): cmd_sharepoint_search, ("sharepoint", "read"): cmd_sharepoint_read,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    cache = TokenCache()
    try:
        if args.cmd == "login":
            login(cache); return 0
        if args.cmd == "logout":
            print("token deleted" if cache.clear() else "no token to delete"); return 0
        g = Graph(lambda: access_token(cache))
        if args.cmd == "doctor":
            data = cmd_doctor(g, args)
        elif args.cmd == "whoami":
            data = {"user": g.get("/me", {"$select": "displayName,userPrincipalName"})}
        elif args.cmd == "request":
            params = dict(p.split("=", 1) for p in args.param)
            data = {"response": g.get(args.path, params or None)}
        else:
            data = HANDLERS[(args.cmd, args.sub)](g, args)
    except CliError as e:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": {"code": e.code, "message": e.message}}))
        else:
            print(f"error: {e.code}: {e.message}", file=sys.stderr)
        return 1
    if getattr(args, "json", False):
        print(json.dumps({"ok": True, "data": data}, indent=2, default=str))
    else:
        print(json.dumps(data, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
