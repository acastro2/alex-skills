# alex-skills

A collection of skills for Claude Code and opencode — modular instruction packs that give AI agents domain-specific expertise, voice guidelines, and tooling.

## Install

```bash
git clone https://github.com/acastro2/alex-skills.git ~/.agents/skills
```

This puts each skill at `~/.agents/skills/<name>/SKILL.md`, which opencode discovers automatically.

Skills are also discoverable from `~/.config/opencode/skills/` and `~/.claude/skills/` — see [opencode skills docs](https://opencode.ai/docs/skills/).

### Voice skill

- `alex-voice/SKILL.md` — Discoverable voice skill for docs, comms, exec, chat, and general prose
- `alex-voice/references/alex-blogger.md` — Blog-specific guidance loaded by the voice skill

## Skill anatomy

```
skill-name/
├── SKILL.md        # Entry point (YAML frontmatter + instructions)
├── scripts/        # Executable helpers
├── references/    # Docs loaded into context as needed
├── assets/         # Templates, icons, fonts
├── agents/         # Subagent instructions
├── evals/          # Test prompts and assertions
└── LICENSE.txt     # Per-skill license
```

## Development and validation

Install the pre-commit hooks:

```bash
pre-commit install
```

Run all hooks on all files:

```bash
pre-commit run --all-files
```

The local validator checks top-level skill frontmatter, directory and name agreement, and sibling relative references.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
