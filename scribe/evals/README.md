# Trigger evals: scribe

Safe-run rules (repo standard): run every `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group, and
put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in this
repo.

Run: `python3 scripts/trigger_eval.py --skill scribe` (7 cases, 3 runs each,
21 runs). The runner already passes the safe flags and writes results to the
workspace.

What it covers: five real asks must load `scribe`; two near-misses must load the
neighbour instead (`bard` for a vault sweep, `archeologist` for a history
question). The card exists because these three skills share inputs: sessions,
meetings, and comms.

This card was first run on 2026-11-03: 6/7. The one miss was a recall gap, not
a collision: "turn this recording into speaker labelled notes" picked no skill
in 1 of 3 runs.
