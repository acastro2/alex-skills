# HANDOFF: alex-skills

Updated: 2026-11-18, HEAD bf65aed (coding evals complete)

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

## reverse-engineer-anything

State: the skill has no server. Checked 2026-11-16: `rea-agents` is not in `~/.config/opencode/opencode.jsonc` (removed in opencode_config `144a911`).

Next:
1. Add the REA MCP back at `rea-agents@6.9.0` in `~/.config/opencode/opencode.jsonc`.

## Other open items

Not re-checked; each was true when it was written:

- `jev` CLI: the auth store key returns HTTP 401, and the CLI falls back to `$OPENCODE_API_KEY`. Fix: `opencode auth login opencode-go`.
- weekly-report: the first team Slack paste has not run; it reports the full name of the prefix channel. Datadog needs `/mcp` login at the Mac.
- Alex only: delete the stale `alex-voice` and `skill-creator` in claude.ai → Customize → Skills.
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
- Install layout: `~/.claude/skills` holds one symlink per skill. Run `scripts/link_claude_skills.sh` after you add or remove a skill.
- This repo is public. Never write employer names, Jira keys, site names, or account ids here. Commit `0ebe692` still holds a Jira key in git history; a history scrub is Alex's call.
