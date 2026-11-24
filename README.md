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
| Tools | `search` (Context7, Exa, cited research files), `jev` (typed decisions), `m365`, `peekaboo`, `browser-control` (rules on top of the browse MCP), `browser-apple-events`, `archify`, `anatomy` (isometric SVG figures with a camera you can turn), `mesh-measure`, `printed-part-modeling`, `find-skills` (installs skills from the open ecosystem), `herdr`, `cf-cli`, `oreilly-answers`, `security-audit`, `unslop` |
| Library guides | `threejs-*` (13: fundamentals, geometry, materials, textures, lighting, loaders, asset-pipeline, animation, interaction, shaders, postprocessing, performance, react-three-fiber) |
| Alex's systems | `scribe`, `bard`, `gather` (fetch-only intake of comms into `~/.gather` for bard), `archeologist`, `projects-curator`, `ticket-writer`, `browser-cookie-auth`, `agent-creator`, `autoresearch`, `skill-creator`, `git-pull-acastro2`, `weekly-report`, `forge`, `rex` |
| Alex's taste and process | `alex-voice`, `coding`, `reviewer`, `improve-codebase-architecture`, `personal-finance-advisor`, `ub-mode`, `terminal-report`, `handoff` |
| Upstream dependencies | `codebase-design`, `domain-modeling`, `grilling` |

Each skill's `SKILL.md` frontmatter says what it does and when it loads. `agent-creator` and `improve-codebase-architecture` are manual-only: you type them.

