---
name: attain-standards
description: Attain Finance engineering standards. Consult when writing or reviewing any Attain code, infrastructure, tests, or docs, choosing how to interact with GitHub, or working with OpenTofu/Terraform. Covers Terraform conventions, code style, testing, GitHub-via-gh, and the brand design system.
---

# Attain Finance Engineering Standards

Apply these when working in any Attain Finance repository. These are team conventions, not personal preference: follow them unless a local `CLAUDE.md`/`AGENTS.md` overrides.

## Delegation

- Treat yourself as an orchestrator. Delegate aggressively to cheaper subagents: `Explore` for read-only code search and mapping, `general-purpose` for self-contained multi-step tasks.
- Run independent tasks in parallel (multiple agents in one message), not one after another.
- Work inline only when full conversation context is required, or it's a one-line edit where dispatch overhead beats the gain.
- Subagents start with zero context. Give them exact file paths, symbol names, constraints, and the expected output. A vague prompt wastes more than doing it yourself.

## Comments

Leave only comments explaining **why**, not **what**. The code already says what it does.

## Code Style

- Prefer functional patterns over class-based when appropriate.
- Use explicit error handling; avoid silent failures.
- Keep functions small and focused on a single responsibility.
- Use descriptive variable names; avoid abbreviations unless widely understood.

## OpenTofu / Terraform

- Use `lifecycle { enabled = <condition> }` (OpenTofu 1.11+) for conditional resources instead of `count`. Only use `count` to create multiple identical copies of a resource.

## GitHub

- Always use the `gh` CLI to access GitHub (PRs, issues, repos, diffs). Never use raw git commands for GitHub API operations, and never use web fetching for GitHub URLs.

## Testing

- Write tests for behavior, not implementation details.
- Prefer integration tests for API boundaries.
- Use descriptive test names that explain the scenario being tested.

## Documentation

- Update relevant docs when changing public interfaces.
- Keep READMEs focused on getting started quickly.

## Local Project Context

When a repo has a local `CLAUDE.md` or `AGENTS.md`:

- Read it first to understand project-specific conventions and accumulated knowledge.
- Update it when discovering important architectural patterns, integration quirks, or non-obvious requirements future agents should know.
- Keep additions concise: this is for context that spans multiple files or isn't obvious from reading code.

## Brand & Design System

For any user-facing work (frontend, marketing, dashboards, decks, Word/PDF docs), install the `attain-brand` plugin and follow its `attain-design-system` skill (`DESIGN.md`) for the palette, typography, the brand wedge motif, semantic tokens, dark mode, and the PowerPoint `.thmx` workflow.
