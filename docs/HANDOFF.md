# HANDOFF: alex-skills

Updated: 2026-11-22 (bard specs lane; gather Slack from 2026-11-20 kept)

## gather Slack

State: committed and pushed to main (2026-11-20). Trigger evals 16/16 (2 new Slack cases, workspace `~/.agents/skill-workspace/alex-skills/gather/triggers-slack-1`). The runner also sweeps OpenCode sessions whose `directory` equals its run folder exactly, at the first call and at run end. gather has a `slack` source: `opencode run --agent gather-slack` in `~/.gather/run-opencode`, model `claude-agent/haiku`, then `opencode-go/deepseek-v4.1-flash#high`. Spec: `docs/specs/gather-slack.md`. bard reads `raw/slack/` through the gather lane, and its native Slack lane is only the fallback. Live 2026-11-20: `slack: fetched 74 calls, 850 items` over 7 days; no session left in opencode.db and no `~/.claude/projects` folder. Tests 158 passed, `check.sh` 193/193, pre-commit passes.

Next:
1. The first real `/gather` run sets the slack cursor (7 days back). Runs at 17:15 and 17:37 UTC on 11-20 logged `no slack user id` and `call mismatch`; both are fixed, so the next run clears them.

Gotchas and dead ends:
- Cursor models get no MCP tools through OpenCode ("Tool not found").
- OpenCode reports parallel tool calls in completion order, not request order (live 2026-11-20: a 7-day run failed `call mismatch`). Slack rounds match each call to its request by exact tool and args; `claude -p` rounds keep the positional match.
- Rewriting `opencode.jsonc` right before `opencode run` gives "Agent not found": write the config once.
- `claude-agent` saves Claude Code sessions under `~/.claude/projects/<cwd>`: gather removes that folder after each attempt.
- `slack_read_user_profile` with `concise` has no `User ID:` line: use `detailed`.

## bard ideas and specs

State: ideas committed in `bef3ffe`; specs added 2026-11-22 (this commit). `/bard spec <idea>` writes `type: spec` notes to `Bard/Specs/` (`bard/references/specs.md`): decision rounds through the question tool first, then a decisions table plus the ticket-writer six sections, then a `reviewer` self-review. Ideas gained status `specced` and a `spec:` back-link. The live `Bard.base` has Ideas and Specs views. Checks 2026-11-22: `check.sh` 12/12, `pre-commit` clean, triggers 17/17 (2 runs each, precision and recall 1.0); results in `~/.agents/skill-workspace/alex-skills/bard/specs-iter1/`.

Next:
1. None open. The spec workflow itself (question rounds, self-review) has no automated eval: `claude -p` cannot answer question prompts.

## coding skill (was code-rules)

State: done and pushed (2026-11-18). The evals are in `coding/evals/`, and results are under `~/.agents/skill-workspace/alex-skills/coding/` (`re-eval-1`, `re-eval-2`). Against the `code-rules-v0` snapshot, on Opus, Sonnet and Haiku: the self-review case goes 0.5 to 1.0, and the other 5 cases tie at 1.0 (Haiku throwaway is 0.83 on both). Triggers 22/22. PR description beats no skill on 3 of 4 cases. Checked 2026-11-18 by `grade.py` and `grade_jev.py`. 2026-11-24 (`6028515`, `6359f41`): part 2 now says run only targeted tests locally (unit, Playwright, `tofu test -filter`), full suite in CI. AGENTS.md, README and skill-creator follow it. Re-run `iter-targeted-1` (Opus, 2 runs, baseline `snapshots/pre-targeted/code-rules-v0`): new case `targeted` 1.0 vs 0.75 (the baseline gave bare `pytest` and `npx playwright test` in both runs); tf-pin, prune, worker, review, webui tie at 1.0; feature 0.9 (one Jev UNSURE, passes by hand); throwaway 0.67 vs 1.0 (251 and 253 words against a 250 limit, from the skipped-and-risk notes, not this rule).

Next:
1. None open. To re-run: `python3 coding/tests/behaviour/run_behaviour.py <iter> --baseline-skill <snapshot> [--only names] [--model claude-haiku-5-5]`, then `grade.py <iter>`.

Gotchas and dead ends:
- The baseline must be named in the prompt (`{SKILL}`): a denied `Skill(coding)` never falls back on its own.
- Jev misreads optional offers and long replies. Keep exact checks (seam asks, file:line, the div finding) in code.
- PR description: the number check flags correct derived numbers (`429`), and the word limit counts notes outside the fenced body. Check those flags by hand.
- `checks.yml` runs on pull requests only, so a direct push to main gets no CI.

## handoff skill

State: `handoff/SKILL.md` reviewed and rewritten, pushed in `0aacd4a`: check the file against the repo on read, re-read before a write, one block per workstream, 400-word limit, gotchas section, never secrets. The AGENTS.md rule in opencode_config (`f0065cb`) and `~/.claude/CLAUDE.md` (`03cfdc9`) is committed. Checked 2026-11-16 by `git log`.

Next:
1. Optional: a behaviour eval in which a fresh agent reads only this file and must state its next command. It needs a fixture with a running server and a HANDOFF.md; the trigger runner cannot set that up.

Gotchas and dead ends:
- Trigger runs: `python3 scripts/run_triggers.py --skill handoff <out>`. Results are in `~/.agents/skill-workspace/alex-skills/handoff/triggers-*`.
- SessionStart hook to auto-load the file: Alex said not now (2026-11-16).

## projects-curator

State: writes to the real wiki space live. The epic split plan is read-only and waits for owner confirmations: `~/.agents/skill-workspace/alex-skills/projects-curator/epic-split-plan-2026-11-16.md`. Not re-checked.

