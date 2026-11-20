# HANDOFF: alex-skills

Updated: 2026-11-20, HEAD 5566380 (Slack moved from bard into gather, uncommitted)

## gather Slack

State: uncommitted (2026-11-20). gather has a `slack` source: `opencode run --agent gather-slack` in `~/.gather/run-opencode`, model `claude-agent/haiku`, then `opencode-go/deepseek-v4.1-flash#high`. Spec: `docs/specs/gather-slack.md`. bard reads `raw/slack/` through the gather lane, and its native Slack lane is only the fallback. Live 2026-11-20: `slack: fetched 32 calls, 284 items`; no session left in opencode.db and no `~/.claude/projects` folder. Tests 150 passed, pre-commit passes.

Next:
1. Alex checks the index: parts were staged by someone else during the work. Then commit by area: `feat(gather): fetch Slack through opencode run`, `feat(bard): read Slack from gather`.
2. The first real `/gather` run sets the slack cursor (7 days back).

Gotchas and dead ends:
- Cursor models get no MCP tools through OpenCode ("Tool not found").
- Rewriting `opencode.jsonc` right before `opencode run` gives "Agent not found": write the config once.
- `claude-agent` saves Claude Code sessions under `~/.claude/projects/<cwd>`: gather removes that folder after each attempt.
- `slack_read_user_profile` with `concise` has no `User ID:` line: use `detailed`.

## bard ideas

State: uncommitted (2026-11-18). bard writes `type: idea` notes to `Bard/Ideas/` (`bard/references/ideas.md`), on demand (`/bard idea`) or from Set K `idea` in a sweep. The live `Bard.base` has an Ideas view. Checks: `check.sh` 12/12, triggers 4/4 (q02, q03, q10, q11, 3 runs each), Jev Set K row in `jev-gates.md`. First note: `Bard/Ideas/A package-published event lets a Hub dependency agent open bump PRs in every consumer within minutes.md`.

Next:
1. Alex commits by area: `feat(bard): capture future ideas in Bard/Ideas`.

## coding skill (was code-rules)

State: done and pushed (2026-11-18). The evals are in `coding/evals/`, and results are under `~/.agents/skill-workspace/alex-skills/coding/` (`re-eval-1`, `re-eval-2`). Against the `code-rules-v0` snapshot, on Opus, Sonnet and Haiku: the self-review case goes 0.5 to 1.0, and the other 5 cases tie at 1.0 (Haiku throwaway is 0.83 on both). Triggers 22/22. PR description beats no skill on 3 of 4 cases. Checked 2026-11-18 by `grade.py` and `grade_jev.py`.

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
