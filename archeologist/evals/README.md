# Trigger evals: archeologist

Safe-run rules (repo standard): run every `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group, and
put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in this
repo.

Run: `python3 scripts/trigger_eval.py --skill archeologist` (7 cases, 3 runs
each, 21 runs).

What it covers: five real asks must load `archeologist`; two near-misses must
load the neighbour instead (`bard` for writing notes, `scribe` for a
transcript). The card exists because archeologist is read-only and returns a
briefing, while its neighbours write and pull.

This card was first run on 2026-11-03: 7/7.

No Microsoft 365 or git access is needed. Under `--tools "Skill,Read"` the body
cannot search anything, and this card only measures which skill the router
picks. Prompts are synthetic: no real colleagues, sessions, or PR numbers.
