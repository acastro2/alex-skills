#!/usr/bin/env python3
"""Audit GitHub Actions CI timing: waiting, setup and running per job, p50 and p95."""
import argparse
import json
import math
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlencode

SETUP_RE = re.compile(
    r"^(?!post )(set up job|set ?up\b|setup\b|run actions/(checkout|cache|setup-)|run [\w.-]+/setup-|checkout\b|install\b|restore\b|cache\b)",
    re.I,
)


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


class GhError(Exception):
    pass


def gh(path, fatal=True):
    # Transient 5xx, stream resets, bad JSON and rate limits are retried; then skip the run or exit 2.
    err = ""
    for attempt in range(3):
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
            if re.search(r"HTTP (429|403)", err) and re.search(r"HTTP 429|rate limit", err, re.I):
                delay = (5, 15, 15)[attempt]
            elif re.search(r"HTTP 5\d\d|stream error", err):
                delay = 2 ** attempt
            else:
                break
        if attempt < 2:
            time.sleep(delay)
    msg = f"gh api {path.split('?')[0]} failed: {err}"
    if not fatal:
        raise GhError(msg)
    die(msg)


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() if s else None


def pct(vals, p):
    s = sorted(vals)
    if not s:
        return 0.0
    k = -(-p * len(s) // 100)
    return s[min(len(s) - 1, max(0, k - 1))]


def resolve_workflow(repo, workflow):
    if workflow.isdigit() or workflow.endswith((".yml", ".yaml")):
        return workflow
    names, page = {}, 1
    while True:
        batch = gh(f"repos/{repo}/actions/workflows?per_page=100&page={page}")["workflows"]
        names.update({w["name"]: w["id"] for w in batch})
        if len(batch) < 100:
            break
        page += 1
    if workflow not in names:
        die(f"workflow {workflow!r} not found; available: {', '.join(sorted(names)) or '(none)'}")
    return str(names[workflow])


def fetch_runs(repo, n, workflow, branch, event):
    base = f"repos/{repo}/actions/" + (f"workflows/{workflow}/runs" if workflow else "runs")
    q = {"status": "completed", "per_page": 100}
    if branch:
        q["branch"] = branch
    if event:
        q["event"] = event
    runs, page = [], 1
    while len(runs) < n:
        batch = gh(f"{base}?{urlencode({**q, 'page': page})}")["workflow_runs"]
        if not batch:
            break
        runs += [r for r in batch if r["conclusion"] not in ("cancelled", "skipped")]
        page += 1
    return runs[:n]


def fetch_jobs(repo, run_id):
    jobs, page = [], 1
    while True:
        # per_page=100 returns HTTP 502 on runs with many jobs; 50 does not (astral-sh/uv, 2026-11-24).
        batch = gh(f"repos/{repo}/actions/runs/{run_id}/jobs?filter=latest&per_page=50&page={page}", fatal=False)["jobs"]
        jobs += batch
        if len(batch) < 50:
            return jobs
        page += 1


def job_record(run, j):
    created, started, done = ts(j["created_at"]), ts(j["started_at"]), ts(j["completed_at"])
    if started is None or done is None or j["conclusion"] in ("skipped", "cancelled"):
        return None
    setup = 0.0
    for s in j.get("steps") or []:
        a, b = ts(s.get("started_at")), ts(s.get("completed_at"))
        if a is not None and b is not None and SETUP_RE.search(s["name"]):
            setup += max(0.0, b - a)
    total_run = done - started
    return {
        "run_id": run["id"],
        "job_id": j["id"],
        "name": f"{run['name']} / {j['name']}",
        "waiting": max(0.0, started - (created or started)),
        "setup": setup,
        "running": max(0.0, total_run - setup),
        "duration": max(0.0, total_run),
        "completed_ts": done,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", metavar="OWNER/REPO")
    ap.add_argument("--runs", type=int, default=150)
    ap.add_argument("--workflow")
    ap.add_argument("--branch")
    ap.add_argument("--event")
    ap.add_argument("--json", dest="out")
    a = ap.parse_args()

    workflow = resolve_workflow(a.repo, a.workflow) if a.workflow else None
    runs = fetch_runs(a.repo, a.runs, workflow, a.branch, a.event)
    def jobs_or_error(r):
        try:
            return r, fetch_jobs(a.repo, r["id"]), None
        except GhError as e:
            return r, None, e

    records, walls, skipped, empty = [], [], [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(jobs_or_error, runs))
    for r, jobs, err in results:
        if err:
            print(f"warning: skipped run {r['id']}: {err}", file=sys.stderr)
            skipped.append(r["id"])
            continue
        recs = [x for x in (job_record(r, j) for j in jobs) if x]
        ends = [ts(j["completed_at"]) for j in jobs if j["completed_at"]]
        if not recs or not ends:
            empty.append(r["id"])
            continue
        records += recs
        start = ts(r.get("run_started_at") or r["created_at"])
        walls.append(max(0.0, max(ends) - start))

    by_name = {}
    for r in records:
        by_name.setdefault(r["name"], []).append(r)
    buckets = ("waiting", "setup", "running", "total")
    stats = {}
    for name, rs in by_name.items():
        stats[name] = {"n": len(rs)}
        for b in buckets:
            vals = [x["waiting"] + x["duration"] if b == "total" else x[b] for x in rs]
            stats[name][b] = {"p50": pct(vals, 50), "p95": pct(vals, 95)}
    wall = {"p50": pct(walls, 50), "p95": pct(walls, 95)}

    w = max([len(n) for n in stats] + [len("RUN WALL TIME"), len("WORKFLOW / JOB")])
    hdr = f"{'WORKFLOW / JOB':<{w}} {'n':>4} " + " ".join(f"{b+' p50':>11} {b+' p95':>11}" for b in buckets)
    print(hdr)
    for name, s in sorted(stats.items()):
        cells = " ".join(f"{s[b]['p50']:>11.1f} {s[b]['p95']:>11.1f}" for b in buckets)
        print(f"{name:<{w}} {s['n']:>4} {cells}")
    print(f"{'RUN WALL TIME':<{w}} {len(walls):>4} " + " " * 72 + f"{wall['p50']:>11.1f} {wall['p95']:>11.1f}")

    sums = {b: sum(s[b]["p50"] for s in stats.values()) for b in buckets[:3]}
    print(f"Fix first: {max(sums, key=sums.get)}" if stats else "Fix first: n/a (no jobs)")
    print("(sum of p50 across jobs; parallel jobs overlap, so read it as where time goes, not wall time)")
    minutes = sum(math.ceil(r["duration"] / 60) for r in records)
    print(f"Billable-ish minutes: {minutes} | runs: {len(walls)} | jobs: {len(records)}")
    if skipped:
        print(f"warning: skipped {len(skipped)} runs whose jobs could not be fetched: {skipped}", file=sys.stderr)
    if empty:
        print(f"warning: {len(empty)} runs had no usable jobs: {empty}", file=sys.stderr)
    if len(runs) < a.runs:
        print(f"warning: fetched {len(runs)} runs, asked for {a.runs}; percentiles on a small sample are noisy", file=sys.stderr)

    if a.out:
        with open(a.out, "w") as f:
            json.dump({"repo": a.repo, "jobs": stats, "wall_time": wall, "skipped_runs": skipped, "empty_runs": empty, "records": records}, f, indent=2)
    if len(skipped) * 10 > len(runs):
        print(f"error: {len(skipped)} of {len(runs)} runs skipped (over 10%); numbers are partial", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
