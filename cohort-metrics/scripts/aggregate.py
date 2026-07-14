#!/usr/bin/env python3
"""Aggregate raw GitHub + ADO pulls into group comparisons.

Groups are defined per-system: GitHub by resolved login, ADO by email. Rates are
per-active-engineer-per-week so the (short, growing) "after" window compares
fairly to the longer baselines.

Rates use PER-METRIC denominators: someone who only reviews, or only closes ADO
stories, is NOT counted as a zero in the authored-PR rate. Counting them as zeros
would punish role specialisation (a QA/BA who closes tickets but merges no PRs)
and understate the real per-author throughput. Each rate is over the people
active in THAT metric, symmetric across cohort and rest.

Usage: python aggregate.py [config.json] [out_dir]
Writes: <out>/metrics.json, <out>/per_person.csv (per_person is PRIVATE)
"""
import csv
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

CFG_PATH, OUT = config.resolve_paths(sys.argv)
CFG = config.load(CFG_PATH)
W = config.windows(CFG)
GH = json.loads(open(os.path.join(OUT, "github_raw.json")).read())
ADO = json.loads(open(os.path.join(OUT, "ado_raw.json")).read())

FULL_START, SNAP_START = W["full_start"], W["snapshot_start"]
BETA, TODAY = W["beta_start"], W["today"]
WEEKS = W["weeks"]

cohort_emails = {p["email"].lower() for p in CFG["cohort"]}
cohort_logins = set(GH["cohort_logins"])
resolved = GH["resolved"]
login_to_email = {v: k for k, v in resolved.items() if v}


def in_window(iso, win):
    if not iso:
        return False
    day = iso[:10]
    if win == "snapshot":
        return SNAP_START <= day <= TODAY
    if win == "before":
        return FULL_START <= day < BETA
    if win == "after":
        return BETA <= day <= TODAY
    return False


def count_in(datemap, win):
    return sum(1 for iso in datemap.values() if in_window(iso, win))


def stories_in(items, win):
    return sum(1 for it in items if in_window(it["changed"], win))


def points_in(items, win):
    return sum((it["sp"] or 0) for it in items if in_window(it["changed"], win))


def stats(values):
    if not values:
        return {"n": 0, "mean": 0.0, "median": 0.0}
    return {"n": len(values), "mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2)}


def gh_person(login, win):
    return (count_in(GH["authored"].get(login, {}), win),
            count_in(GH["reviewed"].get(login, {}), win))


def ado_person(email, win):
    items = ADO["by_email"].get(email, [])
    return stories_in(items, win), points_in(items, win)


def github_group(win, logins):
    wk = WEEKS[win]
    ar, rr, ta, tr, active = [], [], 0, 0, 0
    for lg in logins:
        a, r = gh_person(lg, win)
        ta += a
        tr += r
        if a:
            ar.append(a / wk)
        if r:
            rr.append(r / wk)
        if a or r:
            active += 1
    return {"authored": stats(ar), "reviewed": stats(rr),
            "total_authored": ta, "total_reviewed": tr, "n_active": active}


def ado_group(win, emails):
    wk = WEEKS[win]
    sr, pr, ts, tp = [], [], 0, 0.0
    for em in emails:
        s, p = ado_person(em, win)
        ts += s
        tp += p
        if s:
            sr.append(s / wk)
            pr.append(p / wk)
    return {"stories": stats(sr), "points": stats(pr),
            "total_stories": ts, "total_points": round(tp, 1), "n_active": len(sr)}


gh_logins = set(GH["authored"]) | set(GH["reviewed"])
rest_logins = gh_logins - cohort_logins
rest_emails = set(ADO["by_email"]) - cohort_emails

snapshot = {
    "github": {"cohort": github_group("snapshot", cohort_logins),
               "rest": github_group("snapshot", rest_logins)},
    "ado": {"cohort": ado_group("snapshot", cohort_emails),
            "rest": ado_group("snapshot", rest_emails)},
}
beforeafter = {w: {"github": github_group(w, cohort_logins),
                   "ado": ado_group(w, cohort_emails)}
               for w in ("before", "after")}

metrics = {
    "generated_windows": {**W, "snapshot_start": SNAP_START},
    "counts": {
        "cohort_size": len(CFG["cohort"]),
        "cohort_logins_resolved": len(cohort_logins),
        "rest_gh_authors_reviewers": len(rest_logins),
        "rest_ado_assignees": len(rest_emails),
        "member_count": GH.get("member_count"),
        "ado_total_stories": ADO.get("total_stories"),
    },
    "snapshot": snapshot, "beforeafter": beforeafter,
    "resolve_method": GH.get("resolve_method", {}),
    "truncated_chunks": GH.get("truncated_chunks", []),
    "review_truncated": GH.get("review_truncated", []),
}
open(os.path.join(OUT, "metrics.json"), "w").write(json.dumps(metrics, indent=2))

# Per-person CSV (PRIVATE — individual numbers, never a public leaderboard)
rows = []
for p in CFG["cohort"]:
    em, lg = p["email"].lower(), resolved.get(p["email"])
    for win in ("snapshot", "before", "after"):
        a, r = gh_person(lg, win) if lg else (0, 0)
        s, pts = ado_person(em, win)
        rows.append({"group": "cohort", "name": p["name"], "login": lg or "",
                     "email": em, "tier": p.get("tier", ""), "window": win,
                     "authored_prs": a, "reviewed_prs": r,
                     "closed_stories": s, "story_points": pts})
for lg in sorted(rest_logins):
    a, r = gh_person(lg, "snapshot")
    rows.append({"group": "rest", "name": "", "login": lg,
                 "email": login_to_email.get(lg, ""), "tier": "", "window": "snapshot",
                 "authored_prs": a, "reviewed_prs": r, "closed_stories": "", "story_points": ""})
for em in sorted(rest_emails):
    s, pts = ado_person(em, "snapshot")
    rows.append({"group": "rest", "name": ADO["display_names"].get(em, ""),
                 "login": "", "email": em, "tier": "", "window": "snapshot",
                 "authored_prs": "", "reviewed_prs": "", "closed_stories": s, "story_points": pts})

with open(os.path.join(OUT, "per_person.csv"), "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=["group", "name", "login", "email", "tier",
                                       "window", "authored_prs", "reviewed_prs",
                                       "closed_stories", "story_points"])
    wr.writeheader()
    wr.writerows(rows)

print(f"Wrote {OUT}/metrics.json + {OUT}/per_person.csv")
gc, gr = snapshot["github"]["cohort"], snapshot["github"]["rest"]
ac, ar = snapshot["ado"]["cohort"], snapshot["ado"]["rest"]
print(f"snapshot  PRs/wk cohort={gc['authored']['mean']} rest={gr['authored']['mean']} | "
      f"reviews cohort={gc['reviewed']['mean']} rest={gr['reviewed']['mean']} | "
      f"stories cohort={ac['stories']['mean']} rest={ar['stories']['mean']}")