Next:
1. Ask the space admin to turn databases on in the team wiki space. Until then the board stays in the scratch DB in Alex's personal space.
2. Send the Slack drafts for the epic split owner confirmations.

Gotchas and dead ends:
- Run only one wiki writer at a time: on 11-16 two sessions edited the same pages.

## scribe

State: transcribes with Hex (Parakeet v3) offline. The whisper fallback and the diarizer are blocked. Checked 2026-11-16: `~/.cache/huggingface/hub` holds only parakeet and silero-vad.

Next:
1. When Alex AirDrops `whisper.zip` and `diar.zip`, unpack them with `ditto` into `~/.cache/huggingface/hub`.

Blockers:
- huggingface.co is blocked on every network. Alex must AirDrop the models.

## improve-cicd (was improve-ci)

State: CI half done 2026-11-24, CD half and rename 2026-11-25. A fresh-context review found two Blockers, both fixed: the Go `-race` cache claim was wrong (a second run on 1.27.4 printed `(cached)`), and "promote the saved plan" contradicted the OpenTofu re-plan rule. Evals are in `improve-cicd/evals/behaviour/` (5 cases, skill vs no skill, Opus, 3 runs), and results are in `~/.agents/skill-workspace/alex-skills/improve-cicd/iter-1`. After the grader fix (it now strips YAML comments and accepts `cancel-in-progress: ${{ ... pull_request }}`): ci 1.0 vs 0.67, helm 1.0 vs 0.92, tofu ties at 1.0, cd 0.86 vs 0.91, approval low-signal. Scripts: `ci_audit.py` was checked on astral-sh/uv (120 runs), and `cd_audit.py` on cli/cli plus a synthetic rollback check.

Next:
1. cd case: the skill reply put the rollback in a workflow step and left the ECS circuit breaker and alarms as "needs you". The no-skill reply named the circuit breaker. Make B3's rollback row give the exact ECS setting (from `references/aws.md`), then re-run `--only cd`.
2. approval case: both configs keep the gate, so the case does not tell them apart, and the Jev question returns UNSURE (0.6 to 0.8). Split it into two questions, or drop the case.
3. Re-run: `python3 improve-cicd/tests/behaviour/run_behaviour.py <iter> --runs 3 [--only names]`, then `grade.py <iter>`.

Gotchas:
- The no-skill config tries `Skill(improve-cicd)` and is blocked. The grader only counts loads that ran.
- Real repos deploy the same SHA many times: cli/cli has 10 distinct SHAs in 40 deploys. `cd_audit.py` collapses the repeats.
- `per_page=100` on the jobs API returns HTTP 502 for runs with many jobs. `ci_audit.py` uses 50.

## harness (plan only)

State: spec done and reviewed 2026-11-25, nothing built. `docs/specs/harness-evolution.md` (`de8e40c`): one Bun core behind hooks and an OpenCode plugin, SQLite ledger and journal, MCP tools for deliberate actions, D1 to D74. Threat model D72: guard against agent mistakes, tamper-evident, not a wall (this user has passwordless sudo). One plan, phases 0 to 9 in order (D73). Explainer page source: `~/.agents/skill-workspace/alex-skills/harness/explainer-harness-evolution-20261125/`.

Next:
1. Alex approves Phase 0. Step 0 installs the pinned Bun (not on the VM yet).
2. Run the 18 Phase 0 probes and write each result into the spec before Phase 1.

## Other open items

Not re-checked; each was true when it was written:

- `jev` CLI: the auth store key returns HTTP 401, and the CLI falls back to `$OPENCODE_API_KEY`. Fix: `opencode auth login opencode-go`.
- weekly-report: the first team Slack paste has not run; it reports the full name of the prefix channel. Datadog needs `/mcp` login at the Mac.
- Alex only: delete the stale `alex-voice` and `skill-creator` in claude.ai → Customize → Skills.
- Alex only: `git branch -d feat/jev-speculative-questions`. It is merged into main (`0b7d795`); `git branch` needs Alex's approval.
- Alex only: the label contract names a Done epic as the active bolt epic. Draft an evolution proposal when Alex says go.
- alex-voice round 3: it is not known whether Alex marked the lineup (`wf_7113c18f-530`). Private notes: `~/Developer/obsidian/Alex/40 Writing/Voice/`.

## Running processes

None.


## Pointers

- Upstream resync: `AGENTS.md` → Resync upstreams, `scripts/upstream_audit.py --detail`, sources under `~/.agents/skill-workspace/alex-skills/upstreams/`.
- Push as acastro2: `GH_TOKEN=$(gh auth token --user acastro2)` for that one command. The SSH remote key has no access.
- Eval workspaces: `~/.agents/skill-workspace/alex-skills/<skill>/`. `evals/` is gitignored, so add it with `git add -f`.
- Plain `python3` has no PyYAML, so skillcheck silently skips. Use `uv run --with pyyaml python -m skillcheck`.
- Jev: `~/.local/bin/jev`, MCP `jev-mcp`, model `jev-1.13` on OpenCode Zen. Read a `score` as its lean, not the nearest integer.
- OpenCode denies every `git checkout *` (`~/.config/opencode/opencode.jsonc`). To change branch, use `git switch <branch>`, which refuses to overwrite local changes.
- Install layout: `~/.claude/skills` holds one symlink per skill. Run `scripts/link_claude_skills.sh` after you add or remove a skill.
- This repo is public. Never write employer names, Jira keys, site names, or account ids here. Commit `0ebe692` still holds a Jira key in git history; a history scrub is Alex's call.
