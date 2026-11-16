# jev evals

Behavior evals for how an agent designs `ask_jev` calls: follow-ups in the same call (TypeSafe's speculative fan-out), a second call only when the code cannot build it without an earlier answer, and merging calls that send the same state. Eval 3 is the guard against merging too much: it needs two calls.

## Safe run

The prompts never ask the model to call anything: `ask_jev` is not connected, and the model writes the calls as JSON blocks. `run_evals.py` still runs `claude -p` with `--strict-mcp-config` and `--tools Read`, one process group per run, killed on timeout. Each run gets an empty folder with the guide at `guide/SKILL.md`, so the path does not tell the model which version it reads. Check nothing is left with `pgrep -fl "claude -p"`.

```bash
W=~/.agents/skill-workspace/alex-skills/jev/iteration-N
mkdir -p $W/skill-snapshot && cp ../SKILL.md $W/skill-snapshot/new.md   # and the version before the edit as old.md
python3 -I run_evals.py --guide new=$W/skill-snapshot/new.md --guide old=$W/skill-snapshot/old.md --out $W --runs 3
```

## Grading

```bash
python3 -I grade.py --selftest   # known answers first; must print SELFTEST PASS
python3 -I grade.py $W
```

- `code:` expectations: the number of json blocks in each output. "The follow-up reads alone" is also code: a phrase check for "if yes", "answer above", and similar.
- The rest: one Jev question per expectation, all in one call per output. The state splits the output into `calls` (the json blocks) and `explanation` (the prose); mixed together, Jev misread one for the other.
- Bands from `../references/eval-grading.md`. Unsure verdicts (0.20 to 0.80) go to an LLM grader (`../../skill-creator/vendor/claude/agents/grader.md`); the self-test fails only on a firm verdict that is wrong.
- Each run keeps its Jev request in `jev-request.json` next to `grading.json`.

## Results

| Iteration | Date | Model | New | Old |
| --- | --- | --- | --- | --- |
| 2 | 2026-11-14 | sonnet, 3 runs | 43/45 (2 fails: eval 1 prose never says the order answer is ignored when the gate fails, strict LLM grade); call counts right 12/12 | 36/45; call counts right 7/12 |
