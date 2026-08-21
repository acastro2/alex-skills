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
  agents/             # Subagent instructions (only skill-creator/ uses this)
  evals/
    evals.json       # Test cases for skill evaluation
  LICENSE.txt
```

## Key patterns

- **SKILL.md frontmatter** always has `name` and `description`. Some skills add `allowed-tools` to restrict what the skill may call, and `disable-model-invocation: true` to make a skill manual-only.
- **alex-voice/** is the one discoverable voice skill. Its `SKILL.md` defines Alex's voice for docs, comms, exec, chat, and general prose; `references/alex-blogger.md` adds blog-specific guidance.
- **skill-creator/** is the meta-skill with the most infrastructure: eval loops (`scripts/run_loop.py` uses `claude -p` CLI), grading subagents (`agents/analyzer.md`, `comparator.md`, `grader.md`), benchmark aggregation, and description optimization.
- **pptx/ and docx/** have Python helpers for Office file manipulation (markitdown, thumbnail.py, office/unpack.py, package.py).

## Working with skills

- No root-level build system, package manager, or CI. Each skill is independent.
- To validate a skill, use skill-creator's `scripts/quick_validate.py` or check that `SKILL.md` parses and `evals/evals.json` exists and is valid JSON.
- `.skill-workspace/` is gitignored — skills may create temp working dirs there.

## Conventions

- Skills that produce prose should reference `../alex-voice/SKILL.md`; blog skills should also reference `../alex-voice/references/alex-blogger.md`.
- When creating or editing a skill, follow the schema in `skill-creator/references/schemas.md`.
- Run `pre-commit run --all-files` before you commit.
- When a skill has `evals/evals.json`, run its evals.
