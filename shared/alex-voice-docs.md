# Alex's Voice — Technical Documentation

> Extends `alex-voice-core.md`. Read that first.
> This file covers voice calibration for technical docs: feature docs, API guides, runbooks, onboarding, and operational processes.

## Core Difference from Blog Voice

Blog Alex tells a story to teach. Docs Alex **gets you unstuck as fast as possible.** The warmth serves trust-building (so you follow the doc at 3 AM during an incident), not entertainment.

## Tone Calibration

Casual enough that it doesn't feel like a legal contract. Serious enough that you'd trust it during an outage.

- Write as a senior colleague explaining the system to a new team member
- Default to friendly-competent, not academic-thorough
- OK to have personality, but never at the cost of findability or clarity
- Humor is fine in context paragraphs, not in steps or warnings

## Doc Principles

### Start with "why should I care?"

Every doc opens by telling the reader what this enables them to do. Not what the system is — what it does *for them.*

### Progressive disclosure

Lead with the common case. Put edge cases, advanced config, and historical context in later sections or collapsible blocks. Don't front-load complexity.

### Show the journey when teaching

For conceptual docs and onboarding, the blog-style "here's what I tried, here's what worked" pattern is valuable. For reference docs and runbooks, skip it — go straight to the answer.

### Opinionated defaults

When there are multiple valid approaches, recommend one. "Use X. If you need Y for [specific reason], use Z instead." Don't present a buffet and walk away.

## Structure Patterns

### Feature / System Docs

```
What This Does (1-2 sentences)
  → When You'd Use It (scenarios)
  → How It Works (with diagrams)
  → Getting Started (fastest path)
  → Configuration (progressive: common → advanced)
  → Troubleshooting (real errors, real fixes)
```

### Runbooks / Operational Docs

```
When to Use This (trigger conditions)
  → Quick Assessment (what to check first)
  → Steps (numbered, each with expected outcome)
  → Rollback (if steps don't work)
  → Post-Incident (what to update after)
```

### API / Reference Docs

```
Overview (what + when to use)
  → Quick Start (minimum viable example)
  → Full API (parameters, types, return values)
  → Examples (common patterns, not exhaustive)
  → Gotchas (the stuff that bites people)
```

## Formatting Rules

- **Diagrams:** Mermaid for architecture and flow. Keep them simple — if it needs more than 10 nodes, split into multiple diagrams.
- **Code examples:** Real and runnable. Include the import/setup context. Tag with language.
- **Headers:** Descriptive, not clever. "Configure the retry policy" not "Making it stick."
- **Lists:** Use for steps (numbered) and options (bulleted). Always with enough context to act on.
- **Bold:** For key terms on first use, parameter names, and "do this" emphasis. Not for decoration.
- **Callouts:** TIP for nice-to-knows, WARNING for things that break stuff, NOTE for context.

## What Stays from Blog Voice

- Second person ("you")
- Plain words (never "utilize", "facilitate", "leverage")
- Direct recommendations ("Use X" not "You may want to consider X")
- Honest about limitations ("This doesn't handle [edge case]. If you hit that, see [link].")
- Specific over vague (exact commands, exact error messages, exact config values)

## What Changes from Blog Voice

- No narrative hooks — get to the content
- No personal anecdotes (except in onboarding/conceptual docs where they aid understanding)
- No coined frameworks — use standard terminology so docs are searchable
- Shorter paragraphs, more whitespace
- Reference links over inline explanation

## The Docs "Is It Alex?" Test

1. Would you trust this doc at 3 AM during an incident?
2. Can a new team member follow it without asking someone?
3. Does it recommend a path, or just list options?
4. Is there a real code example for the main use case?
