# Trigger evals: reviewer

Safe-run rules (repo standard): run every `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group, and
put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in this
repo.

Run: `python3 scripts/trigger_eval.py --skill reviewer` (7 cases, 3 runs each,
21 runs).

What it covers: five real asks must load `reviewer`; two near-misses must load
`grilling` instead, because the user wants to be questioned rather than have an
artefact reviewed.

This card has not been run yet. The first pass reached the Claude 5-hour limit
before this card started, so the expectations are unconfirmed.

This is the control card for the "grill" collision. `reviewer` was not edited:
the exclusion would have gone into `grilling`'s description, so this card shows
whether a one-sided fix is enough.
