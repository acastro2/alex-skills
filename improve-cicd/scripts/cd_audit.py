#!/usr/bin/env python3
"""Audit delivery from GitHub Deployments: lead time, frequency, change failure rate, recovery, deploy duration."""
import argparse
import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlencode

DAY, WEEK = 86400, 7 * 86400
LOOKBACK_DAYS = 30
TERMINAL = {"success", "failure", "error", "inactive"}


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


class GhError(Exception):
    pass


def fmt_ts(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rate_core():
    """(remaining, reset_ts) for the core rate limit, or None if it cannot be read."""
    try:
        p = subprocess.run(["gh", "api", "rate_limit"], capture_output=True, text=True)
        c = json.loads(p.stdout)["resources"]["core"]
        return c["remaining"], c["reset"]
    except (OSError, ValueError, KeyError):
        return None


def gh(path, fatal=True):
    # Transient 5xx, stream resets and bad JSON are retried. A rate limit waits once, and only when the reset is under 60 s.
    err, attempt, waited = "", 0, False
    while attempt < 3:
        delay = 0
        try:
            p = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        except FileNotFoundError:
            die("gh CLI not found; install it and run `gh auth login`")
        if p.returncode == 0:
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                err, delay = "invalid JSON from gh", 2 ** attempt
        else:
            err = p.stderr.strip() or p.stdout.strip()
            if re.search(r"HTTP 429", err) or (re.search(r"HTTP 403", err) and re.search(r"rate limit", err, re.I)):
                core = rate_core()
                wait = core[1] - time.time() if core else None
                if wait is not None and wait < 60 and not waited:
                    waited = True
                    time.sleep(max(wait, 0) + 1)
                    continue
                err += f" (rate limit; resets at {fmt_ts(core[1]) if core else 'unknown time'})"
                break
            elif re.search(r"HTTP 5\d\d|stream error", err):
                delay = 2 ** attempt
            else:
                break
        attempt += 1
        if attempt < 3:
            time.sleep(delay)
    msg = f"gh api {path.split('?')[0]} failed: {err}"
    if not fatal:
        raise GhError(msg)
    die(msg)


# Lookup caches for compare and commit calls. A failed lookup is cached as None and counted once.
_cache, _lock, _failed = {}, threading.Lock(), []


def reset_lookups():
    with _lock:
        _cache.clear()
        _failed.clear()


def _lookup(key, fn):
    with _lock:
        if key in _cache:
            return _cache[key]
    try:
        val = fn()
    except GhError as e:
        val = None
        with _lock:
            _failed.append(str(e))
    with _lock:
        _cache[key] = val
    return val


def compare(repo, base, head):
    """Compare status of base...head ('ahead' = head is ahead of base), or None if the lookup failed."""
    return _lookup(("cmp", base, head),
                   lambda: gh(f"repos/{repo}/compare/{base}...{head}?per_page=1", fatal=False)["status"])


def commit_msg(repo, sha):
    return _lookup(("msg", sha), lambda: gh(f"repos/{repo}/commits/{sha}", fatal=False)["commit"]["message"])


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() if s else None


def pct(vals, p):
    s = sorted(vals)
    if not s:
        return 0.0
    k = -(-p * len(s) // 100)
    return s[min(len(s) - 1, max(0, k - 1))]


def human(sec):
    if sec is None:
        return "n/a"
    if sec < 60:
        return f"{sec:.0f}s"
    if sec < 3600:
        return f"{sec / 60:.1f}min"
    if sec < DAY:
        return f"{sec / 3600:.1f}h"
    return f"{sec / DAY:.1f}d"


def paged(path, q, stop=None):
    out, page = [], 1
    while True:
        batch = gh(f"{path}?{urlencode({**q, 'per_page': 100, 'page': page})}")
        out += batch
        if len(batch) < 100 or (stop and stop(batch)):
            return out
        page += 1


def fetch_deployments(repo, env, cutoff):
    deps = paged(f"repos/{repo}/deployments", {"environment": env},
                 stop=lambda b: ts(b[-1]["created_at"]) < cutoff)
    return [d for d in deps if ts(d["created_at"]) >= cutoff]


def classify(dep, statuses):
    states = {s["state"] for s in statuses}
    succ = [ts(s["created_at"]) for s in statuses if s["state"] == "success"]
    return {
        "id": dep["id"], "sha": dep["sha"], "created": ts(dep["created_at"]),
        "success": min(succ) if succ else None,
        "failed": not succ and bool(states & {"failure", "error"}),
        "no_statuses": not statuses,
        "in_progress": bool(statuses) and not (states & TERMINAL),
    }


def merged_prs(repo, branch, cutoff):
    prs = paged(f"repos/{repo}/pulls", {"state": "closed", "base": branch, "sort": "updated", "direction": "desc"},
                stop=lambda b: ts(b[-1]["updated_at"]) < cutoff)
    return [p for p in prs if p.get("merged_at") and ts(p["merged_at"]) >= cutoff]


def contains(repo, merge_sha, deploy_sha):
    return merge_sha == deploy_sha or compare(repo, merge_sha, deploy_sha) in ("identical", "ahead")


def first_containing(repo, merge_sha, cands):
    """First deployment in cands (sorted by time) that contains merge_sha. Bisect, then verify against the last one."""
    if not cands:
        return None
    has = lambda d: contains(repo, merge_sha, d["sha"])
    lo, hi = 0, len(cands)
    while lo < hi:
        mid = (lo + hi) // 2
        if has(cands[mid]):
            hi = mid
        else:
            lo = mid + 1
    if has(cands[-1]) == (lo < len(cands)):
        return cands[lo] if lo < len(cands) else None
    # Non-linear history: a later deployment contradicts the bisect. Scan linearly.
    return next((d for d in cands if has(d)), None)


def collapse(succ):
    """Merge consecutive successful deployments with the same sha, keeping the earliest success."""
    out = []
    for d in succ:
        if not out or out[-1]["sha"] != d["sha"]:
            out.append(d)
    return out


def compute(repo, branch, recs, prs, cutoff, now, days, max_prs=200):
    """Core computation on plain data. recs: classified deployments (lookback included). prs: merged PR dicts."""
    shas = sorted({r["sha"] for r in recs})
    with ThreadPoolExecutor(max_workers=8) as pool:
        status = dict(zip(shas, pool.map(lambda s: compare(repo, branch, s), shas)))
    # Dropped only when the lookup worked and the sha is not an ancestor of (or equal to) the default branch.
    keep = lambda r: status[r["sha"]] is None or status[r["sha"]] in ("behind", "identical")
    kept = [r for r in recs if keep(r)]
    dropped = len(recs) - len(kept)

    succ_all = sorted((r for r in kept if r["success"] is not None), key=lambda r: r["success"])
    in_window = [r for r in succ_all if r["success"] >= cutoff]
    durations = [r["success"] - r["created"] for r in in_window if r["success"] >= r["created"]]
    chain = collapse(succ_all)
    win = [d for d in chain if d["success"] >= cutoff]
    failed = [r for r in kept if r["failed"] and r["created"] >= cutoff]
    in_progress = [r for r in kept if r["in_progress"]]

    def check(i):
        cur, nxt = chain[i], chain[i + 1]
        if cur["success"] < cutoff:
            return None
        if compare(repo, nxt["sha"], cur["sha"]) == "ahead":
            pass  # nxt is an ancestor of cur: rollback
        else:
            msg = commit_msg(repo, nxt["sha"])
            if not (msg or "").startswith("Revert"):
                return None
        return {"deployment_id": cur["id"], "recovery": nxt["success"] - cur["success"]}
    with ThreadPoolExecutor(max_workers=8) as pool:
        cfs = [r for r in pool.map(check, range(len(chain) - 1)) if r]
    cfr = len(cfs) / len(win) if win else 0.0

    no_sha = [p["number"] for p in prs if not p.get("merge_commit_sha")]
    usable = sorted((p for p in prs if p.get("merge_commit_sha")), key=lambda p: p["merged_at"], reverse=True)
    capped = len(usable) > max_prs
    usable = usable[:max_prs]

    def lead(pr):
        merged = ts(pr["merged_at"])
        d = first_containing(repo, pr["merge_commit_sha"], [c for c in chain if c["success"] >= merged])
        return {"pr": pr["number"], "merged_at": pr["merged_at"], "deployment_id": d["id"] if d else None,
                "lead": d["success"] - merged if d else None}
    with ThreadPoolExecutor(max_workers=8) as pool:
        leads = list(pool.map(lead, usable))

    span = max(DAY, min(days * DAY, now - win[0]["success"])) if win else days * DAY
    return {
        "dropped_off_branch": dropped, "recs_kept": len(kept), "successful": len(in_window),
        "distinct_deploys": len(win), "failed_before_success": len(failed), "in_progress": len(in_progress),
        "durations": durations, "change_failures": cfs, "cfr": cfr,
        "per_week": len(win) / (span / WEEK), "leads": leads, "prs_no_merge_sha": no_sha,
        "prs_capped": capped, "prs_measured": len(usable),
    }


def band_lead(s):
    if s is None:
        return None
    return "Elite" if s < DAY else "High" if s < WEEK else "Medium" if s < 30 * DAY else "Low"


def band_freq(per_week):
    return "Elite" if per_week > 7 else "High" if per_week >= 1 else "Medium" if per_week * 52 / 12 >= 1 else "Low"


def band_cfr(rate):
    # Published 2024 values: Elite 5, High 20, Medium 10, Low 40 (%). Nearest wins; ties go to the earlier band.
    return min([("Elite", 5), ("High", 20), ("Medium", 10), ("Low", 40)], key=lambda b: abs(b[1] - rate * 100))[0]


def band_rec(s):
    if s is None:
        return None
    return "Elite" if s < 3600 else "High" if s < DAY else "Low" if s >= 7 * DAY else "Medium"


ORDER = {"Elite": 0, "High": 1, "Medium": 2, "Low": 3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", metavar="OWNER/REPO")
    ap.add_argument("--environment", default="production")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--max-prs", type=int, default=200)
    ap.add_argument("--force", action="store_true", help="skip the rate limit pre-check")
    ap.add_argument("--json", dest="out")
    a = ap.parse_args()

    now = time.time()
    cutoff = now - a.days * DAY
    deps = fetch_deployments(a.repo, a.environment, cutoff - LOOKBACK_DAYS * DAY)
    if not deps:
        envs = [e["name"] for e in gh(f"repos/{a.repo}/environments").get("environments", [])]
        die(f"no deployments for environment {a.environment!r} in the last {a.days + LOOKBACK_DAYS} days in {a.repo}; "
            f"available environments: {', '.join(envs) or '(none)'}")

    core, est = rate_core(), len(deps) * 3 + 200
    if core and core[0] < est and not a.force:
        die(f"core rate limit remaining {core[0]} is below the estimate {est}; resets at {fmt_ts(core[1])} (use --force to run anyway)")

    def statuses(d):
        try:
            return d, gh(f"repos/{a.repo}/deployments/{d['id']}/statuses?per_page=100", fatal=False)
        except GhError as e:
            with _lock:
                _failed.append(str(e))
            return d, None
    reset_lookups()
    with ThreadPoolExecutor(max_workers=8) as pool:
        got = list(pool.map(statuses, deps))
    recs = [classify(d, s) for d, s in got if s is not None]
    nostat = [r["id"] for r in recs if r["no_statuses"]]
    if nostat:
        print(f"warning: {len(nostat)} deployments have no statuses (GitHub may delete statuses older than 90 days)", file=sys.stderr)

    branch = gh(f"repos/{a.repo}")["default_branch"]
    prs = merged_prs(a.repo, branch, cutoff)
    r = compute(a.repo, branch, recs, prs, cutoff, now, a.days, a.max_prs)

    lt = [x["lead"] for x in r["leads"] if x["lead"] is not None]
    undeployed = [x["pr"] for x in r["leads"] if x["lead"] is None]
    rec = [c["recovery"] for c in r["change_failures"]]
    p = lambda v, q: pct(v, q) if v else None
    stats = {
        "lead_time": {"p50": p(lt, 50), "p95": p(lt, 95), "n": len(lt)},
        "deploy_duration": {"p50": p(r["durations"], 50), "p95": p(r["durations"], 95), "n": len(r["durations"])},
        "recovery_time": {"p50": p(rec, 50), "p95": p(rec, 95), "n": len(rec)},
    }
    bands = {
        "lead_time": band_lead(stats["lead_time"]["p50"]),
        "deploy_frequency": band_freq(r["per_week"]) if r["distinct_deploys"] else None,
        "change_failure_rate": band_cfr(r["cfr"]) if r["distinct_deploys"] else None,
        "recovery_time": band_rec(stats["recovery_time"]["p50"]),
    }
    ranked = [(ORDER[b], i, m) for i, (m, b) in enumerate(bands.items()) if b]
    fix = None
    if ranked:
        worst = max(o for o, _, _ in ranked)
        fix = next(m for o, _, m in sorted(ranked, key=lambda x: x[1]) if o == worst)  # ties: lead time first

    print(f"Repo: {a.repo} | env: {a.environment} | window: {a.days}d | default branch: {branch}")
    print(f"Window: only deployments whose success time is in the last {a.days}d are counted; "
          f"{LOOKBACK_DAYS} more days were fetched as ancestry context for rollback and redeploy checks.")
    print(f"Deployments: {len(recs)} | dropped (sha not on {branch}): {r['dropped_off_branch']} | "
          f"successful (in window): {r['successful']} | distinct deploys (same-sha repeats collapsed): {r['distinct_deploys']} | "
          f"failed before success: {r['failed_before_success']} | in progress: {r['in_progress']}")
    print("(failed before success = failure/error with no success; they never reached prod, so they are NOT change failures)")
    print(f"Merged PRs: {r['prs_measured']} measured | deployed: {len(lt)} | not yet deployed: {len(undeployed)} | "
          f"no merge_commit_sha: {len(r['prs_no_merge_sha'])}")
    if r["prs_capped"]:
        print(f"warning: more merged PRs than --max-prs {a.max_prs}; measured the newest {a.max_prs} by merge time", file=sys.stderr)
    if r["prs_no_merge_sha"]:
        print(f"PRs with no merge_commit_sha (not measured): {r['prs_no_merge_sha'][:20]}")
    if undeployed:
        print(f"Not yet deployed PRs: {undeployed[:20]}{' ...' if len(undeployed) > 20 else ''}")
    print()
    print(f"{'METRIC':<18} {'n':>4} {'p50':>9} {'p95':>9}")
    for name, s in stats.items():
        extra = f"   ({len(lt)} deployed of {r['prs_measured']} merged)" if name == "lead_time" else ""
        print(f"{name:<18} {s['n']:>4} {human(s['p50']):>9} {human(s['p95']):>9}{extra}")
    if r["prs_measured"] and len(undeployed) * 10 > r["prs_measured"]:
        print(f"note: {len(undeployed)} PRs not yet deployed are excluded from lead time; real lead time is worse")
    print()
    print(f"Deploys/week: {r['per_week']:.2f}")
    print(f"Change failure rate: {r['cfr'] * 100:.1f}% ({len(r['change_failures'])} of {r['distinct_deploys']})")
    print()
    print("DORA 2024 bands (lead <1d Elite, 1d-1w High, 1w-1mo Medium, 1-6mo Low; freq multiple/day Elite, daily-weekly High, weekly-monthly Medium, monthly-6 monthly Low;")
    print("                 CFR 5% Elite, 10% Medium, 20% High, 40% Low; recovery <1h Elite, <1d High/Medium, 1w-1mo Low)")
    for m, b in bands.items():
        print(f"  {m:<20} {b or 'n/a'}")
    print("  CFR and recovery show the nearest band: bands are survey clusters, not targets")
    print(f"Fix first: {fix or 'n/a'}")

    if a.out:
        with open(a.out, "w") as f:
            json.dump({"repo": a.repo, "environment": a.environment, "days": a.days, "default_branch": branch,
                       "counts": {"deployments": len(recs), "dropped_off_branch": r["dropped_off_branch"],
                                  "successful": r["successful"], "distinct_deploys": r["distinct_deploys"],
                                  "failed_before_success": r["failed_before_success"], "in_progress": r["in_progress"],
                                  "merged_prs": r["prs_measured"], "deployed_prs": len(lt),
                                  "not_yet_deployed_prs": len(undeployed), "prs_no_merge_sha": len(r["prs_no_merge_sha"])},
                       "stats": stats, "deploys_per_week": r["per_week"], "change_failure_rate": r["cfr"],
                       "change_failures": r["change_failures"], "bands": bands, "fix_first": fix,
                       "no_status_deployments": nostat, "failed_lookups": len(_failed),
                       "leads": r["leads"], "undeployed_prs": undeployed}, f, indent=2)
    if _failed:
        print(f"warning: {len(_failed)} lookups failed; results are incomplete", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
