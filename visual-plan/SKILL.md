---
name: visual-plan
description: >-
  Turn an implementation plan into a single self-contained HTML file (diagrams,
  file map, annotated code, data shapes, wireframes, open questions), then open
  it in the browser for review before any code is written. Use whenever the user
  wants to plan a feature, refactor, migration, or architecture change; wants to
  review or approve an approach before implementation; asks for a plan as a doc,
  page, or HTML; or for any multi-file or ambiguous work better seen as a
  reviewable artifact than a chat message. Prefer this over a plain chat plan for
  non-trivial work.
metadata:
  visibility: exported
---

# Visual Plan

Render an implementation plan as one self-contained HTML file the user opens in
a browser to review and approve before you write code. No external platform, no
account, no MCP connector: just an `.html` file with inline CSS and one Mermaid
CDN script for diagrams. The document is the approval gate and the source of
truth.

This replaces writing the plan as a chat paragraph. The result is a scannable
page with inline diagrams, a file map, annotated snippets, data shapes, optional
wireframes, and a single open-questions block at the bottom.

## When to use

Build a visual plan when the plan is better as a reviewable artifact than a chat
message: multi-file or ambiguous work, a UI surface with states, a workflow, a
before/after change, or an architecture/API/data-shape decision that needs
alignment before implementation.

Skip it for truly trivial, unambiguous work: typos, one-line fixes, a single
well-specified function, anything whose diff fits in one sentence. Just make the
change. Never pad a plan with filler and never ship a single-step plan.

## How it works

1. **Research first (read-only).** Inspect the real files, actions, schema, and
   patterns before drafting. Name actual files, symbols, and data shapes, never
   invent them. Check existing `actions/`/helpers before proposing new ones.
   Delegate wide exploration to a sub-agent (`Explore`). Make **no source edits**
   while planning.
2. **Lead with reuse.** For each step, name what it reuses (existing actions,
   schema, components, helpers) before what it adds, so the plan shows the genuinely
   new delta instead of redescribing what exists.
3. **Decide the hard-to-reverse bets.** For backend/data/API work, get the
   expensive-to-undo decisions right in the plan (wire format, public ids,
   data-model shape, auth/ownership boundaries), then scope to the smallest first
   cut that proves the approach, stating what is in and what is explicitly deferred.
4. **Compose the HTML.** Copy `references/template.html`, fill the slots, and keep
   only the blocks that earn their place. Read `references/blocks.md` for the block
   vocabulary (diagram, steps, file-tree, code, diff, data-model, api-endpoint,
   wireframe, callout, open-questions). Prose is the default; a block is for what
   prose explains badly.
5. **Write the file and open it.**
   - **Path:** scratchpad for a throwaway review; the project's `./plans/` dir
     when the plan should persist or be checked in. Name it `plan-<slug>.html`.
   - **Open it:** macOS `open <file>`, Linux `xdg-open <file>`, WSL
     `wslview <file>`. Always print the absolute path in chat too, so the user can
     click it in a text-only host.
6. **Hand off for approval.** Surfacing the plan and asking for sign-off **is** the
   approval step; do not tack on a separate "does this look good?". Name which
   files/areas the work touches. Start editing only after the user approves.

## Document quality

- **Outcome-first.** The header lede states what this delivers and why in one
  sentence. The Overview gives the problem, the chosen approach, and the smallest
  first cut in real terms, naming real symbols.
- **Standalone.** A reader who never saw the chat understands it. If the user
  pasted an existing plan, treat it as source material and rewrite a clean
  proposal, with no revision language ("unlike the previous version", "this
  revision changes...").
- **Right altitude.** For broad framework/product changes, separate the core
  abstraction from motivating examples; label examples as examples. Lead with one
  concrete product example near the top when the concept is abstract.
- **Diagrams earn their place.** One diagram per decision or relationship. Prefer
  grouped regions, before/after, or layers over a single-axis chain unless the
  relationship is genuinely sequential. Keep product wireframes separate from
  explanatory architecture diagrams.
- **Open questions go in one bottom block.** Each is a question that would change
  the design, with a recommended default. If it does not change the design, decide
  it in the plan with rationale instead of asking.

## Clarify vs. assume

Do not ask *how* to build it: explore and present the approach and options in the
plan. Ask a clarifying question only when an ambiguity would change the design and
you cannot resolve it from the code; batch 2-4 high-leverage questions via the
normal ask-user flow before finalizing. Otherwise state the assumption explicitly
and proceed, leaving anything unresolved in the bottom open-questions block.

## Self-review before handoff (high-stakes plans)

For architecture, backend, data-model, migration, multi-file, or risky plans, run
one cheap adversarial pass after writing the file. Open it for the user first,
review concurrently, never block the handoff. Critique the plan text, do not
re-research: hunt for hard-to-reverse decisions made implicitly or skipped, steps
not anchored in real files/symbols, a menu of options where the plan should commit
to one, obvious missing decisions, and padding. Fix clear-cut issues by editing
the HTML; route genuine judgment calls into the open-questions block or back to
the user. Skip the pass for small UI-only or single-decision plans.

## Updating a plan

When scope shifts, edit the HTML file (do not only change course in chat) and keep
it standalone, without narrating the edit as a correction to an earlier draft.
Re-open the file so the user sees the current version. Re-read the approved plan
before major implementation steps.

## Diagrams & offline note

Diagrams use Mermaid loaded from `cdn.jsdelivr.net` (one `<script>` in the
template), which needs internet the first time the file is opened. If the CDN is
blocked, raw Mermaid text still degrades to a readable indented outline. For a
hardened/offline setup, the user can pin the script to an exact version with an
`integrity="sha384-..."` SRI hash, or vendor `mermaid.min.js` next to the HTML and
point the `src` at the local copy. Default leaves it unpinned so patch releases
do not break rendering.
