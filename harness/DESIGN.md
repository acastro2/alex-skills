# Design

The look of the harness working views. Source of truth is `ui/app/app.css`. The palette and type match the anatomy office figure (O12).

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

Text is tinted, never pure black or white. Light and dark follow the system; the top-bar switch cycles system, light, dark and is stored in `localStorage`.

## Type

System sans for text, system mono for ids, times and code. Numbers use tabular figures. Page title 20px, body 14px, labels 12px. No display type.

## Shape and depth

Square corners (2px). Hairline rules instead of shadows. No cards inside cards: a table is one plate, and a detail row opens under its row.

## Components

- Chip: outlined state label. Amber, red, green or ink fill.
- Button: 30px high, outlined; primary is solid ink. Buttons that need a passkey tap show a key icon.
- Table: sticky-free, one hairline per row, expanding detail row. At 760px and below each row becomes a labelled block.
- Badge on the rail: amber number when something needs Alex, plain count otherwise.
- States: skeleton rows while loading, an empty box that says what will appear and why, a banner plus greyed last-good data on error or a dropped stream.

## Motion

None on the working views except a 120ms colour fade on hover and a chevron turn. Both stop under `prefers-reduced-motion`.

## Do not

Eyebrow labels above headings, gradient text, side-stripe borders, glows, emoji as icons, human figures, a modal as the first choice.
