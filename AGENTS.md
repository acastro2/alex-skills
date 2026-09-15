# AGENTS.md — alex-skills

## What this repo is

A collection of self-contained OpenCode/Claude skills. Each top-level directory is one skill with a `SKILL.md` entry point. Skills are discovered from `~/.agents/skills/`, `~/.config/opencode/skills/`, or `~/.claude/skills/`.

This repo should be cloned to `~/.agents/skills/`.

## Skill anatomy

```
skill-name/
  SKILL.md          # Required. YAML frontmatter (name, description, optional: allowed-tools, license) + instructions
  scripts/           # Python or shell helpers the skill invokes
  references/        # Supplementary markdown the skill references
  assets/             # Static files (templates, images)
  agents/             # Optional host metadata or subagent instructions
  evals/
    evals.json       # Test cases for skill evaluation
  LICENSE.txt
```

## Key patterns

- **SKILL.md frontmatter** always has `name` and `description`. Some skills add `allowed-tools` to restrict what the skill may call, and `disable-model-invocation: true` to make a skill manual-only.
- **alex-voice/** is the one discoverable voice skill. Its `SKILL.md` defines Alex's voice for chat, comms, exec, docs, spoken, and general prose; `references/alex-blogger.md` adds the blog layer; `references/voice-fingerprint.md` holds the measured markers; `scripts/voice_check.py` scores drafts. Real excerpts live in Alex's private vault, never in this repo.
- **skill-creator/** is a router to the pinned OpenAI and Anthropic creators under `.upstream/`. Its `SKILL.md` selects the source and names the current validation and evaluation paths. Keep upstream files read-only; do not copy their infrastructure into the wrapper.

## Working with skills

- No root-level build system, package manager, or CI. Each skill is independent.
- Run `python3 scripts/validate_skill_graph.py` for local skill frontmatter and sibling-reference checks. For skill-specific validation, follow `skill-creator/SKILL.md`.
- `.skill-workspace/` is gitignored — skills may create temp working dirs there.

## Conventions

- Skills that produce prose should reference `../alex-voice/SKILL.md`; blog skills should also reference `../alex-voice/references/alex-blogger.md`.
- When creating or editing a skill, follow `skill-creator/SKILL.md`. When writing evaluation JSON, use `.upstream/claude/skills/skill-creator/references/schemas.md`.
- Run `pre-commit run --all-files` before you commit.
- When a skill has `evals/evals.json`, run its evals.
