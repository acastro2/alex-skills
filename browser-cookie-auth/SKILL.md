---
name: browser-cookie-auth
description: Reuse an already-authenticated interactive browser session (SSO/passkey login) to authenticate scripted automation against an internal web service, by caching session cookies to disk with a TTL instead of re-triggering login on every run. Use when building a new REST/API automation against an internal tool that only supports interactive SSO (no service principal, no API key) -- e.g. a new SharePoint site, an internal wiki, an internal dashboard -- and you want the same "log in once, reuse the session" pattern already used for the SharePoint page assistant. Do NOT use to access a service the operator isn't already personally authorized to use, and do not use it as a substitute for a real service credential when one is available.
---

# Browser Cookie Auth

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

Pattern for scripted automation against internal services that only support interactive
SSO login (no service principal, no long-lived API key): open a real browser once,
let the operator log in (or reuse an already-logged-in persistent profile), capture the
session cookies, and cache them to disk with a TTL so later script runs skip the login
step until the cache expires.

The mechanism ships with this skill: `scripts/cookie_auth.py`. It opens one visible browser
window, waits for the operator's login, stores the named cookies under
`~/.cache/browser-cookie-auth/`, and hands back either the cookies or a ready
`requests.Session`. Nothing else is needed, and nothing is read from another skill or from
a tool's config tree.

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

- **Cookie values are secrets.** The CLI prints cookie names, domains, and paths only,
  never a value. Keep that discipline in anything you build on top of it: no cookie value in
  chat, in a report, in a log, or in a commit message.
- **Cache files and browser profiles are secret-bearing artifacts, not source.** They live
  under `~/.cache/browser-cookie-auth/`, with the cache at mode 0600 and its directory and
  the browser profile at 0700. Never move them next to the script: a cache in a git
  checkout is a credential in a git checkout.
- **Don't build unattended or background harvesting.** The visible login window is the
  consent step, not friction. This script deliberately does not read another browser's
  cookie store and does not attach to a running browser over CDP; adding either is a
  separate, higher-sensitivity decision for one named, already-approved service.

## Usage

```bash
python3 scripts/cookie_auth.py <service_slug> <url> \
  [--cookie-names FedAuth,rtFa] [--ttl-hours 7] [--refresh] \
  [--browser chromium|msedge|chrome] [--timeout 120]
```

- `service_slug`: short name for the service (e.g. `confluence`, `internal-wiki`). It keys
  the cache file and the persistent browser profile, so services never collide.
- `url`: a page on the target service that mints or holds the session cookies.
- `--cookie-names`: comma-separated names to wait for and capture (default
  `FedAuth,rtFa`; find the real ones in devtools while logged in).
- `--ttl-hours`: how long to trust the cache before forcing a fresh login (default 7,
  tuned for typical enterprise SSO lifetime).
- `--refresh`: force an interactive login even when a cache entry is valid.
- `--browser`: `chromium` by default, or an installed Chrome or Edge channel.

From Python, import the module:

```python
from cookie_auth import make_session

session = make_session("sharepoint", "https://example.internal/sites/team")
response = session.get("https://example.internal/sites/team/_api/web")
```

`make_session` loads the cached cookies into a `requests.Session`. For a service that needs
a per-write verification token (SharePoint's `X-RequestDigest` is one), fetch that token
once per session and send it as a header on writes; the module does not guess at a
service-specific token.

## Workflow for a brand-new service

1. Confirm scope with the user (see "Before you wire this" above).
2. Log into the target service once in a normal browser tab and find its session cookie
   name(s) in devtools.
3. Run the CLI once interactively to seed the cache and the persistent profile.
4. Build the service's REST calls on top of `make_session`, adding a token fetch only if
   that service requires one.
5. On 401 or 403 in a later run, re-run with `--refresh`.
