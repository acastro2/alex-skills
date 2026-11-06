---
name: ticket-writer
description: Write and update work items from real code changes, using a six-section spec template with Given/When/Then acceptance criteria. Use when creating a ticket, updating one from code changes, converting a PR or branch into a structured story, or backfilling tickets for merged work. Tool-agnostic core with per-tracker adapters; Azure DevOps is in references/ado.md. Not for filing GitHub issues by interview, that is the gh-issue-creator agent.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: ticket-management
---

# Ticket Writer

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

Write spec-driven work items that capture **what** changed and **why**, derived from actual code changes, not written in isolation. For prose, follow [Alex's voice](../alex-voice/SKILL.md).

## Core Principle: Code-First Ticket Writing

**Traditional approach**: Write ticket → Do work → Close ticket
**This skill's approach**: Do work → Analyze changes → Write/update ticket

Tickets should describe actual changes, not speculative requirements. Traverse branches/PRs to understand what was built, then document it properly.

## When to Use

- **Creating items from branches/PRs**: Code exists, needs documentation
- **Updating existing items**: Sync the item with the actual implementation
- **Writing spec-driven items**: Clear ACs based on real changes
- **Converting PR descriptions**: Formalize ad-hoc work
- **Backfilling documentation**: Code merged without proper work items

## Workflow Overview

```
Analyze Changes → Extract Intent → Structure in Six Sections → Create/Update through the tracker adapter
```

---

## Phase 1: Analyze Code Changes

### Git Traversal

Before writing anything, understand what actually changed:

```bash
git log main..HEAD --oneline --no-merges
git diff main..HEAD --stat
git diff main..HEAD
git diff main..HEAD --name-only
```

### Change Analysis Framework

For each commit or logical change group, extract:

| Element | What to Capture | Example |
|---------|----------------|---------|
| **Action** | What was done | "Added", "Fixed", "Refactored", "Removed" |
| **Target** | What was changed | "user authentication", "API rate limiting" |
| **Motivation** | Why it was done | "to support OAuth2", "to prevent abuse" |
| **Impact** | What changes for users | "Users can now login with Google" |

### Commit Message Parsing

Parse conventional commits for structure:

```
feat(auth): add OAuth2 Google provider

- Implements OAuth2 flow for Google
- Adds user profile sync
- Updates login UI with Google button

Fixes: #1234
```

Extract:

- **Type**: feat → Feature
- **Scope**: auth → Authentication service
- **Subject**: add OAuth2 Google provider
- **Body**: Implementation details
- **Footer**: Related ticket IDs

---

## Phase 2: Structure with the Six-Section Template

Every story-level ticket uses these six sections. The full template with examples is in `references/template.md`. The sections are the contract; the tracker only changes how they render.

1. **Intent & Success Criteria.** A one-sentence objective, then Given/When/Then acceptance criteria. The objective must be testable reality, not activity. ACs must be verifiable without implementation knowledge.
2. **Constraints & Guardrails.** Critical non-actions (`DO NOT: ...`), security and compliance needs, timing or SLA.
3. **Technical Interface (The Contract).** Configuration and connectivity, data schemas, API contracts.
4. **Logic & Implementation Flow.** Preparation, execution, finalization.
5. **Validation Steps.** The action or test, and the expected result.
6. **Resources & Team Context.** Runbook, source link, support channel, related PRs. Use the tracker's native links for PRs and related items instead of inline URLs when it has them.

---

## Phase 3: Create or Update the Item

### Pick the adapter

Find out which tracker the team uses, then read its adapter before any write:

| Tracker | Adapter |
|---|---|
| Azure DevOps | `references/ado.md` |
| Anything else | No adapter yet. Render the six sections in the tracker's format, and confirm its fields and types first |

A new tracker gets its own `references/<tracker>.md`. The core stays tool-free.

### Before any write

- **Resolve the org, project and types live. Never memorize them.** A stale name files work where nobody looks.
- **Search for a duplicate** with the title you are about to use. Search again before you retry a failed create: the create may have landed.
- **For an update, read the current item first**, so you merge instead of overwrite.

### Choose the type

Never default to the Story type. List the types the project has, then pick per ticket:

| The ticket is... | Type |
|---|---|
| A timeboxed investigation or spike | Spike, with its timebox |
| A defect in something that already shipped | Bug, with repro steps |
| Planned delivery with a user-visible outcome | Story, with acceptance criteria |
| Run-the-business work with no new outcome | The project's operational type, if it has one |
| A change record | The org's change-control type; ask for its process first |

If the type you need is not in the list, say so and ask. Do not substitute, and do not fake a type with a tag.

### Title format

`[SERVICE-NAME] Outcome description`

- **SERVICE-NAME**: Affected service or component, ALL CAPS (`AUTH-SERVICE`, `API-GATEWAY`, `PAYMENT-ENGINE`)
- **Outcome**: What was achieved, not the activity
- Keep it under 80 characters when possible

**Good**: `[API-GATEWAY] Add rate limiting to prevent abuse`, `[PAYMENT-ENGINE] Fix race condition in transaction processing`

**Bad**: ~~"Add OAuth2"~~ (no service, no outcome), ~~"[Auth] Implement Google login"~~ (lowercase service, describes activity), ~~"Authentication Service Changes"~~ (vague)

### Updating existing items

**Preserve existing content and merge new information.** Change the title when scope or outcome changed.

| Section | Approach |
|---------|----------|
| 1 | Append new ACs, update the objective if scope changed |
| 2 | Add new constraints, keep existing |
| 3 | Merge technical details, update schemas |
| 4 | Update phases to reflect the actual implementation |
| 5 | Add new validation steps |
| 6 | Append new resources, keep existing |

---

## Complete Workflow Example

A PR adds Google login:

1. **Analyze**: `git log main..HEAD --oneline` shows the OAuth2 provider, the login button, and the profile sync.
2. **Extract intent**: add OAuth2 authentication so users can log in with Google.
3. **Fill in the template**:
   - Section 1: Objective = "Users can authenticate via Google OAuth2"
   - Section 2: Constraints = "DO NOT: Store Google tokens in plain text"
   - Section 3: Interface = OAuth2 endpoints, callback URLs
   - Section 4: Flow = Initiate → Google auth → Callback → Profile sync
   - Section 5: Validation = Test login flow, verify profile data
   - Section 6: Resources = PR link, OAuth docs
4. **Render and write** through the adapter.
5. **Link the PR** to the item, and put the item's URL in the PR description.

## Common Patterns

- **Bug fix** (`fix(api): resolve race condition in payment processing`): type Bug. Section 1 objective = "Payment processing handles concurrent requests without race conditions". Section 4 = identify, atomic ops, concurrency tests.
- **Feature**: Section 3 documents the new endpoint and schemas. Section 4 = backend, frontend, end-to-end.
- **Refactoring**: Section 1 objective = "[Service] codebase follows clean architecture principles". Section 2 = "DO NOT: Change external API contracts". Section 4 = strategy and migration path.

## Resources

- `references/template.md`: the full six-section template with examples
- `references/ado.md`: the Azure DevOps adapter. Read it first for any ADO write
- `references/ado-api-guide.md`: ADO REST calls, when the adapter is not enough
- `references/html-examples.md`: HTML snippets for ADO descriptions
- `scripts/git_change_analyzer.py`: analyze git changes and extract intent
- `scripts/html_builder.py`: build ADO HTML and the JSON Patch
- `scripts/resolve_ado.py`: resolve the ADO org and its live projects
