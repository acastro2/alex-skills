#!/usr/bin/env python3
"""Compare every upstream-copied skill with its upstream. Read-only; needs `gh` signed in.

For each skill in UPSTREAMS it lists the files that match upstream's default branch by git
blob hash, the files that differ, and the files only one side has. With --detail it also
counts the upstream commits on the path since our last local commit, and diffs SKILL.md
with our `## Asking` block removed, so a local edit and upstream drift read apart.

    python3 -I scripts/upstream_audit.py               # one line per skill
    python3 -I scripts/upstream_audit.py --detail      # plus commits since, SKILL.md diff
    python3 -I scripts/upstream_audit.py archify peekaboo --json

A difference is not drift by itself: a skill we copy from a release (archify) or a package
(reverse-engineer-anything) differs from `main`. Read the README "Upstream provenance" row
before calling a skill behind. Keep UPSTREAMS in step with that table.
"""
from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (folder in this repo, upstream repo, path in that repo; "" means the repo root)
UPSTREAMS: list[tuple[str, str, str]] = [
    ("grilling", "mattpocock/skills", "skills/productivity/grilling"),
    ("codebase-design", "mattpocock/skills", "skills/engineering/codebase-design"),
    ("domain-modeling", "mattpocock/skills", "skills/engineering/domain-modeling"),
    ("improve-codebase-architecture", "mattpocock/skills", "skills/engineering/improve-codebase-architecture"),
    ("implement", "mattpocock/skills", "skills/engineering/implement"),
    ("find-skills", "vercel-labs/skills", "skills/find-skills"),
    ("skill-creator/vendor/codex", "openai/skills", "skills/.system/skill-creator"),
    ("skill-creator/vendor/claude", "anthropics/skills", "skills/skill-creator"),
    ("peekaboo", "openclaw/Peekaboo", "skills/peekaboo"),
    ("archify", "tt-a1i/archify", "archify"),
    ("herdr", "herdrdev/herdr", "skills/herdr"),
    ("browser-control", "anomalyco/browse", "cli/skills/browse"),
    ("security-audit", "cloudflare/security-audit-skill", "skills/security-audit"),
    ("reverse-engineer-anything", "morluto/rea", ".agents/skills/reverse-engineer-anything"),
    ("autoresearch", "uditgoenka/autoresearch", ".agents/skills/autoresearch"),
    ("ub-mode", "unclebob/ub-mode", ""),
    ("unslop", "heydamir/unslop", "skills/unslop"),
    ("isoscene", "cintelis/isoscene", ""),
] + [
    (f"threejs-{t}", "CloudAI-X/threejs-skills", f"skills/threejs-{t}")
    for t in ("animation", "asset-pipeline", "fundamentals", "geometry", "interaction", "lighting",
              "loaders", "materials", "performance", "postprocessing", "react-three-fiber",
              "shaders", "textures")
]

SKIP_DIRS = {"__pycache__", ".venv", "node_modules", "evals", "tests", ".pytest_cache"}
# installed tool checkouts, not part of the copied skill (ub-mode/tools/setup.sh writes them)
SKIP_PATHS = {"ub-mode/tools/src", "ub-mode/tools/bin"}


def gh(path: str):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


_trees: dict[str, tuple[str, str, str, dict[str, str]]] = {}


def upstream_tree(repo: str):
    if repo not in _trees:
        branch = gh(f"repos/{repo}")["default_branch"]
        head = gh(f"repos/{repo}/commits/{branch}")
        tree = gh(f"repos/{repo}/git/trees/{head['sha']}?recursive=1")
        blobs = {e["path"]: e["sha"] for e in tree["tree"] if e["type"] == "blob"}
        _trees[repo] = (branch, head["sha"][:7], head["commit"]["committer"]["date"][:10], blobs)
    return _trees[repo]


