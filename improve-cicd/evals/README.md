# Evals: improve-cicd

Safe-run rules (repo standard): every `claude -p` run uses `--strict-mcp-config --tools "Skill,Read"`, in its own process group. Workspaces go under `~/.agents/skill-workspace/alex-skills/improve-cicd/`, never in this repo. Grade countable things in code and yes-or-no claims with Jev.

| Set | What it proves | Run |
| --- | --- | --- |
| `behaviour/` | Five cases (ci, cd, tofu, helm, approval): the skill beats no skill on the fixed CI/CD fixes, and keeps the approval gate | `python3 -I improve-cicd/tests/behaviour/run_behaviour.py <iteration>`, then `python3 -I improve-cicd/tests/behaviour/grade.py <iteration>`. Add `--only helm,ci`, `--runs N` (default 3), `--dry-run` |

Behaviour notes:

- Two configs. `with_skill`: the prompt says "Use my improve-cicd skill. ". `without_skill`: no skill line, and `Skill(improve-cicd)` plus `Read` of the skill folder are denied (absolute paths need the leading `//` in Claude Code permission syntax). `grade.py` prints `skills_loaded` per run: check that with_skill loaded it and without_skill did not.
- Fixtures are copied to `<iteration>/fixtures`, a neutral path, so a denied run cannot read the skill from disk.
- The runs have no shell and cannot change files. The reply is the workflow in a yaml block plus a plan.
- Code checks run on the yaml blocks of the reply. `[jev]` expectations get one Jev call per run, all positive questions; 0.80 or more passes, 0.20 or less fails, between is UNSURE and counts as not passed. `grade.py` prints the UNSURE count: send those to an LLM grader (`jev/references/eval-grading.md`).
- `benchmark.json` holds the mean pass rate and the mean cost (USD) and seconds per case and config.
