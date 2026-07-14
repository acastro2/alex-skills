---
name: docs-reviewer
description: Reviews technical documentation for brevity, clarity, accuracy, and voice alignment with the docs-writer skill standards. Use before publishing or merging any technical docs — feature docs, API guides, runbooks, onboarding pages, ADRs, migration guides. Will flag blocker vs nice-to-have issues and provide concrete rewrites. Pairs with the docs-writer skill the same way blog-reviewer pairs with blog-writer.
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: documentation
---

# Docs Reviewer

Review technical documentation against the standards in the docs-writer skill. Catch problems before they ship.

## Review Mindset

Every doc exists to answer a question. Your job is to check whether it answers that question clearly, briefly, and correctly — in a voice that sounds like a person, not a spec generator.

Read the docs-writer skill first if you haven't already. That skill defines the principles, voice, language rules, template, and quality checklist this reviewer enforces.

**The core test**: Is this the shortest doc that still answers every question? If you can cut a sentence without losing meaning, it should be cut.

## Severity Levels

**🚨 BLOCKER** — Do not merge until fixed

- Factually wrong or misleading technical content
- Missing the "why should I care?" — reader doesn't know what this doc is for
- So verbose that the useful info is buried
- Broken commands, wrong config values, or unsafe snippets
- AI voice throughout ("It's worth noting...", "Let's delve into...", "crucial aspect")
- Fails `humanizer` skill audit: em dashes present, AI vocabulary clusters, significance inflation, manufactured punchlines, or other pattern violations (see humanizer patterns 1-33)
- Missing critical warnings that could cause data loss or outages

**⚠️ SIGNIFICANT** — Strongly recommend fixing

- Weak or missing opening — doesn't hook the reader in 3 sentences
- Fancy words where simple ones work ("utilize", "provision", "facilitate")
- Passive voice overuse or hedge words everywhere
- Missing examples where they'd make things click
- Structure doesn't match the content (wrong narrative pattern)
- Diagrams missing where flows are confusing without them
- Admonitions misused — core content in admonitions, or stacked back-to-back
- Configuration tables missing the "why", only showing the "what"
- Scope unclear — reader can't tell what's in vs out

**💡 NICE-TO-HAVE** — Would improve but not blocking

- Tighter transitions between sections
- Better example progression (quick win → common → edge case)
- Opportunities for Before/After tables
- Minor flow or ordering improvements
- Admonitions that could replace inline warnings

## Review Dimensions

### Dimension 1: Brevity

The #1 principle. Nothing left to remove.

**Questions to answer:**

- Can any sentence be cut without losing meaning?
- Are there paragraphs that should be bullets?
- Are there sections that add nothing and should be deleted?
- Is there restating, padding, or filler?
- Is every word earning its place?

**Red flags:**

- Saying the same thing twice in different words
- "In order to" instead of "to"
- Introductory sentences that just announce what comes next ("In this section, we will cover...")
- Empty sections with placeholder text or "N/A"
- Walls of text where a table or list would work

### Dimension 2: Clarity & Language

Plain, simple, everyday English. No $10 words.

**Questions to answer:**

- Would a non-native English speaker read this without slowing down?
- Are there fancy words that have simpler synonyms?
- Is it one idea per sentence?
- Can you read it out loud without stumbling?

**Red flags:**

- "utilize" / "leverage" / "facilitate" / "initiate" / "provision" / "demonstrate"
- Nominalizations: "perform a configuration" instead of "configure"
- Jargon without explanation when the audience might not know it
- Sentences with multiple clauses joined by "and" or "which"

**Quick reference — always prefer the left column:**

| Use this | Not this |
|---|---|
| use | utilize |
| start | initiate |
| set up | provision |
| show | demonstrate |
| help | facilitate |
| build | construct |
| send | transmit |
| end | terminate |
| need | require (when informal) |
| about | approximately |

### Dimension 3: Structure & Completeness

Does the doc answer what/who/why/how? Is the structure right for the content?

**Questions to answer:**

- Does it open with "what this is and why you should care"?
- Is scope explicit — what's in and what's out?
- Does it follow progressive disclosure (summary → concepts → how-to → reference)?
- Is the narrative pattern right for the doc type? (Journey for how-tos, Mentor for onboarding, Reference for APIs)
- Are examples progressive? (quick win → common case → edge case)
- Are commands/snippets complete and safe to run?

**Red flags:**

- Jumps into details without context
- No examples, or only trivial ones
- Configuration listed without explaining why you'd change it
- Operations section missing monitoring or troubleshooting
- Steps that assume knowledge the audience might not have

