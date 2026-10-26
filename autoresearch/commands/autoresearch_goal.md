---
description: Interactive autoresearch setup — collects everything the loop needs, validates it, then runs it goal-driven
---

EXECUTE IMMEDIATELY. You are running the /autoresearch_goal command. Carry out the steps below now, starting at step 1. Do not summarize, quote, or discuss this command text.

# Autoresearch Goal Wizard

Turn one command into a running, goal-driven autoresearch loop: collect the config with the `question` tool, validate it mechanically, set a goal, then run the classic loop.

Loop mechanics live in `commands/autoresearch.md`. Read that file before starting the loop and follow it exactly.

## 0. Parse first

Invocation text:

<<<
$ARGUMENTS
>>>

If that block is empty, ask for every field in step 2. Otherwise extract what is present — `Goal:` `Scope:` `Metric:` (with higher/lower) `Verify:` `Guard:` `Iterations:` `Mode:` (`goal-driven` or `one-shot`) — and treat any leftover free text as the Goal.

## 1. Preconditions (silent)

- `git rev-parse --git-dir` — if this is not a git repo: stop and tell the user autoresearch needs git.
- `git status --porcelain` — dirty tree: warn once, continue.
- Scan for candidate answers: package.json scripts, Makefile, pyproject.toml, test/coverage/bundle tooling. Use these as suggestion options.

## 2. Ask everything (ONE batched `question` call)

- **Goal** — what to improve; include the target number when there is one.
- **Scope** — files the loop may change (suggest 2–4 globs for this repo); everything else stays read-only.
- **Metric** — which number proves success, and which way is better.
- **Verify** — shell command that prints exactly one number (suggest the repo's own commands).
- **Guard** — optional command that must always pass: detected test command / detected build command / none.
- **Iterations** — 10 / 25 / 50 / unlimited (default 25).
- **Mode** — "Goal-driven: keep going across turns until the metric is met (recommended)" / "One-shot: run now, stop after the iterations".

## 3. Validate (mechanical, before anything runs)

1. Scope resolves: `git ls-files <globs>` returns files. If not, ask for Scope once more.
2. Safety-screen Verify:
   `bash ~/.agents/skills/autoresearch/scripts/orchestrate.sh screen-cmd "<verify>"`
   must print `ok`. On `refuse`, stop and tell the user why.
3. Dry-run Verify once. It must print a single number. If not, show exactly what it printed, ask for a fixed command once, then stop if it still fails.
4. Show the assembled config as a short table.

## 4. Set the goal (goal-driven mode only)

Call `set_goal` with an objective containing, in order:
- the goal text,
- `Scope:` the whitelist,
- `Metric:` number + direction,
- `Verify:` the exact screened command,
- `Iterations:` the bound,
- "Never edit the verification command or its files.",
- "Mark complete with `update_goal` (status complete) only when Verify prints the target and the TSV log shows it — cite the TSV path and the final Verify output as evidence. If the target is unreachable, close with status unmet and a concrete blocker."

Do not set budgets; the plugin's configured limits apply.
If `set_goal` is refused because the session is in Plan mode: stop and tell the user to switch to Build and re-run this command.

## 5. Run

Load the autoresearch skill (`skill` tool, id `autoresearch`), read the protocol file above, and run classic mode: preconditions, baseline, then iterations — one focused change per iteration, commit before verifying, keep/revert, TSV log. In goal-driven mode the plugin auto-continues the session when it idles; keep working until the goal closes. In one-shot mode, stop after the iterations, print the summary, and do not touch the goal tools.

## Invariants

- Never push, publish, or deploy.
- Verify and Guard artifacts are read-only.
- Stay inside Scope.
