# alex-skills

Skills for Claude Code, OpenCode, and Pi: instruction packs that teach an agent what it cannot know on its own.

## What belongs here

A skill stays in this repo only if it holds facts the model cannot know:

- **How to use a tool**: a CLI, an API, its flags and limits.
- **Alex's systems**: his boards, vault, devices, and workflows.
- **Alex's taste**: his voice, his coding rules, how he reviews.

Generic method (how to do TDD, how to debug, how to grill a plan) does not belong here. Current models do that well without a skill, and every extra skill competes for the agent's attention.

## Skills

| Kind | Skills |
| --- | --- |
| Tools | `search` (Context7 and Exa), `jev` (typed decisions), `m365`, `peekaboo`, `browser-control`, `browser-apple-events`, `archify`, `mesh-measure`, `printed-part-modeling`, `ado-dashboards` |
| Alex's systems | `scribe`, `bard`, `archeologist`, `ea-projects-curator`, `ado-ticket-writer`, `browser-cookie-auth`, `agent-creator`, `autoresearch`, `skill-creator` |
| Alex's taste and process | `alex-voice`, `code-rules`, `reviewer`, `implement`, `improve-codebase-architecture` |

Each skill's `SKILL.md` frontmatter says what it does and when it loads. `agent-creator` and `improve-codebase-architecture` are manual-only: you type them.

## Install

```bash
git clone https://github.com/acastro2/alex-skills.git ~/.agents/skills
~/.agents/skills/scripts/link_claude_skills.sh
```

OpenCode and Pi read `~/.agents/skills` directly. Claude Code reads `~/.claude/skills`, so the script links each skill there, one symlink per skill. Run it again after you add or remove a skill.

Do not point `~/.claude/skills` at this repo with one symlink. Claude Code syncs personal claude.ai skills into `~/.claude/skills/synced/`, and with a whole-folder link those copies land inside the repo, where OpenCode and Pi load them as skills.

## Skill anatomy

```
skill-name/
├── SKILL.md        # Entry point: YAML frontmatter (name, description) + instructions
├── scripts/        # Code the agent runs while doing the skill's job
├── references/     # Docs loaded into context only when needed
├── assets/         # Templates, icons, fonts
├── agents/         # Host metadata or subagent instructions
├── tests/          # Tests and development tooling, such as audit metrics
└── evals/          # Eval prompts, expectations, and a safe-run README
```

## Skill creator

`skill-creator/SKILL.md` routes structure work to OpenAI's creator and evaluation work to Anthropic's creator. Both are vendored as pinned copies in `skill-creator/vendor/`, with sources, commits, and licenses in `skill-creator/vendor/PROVENANCE.md`. Their entry files are named `CREATOR.md`, because OpenCode would otherwise register them as separate skills. Do not edit files inside `vendor/`. To update them, follow the Refresh section of `PROVENANCE.md`.

## Development and validation

```bash
pre-commit install            # once
pre-commit run --all-files    # before every commit
```

The pre-commit hooks run `scripts/validate_skill_graph.py`, which checks each skill's frontmatter, that the folder name matches `name`, and that relative links between skills resolve.

## License

Apache License 2.0. See [LICENSE](LICENSE).
