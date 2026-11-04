# Trigger evals: grilling

Safe-run rules (repo standard): run every `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group, and
put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in this
repo.

Run: `python3 scripts/trigger_eval.py --skill grilling` (7 cases, 3 runs each,
21 runs).

What it covers: five real asks must load `grilling`; two near-misses must load
`reviewer` instead (an ADR, a PR). This is the card that measures the "grill"
collision: `reviewer`'s description also claims "grill, poke holes in, tear
apart", so a bare "grill me" can route to either.

First run 2026-11-03 was partial: four cases passed 3/3, and the last three
never ran because the Claude 5-hour limit was reached. Re-run before trusting
the near-miss side.

No files are read by the body in a way that matters: under
`--tools "Skill,Read"` the grill runs on the prompt alone, and this card only
measures which skill the router picks.
