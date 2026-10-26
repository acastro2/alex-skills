#!/usr/bin/env python3
"""Reuse a browser session for scripted calls by caching its cookies.

Open one real browser window, let the operator log in, capture the session cookies, and
cache them to disk with a TTL. Later runs reuse the cached cookies and a persistent browser
profile, so the login happens once per session lifetime, not once per script run.

    python3 cookie_auth.py confluence https://wiki.internal/ --cookie-names JSESSIONID
    python3 cookie_auth.py sharepoint https://example.internal/sites/team --cookie-names FedAuth,rtFa

Print cookies as JSON, or import `make_session` to get a `requests.Session` already
authenticated against the service.

Secrets stay out of the repo: the cache and the browser profile live under
`~/.cache/browser-cookie-auth/`, both mode 0600 and 0700, never next to this file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

DEFAULT_COOKIE_NAMES = ("FedAuth", "rtFa")
DEFAULT_TTL_HOURS = 7
DEFAULT_BROWSER = "chromium"
CACHE_ROOT = Path.home() / ".cache" / "browser-cookie-auth"


def _root() -> Path:
    override = os.environ.get("BROWSER_COOKIE_AUTH_HOME")
    return Path(override) if override else CACHE_ROOT


def _slug(value: str) -> str:
    """A slug becomes a filename, so it may not escape the cache directory."""
    cleaned = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")
    if not cleaned:
        raise ValueError("service slug must contain a letter or digit")
    return cleaned


def cache_file(service: str) -> Path:
    return _root() / f"{_slug(service)}.json"


def profile_dir(service: str) -> Path:
    return _root() / f"{_slug(service)}-profile"


def get_cached_cookies(
    service: str,
    url: str,
    cookie_names: tuple[str, ...] = DEFAULT_COOKIE_NAMES,
    ttl_hours: float = DEFAULT_TTL_HOURS,
) -> dict | None:
    """Cached cookies for this service and URL, or None when absent, stale, or incomplete."""
    path = cache_file(service)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("url") != url:
        return None
    if time.time() - data.get("timestamp", 0) > ttl_hours * 3600:
        return None
    cookies = data.get("cookies", {})
    if all(name in cookies for name in cookie_names):
        return cookies
    return None


def save_cookies(service: str, url: str, cookies: dict) -> Path:
    """Persist the cookies, readable by this user only."""
    path = cache_file(service)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    path.write_text(
        json.dumps({"url": url, "timestamp": time.time(), "cookies": cookies}, indent=2)
    )
    path.chmod(0o600)
    return path


def extract_cookies_from_browser(
    service: str,
    url: str,
    cookie_names: tuple[str, ...] = DEFAULT_COOKIE_NAMES,
    browser_channel: str = DEFAULT_BROWSER,
    timeout: int = 120,
) -> dict:
    """Open a visible browser, wait for the operator's login, return the named cookies.

    The window is the consent step: a human either reuses their own session or logs in.
    Nothing here reads another browser's cookie store or attaches to a running one.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "ERROR: playwright is not installed. Run: pip3 install playwright "
            "&& python3 -m playwright install chromium",
            file=sys.stderr,
        )
        raise SystemExit(1)

    profile = profile_dir(service)
    profile.mkdir(parents=True, exist_ok=True)
    profile.chmod(0o700)

    print(f"Opening {browser_channel} for {service}: {url}", file=sys.stderr)
    print("Log in if asked. The cookies are captured as soon as they appear.", file=sys.stderr)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            channel=None if browser_channel == "chromium" else browser_channel,
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, wait_until="domcontentloaded")

        deadline = time.time() + timeout
        while time.time() < deadline:
            found = {
                cookie["name"]: {
                    "value": cookie["value"],
                    "domain": cookie.get("domain", ""),
                    "path": cookie.get("path", "/"),
                }
                for cookie in context.cookies()
                if cookie["name"] in cookie_names
            }
            if len(found) == len(cookie_names):
                context.close()
                return found
            time.sleep(2)

        context.close()
    print("ERROR: timed out waiting for the login cookies.", file=sys.stderr)
    raise SystemExit(1)


def get_cookies(
    service: str,
    url: str,
    cookie_names: tuple[str, ...] = DEFAULT_COOKIE_NAMES,
    ttl_hours: float = DEFAULT_TTL_HOURS,
    force_refresh: bool = False,
    browser_channel: str = DEFAULT_BROWSER,
    timeout: int = 120,
) -> dict:
    """From the cache when it is valid, otherwise from a fresh login."""
    if not force_refresh:
        cached = get_cached_cookies(service, url, cookie_names, ttl_hours)
        if cached:
            return cached
    cookies = extract_cookies_from_browser(service, url, cookie_names, browser_channel, timeout)
    save_cookies(service, url, cookies)
    return cookies


def make_session(
    service: str,
    url: str,
    cookie_names: tuple[str, ...] = DEFAULT_COOKIE_NAMES,
    ttl_hours: float = DEFAULT_TTL_HOURS,
    force_refresh: bool = False,
    browser_channel: str = DEFAULT_BROWSER,
):
    """A `requests.Session` carrying the cached cookies for this service."""
    import requests

    cookies = get_cookies(service, url, cookie_names, ttl_hours, force_refresh, browser_channel)
    session = requests.Session()
    for name, cookie in cookies.items():
        session.cookies.set(name, cookie["value"], domain=cookie.get("domain") or None, path=cookie.get("path", "/"))
    return session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cache browser session cookies for a service.")
    parser.add_argument("service", help="short name, e.g. confluence or sharepoint")
    parser.add_argument("url", help="a page on the service that mints the session cookies")
    parser.add_argument(
        "--cookie-names",
        default=",".join(DEFAULT_COOKIE_NAMES),
        help="comma-separated cookie names to capture",
    )
    parser.add_argument("--ttl-hours", type=float, default=DEFAULT_TTL_HOURS)
    parser.add_argument("--refresh", action="store_true", help="ignore a valid cache")
    parser.add_argument("--browser", default=DEFAULT_BROWSER, choices=("chromium", "msedge", "chrome"))
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)

    names = tuple(name.strip() for name in args.cookie_names.split(",") if name.strip())
    cookies = get_cookies(
        args.service,
        args.url,
        cookie_names=names,
        ttl_hours=args.ttl_hours,
        force_refresh=args.refresh,
        browser_channel=args.browser,
        timeout=args.timeout,
    )
    # Names, domains and paths only: a cookie value is a credential and never goes to stdout.
    print(json.dumps({name: {"domain": c.get("domain", ""), "path": c.get("path", "/")} for name, c in cookies.items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
