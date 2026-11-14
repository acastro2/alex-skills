# alex-skills

Skills for Claude Code and OpenCode: instruction packs that teach an agent what it cannot know on its own.

## What belongs here

A skill stays in this repo only if it holds facts the model cannot know:

- **How to use a tool**: a CLI, an API, its flags and limits.
- **Alex's systems**: his boards, vault, devices, and workflows.
- **Alex's taste**: his voice, his coding rules, how he reviews.

Generic method (how to do TDD, how to debug, how to grill a plan) does not belong here. Current models do that well without a skill, and every extra skill competes for the agent's attention.

The exceptions are skills that carry facts, not only method: `ub-mode`, plus the three that `improve-codebase-architecture` calls by name. `AGENTS.md` records why each one stays.

## Skills

| Kind | Skills |
| --- | --- |
| Tools | `search` (Context7, Exa, cited research files), `jev` (typed decisions), `m365`, `peekaboo`, `browser-control` (rules on top of the browse MCP), `browser-apple-events`, `archify`, `isoscene` (isometric SVG scenes), `mesh-measure`, `printed-part-modeling`, `find-skills` (installs skills from the open ecosystem) |
| Library guides | `threejs-*` (13: fundamentals, geometry, materials, textures, lighting, loaders, asset-pipeline, animation, interaction, shaders, postprocessing, performance, react-three-fiber) |
| Alex's systems | `scribe`, `bard`, `gather` (fetch-only intake of comms into `~/.gather` for bard), `archeologist`, `projects-curator`, `ticket-writer`, `browser-cookie-auth`, `agent-creator`, `autoresearch`, `skill-creator`, `git-pull-acastro2`, `weekly-report`, `design-system` (points at a work repo's `DESIGN.md` through `~/.config/design-system.json`, holds no brand values) |
| Alex's taste and process | `alex-voice`, `code-rules`, `reviewer`, `implement`, `improve-codebase-architecture`, `personal-finance-advisor`, `ub-mode`, `terminal-report`, `pr-change-description` |
| Upstream dependencies | `codebase-design`, `domain-modeling`, `grilling` |

Each skill's `SKILL.md` frontmatter says what it does and when it loads. `agent-creator` and `improve-codebase-architecture` are manual-only: you type them.

