---
name: to-tickets
description: "Break a plan, spec, or conversation into tracer-bullet tickets, each declaring the tickets that block it, and publish them to the project issue tracker (Azure DevOps at Attain, or one Markdown file per ticket locally). Use when the user says to cut this into tickets, break this down, plan the slices, or split work so it can be built one piece at a time."
license: MIT
disable-model-invocation: true
---

# To Tickets

Break a plan, a spec, or the conversation into **tickets**: tracer-bullet vertical slices, each declaring the tickets that **block** it.

## Process

### 1. Gather context

Work from what is already in the conversation. If the user passes a reference (a spec path, a work item ID or URL), fetch it and read the full body and comments.

### 2. Explore the codebase

If you have not already, read enough of the code to understand its current state. Ticket titles and descriptions must use the project's domain glossary vocabulary, and respect ADRs in the area you are touching.

Look for chances to prefactor the code first, to make the implementation easier. Make the change easy, then make the easy change.

### 3. Draft vertical slices

Break the work into **tracer bullet** tickets:

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests). Vertical, not a horizontal slice of one layer.
- A completed slice is demoable or verifiable on its own.
- Each slice is sized to fit a single fresh context window.
- Any prefactoring goes first.

Give each ticket its **blocking edges**: the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

**Wide refactors are the exception to vertical slicing.** A wide refactor is one mechanical change (rename a column, retype a shared symbol) whose blast radius fans across the whole codebase, so a single edit breaks thousands of call sites and no vertical slice can land green. Do not force it into a tracer bullet. Sequence it as **expand, migrate, contract**:

1. **Expand**: add the new form beside the old, so nothing breaks.
2. **Migrate**: move the call sites over in batches sized by blast radius (per package, per directory). Each batch is its own ticket blocked by the expand, and CI stays green batch to batch because the old form still exists.
3. **Contract**: delete the old form once no caller remains, in a ticket blocked by every migrate batch.

When even the batches cannot stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket. Green is promised only there.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each ticket show:

- **Title**: short descriptive name
- **Blocked by**: which other tickets must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work

Ask:

- Does the granularity feel right? Too coarse, or too fine?
- Are the blocking edges correct? Does each ticket depend only on tickets that genuinely gate it?
- Should any tickets be merged or split?

Iterate until the user approves the breakdown. Do not publish before approval.

### 5. Publish

Read `docs/agents/issue-tracker.md` in the repo if it exists; it overrides everything below.

Otherwise, how you publish depends on the tracker. The tickets are the same either way; only the shape of the blocking edge changes.

#### Azure DevOps

Publish through the `ado` agent. Read `~/.pi/agent/agents/ado.md` and `~/.agents/skills/ado-ticket-writer/references/ado-api-guide.md` first; do not guess at the API.

Publish **in dependency order, blockers first**, so each ticket can reference real IDs as it is created.

- **Title**: the repo's ADO title convention. At Attain the shape is `[SERVICE] Short outcome`.
- **Type**: the Story-equivalent type for the project, detected by the agent, never assumed.
- **Description**: what to build and the acceptance criteria, as HTML. Never raw Markdown.
- **Acceptance criteria**: mirror into `Microsoft.VSTS.Common.AcceptanceCriteria`.
- **Blocking edges**: use ADO's dependency link. The blocked ticket gets `System.LinkTypes.Dependency-Reverse` pointing at its blocker, which makes the blocker a **predecessor**. Confirm the direction on the first ticket before creating the rest of the links; a reversed dependency graph is worse than none.
- **Placement**: attach each ticket under the spec or feature work item, matching whatever the repo already does.
- **Ready marker**: apply the tracker's ready-for-agent marker unless told otherwise. At Attain that is a tag.

Work the **frontier**: any ticket whose blockers are all done. For a linear chain that means top to bottom.

Do **not** close or modify a parent work item.

#### Local files

Write one file per ticket under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in dependency order, blockers first. Never one combined file.

```markdown
# <NN>: <Ticket title>

**What to build:** the end-to-end behaviour this ticket makes work, from the user's perspective, not a layer-by-layer implementation list.

**Blocked by:** the numbers or titles of the tickets that gate this one, or "None (can start immediately)".

**Status:** ready-for-agent

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2
```

## Rules

- Avoid specific file paths and code snippets in a ticket: they go stale fast. Exception: a snippet a prototype produced that encodes a decision more precisely than prose can (a state machine, a reducer, a schema, a type shape). Inline it and say it came from a prototype.
- Each ticket describes behaviour a person can see, not a layer-by-layer task list.
- Creating work items is a write the whole team sees. Show the user the breakdown and get agreement before you POST anything.
