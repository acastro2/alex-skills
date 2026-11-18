# Evals: coding

Safe-run rules (repo standard): every `claude -p` run uses `--strict-mcp-config --tools "Skill,Read"`, in its own process group. Workspaces go under `~/.agents/skill-workspace/alex-skills/coding/`, never in this repo. Grade countable things in code and yes-or-no claims with Jev.

| Set | What it proves | Run |
| --- | --- | --- |
| `trigger-evals.json` | The description loads the skill for code, PR, Terraform, and UI tasks, and stays quiet for near misses (critique a PR, an email, a diagram, a ticket) | `python3 scripts/run_triggers.py --skill coding <out>` |
| `behaviour/` | Four rules change what the model does: an exact module pin in a CI-applied root, the prune before done, a delegated worker that does not stop to ask for seams, and no test-first ceremony for a one-off script | `python3 coding/tests/behaviour/run_behaviour.py <iteration> --baseline-skill <snapshot>`, then `python3 coding/tests/behaviour/grade.py <iteration>` |
| `pr-description/` | The PR description shape. See its own README | `coding/tests/pr-description/` |

Behaviour notes:

- The baseline is a snapshot of the skill before the edit, installed as the project skill `code-rules-v0` in each baseline cwd, with `Skill(coding)` denied. Each prompt says "Follow my coding standards skill", so both configs load a version of the rules. `grade.py` records the skills each run loaded; a run that loaded neither version is not a fair comparison.
- `~/.claude/CLAUDE.md` is loaded in every run, as it is in real use.
- All fixtures are synthetic. The runs have no shell, so the prompts say the tests cannot run; a reply that claims they pass fails.
