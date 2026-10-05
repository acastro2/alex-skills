# Docs (feature docs, API guides, runbooks, onboarding, ADRs, processes)

Docs are not messages: the "cut to two thirds" rule does not apply here. A doc is complete when a new teammate can follow it alone. Every sentence gives an action, a reason, or prevents a mistake. Cut adjectives and repetition, never the reason or the tip.

Why this shape: in a blind test (2026-10-05), Alex picked fuller drafts that explain the why and warn about the next mistake over tighter drafts, 6 of 6. The tighter drafts kept the steps and dropped what makes a doc trustworthy.

## Rules

- Open with why the reader should care, not what the system is. One sentence of stakes is enough: "Secrets that never rotate are a risk you carry quietly."
- Never invent a fact, plan, number, or decision the user did not give. A reason or a tip must follow from the facts you have. If the doc needs something you do not know (a rollback plan, an owner, a date), write "[to confirm]" in its place. Arithmetic on given numbers is fine ($90,000 a year is about $7,500 a month).
- Recommend a path: "Use X. If you need Y for [reason], use Z." Never a buffet.
- Give the why for every step that is not obvious, with "because" or "so": "The restart is safe, because re-runs are idempotent." "Do not rebuild from a branch, because the branch may have moved."
- Head off the next mistake. Add the one tip a teammate learns the hard way: "Tell your manager to expect the approval, so it does not sit in their queue." "Include the run [id]; it saves a round trip."
- Mark the scope with its own short section: "When to use this", "What it does not cover yet", "If you skip a step".
- Help the reader decide with one plain question when the call is theirs: "Not sure? Ask yourself one question: is [system] broken for customers right now?"
- Steps are numbered, one action each, with "Expected result:" after it. Close a process with "What done looks like" when the end state is not obvious.
- End with routing: who to ask, where status lives, and what to include when asking.
- Common case first, edge cases later. Real code, real errors, real fixes.
- Structures: feature docs (What This Does, When You'd Use It, How It Works with a diagram, Getting Started, Configuration, Troubleshooting); runbooks (When to Use This, Quick Assessment, Steps with expected results, Rollback, Post-Incident); API docs (Overview, Quick Start, Full API, Examples, Gotchas). Mermaid capped at about 10 nodes.
- ADRs: Context states the problem and its cost; Decision states the choice flat. One "I think" or "To me" is fine in the rationale, because an ADR records a judgment. Say how the decision could be reversed (for example, a new ADR).
- Parentheses for a short clarifier are fine: "(a job that runs twice gives the same result as a job that runs once)".
- No anecdotes except in onboarding or conceptual docs, no coined frameworks, searchable standard terms.

## Red flags

- A step with no reason when the reader would ask "why?".
- Chat and speech markers in a doc: "trust me", "don't get me wrong", "make sense?", "right?", jokes in asides ("especially at 3 AM").
- An owner line or a link list instead of a sentence that routes the reader.
- A buffet of options with no recommendation.

Test: can a new teammate follow it unassisted, and do they know why each step is there?

## Register samples

Synthetic, modeled on the real patterns. No internal names, facts, or decisions.

> ## When to use this
>
> Use this runbook when the nightly scheduler hangs and jobs stop moving. The restart is safe, because re-runs are idempotent (a job that runs twice gives the same result as a job that runs once), so you cannot double-process anything by trying again.
>
> ## Quick assessment
>
> Check the queue depth in [link] before you touch anything. Is the oldest job older than 30 minutes? If not, wait and check again, because a long job can look like a hang.
>
> ## Steps
>
> 1. Drain the queue. Expected result: queue depth reads 0.
> 2. Restart the scheduler service. Expected result: the service shows as running within a few minutes.
> 3. Re-run the failed jobs. Expected result: each job reaches done.
>
> If it is still stuck after the re-run, ask [team] in the incident channel and include the run [id], so they can check the scheduler logs without a round trip.
