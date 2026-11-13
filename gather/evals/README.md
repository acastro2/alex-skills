# Evals: gather

Trigger evals only. Behaviour is covered by `tests/test_gather.py` and the opt-in live test.

Safe-run rules (repo standard): `tests/run_triggers.py` runs each query as one
`claude -p --strict-mcp-config --tools "Skill,Read" --no-session-persistence`, in its own
process group. No run can reach M365, Jira, or Slack, and none can run `gather.py`: Bash is
off and the connectors are gone. Put workspaces under
`~/.agents/skill-workspace/alex-skills/gather/`, never in this repo. After a run, check that
none is left: `pgrep -fl 'claude -p'`.

    python3 gather/tests/run_triggers.py ~/.agents/skill-workspace/alex-skills/gather/triggers-1 --runs 2

Near-misses: bard (sweep into Obsidian), m365 and archeologist (find one mail, a decision,
a Slack thread), scribe (recordings), weekly-report.

After a run, Claude Code leaves one empty `~/.claude/projects/<cwd>` folder per query even with
`--no-session-persistence`. Remove the empty `...gather-triggers-*-cwd-*` folders (seen 2026-11-13: 24).
