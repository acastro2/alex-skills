# HANDOFF: alex-skills

Updated: 2026-11-16 14:30 CST (trimmed to the `handoff` skill shape; the old session log is in `git log -p docs/HANDOFF.md`, last long version at `a2927d9`)

## Current state

- `main` is level with `origin/main` at `a2927d9`. Uncommitted: new `handoff/` skill, `AGENTS.md` resync step 9, and `README.md`, which lists `handoff` in two places. skillcheck (with PyYAML) PASS on 58 skills, `check.sh` 11/11, and pre-commit clean.
- The `handoff` skill replaces the long HANDOFF rule in `~/.config/opencode/AGENTS.md:22` and `~/.claude/CLAUDE.md:26`. Both files now carry one line that holds the trigger and the duty to update. The path is root first, then `docs/`. Both files are uncommitted in their own places.
- projects-curator writes to the real wiki space live (2026-11-16). Run only one wiki writer at a time: on 11-16 two sessions edited the same pages. The epic split plan is read-only and waits for owner confirmations: `~/.agents/skill-workspace/alex-skills/projects-curator/epic-split-plan-2026-11-16.md`.
- scribe transcribes with Hex (Parakeet v3) offline. The whisper fallback and the diarizer are still blocked: `whisper.zip` and `diar.zip` never arrived, and `~/.cache/huggingface/hub` holds only parakeet and silero-vad.

## Next

1. Alex commits `handoff/`, `AGENTS.md`, and `README.md` here, then `~/.config/opencode/AGENTS.md` in opencode_config. `~/.claude/CLAUDE.md` changed too.
2. projects-curator: ask the space admin to turn databases on in the team wiki space. Until then the board stays in the scratch DB in Alex's personal space. Then send the Slack drafts for the epic split owner confirmations.
3. Add the REA MCP back at `rea-agents@6.9.0` in `~/.config/opencode/opencode.jsonc`. It was removed in opencode_config `144a911`, so the `reverse-engineer-anything` skill has no server.

## Blockers

Not re-checked on 2026-11-16; each was true when it was written:

- scribe diarization and the whisper fallback: Alex must AirDrop `whisper.zip` and `diar.zip`. huggingface.co is blocked on every network.
- `jev` CLI: the auth store key returns HTTP 401, and the CLI falls back to `$OPENCODE_API_KEY`. Fix: `opencode auth login opencode-go`.
- weekly-report: the first team Slack paste has not run; it reports the full name of the prefix channel. Datadog needs `/mcp` login at the Mac.
- Alex only: delete the stale `alex-voice` and `skill-creator` in claude.ai → Customize → Skills.
- Alex only: the label contract names a Done epic as the active bolt epic. Draft an evolution proposal when Alex says go.
- alex-voice round 3: it is not known whether Alex marked the lineup (`wf_7113c18f-530`). Private notes: `~/Developer/obsidian/Alex/40 Writing/Voice/`.

## Running processes

None.

## Pointers

- Upstream resync: `AGENTS.md` → Resync upstreams, `scripts/upstream_audit.py --detail`, plan `docs/specs/upstream-refresh.md`, sources under `~/.agents/skill-workspace/alex-skills/upstreams/`.
- Push as acastro2: `GH_TOKEN=$(gh auth token --user acastro2)` for that one command. The SSH remote key has no access.
- Eval workspaces: `~/.agents/skill-workspace/alex-skills/<skill>/`. `evals/` is gitignored, so add it with `git add -f`. The safe trigger runner is `scripts/run_triggers.py --skill <name>`.
- Plain `python3` has no PyYAML, so skillcheck silently skips. Use `uv run --with pyyaml python -m skillcheck`.
- Jev: `~/.local/bin/jev`, MCP `jev-mcp`, model `jev-1.13` on OpenCode Zen. Read a `score` as its lean, not the nearest integer.
- Install layout: `~/.claude/skills` holds one symlink per skill. Run `scripts/link_claude_skills.sh` after you add or remove a skill.
- This repo is public. Never write employer names, Jira keys, site names, or account ids here. Commit `0ebe692` still holds a Jira key in git history; a history scrub is Alex's call.
- Old detail on any feature: `git log -p docs/HANDOFF.md`, or `git show a2927d9:docs/HANDOFF.md` for the last long version.
