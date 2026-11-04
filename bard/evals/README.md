# Trigger evals: bard

Safe-run rules (repo standard): run every `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group, and
put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in this
repo.

Run: `python3 scripts/trigger_eval.py --skill bard` (7 cases, 3 runs each,
21 runs).

What it covers: five real asks must load `bard`; two near-misses must load the
neighbour instead (`scribe` for a raw transcript, `archeologist` for a question
about who sent what). The card exists because bard reads scribe notes and the
comms that archeologist surfaces, so the three descriptions overlap.

This card was first run on 2026-11-03: 7/7.

No live vault, mail, or Teams access is needed. Under `--tools "Skill,Read"` the
body cannot write or fetch, and this card only measures which skill the router
picks. Prompts are synthetic: no real vault paths, task titles, or names.
