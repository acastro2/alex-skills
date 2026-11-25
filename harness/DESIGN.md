# Design

The look of the harness dashboard (the home route) and the 8 working views behind it. Source of truth is `ui/app/app.css`. The palette and type match the anatomy office figure (O12).

## Register

Product. Alex reads it beside his terminals: many glances a day, a few actions. It must be plain, dense and quiet. No decoration in the working views.

## Colour

Paper and ink. One lit accent, amber, and it means only "this needs Alex". Red means failed or blocked. Green means a passing proof.

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--page` | `#f2f2ef` | `#0b0b0b` | page |
| `--plate` | `#fbfbfa` | `#131313` | tables, cards, top bar |
| `--rail` | `#ebebe7` | `#0f0f0f` | left rail, detail rows |
| `--ink` | `#18181a` | `#ececec` | headings, primary button |
| `--text` | `#3f3f43` | `#c4c4c8` | body |
| `--muted` | `#5f5f63` | `#8f8f94` | labels, times |
| `--rule` | `#d8d8d3` | `#2a2a2a` | hairlines |
| `--amber` | `#e8a010` | `#f2b530` | needs you |

Text is tinted, never pure black or white. Light and dark follow the system. The top bar has three buttons (Auto, Light, Dark); each label names what its click sets, and the current one is pressed. The choice is stored in `localStorage`.

## Type

System sans for text, system mono for ids, times and code. Numbers use tabular figures. Page title 20px, body 14px, labels 12px. The dashboard keeps rows at 13 to 14px and the one question text at 16px; the health counts are 30px mono. No display type.

## Shape and depth

Square corners (2px). Hairline rules instead of shadows. No cards inside cards: a table is one plate, and a detail row opens under its row.

## Dashboard

The home route (`#/` and `#/office`) is one screen of panels, built for a 27 inch screen at 2560 wide and a 32 inch screen at 3840 (often 1.5x, so 2560 CSS px). Everything important shows at once and the data moves.

- Columns: 4 from 2200px (needs you, health and jobs | live sessions and processes | journal tail | office figure, worktrees and proof bundles), 3 from 1600px, 2 from 900px, 1 below that. From 2200px wide and 860px tall the page does not scroll: each panel scrolls inside itself, and the panel with the longer list grows into spare room. Below that the page scrolls and each panel body is capped.
- Panels are plain plates with a hairline header: title (a link to its drill-down page), then a count line. No card inside a panel; rows are divided by hairlines.
- Live: the page builds once and each snapshot patches the panels that changed. Scroll position and focus survive. Times age in place.
- Journal tail: oldest first, newest at the bottom, follows. It pauses while the pointer is over it or after a scroll up, shows how many rows arrived, and has a Jump to latest button. New rows get a short neutral highlight (not amber). Chips filter to deny, advise or send-back.
- Amber still means only "needs Alex": a waiting question and a stuck session get the wash. Deny is red, send-back is dark amber text, advise is bold ink.
- The office figure keeps its own frame, caption and styles (`/office/office.css`). It goes in bare: no plate of ours around it.

## Components

- Chip: outlined state label. Amber, red, green or ink fill.
- Button: 30px high, outlined; primary is solid ink. Buttons that need a passkey tap show a key icon.
- Table: one hairline per row, expanding detail row. The dashboard tables (processes, jobs) are denser, with a sticky header inside their panel. At 760px and below each row becomes a labelled block.
- Badge on the rail: amber number when something needs Alex, plain count otherwise.
- States: skeleton rows while loading, an empty box that says what will appear and why, a banner plus greyed last-good data on error or a dropped stream.

## Motion

A 120ms colour fade on hover, a chevron turn, and an 1.8s fade of the highlight on a new journal row. Under `prefers-reduced-motion` they stop; the new row keeps its highlight for 2.6s and then drops it.

## Do not

Eyebrow labels above headings, gradient text, side-stripe borders, glows, emoji as icons, human figures, a modal as the first choice.
