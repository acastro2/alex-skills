# AGENTS.md: alex-skills

## What this repo is

Self-contained skills for Claude Code and OpenCode. Each top-level folder with a `SKILL.md` is one skill. The repo lives at `~/.agents/skills/`. OpenCode reads it there; Claude Code reads per-skill symlinks in `~/.claude/skills/` (see `README.md`, Install).

## What belongs here

Keep a skill only if it holds facts the model cannot know: how to use a tool, Alex's systems, or Alex's taste. Do not add generic method skills (TDD, debugging, grilling); the model does those well, and each extra description competes in the skill list. Before you add a skill, say which of the three it is.

The exceptions are the ones that carry facts, not only method:

- `ub-mode` (Uncle Bob's reduced principles). Three of its gates cannot be done from
  memory: CRAP under 10, duplicate rank above 0.8, and mutation survivors killed.
  Those are the tools in `ub-mode/tools/`, pinned and installed by
  `ub-mode/tools/setup.sh`.
- `codebase-design`, `grilling`, and `domain-modeling`, copied from
  mattpocock/skills because `improve-codebase-architecture` calls them by name.
  `codebase-design` fixes the deep-module vocabulary, `domain-modeling` fixes the
  `GLOSSARY.md` and ADR formats, and `grilling` fixes the interview round format
  that skill uses at its grill step. Refresh all four together from
  `skills/engineering/` and `skills/productivity/`. Keep our edits small: the `## Asking`
  block, `grilling`'s routing exclusion and question-tool rounds, and
  `improve-codebase-architecture`'s shorter intro. Re-apply them on every refresh (see Upstreams).

Do not widen this list without the same argument: name the fact the skill carries.

**A skill carries its own code.** Anything a skill runs or reads to do its job lives in its
own folder: `scripts/`, `references/`, `assets/`. A path outside the repo is allowed only
for a work artifact the skill cites, such as an incident's evidence file, and the exact span
is recorded in `skillcheck/policy.py` under `external_paths`. Why: a skill that calls
`~/.claude/scripts/...` breaks the day that tree moves, and two copies of the same helper
drift apart. `browser-cookie-auth`, `cf-cli`, and `autoresearch` were rebuilt this way on
2026-10-26.

Every `SKILL.md` carries an `## Asking` block: decisions go through the `question` tool,
one call per round, recommended option first with its reason. `reviewer` folds the same rule
into its step 5 (grill rounds) instead of a separate section.

## Upstreams

The "Upstream provenance" table in `README.md` lists every skill that comes from another repo. Keep it true.

- **Fetch before you judge.** Run `git fetch origin` and compare with `origin/main` before you call a commit, skill, or file missing. A stale or detached checkout is not the repo.
- **Always check the upstream first.** Before you edit, refresh, review, or report on a skill in the table, compare it with the upstream's current default branch. Use `gh api`, not memory. Report the drift: our pin, upstream's latest release or commit, and what changed. Do not apply it until Alex picks.
- **Keep local edits on a refresh.** Diff our copy against the upstream file first. Re-apply every local change (the `## Asking` block, description edits) after you copy. A plain re-copy deletes them.
- **Record a pin on every refresh.** Write the upstream commit and date into the table row, or into the skill's own `PROVENANCE.md` or `UPSTREAM.md` where it has one.
- **New skill from another repo:** add its row in the same change. To decide, count the long lines the two files share. Do not use a whole-file similarity ratio: it scores unrelated files of the same genre as matches.
- **Check a sync report before you repeat it.** Check each claim (commit, skill count, added, updated) against `git log origin/main` and the files.

**Why:** On 2026-11-13 an agent called a correct sync report false, because its checkout was detached and 21 commits behind `origin/main`. The same agent first listed `cf-cli` as derived from cloudflare/skills on a 0.81 character ratio, but the two files share 0 of 45 long lines. Pins were missing for most rows, so drift was visible only when someone checked by hand.

## Skill anatomy

```
skill-name/
  SKILL.md       # Required. Frontmatter: name, description; optional allowed-tools, license, disable-model-invocation
  scripts/       # Code the agent runs while doing the skill's job
  references/    # Markdown loaded only when the skill points to it
  assets/        # Static files (templates, images)
  agents/        # Host metadata or subagent instructions
  tests/         # Tests for the skill's scripts, plus development tooling such as audit metrics
  evals/         # evals.json, trigger-evals.json, files/, README.md (safe-run rules)
  LICENSE.txt
```

Repo-wide tooling lives in `skillcheck/` and `scripts/`: `python -m skillcheck` owns every skill rule and is the pre-commit hook, `validate_skill_graph.py` is a shim over it, `scripts/check.sh` runs the rules plus every test suite, and `link_claude_skills.sh` relinks Claude Code. Tooling for one skill goes in that skill's `tests/`.

## Key patterns

- **alex-voice/** is the one voice skill. `SKILL.md` covers chat, comms, exec, docs, and spoken; `references/alex-blogger.md` adds blog; `scripts/voice_check.py` scores a draft. Real excerpts live in Alex's private vault, never in this repo.
- **skill-creator/** routes to the pinned OpenAI and Anthropic creators in `skill-creator/vendor/`. The vendored files are read-only, and their entry file is `CREATOR.md` so OpenCode does not register them as skills.
- **reviewer/**, **search/**, and **jev/** serve other skills too: `implement` reviews its diff with `reviewer`, any skill that looks something up uses `search`, and eval grading uses `jev/references/eval-grading.md`.

## Working with skills

- When you create or edit a skill, follow `skill-creator/SKILL.md`. Write eval JSON in the format of `skill-creator/vendor/claude/references/schemas.md`.
- Skills that produce prose reference `../alex-voice/SKILL.md`; blog skills also reference `../alex-voice/references/alex-blogger.md`.
- In a `SKILL.md`, never write a dollar sign followed by a digit: Claude Code replaces it with the skill's arguments. Write `USD 0.10`.
- Run `python3 scripts/validate_skill_graph.py` after any edit, and `pre-commit run --all-files` before you commit.
- After you add or remove a skill, run `scripts/link_claude_skills.sh` and update the skills table in `README.md`.

## Evals

- When a skill has `evals/evals.json`, run its evals after a behavior change. Read the skill's `evals/README.md` first.
- Run every `claude -p` eval with `--strict-mcp-config --tools "Skill,Read"`, each in its own process group, and check that nothing is left running. Why: near-miss prompts name real systems ("query snowflake…"), and with normal tools the model runs them.
- Count words, items, and exact strings in code. Grade yes-or-no expectations with Jev (`jev/references/eval-grading.md`), and send only the unsure ones to an LLM grader.
- Put eval workspaces under `~/.agents/skill-workspace/alex-skills/`, never in this repo: OpenCode scans nested `SKILL.md` files even in ignored folders, so an in-repo snapshot can replace a live skill.
- `evals/` is in `.gitignore`. Commit eval files with `git add -f`.