The upstream dependencies are copied from [mattpocock/skills](https://github.com/mattpocock/skills) and refreshed with them. Their only local edits are the `## Asking` block, `grilling`'s routing exclusion and question-tool rounds, and `improve-codebase-architecture`'s shorter intro. `improve-codebase-architecture` calls `codebase-design` for its vocabulary, `domain-modeling` to keep `GLOSSARY.md` and ADRs current, and `grilling` at its grill step.

## Upstream provenance

More skills here derive from public sources than the upstream dependencies above. This table records every confirmed one, verified by content comparison on 2026-11-12 and re-audited against each upstream on 2026-11-13 (matching text and structure, not names alone). The Pin column is the upstream commit or release our copy matches; "checked" means compared on that date, "copied" means refreshed from it. Unless a row says verbatim, the local copy carries Alex's changes; most add a standard `## Asking` preamble that routes decisions through his question tool.

| Source | Skills | License | Pin | Notes |
| --- | --- | --- | --- | --- |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `grilling`, `codebase-design`, `domain-modeling`, `improve-codebase-architecture` | MIT | `5863806` (checked 2026-11-13) | Copies with the local edits listed above |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `coding` (part 0 and the self-review step) | MIT | `implement` at `5863806`, folded in 2026-11-18 | Was the standalone `implement` skill, heavily rewritten on the upstream skeleton. Folded into `coding` on 2026-11-18 and no longer tracked by `upstream_audit.py`: almost all of it was already in `coding` and AGENTS |
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | `coding` (part 1, "Make the smallest complete change") | MIT | `ebd8654`, adapted 2026-11-24 | Rewritten in STE and folded into `coding`. Dropped its session levels and its rule to leave a test for new logic, which conflicts with `coding` part 2. Not in `upstream_audit.py`: it is adapted text, not a copy |
| [CloudAI-X/threejs-skills](https://github.com/CloudAI-X/threejs-skills) | `threejs-*` (all 13) | MIT | `0e18186` (checked 2026-11-13) | Verbatim, the current r186 edition, except one sentence in `threejs-performance` reworded for a skillcheck finding (`ebdd128`) |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | `find-skills` | MIT | `b716f9d` (checked 2026-11-13) | Byte-identical to upstream |
| [openai/skills](https://github.com/openai/skills) and [anthropics/skills](https://github.com/anthropics/skills) | `skill-creator` | Apache-2.0 | See `skill-creator/vendor/PROVENANCE.md` | Both creators vendored as pinned copies; see `skill-creator/vendor/PROVENANCE.md`. The wrapper that routes between them is Alex's |
| [exa-labs/agent-skills](https://github.com/exa-labs/agent-skills), [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server) and [upstash/context7](https://github.com/upstash/context7) | `search` | MIT | exa `a0c2df8`, context7 `251c6c5` (checked 2026-11-13); exa-mcp-server `81d687e` (2026-11-21) | The router on top is Alex's; the bundled references adapt Exa's `exa-search` and `exa-contents`, and `references/context7.md` adapts Context7's `find-docs` (22 of its 71 long lines match). Three sections of `references/exa-agent.md` (run plan, agent-or-script, coverage check) adapt the `exa-agent` skill from exa-mcp-server, the source of the official `exa@claude-plugins-official` plugin; its 3-line `search` skill is not taken. One section comes from mattpocock/skills `research`, credited in the file |
| [openclaw/Peekaboo](https://github.com/openclaw/Peekaboo) | `peekaboo` | MIT | v4.9.8 `70dbc41`, copied 2026-11-13 | Upstream file plus two local edits (description suffix, Asking block); see `peekaboo/PROVENANCE.md`. Keep the pin equal to the installed CLI |
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | `archify` | Apache-2.0 (release zip; `LICENSE-MIT` preserves the historical MIT grants) | v3.3.0 release zip `af3aaf3`, copied 2026-11-23 | Copied from the release zip (SHA-256 checked). Local edits: the anatomy exclusion in the description, the Asking block, and the example title "Incident Handling Runbook". Itself based on Cocoon-AI/architecture-diagram-generator (MIT) |
| [herdrdev/herdr](https://github.com/herdrdev/herdr) | `herdr` | Apache-2.0 | `ee5bfb5` (checked 2026-11-13) | Line-for-line apart from the Asking preamble |
| [anomalyco/browse](https://github.com/anomalyco/browse) | `browser-control` | MIT | `0f51721` on `dev` (checked 2026-11-13) | Condensed adaptation of the upstream `browse` skill |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | `security-audit` | MIT | `c1c8a8c` (checked 2026-11-13) | File set matches upstream 1:1 |
| [uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch) | `autoresearch` | MIT | Trim of v2.3.0; screen-cmd from `66b3d57`, copied 2026-11-13 | Not karpathy/autoresearch: this is Udit Goenka's generalisation of that concept. Local copy trims 14 commands to 2 and ships only `screen-cmd`; its `screen-cmd` and its tests (`tests/test_screen_cmd.sh`) come from the bypass fix `66b3d57` |
| [unclebob/ub-mode](https://github.com/unclebob/ub-mode) | `ub-mode` | MIT | `3da62bf` (checked 2026-11-13) | Upstream added an MIT license in `3da62bf`. Upstream is itself loosely based on portions of @poteto's rules |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | `coding` (`references/web-interface.md`) | MIT | `web-design-guidelines` at `1a2c79d`, folded in 2026-11-18 | Was the standalone `web-design-guidelines` skill, copied 2026-11-17; rewritten as a coding reference on 2026-11-18. It fetches its rules live from vercel-labs/web-interface-guidelines `command.md` on every run, so the rules are not pinned |
| [caldoai/skills](https://github.com/caldoai/skills) | `coding` (`references/prune-tests.md`) | MIT | `026b1b3`, copied 2026-11-18 | Byte-identical to upstream `skills/prune-tests/SKILL.md`, frontmatter included. `coding/SKILL.md` runs it on the tests a change touches before the work is called done. Not in `upstream_audit.py`: the audit compares whole folders, and this is one file inside `coding` |
| [heydamir/unslop](https://github.com/heydamir/unslop) | `unslop` | CC BY 4.0 | `97daa3e`, copied 2026-11-13 | By Damir Sokolovsky, credit kept in the skill. Local edit: the anatomy routing in `references/visuals.md`. `agents/openai.yaml` is left out |
| [wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) | `anatomy` | MIT | `1482e84`, copied 2026-11-17 | Picked over isoscene in a camera bake-off on 2026-11-17: the camera azimuth is one parameter, and shading, occlusion and face text follow it. Copied from the tarball at that commit without `.github/`, images, video and the example PDFs (about 14 MB of generated output). Local edit: the Asking block. isoscene (cintelis, no license) was retired the same day and moved out of the repo |

Everything else in this repo is Alex's own work: `agent-creator`, `alex-voice`, `archeologist`, `bard`, `browser-apple-events`, `browser-cookie-auth`, `cf-cli`, `forge`, `git-pull-acastro2`, `handoff`, `m365`, `mesh-measure`, `oreilly-answers`, `personal-finance-advisor`, `printed-part-modeling`, `projects-curator`, `scribe`, `terminal-report`, `ticket-writer`, `weekly-report`. One nuance: `personal-finance-advisor` is original writing, but its `references/UPSTREAM.md` pins four method references it borrows topics from.

Two skills are neither copies nor Alex's own text. `rex` is a stub that `rex skill setup` writes, and its guide comes from the installed Rex CLI. `opencode-charts` is not in this checkout: it is a symlink into Alex's [acastro2/opencode-chart-tui](https://github.com/acastro2/opencode-chart-tui) repo, which is its source, and `skillcheck/policy.py` records the one external path it needs.

Unverified candidates, recorded so they are not lost: `coding` shares one section with mattpocock/skills `tdd`, and `reviewer` shares its code layer with mattpocock/skills `code-review`; both matches are section-level only. `jev` shares distinctive guidance with typesafe-ai/skills but no verbatim text. The local sync tracks this table's sources and reports when an upstream moves ahead of the copy here.

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

A skill is a folder with `SKILL.md` at its root. Two top-level folders are not skills: `docs/specs/` holds the designs, and `skillcheck/` is the linter the hook calls.

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
scripts/check.sh              # the rules, then every offline suite
scripts/check.sh --tools      # also the ub-mode tools' own suites
```

The `skillcheck` hook runs `python -m skillcheck`, which checks each skill's frontmatter, that the folder name matches `name`, and that relative links between skills resolve. The hook installs PyYAML in its own environment; to run either it or `scripts/validate_skill_graph.py` (the same rules, same exit codes) by hand, use `uv run --with pyyaml python -m skillcheck`, because plain `python3` has no PyYAML.

## License

Apache License 2.0. See [LICENSE](LICENSE).