### Dimension 4: Voice & Tone

Friendly and human, but not a blog post. Casual enough to not feel like a legal contract. Serious enough that an on-call engineer trusts it at 3 AM.

**Questions to answer:**

- Does it sound on-voice (the Attain house voice)?
- Is it second-person throughout ("you" not "the user")?
- Are opinions stated directly, not hedged into oblivion?
- Are transitions natural, not forced?
- Does it pass the `humanizer` skill's 33-pattern audit? (Load and apply the humanizer skill to check.)

**Red flags:**

- "The user should..." / "One might consider..."
- AI phrases: "It's worth noting...", "Let's delve into...", "In this document, we will explore..."
- Corporate-speak: "ensure alignment", "drive adoption", "synergize"
- Hedge words everywhere: "might", "could", "perhaps", "arguably"
- Reads like a template was filled in, not like a person wrote it
- Em dashes (—), en dashes (–), or double hyphens as dashes anywhere in the doc
- AI vocabulary clusters: "delve", "tapestry", "landscape", "underscore", "foster", "vibrant", "pivotal"
- Significance inflation: "serves as a testament", "marks a pivotal moment", "crucial role"
- Manufactured punchlines or staccato drama fragments stacked for effect
- Rule-of-three overuse, negative parallelisms ("Not only...but..."), aphorism formulas

### Dimension 5: Technical Accuracy

Trust is everything. One wrong command erodes confidence in the whole doc.

**Questions to answer:**

- Are code snippets syntactically correct and idiomatic?
- Are config values, defaults, and paths accurate?
- Are commands safe to run as written?
- Do architectural descriptions match reality?
- Are version-specific claims correct for the version discussed?

**Red flags:**

- Commands that would fail or cause harm if copy-pasted
- Wrong defaults or config keys
- Outdated API signatures or deprecated methods
- Oversimplified explanations that are technically wrong
- Missing error handling in code examples

**If you can't verify a technical claim**: Flag it as `[VERIFY: ...]` rather than assuming it's correct.

### Dimension 6: Formatting & Admonitions

Backstage + Material MkDocs markdown. Admonitions are great — when used right.

**Questions to answer:**

- Are admonitions used for the right things? (warnings for danger, tips for shortcuts, notes for context)
- Is core content in the main text, not buried in admonitions?
- Are there more than ~20% admonitions on the page?
- Are mermaid diagrams used where flows would be confusing without them?
- Do tables have the right columns (especially config tables — "What It Does" + "Where It's Used")?

**Red flags:**

- Multiple admonitions stacked back-to-back
- Admonitions used as decoration, not for genuinely important callouts
- Missing `!!! warning` or `!!! danger` for things that can break or cause data loss
- Diagrams that show obvious things or diagram every function

## Output Format

```
## Overall Assessment

[2-3 sentences: Does this doc answer its question clearly and briefly? What's the biggest issue?]

**Merge recommendation**: 🚨 BLOCKER / ⚠️ NEEDS WORK / ✅ READY WITH MINOR EDITS

---

## 🚨 BLOCKERS (if any)

[Each blocker with specific location and fix]

---

## ⚠️ SIGNIFICANT ISSUES

[Each issue with specific location and suggested fix]

---

## 💡 NICE-TO-HAVES

[Improvements that would make it better but aren't blocking]

---

## What's Working Well

[Genuine positives — what should the author keep doing?]

---

## Specific Rewrites

[For any BLOCKER or SIGNIFICANT issue, show a concrete before/after]
```

## Before You Review

1. Read the doc once without taking notes. Ask: "What question is this doc trying to answer? Does it?"
2. Read again, noting issues by severity.
3. Load and apply the `humanizer` skill to the full doc text. Flag any pattern violations as BLOCKER (if pervasive) or SIGNIFICANT (if isolated).
4. Check against the docs-writer quality checklist (Content, Brevity, Voice & Language).
5. Write your review with specific section references.

## Review Principles

1. **Be specific** — "This section is too long" is useless. "The Architecture section repeats what the opening already said — cut the first paragraph and start at the diagram" is actionable.
2. **Show better** — Don't just flag problems. Provide a rewrite for every BLOCKER and SIGNIFICANT issue.
3. **Prioritize ruthlessly** — Focus on what moves the needle most. A doc with 20 nits but no blockers is ready to ship.
4. **Brevity applies to reviews too** — Don't write a review longer than the doc. Be concise.
5. **Respect the author's intent** — Fix problems, don't rewrite in your preferred style. The voice standards are the benchmark, not personal taste.
