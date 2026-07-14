#!/usr/bin/env python3
"""Collect Azure DevOps metrics: closed User Stories grouped by assignee.

One WIQL query for all closed User Stories changed since the full-window start,
then a batched field fetch (200 ids/call). Keyed by assignee email (uniqueName)
so cohort matching is exact. Auth via AZURE_DEVOPS_PAT (never printed).

Usage: python collect_ado.py [config.json] [out_dir]
Writes: <out>/ado_raw.json
"""
import json
import os
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

CFG_PATH, OUT = config.resolve_paths(sys.argv)
CFG = config.load(CFG_PATH)
W = config.windows(CFG)
BASE = CFG["ado_base"]
FULL_START = W["full_start"]
PAT = os.environ.get("AZURE_DEVOPS_PAT")
if not PAT:
    sys.exit("AZURE_DEVOPS_PAT not set. Regenerate a Work-Items (read) token at "
             "your ADO org's _usersSettings/tokens page and export it.")

FIELDS = ["System.Id", "System.AssignedTo",
          "Microsoft.VSTS.Scheduling.StoryPoints",
          "System.ChangedDate", "System.State", "System.WorkItemType"]


def ado_post(path, body):
    p = subprocess.run(
        ["curl", "-s", "-u", f":{PAT}", "-H", "Content-Type: application/json",
         "-X", "POST", f"{BASE}{path}", "-d", json.dumps(body)],
        capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"curl failed: {p.stderr}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        sys.exit(f"bad ADO response: {p.stdout[:300]}")


wiql = (f"SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.WorkItemType] = 'User Story' AND [System.State] = 'Closed' "
        f"AND [System.ChangedDate] >= '{FULL_START}' "
        f"ORDER BY [System.ChangedDate] DESC")
res = ado_post("/_apis/wit/wiql?api-version=7.1", {"query": wiql})
if "message" in res:
    sys.exit(f"WIQL error: {res['message']}")
ids = [w["id"] for w in res.get("workItems", [])]
print(f"WIQL: {len(ids)} closed User Stories since {FULL_START}", file=sys.stderr)

by_email, by_email_name, unassigned = defaultdict(list), {}, 0
for i in range(0, len(ids), 200):
    data = ado_post("/_apis/wit/workitemsbatch?api-version=7.1",
                    {"ids": ids[i:i + 200], "fields": FIELDS})
    for item in data.get("value", []):
        f = item["fields"]
        assignee = f.get("System.AssignedTo")
        email = (assignee.get("uniqueName") or "").lower() if assignee else ""
        if not email:
            unassigned += 1
            continue
        by_email_name[email] = assignee.get("displayName", "")
        sp = f.get("Microsoft.VSTS.Scheduling.StoryPoints")
        by_email[email].append({
            "id": f["System.Id"],
            "sp": sp if isinstance(sp, (int, float)) else None,
            "changed": f.get("System.ChangedDate"),
        })
    print(f"  fetched {min(i+200, len(ids))}/{len(ids)}", file=sys.stderr)

out = {"by_email": dict(by_email), "display_names": by_email_name,
       "unassigned": unassigned, "total_stories": len(ids), "windows": W}
open(os.path.join(OUT, "ado_raw.json"), "w").write(json.dumps(out, indent=2))
print(f"\nWrote {OUT}/ado_raw.json (assignees={len(by_email)}, unassigned={unassigned})",
      file=sys.stderr)
