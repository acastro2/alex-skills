#!/usr/bin/env python3
"""Collect GitHub metrics for the cohort-vs-rest comparison.

Pulls *authored* merged PRs with one query per org per weekly window (org-level
search truncates at 1000, so we chunk by date), then *reviewed* PRs per active
person. Everything keyed by exact GitHub login. Cohort logins are resolved by
normalizing the email local-part against the enterprise login pattern (e.g.
`jane@corp.com` -> `JaneSmith_attain`), with name-match fallback and manual
overrides for anyone that misses.

Usage: python collect_github.py [config.json] [out_dir]
Writes: <out>/github_raw.json
Requires: gh (authenticated with org read access), jq not needed.
"""
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

CFG_PATH, OUT = config.resolve_paths(sys.argv)
CFG = config.load(CFG_PATH)
W = config.windows(CFG)

ORGS = CFG["github_orgs"]
FULL_START = date.fromisoformat(W["full_start"])
TODAY = date.fromisoformat(W["today"])
OVERRIDES = CFG.get("login_overrides", {})

SEARCH_SLEEP = 1.5  # stay under the 30/min search rate limit
BOT_LOGINS = {"dependabot", "renovate", "github-actions", "snyk-bot",
              "codecov", "mergify", "copilot"}


def gh_json(args, retries=3):
    for attempt in range(retries):
        p = subprocess.run(["gh", *args], capture_output=True, text=True)
        if p.returncode == 0:
            out = p.stdout.strip()
            return json.loads(out) if out else None
        err = p.stderr.lower()
        if any(k in err for k in ("rate limit", "too quickly", "502", "503",
                                  "eof", "timeout", "connection")) and attempt < retries - 1:
            time.sleep(30 * (attempt + 1))
            continue
        print(f"  gh {' '.join(args)} -> {p.stderr.strip()}", file=sys.stderr)
        return None
    return None


def is_bot(author):
    if not author:
        return True
    if author.get("is_bot") or author.get("type") == "Bot":
        return True
    login = (author.get("login") or "").lower()
    return login.endswith("[bot]") or login in BOT_LOGINS


def weekly_windows(start, end):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=7), end)
        yield cur.isoformat(), nxt.isoformat()
        cur = nxt + timedelta(days=1)


def norm(s):
    return "".join(c for c in s.lower() if c.isalnum())


# 1. Member universe + names (used to resolve cohort logins)
print("Fetching org members...", file=sys.stderr)
member_logins = set()
for org in ORGS:
    p = subprocess.run(["gh", "api", f"/orgs/{org}/members", "--paginate",
                        "--jq", ".[].login"], capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if line.strip():
            member_logins.add(line.strip())
print(f"  {len(member_logins)} unique members", file=sys.stderr)

member_names = {}
for i, login in enumerate(sorted(member_logins)):
    info = gh_json(["api", f"/users/{login}", "--jq", "{login: .login, name: .name}"])
    if info:
        member_names[login] = info.get("name") or ""
    if (i + 1) % 25 == 0:
        print(f"  resolved names {i+1}/{len(member_logins)}", file=sys.stderr)

login_by_normlocal, login_by_normname = {}, {}
for login in member_logins:
    login_by_normlocal.setdefault(norm(login.replace("_attain", "")), login)
    nm = member_names.get(login, "")
    if nm:
        login_by_normname.setdefault(norm(nm), login)


def resolve_login(person):
    email, name = person["email"], person["name"]
    local = email.split("@")[0]
    if email in OVERRIDES:
        return OVERRIDES[email], "override"
    hit = login_by_normlocal.get(norm(local))
    if hit:
        return hit, "email-localpart"
    hit = login_by_normname.get(norm(name))
    if hit:
        return hit, "name-exact"
    toks = [t for t in name.lower().split() if len(t) > 1]
    if toks:
        first, last = toks[0], toks[-1]
        for login, nm in member_names.items():
            nl = nm.lower()
            if nl and first in nl and last in nl:
                return login, "name-tokens"
    return None, "unresolved"


print("Resolving cohort logins...", file=sys.stderr)
resolved, resolve_method, cohort_logins = {}, {}, set()
for person in CFG["cohort"]:
    login, method = resolve_login(person)
    resolved[person["email"]] = login
    resolve_method[person["email"]] = method
    if login:
        cohort_logins.add(login)
    print(f"  {person['name']:32s} {method:15s} -> {login}", file=sys.stderr)

# 2. Authored merged PRs across the org universe (weekly chunks)
print("Fetching authored merged PRs...", file=sys.stderr)
authored = defaultdict(dict)
authored_created = defaultdict(dict)
authored_title = defaultdict(dict)
truncated = []
for org in ORGS:
    for a, b in weekly_windows(FULL_START, TODAY):
        rng = f"{a}..{b}"
        rows = gh_json(["search", "prs", "--owner", org, "--merged",
                        "--merged-at", rng, "--json", "author,closedAt,createdAt,url,title",
                        "--limit", "1000"])
        time.sleep(SEARCH_SLEEP)
        if rows is None:
            continue
        if len(rows) >= 1000:
            truncated.append(f"{org} {rng}")
        for pr in rows:
            if is_bot(pr.get("author")):
                continue
            authored[pr["author"]["login"]][pr["url"]] = pr.get("closedAt")
            authored_created[pr["author"]["login"]][pr["url"]] = pr.get("createdAt")
            authored_title[pr["author"]["login"]][pr["url"]] = pr.get("title")
print(f"  authors with >=1 merged PR: {len(authored)}", file=sys.stderr)
if truncated:
    print(f"  WARNING truncated chunks (raise chunk granularity): {truncated}", file=sys.stderr)

# 3. Reviewed merged PRs for the full member universe (so rest-side reviewers,
#    who may never author, are not undercounted vs the cohort)
active = set(authored) | cohort_logins | member_logins
print(f"Fetching reviews for {len(active)} logins...", file=sys.stderr)
reviewed = defaultdict(dict)
rng_full = f"{FULL_START.isoformat()}..{TODAY.isoformat()}"
rev_trunc = []
for i, login in enumerate(sorted(active)):
    rows = gh_json(["search", "prs", "--reviewed-by", login, "--merged",
                    "--merged-at", rng_full, "--json", "closedAt,url", "--limit", "1000"])
    time.sleep(SEARCH_SLEEP)
    if rows is None:
        continue
    if len(rows) >= 1000:
        rev_trunc.append(login)
    for pr in rows:
        reviewed[login][pr["url"]] = pr.get("closedAt")
    if (i + 1) % 25 == 0:
        print(f"  reviews {i+1}/{len(active)}", file=sys.stderr)

out = {
    "resolved": resolved, "resolve_method": resolve_method,
    "cohort_logins": sorted(cohort_logins),
    "authored": dict(authored), "authored_created": dict(authored_created),
    "authored_title": dict(authored_title),
    "reviewed": dict(reviewed),
    "member_count": len(member_logins),
    "truncated_chunks": truncated, "review_truncated": rev_trunc,
    "windows": W,
}
open(os.path.join(OUT, "github_raw.json"), "w").write(json.dumps(out, indent=2))
print(f"\nWrote {OUT}/github_raw.json (authors={len(authored)}, reviewers={len(reviewed)})",
      file=sys.stderr)
unresolved = [e for e, l in resolved.items() if not l]
if unresolved:
    print(f"UNRESOLVED (add to login_overrides in config, or they are non-engineers): "
          f"{unresolved}", file=sys.stderr)
