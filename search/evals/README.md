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

Then send them and grade:

```bash
python3 -I grade.py send $W             # pipes each request to `jev - --raw` unchanged; writes jev-response.json
python3 -I grade.py apply $W            # writes grading.json per run and a TOTAL line per guide
```

`send` needs the `jev` CLI on `PATH` (`~/.config/opencode/bin/install.sh` links it). Do not copy the requests into the `ask_jev` tool by hand: on 2026-11-23 two agents changed the state text while copying, so those answers graded different evidence. Script blocks and diagrams in an output become `[<lang> block omitted]` in the state; the questions judge only the prose and the `agent_run` calls.

Unsure verdicts (between 0.20 and 0.80) need a second look by hand or an LLM grader. A run with no `jev-response.json` is graded on its code checks only, with a warning.

## Results

| Iteration | Date | Model | New | Old |
| --- | --- | --- | --- | --- |
| 1 | 2026-11-23 | sonnet, 2 runs | Not graded. Eval 2 showed a bug: the first script rule made the model start one Agent run per row (400 runs, about USD 40, against about USD 2 batched). Rule fixed. | Not graded |
| 2 | 2026-11-23 | sonnet, 2 runs; eval 2 new re-run after the fix, the rest reused from iteration 1 | 38/38 | 35/38, 1 unsure: eval 2 never says where the script can run (both runs), and gives no cost gate (run 1, unsure 0.48). Evals 1, 3 and 4 tie. |

Iteration 1 call bounds were widened after reading the outputs: both guides split eval 1 into one run per country, and eval 3's follow-up the same way, which the guide allows. Claude cost about USD 2 for both iterations. Zero Exa calls.
