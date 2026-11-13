# projects-curator evals

Read this before you run anything here.

- `trigger-evals.json`: run with `python3 scripts/run_triggers.py --skill projects-curator <out-dir>`.
- `evals.json` + `files/`: behavior evals, run with
  `python3 projects-curator/tests/run_iteration.py <iteration-dir> --runs 2`.
  Configs: `with_skill` (the live skill) and `old_skill` (a snapshot of the skill at `--ref`, default `HEAD`).

## Safe-run rules

- Every run is `claude -p` with `--strict-mcp-config --tools "Skill,Read"` in its own process group. No shell,
  no Atlassian MCP: a run cannot touch Jira or Confluence. Check that no `claude` process is left after a run.
- Both configs are denied the real ledger (`curated.json`) and this folder. Why: the ledger holds org facts, and
  this folder holds the expectations. `timing.json` records `real_ledger_reads`; it must be empty.
- The fixtures are a made-up org ("Acme"). Never put a real site, key, page id or name in `files/`: this folder
  is force-added to a public repo.
- Put iteration dirs under `~/.agents/skill-workspace/alex-skills/projects-curator/`, never in this repo.
- Grade yes-or-no expectations with Jev (`../../jev/references/eval-grading.md`); grade exact strings in code.
  Eval 1 expectation 2 (`edit_entry,3,`) and eval 2 expectation 1 (`P1`) are code checks.
