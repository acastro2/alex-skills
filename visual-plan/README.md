# visual-plan

Render an implementation plan as a single self-contained HTML file (diagrams,
file map, annotated code, data shapes, wireframes, open questions), then open it
in the browser for review before any code is written.

No external platform, no account, no MCP connector. Just an `.html` file with
inline CSS and one Mermaid CDN script for diagrams.

## Files

- `SKILL.md`: when to use, the workflow, document-quality bar, self-review pass.
- `references/template.html`: the scaffold to copy and fill. Inline CSS, dark/light
  aware, print-friendly, Mermaid via CDN (version-pinned with an SRI hash).
- `references/blocks.md`: the block vocabulary (diagram, chart, image, steps,
  file-tree, code, diff, data-model, api-endpoint, wireframe, callout,
  open-questions) as HTML.
- `references/design.md`: what makes the page read well: layout, color
  discipline, chart/diagram rules, the self-check.
- `scripts/check_plan.py`: fast structural validation (leftover slots, tag
  balance, Mermaid sanity) so the model does not re-read the file by hand.

## Flow

1. Research the real codebase (read-only).
2. Copy `template.html`, fill the slots, keep only blocks that earn their place.
3. Write to scratchpad (throwaway) or the project's `./plans/` (persistent).
4. Open it (`open` / `xdg-open` / `wslview`) and print the path in chat.
5. Get approval before writing code.

## Diagrams offline

Mermaid loads from `cdn.jsdelivr.net`, so it needs internet the first time the
file opens; raw diagram text degrades to a readable outline if blocked. For
offline/hardened use, pin the script with an SRI hash or vendor `mermaid.min.js`
locally.

Originally a hosted-platform skill from BuilderIO/skills, rewritten to render
plans as local self-contained HTML.
