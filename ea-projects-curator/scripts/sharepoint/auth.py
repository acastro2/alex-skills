#!/usr/bin/env python3
"""
SharePoint cookie-based authentication via Playwright.

Opens a browser to the SharePoint site, waits for login (or reuses existing session),
extracts FedAuth/rtFa cookies, and caches them to disk.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Outside the checkout on purpose: a cookie file next to the script is a credential in
# a git working tree, and this repo is public.
COOKIE_CACHE = Path.home() / ".cache" / "ea-projects-curator" / "cookies.json"
# Default to 7 hours — FedAuth typically lasts 8hrs
COOKIE_TTL_SECONDS = 7 * 3600


def get_cached_cookies(site_url: str) -> Optional[dict]:
    """Return cached cookies if they exist and aren't expired."""
    if not COOKIE_CACHE.exists():
        return None
    try:
        data = json.loads(COOKIE_CACHE.read_text())
        if data.get("site_url") != site_url:
            return None
        if time.time() - data.get("timestamp", 0) > COOKIE_TTL_SECONDS:
            return None
        cookies = data.get("cookies", {})
        if "FedAuth" in cookies and "rtFa" in cookies:
            return cookies
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def save_cookies(site_url: str, cookies: dict):
    """Persist cookies to disk, readable by this user only."""
    COOKIE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_CACHE.write_text(json.dumps({
        "site_url": site_url,
        "timestamp": time.time(),
        "cookies": cookies,
    }, indent=2))
    COOKIE_CACHE.chmod(0o600)


def extract_cookies_from_browser(site_url: str, timeout: int = 120) -> dict:
    """
    Launch a Chromium browser, navigate to the SharePoint site,
    wait for authentication cookies, and return them.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip3 install playwright && python3 -m playwright install chromium", file=sys.stderr)
        sys.exit(1)

    print(f"Opening browser for SharePoint login...", file=sys.stderr)
    print(f"URL: {site_url}", file=sys.stderr)
    print(f"If already logged in, cookies will be extracted automatically.", file=sys.stderr)
    print(f"Otherwise, please log in within {timeout} seconds.", file=sys.stderr)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(site_url, wait_until="domcontentloaded")

        deadline = time.time() + timeout
        cookies_dict = {}

        while time.time() < deadline:
            all_cookies = context.cookies()
            for c in all_cookies:
                if c["name"] in ("FedAuth", "rtFa"):
                    cookies_dict[c["name"]] = {
                        "value": c["value"],
                        "domain": c.get("domain", ""),
                        "path": c.get("path", "/"),
                    }

            if "FedAuth" in cookies_dict and "rtFa" in cookies_dict:
                print("Cookies extracted successfully.", file=sys.stderr)
                for name, info in cookies_dict.items():
                    print(f"  {name}: domain={info['domain']}, path={info['path']}", file=sys.stderr)
                browser.close()
                return cookies_dict

            time.sleep(2)

        browser.close()
        print("ERROR: Timed out waiting for authentication cookies.", file=sys.stderr)
        sys.exit(1)


def get_cookies(site_url: str, force_refresh: bool = False) -> dict:
    """Get cookies — from cache if valid, otherwise via browser."""
    if not force_refresh:
        cached = get_cached_cookies(site_url)
        if cached:
            return cached

    cookies = extract_cookies_from_browser(site_url)
    save_cookies(site_url, cookies)
    return cookies


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 auth.py <sharepoint_site_url> [--refresh]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    refresh = "--refresh" in sys.argv
    cookies = get_cookies(url, force_refresh=refresh)
    # Output as JSON for consumption by other scripts
    print(json.dumps(cookies))