The upstream dependencies are copied from [mattpocock/skills](https://github.com/mattpocock/skills) and refreshed with them. Their only local edits are the `## Asking` block, `grilling`'s routing exclusion and question-tool rounds, and `improve-codebase-architecture`'s shorter intro. `improve-codebase-architecture` calls `codebase-design` for its vocabulary, `domain-modeling` to keep `GLOSSARY.md` and ADRs current, and `grilling` at its grill step.

## Upstream provenance

More skills here derive from public sources than the upstream dependencies above. This table records every confirmed one, verified by content comparison on 2026-11-12 and re-audited against each upstream on 2026-11-13 (matching text and structure, not names alone). The Pin column is the upstream commit or release our copy matches; "checked" means compared on that date, "copied" means refreshed from it. Unless a row says verbatim, the local copy carries Alex's changes; most add a standard `## Asking` preamble that routes decisions through his question tool.

| Source | Skills | License | Pin | Notes |
| --- | --- | --- | --- | --- |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `grilling`, `codebase-design`, `domain-modeling`, `improve-codebase-architecture` | MIT | `5863806` (checked 2026-11-13) | Copies with the local edits listed above |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `implement` | MIT | `5863806` (checked 2026-11-13) | Heavily rewritten on the upstream skeleton; its TDD step defers to `code-rules`, its review step to `reviewer`, and the upstream commit instruction is reversed (never commit) |
| [CloudAI-X/threejs-skills](https://github.com/CloudAI-X/threejs-skills) | `threejs-*` (all 13) | MIT | `0e18186` (checked 2026-11-13) | Verbatim, the current r186 edition, except one sentence in `threejs-performance` reworded for a skillcheck finding (`ebdd128`) |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | `find-skills` | MIT | `b716f9d` (checked 2026-11-13) | Byte-identical to upstream |
| [openai/skills](https://github.com/openai/skills) and [anthropics/skills](https://github.com/anthropics/skills) | `skill-creator` | Apache-2.0 | See `skill-creator/vendor/PROVENANCE.md` | Both creators vendored as pinned copies; see `skill-creator/vendor/PROVENANCE.md`. The wrapper that routes between them is Alex's |
| [exa-labs/agent-skills](https://github.com/exa-labs/agent-skills) and [upstash/context7](https://github.com/upstash/context7) | `search` | MIT | exa `a0c2df8`, context7 `251c6c5` (checked 2026-11-13) | The router on top is Alex's; the bundled references adapt Exa's `exa-search` and `exa-contents`, and `references/context7.md` adapts Context7's `find-docs` (22 of its 71 long lines match). One section comes from mattpocock/skills `research`, credited in the file |
| [openclaw/Peekaboo](https://github.com/openclaw/Peekaboo) | `peekaboo` | MIT | v4.9.8 `70dbc41`, copied 2026-11-13 | Upstream file plus two local edits (description suffix, Asking block); see `peekaboo/PROVENANCE.md`. Keep the pin equal to the installed CLI |
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | `archify` | MIT (release zip; repo `main` is now Apache-2.0) | v3.2.0 release zip `208acba`, copied 2026-11-13 | Copied from the release zip (SHA-256 checked). Local edits: the isoscene exclusion in the description, the Asking block, and the example title "Incident Handling Runbook". Itself based on Cocoon-AI/architecture-diagram-generator (MIT) |
| [herdrdev/herdr](https://github.com/herdrdev/herdr) | `herdr` | Apache-2.0 | `ee5bfb5` (checked 2026-11-13) | Line-for-line apart from the Asking preamble |
| [anomalyco/browse](https://github.com/anomalyco/browse) | `browser-control` | MIT | `0f51721` on `dev` (checked 2026-11-13) | Condensed adaptation of the upstream `browse` skill |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | `security-audit` | MIT | `c1c8a8c` (checked 2026-11-13) | File set matches upstream 1:1 |
| [morluto/rea](https://github.com/morluto/rea) | `reverse-engineer-anything` | MIT | npm `rea-agents` 6.9.0 (`d74549e`), copied 2026-11-13 | Copied from the npm package `rea-agents`, not the repo: the package pins its own version into the commands. Skill version 62, 255 tools. The REA MCP in `~/.config/opencode/opencode.jsonc` still runs 6.8.0 (229 tools) by Alex's choice, so some tools the skill names are missing until the MCP moves to 6.9.0 |
| [uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch) | `autoresearch` | MIT | Trim of v2.3.0; screen-cmd from `66b3d57`, copied 2026-11-13 | Not karpathy/autoresearch: this is Udit Goenka's generalisation of that concept. Local copy trims 14 commands to 2 and ships only `screen-cmd`; its `screen-cmd` and its tests (`tests/test_screen_cmd.sh`) come from the bypass fix `66b3d57` |
| [unclebob/ub-mode](https://github.com/unclebob/ub-mode) | `ub-mode` | MIT | `3da62bf` (checked 2026-11-13) | Upstream added an MIT license in `3da62bf`. Upstream is itself loosely based on portions of @poteto's rules |
| [heydamir/unslop](https://github.com/heydamir/unslop) | `unslop` | CC BY 4.0 | `97daa3e`, copied 2026-11-13 | By Damir Sokolovsky, credit kept in the skill. Local edit: the isoscene routing in `references/visuals.md`. `agents/openai.yaml` is left out |
| [cintelis/isoscene](https://github.com/cintelis/isoscene) | `isoscene` | None | `e9243171`, copied 2026-11-13 | By Cintelis. The upstream repo has no license file and its README says "Private. © Cintelis", so reuse is not licensed. Pinned at commit e9243171. Local changes: a `plane()` helper for content on any face, its tests, and the install path in `SKILL.md`. Its `NOTICE.md` and an `UPSTREAM.txt` stay in the folder |

Everything else in this repo is Alex's own work: `agent-creator`, `alex-voice`, `archeologist`, `bard`, `browser-apple-events`, `browser-cookie-auth`, `cf-cli`, `design-system`, `forge`, `git-pull-acastro2`, `m365`, `mesh-measure`, `oreilly-answers`, `personal-finance-advisor`, `pr-change-description`, `printed-part-modeling`, `projects-curator`, `scribe`, `terminal-report`, `ticket-writer`, `weekly-report`. One nuance: `personal-finance-advisor` is original writing, but its `references/UPSTREAM.md` pins four method references it borrows topics from.

Two skills are neither copies nor Alex's own text: `rex` is a stub that `rex skill setup` writes, and its guide comes from the installed Rex CLI; `opencode-charts` ships from Alex's [acastro2/opencode-chart-tui](https://github.com/acastro2/opencode-chart-tui) repo, which is its source.

Unverified candidates, recorded so they are not lost: `code-rules` shares one section with mattpocock/skills `tdd`, and `reviewer` shares its code layer with mattpocock/skills `code-review`; both matches are section-level only. `jev` shares distinctive guidance with typesafe-ai/skills but no verbatim text. The local sync tracks this table's sources and reports when an upstream moves ahead of the copy here.

## Install

```bash
git clone https://github.com/acastro2/alex-skills.git ~/.agents/skills
~/.agents/skills/scripts/link_claude_skills.sh
```

OpenCode reads `~/.agents/skills` directly. Claude Code reads `~/.claude/skills`, so the script links each skill there, one symlink per skill. Run it again after you add or remove a skill.

`ub-mode` is the one skill with a slash command. It ships at `ub-mode/commands/ub-mode.md`, linked into both hosts so `/ub-mode` works in each:

```bash
ln -sfn ~/.agents/skills/ub-mode/commands/ub-mode.md ~/.config/opencode/commands/ub-mode.md
ln -sfn ~/.agents/skills/ub-mode/commands/ub-mode.md ~/.claude/commands/ub-mode.md
```

Do not point `~/.claude/skills` at this repo with one symlink. Claude Code syncs personal claude.ai skills into `~/.claude/skills/synced/`, and with a whole-folder link those copies land inside the repo, where OpenCode loads them as skills.

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
