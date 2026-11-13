# Evals: bard

Trigger evals only (2026-11-13). The near-misses are the skills that border bard: gather
(fetch raw comms), scribe (recordings), archeologist (history questions), weekly-report,
m365 (one mail), ticket-writer.

Safe-run rules (repo standard): `tests/run_triggers.py` runs each query as one
`claude -p --strict-mcp-config --tools "Skill,Read" --no-session-persistence`, in its own
process group. No run can reach the vault, M365, Jira, or Slack. Workspaces go under
`~/.agents/skill-workspace/alex-skills/bard/`, never in this repo.

    python3 bard/tests/run_triggers.py ~/.agents/skill-workspace/alex-skills/bard/triggers-1 --runs 2

After a run, check `pgrep -fl 'claude -p'`, and remove the empty
`~/.claude/projects/...bard-triggers-*-cwd-*` folders that each query leaves behind.

A literal `/bard` query is a slash command, not a description test: `claude -p` expands it
without a Skill tool call, so the runner cannot see it (seen 2026-11-13). Use natural phrases.
