---
name: browser-cookie-auth
description: Reuse an already-authenticated interactive browser session (SSO/passkey login) to authenticate scripted automation against an internal web service, by caching session cookies to disk with a TTL instead of re-triggering login on every run. Use when building a new REST/API automation against an internal tool that only supports interactive SSO (no service principal, no API key) -- e.g. a new SharePoint site, an internal wiki, an internal dashboard -- and you want the same "log in once, reuse the session" pattern already used for the SharePoint page assistant. Do NOT use to access a service the operator isn't already personally authorized to use, and do not use it as a substitute for a real service credential when one is available.
---

# Browser Cookie Auth

Pattern for scripted automation against internal services that only support interactive
SSO login (no service principal, no long-lived API key): open a real browser once,
let the operator log in (or reuse an already-logged-in persistent profile), capture the
session cookies, and cache them to disk with a TTL so later script runs skip the login
step until the cache expires.

This is exactly the mechanism the SharePoint page-assistant skill uses
(`~/.claude/scripts/sharepoint/auth.py`) — generalized here so a new integration doesn't
have to reinvent it. Read `~/.claude/scripts/sharepoint/auth.py` and `sharepoint_api.py`
for a complete worked example (auth + REST calls + a cookie-authenticated `requests.Session`).

## Before you wire this to a new service — scope it explicitly

This reuses a *human's own authenticated session*. That's legitimate for internal
automation, but only within a specific scope. Before pointing it at a new service, confirm
out loud (with the user, not silently):

1. **The operator is already personally authorized** to access this service via normal
   interactive login. This tool never requests, elevates, or grants access — it only
   captures a session the operator already established themselves. If the task would need
   *more* access than the operator already has, this is the wrong tool — that's a PIM/access
   request, a human workflow, not something to route around with cookies.
2. **Which cookies, which URL.** Session cookie names are service-specific (SharePoint/ADFS
   uses `FedAuth`+`rtFa`; other services use different names — check the browser's
   devtools → Application → Cookies on that service while logged in).
3. **A real credential isn't available instead.** If the service has an API key, PAT, or
   service principal you're already permitted to use for this purpose, prefer that — it's
   auditable and scoped, unlike a human session cookie. Cookie auth is the fallback for
   services that genuinely only offer interactive login.

Don't generalize this into "point it at any site" tooling off a casual request — get the
specific service named and confirmed first.

## Hard rules (same as any credential)

- **Cookie values are secrets.** Never print, log, or paste a cookie value anywhere —
  not in chat, not in a report, not in a commit message. `cookie_auth.py` only ever prints
  cookie *names* and *domains*, never values. Keep that discipline in anything you build
  on top of it.
- **Cache files and browser profiles are secret-bearing artifacts, not source.** They must
  live somewhere gitignored. This skill's script writes to `.cache/` and `.profiles/`
  next to itself under `~/.claude/scripts/browser-cookie-auth/`, which is covered by
  `~/.claude/scripts/.gitignore` (added 2026-07-20 alongside this skill — that same fix also
  closed a real gap where the SharePoint script's `.cookies.json`/`.browser-profile/` were
  untracked-but-not-ignored in a repo with a live GitHub remote). If you copy this script
  elsewhere, port the gitignore protection with it.
- **Don't build unattended/background harvesting.** The visible-browser-window login step
  is a feature, not friction — it's the moment a human either reuses their own consented
  session or explicitly logs in. Don't silently read another browser's cookie store or
  attach to a running browser via CDP as the *default* path for a new service; those are
  higher-sensitivity variants (present as a reference implementation in
  `sharepoint/auth.py`'s `extract_cookies_from_edge_store` / `extract_cookies_via_cdp`)
  that should only be added for a specific named, already-approved service, not by default.

## Usage

```bash
python3 ~/.claude/scripts/browser-cookie-auth/cookie_auth.py <service_slug> <url> \
  --cookie-names FedAuth,rtFa \
  [--ttl-hours 7] [--refresh] [--browser msedge|chromium]
```

- `service_slug`: short name for the service (e.g. `confluence`, `internal-wiki`) — keys the
  cache file and the persistent browser profile so different services don't collide.
- `url`: a page on the target service that will mint/hold the session cookies.
- `--cookie-names`: comma-separated names to wait for and capture (service-specific —
  find them via devtools on that service while logged in).
- `--ttl-hours`: how long to trust the cache before forcing a fresh login (default 7h,
  tuned for typical enterprise SSO session length — adjust per service).
- `--refresh`: force a fresh interactive login even if a cache entry exists.

From Python, `import` the module directly for the same functions
(`get_cookies`, `make_session`) — see the module docstring in
`~/.claude/scripts/browser-cookie-auth/cookie_auth.py` for the full API, which mirrors
`sharepoint_api.py`'s `make_session`/`get_request_digest` pattern: load the cached cookies
into a `requests.Session`, fetch a fresh request-verification token per write if the
target service uses one (SharePoint's `X-RequestDigest` is one example), and proceed with
normal authenticated REST calls.

## Workflow for a brand-new service

1. Confirm scope with the user (see "Before you wire this" above).
2. Log into the target service once in a normal browser tab to find its session cookie
   name(s) via devtools.
3. Run the CLI once interactively to seed the cache and persistent profile.
4. Build the service-specific REST calls on top of `make_session(service_slug)`, following
   `sharepoint_api.py` as the reference shape (session + request-digest/token fetch +
   typed helper functions per operation).
5. On 401/403 in later runs, re-run with `--refresh`.