def local_blobs(folder: str) -> dict[str, str]:
    base = os.path.join(ROOT, folder)
    paths = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                       and os.path.relpath(os.path.join(dirpath, d), ROOT) not in SKIP_PATHS]
        paths += [os.path.join(dirpath, f) for f in filenames]
    if not paths:
        return {}
    shas = subprocess.run(["git", "hash-object", "--", *paths], capture_output=True, text=True,
                          check=True).stdout.split()
    return {os.path.relpath(p, base): s for p, s in zip(paths, shas)}


def strip_asking(text: str) -> str:
    return re.sub(r"\n## Asking\n\n.*?\n\n", "\n", text, flags=re.S)


def audit(folder: str, repo: str, path: str, detail: bool) -> dict:
    branch, head, date, blobs = upstream_tree(repo)
    prefix = f"{path}/" if path else ""
    ours = local_blobs(folder)
    theirs = {p[len(prefix):]: s for p, s in blobs.items() if p.startswith(prefix)}
    if not path:  # a repo-root skill: compare only top-level files and files we also ship
        theirs = {p: s for p, s in theirs.items() if p in ours or "/" not in p}
    row = {
        "skill": folder, "repo": repo, "branch": branch, "head": head, "head_date": date,
        "same": sum(1 for p in ours if theirs.get(p) == ours[p]),
        "differ": sorted(p for p in ours if p in theirs and theirs[p] != ours[p]),
        "ours_only": sorted(p for p in ours if p not in theirs),
        "upstream_only": sorted(p for p in theirs if p not in ours),
    }
    if detail and (row["differ"] or row["upstream_only"]):
        since = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%cI", "--", folder],
                               capture_output=True, text=True).stdout.strip()
        query = f"repos/{repo}/commits?sha={branch}&per_page=100" + (f"&since={since}" if since else "")
        commits = gh(query + (f"&path={path}" if path else "")) or []
        row["last_local_commit"] = since[:10]
        row["upstream_commits_since"] = [c["sha"][:7] + " " + c["commit"]["message"].splitlines()[0][:80]
                                         for c in commits]
        if "SKILL.md" in row["differ"]:
            blob = gh(f"repos/{repo}/contents/{prefix}SKILL.md?ref={branch}")
            up = base64.b64decode(blob["content"]).decode() if blob else ""
            mine = strip_asking(open(os.path.join(ROOT, folder, "SKILL.md"), encoding="utf-8").read())
            lines = [line for line in difflib.unified_diff(up.splitlines(), mine.splitlines(), lineterm="", n=0)
                     if line[:1] in "+-" and not line.startswith(("+++", "---"))]
            row["skill_md_without_asking"] = {"upstream_only_lines": sum(l.startswith("-") for l in lines),
                                              "our_only_lines": sum(l.startswith("+") for l in lines)}
    return row


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("skills", nargs="*", help="limit to these folders")
    ap.add_argument("--detail", action="store_true", help="commits since our last change, SKILL.md diff")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args(argv)
    rows = [audit(f, r, p, args.detail) for f, r, p in UPSTREAMS if not args.skills or f in args.skills]
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    for r in rows:
        print(f"{r['skill']:32} {r['repo']:32} {r['head']} {r['head_date']}  same={r['same']} "
              f"differ={len(r['differ'])} ours_only={len(r['ours_only'])} upstream_only={len(r['upstream_only'])}")
        for key in ("differ", "ours_only", "upstream_only"):
            if r[key]:
                shown = r[key][:6] + (["..."] if len(r[key]) > 6 else [])
                print(f"    {key}: {', '.join(shown)}")
        if "upstream_commits_since" in r:
            print(f"    upstream commits since {r['last_local_commit'] or 'ever'}: {len(r['upstream_commits_since'])}")
            for c in r["upstream_commits_since"][:5]:
                print(f"      {c}")
        if "skill_md_without_asking" in r:
            d = r["skill_md_without_asking"]
            print(f"    SKILL.md minus Asking: {d['upstream_only_lines']} upstream-only lines, {d['our_only_lines']} ours-only")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
