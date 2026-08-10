# alex-skills

A collection of skills for Claude Code and opencode — modular instruction packs that give AI agents domain-specific expertise, voice guidelines, and tooling.

## Install

```bash
git clone https://github.com/acastro2/alex-skills.git ~/.agents/skills
```

This puts each skill at `~/.agents/skills/<name>/SKILL.md`, which opencode discovers automatically.

Skills are also discoverable from `~/.config/opencode/skills/` and `~/.claude/skills/` — see [opencode skills docs](https://opencode.ai/docs/skills/).

### Shared resources

- `shared/alex-voice.md` — Alex's voice for docs, comms, chat, and general prose
- `shared/alex-blogger.md` — Alex's blog-specific voice

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

## License

Apache License 2.0 — see [LICENSE](LICENSE).