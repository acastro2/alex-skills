---
name: autoresearch
description: "Autonomous iteration loop: modify, verify, keep/discard against any metric"
version: 3.0.0
---

# Autoresearch — Autonomous Metric-driven Iteration

Two commands. The loop, and a wizard that turns a goal into a running loop.

| Command | Does |
|---|---|
| `/autoresearch` | Iterate against a metric: modify → verify → keep/discard |
| `/autoresearch_goal` | Collect + validate the config with `question`, `set_goal`, then run the loop |

Loop mechanics live in `commands/autoresearch.md`. Setup and goal wiring live in
`commands/autoresearch_goal.md`. Read the relevant file before running anything.

## Why a loop and not just a goal

Goal mode gives persistence: the session keeps going between turns. It does not give a
measured before and after for each change, so the model can declare victory.

The loop forces the sequence: baseline number → ONE change → commit → measure → keep if the
number improved, else revert. Use a goal for "finish this feature". Use the loop for "make
this number go up".

## Safety Invariants

- Never push, publish, or deploy without explicit user approval.
- Bounded by default: 25 iterations. Override with `Iterations: unlimited`.
- Results go to `autoresearch/loop-{YYMMDD}-{HHMM}/` **in the repo under test**, never in
  this skill directory.
- Screen every derived or persisted shell command before it runs:
  `bash "<skill-dir>/scripts/orchestrate.sh" screen-cmd "<command>"` must print `ok`.
  On `refuse`, stop and tell the user why.
- The Verify command and its files are read-only. Never edit them to make a number pass.
- Discard by revert only: `git revert HEAD --no-edit`. Never rewrite history.

## Flags

| Flag | Applies To | Purpose |
|---|---|---|
| `Iterations: N` | Both | Set iteration count (default 25) |
| `Iterations: unlimited` | Both | Opt-in unbounded |
| `--evals` | Loop | Inline checkpoint every `floor(N / 3)` iterations, plus `evals-summary.md` at the end |
| `--evals-interval N` | Loop | Override the checkpoint frequency |

## Files

- `scripts/orchestrate.sh` — the `screen-cmd` safety gate. One subcommand, nothing else.
