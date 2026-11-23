# search evals

Behavior evals for the run plan in `references/exa-agent.md`: one `agent_run` with an exact date range and an output schema for a list build, a script instead of one run per row for a 400-row batch, an honest report of a short run, and one `agent_run` with the three known rows in `input.data` (no script).

## What is evaluated

- Code checks: how many `agent_run` json blocks the model writes (exact counts, from `evals.json`).
- Judgment checks: yes or no questions about the answer, graded by Jev. Some are inverted (the answer must not do something).

## Safe run

No Exa call is ever made. `agent_run` is not connected. The prompts never ask the model to call it: the model writes each call as a json block. `run_evals.py` still runs `claude -p` with `--strict-mcp-config` and `--tools Read`, one process group per run, killed on timeout. Each run gets an empty folder with the guide at `guide/exa-agent.md`, so the path does not tell the model which version it reads.

After a run, check nothing is left:

```bash
pgrep -fl "claude -p"   # must print nothing
```

## Commands

```bash
cd ~/.agents/skills/search/evals
W=~/.agents/skill-workspace/alex-skills/search/iteration-N
mkdir -p $W/skill-snapshot
git show HEAD:search/references/exa-agent.md > $W/skill-snapshot/old.md   # the committed guide before the edit
cp ../references/exa-agent.md $W/skill-snapshot/new.md

python3 -I run_evals.py --guide new=$W/skill-snapshot/new.md --guide old=$W/skill-snapshot/old.md --out $W --runs 2
python3 -I run_evals.py --guide new=$W/skill-snapshot/new.md --out $W --dry-run   # list the jobs, no claude call

python3 -I grade.py --selftest          # offline known answers; must print SELFTEST PASS
python3 -I grade.py prepare $W          # writes jev-request.json in each run folder
```

Then the orchestrator sends each `jev-request.json` to `ask_jev` (one call per run), and saves the reply as `jev-response.json` in the same run folder. Then:

```bash
python3 -I grade.py apply $W            # writes grading.json per run and a TOTAL line per guide
```

Unsure verdicts (between 0.20 and 0.80) need a second look by hand or an LLM grader. A run with no `jev-response.json` is graded on its code checks only, with a warning.

## Results

| Iteration | Date | Model | New | Old |
| --- | --- | --- | --- | --- |
