# Docs (feature docs, API guides, runbooks, onboarding, ADRs, processes)

- Open with why the reader should care, not what the system is.
- Recommend a path: "Use X. If you need Y for [reason], use Z." Never a buffet.
- Common case first, edge cases later. Real code, real errors, real fixes.
- Structures: feature docs (What This Does, When You'd Use It, How It Works with a diagram, Getting Started, Configuration, Troubleshooting); runbooks (When to Use This, Quick Assessment, Steps with expected outcomes, Rollback, Post-Incident); API docs (Overview, Quick Start, Full API, Examples, Gotchas).
- Humor only in context paragraphs, never in steps or warnings. Mermaid capped at about 10 nodes.
- No anecdotes except in onboarding or conceptual docs, no coined frameworks, searchable standard terms.
- Test: can a new teammate follow it unassisted?

## Register samples

Synthetic, modeled on the real patterns. No internal names, facts, or decisions.

> This lets you rotate the API key without restarting the service. Use the managed secret path unless you're debugging locally. The manual option works, but it puts rotation back on you.
