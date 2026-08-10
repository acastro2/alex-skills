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
- **shared/alex-voice.md** defines Alex's voice for docs, comms, chat, and general prose. **shared/alex-blogger.md** adds blog-specific guidance. Use only these two voice files.
- **skill-creator/** is the meta-skill with the most infrastructure: eval loops (`scripts/run_loop.py` uses `claude -p` CLI), grading subagents (`agents/analyzer.md`, `comparator.md`, `grader.md`), benchmark aggregation, and description optimization.
- **pptx/ and docx/** have Python helpers for Office file manipulation (markitdown, thumbnail.py, office/unpack.py, package.py).

## Working with skills

- No root-level build system, package manager, or CI. Each skill is independent.
- To validate a skill, use skill-creator's `scripts/quick_validate.py` or check that `SKILL.md` parses and `evals/evals.json` exists and is valid JSON.
- `.skill-workspace/` is gitignored — skills may create temp working dirs there.

## Conventions

- Skills that produce prose should reference `shared/alex-voice.md`; blog skills should also reference `shared/alex-blogger.md`.
- When creating or editing a skill, follow the schema in `skill-creator/references/schemas.md`.
- 7 skills have `evals/evals.json` test cases. When modifying those skills, run their evals if possible.