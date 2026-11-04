# Trigger evals: agent-creator

Safe-run rules (repo standard): run every `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group, and
put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in this
repo.

Run: `python3 scripts/trigger_eval.py --skill agent-creator` (7 cases, 3 runs
each, 21 runs).

What it covers: five real asks must load `agent-creator`; two near-misses must
load `skill-creator` instead (a skill, its description, its structure).

This card has not been run yet. The first pass reached the Claude 5-hour limit
before this card started, so the expectations are unconfirmed.

No agent files are written: under `--tools "Skill,Read"` the body can read but
not write, and this card only measures which skill the router picks.
