---
name: to-spec
description: "Turn the current conversation into a spec and publish it to the project issue tracker, which at Attain is Azure DevOps. Use when the user says to write a spec, turn this into a story or ticket, capture what we just decided, or before a multi-session build. Synthesises what was already discussed; it does not interview."
license: MIT
disable-model-invocation: true
---

# To Spec

Take the current conversation and the codebase understanding and produce a spec. **Do not interview the user.** Synthesise what you already know. If a decision is genuinely missing, ask that one question and stop.

## Process

### 1. Explore the repo

Understand the current state of the code, if you have not already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you are touching.

### 2. Agree the seams

Sketch out the seams at which you will test the feature.

- Prefer existing seams to new ones.
- Use the highest seam possible.
- If a new seam is needed, propose it at the highest point you can.
- Fewer seams across the codebase is better. The ideal number is one.

Check with the user that these seams match their expectations. Do not publish a spec whose seams were never confirmed.

### 3. Pick the tracker

Read `docs/agents/issue-tracker.md` in the repo if it exists; it overrides everything below.

Otherwise:

- **An Attain repo** publishes to **Azure DevOps**. See "Publishing to Azure DevOps" below.
- **Any other repo with no tracker config** writes the spec as one Markdown file at `.scratch/<feature-slug>/spec.md` and tells the user where it landed.

### 4. Write the spec

```markdown
## Problem Statement

The problem the user faces, from the user's perspective.

## Solution

The solution, from the user's perspective.

## User Stories

A LONG, numbered list. Each in the form:

1. As an <actor>, I want a <feature>, so that <benefit>

Example:

1. As a mobile bank customer, I want to see the balance on my accounts, so that I can make better informed decisions about my spending.

Cover all aspects of the feature. This list is the acceptance criteria in plain language.

## Implementation Decisions

The decisions that were made:

- The modules that will be built or modified
- The interfaces of those modules that will change
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do **not** include specific file paths or code snippets. They go stale fast.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (a state machine, a reducer, a schema, a type shape), inline it within the relevant decision and note that it came from a prototype. Trim to the decision-rich parts, not a working demo.

## Testing Decisions

- What makes a good test here (behaviour, not implementation)
- Which modules will be tested
- Prior art: similar tests that already exist in this codebase

## Out of Scope

What this spec deliberately does not cover.

## Further Notes

Anything else about the feature.
```

## Publishing to Azure DevOps

Publish through the `ado` agent. Its rules and the REST mechanics are in `~/.pi/agent/agents/ado.md` and `~/.agents/skills/ado-ticket-writer/references/ado-api-guide.md`. Read those, do not guess at the API.

1. **Pre-flight.** Let the agent detect the Story-equivalent work item type for the project, and validate the area and iteration path. Never assume a type or a path.
2. **Title.** Follow the repo's ADO convention. At Attain the shape is `[SERVICE] Short outcome`.
3. **Description.** The spec template above, rendered as HTML in `System.Description`. Never send raw Markdown; ADO renders HTML.
4. **Acceptance criteria.** Mirror the User Stories into `Microsoft.VSTS.Common.AcceptanceCriteria` so ADO's native AC reporting works.
5. **Link the parents.** Add the parent work item relation if this spec sits under an epic or a feature.
6. **Return the URL.** Report the `_links.html.href` so the user can open it, plus the work item ID.

Apply the tracker's ready-for-agent marker so the spec is grabbable later. At Attain that is a tag, not a label; check what the repo already uses before inventing one.

**The section shape of the description follows the repo's ADO conventions, not this file.** If the repo's existing stories use a different section structure, match it. Consistency with the tracker beats consistency with this template.

## Rules

- Do not interview. Synthesise. One question is fine; a questionnaire is not.
- Do not invent decisions the conversation did not contain. Write "undecided" and say so.
- Do not close or modify a parent work item.
- Publishing a work item is a write to a system the whole team sees. Show the user the rendered content and get agreement before you POST it.
