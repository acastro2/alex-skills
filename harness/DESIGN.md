---
name: Harness
description: Plain, dense, quiet paper-and-ink dashboard for the harness, with one amber accent that means "needs Alex".
colors:
  page: "#f2f2ef"
  plate: "#fbfbfa"
  rail: "#ebebe7"
  ink: "#18181a"
  text: "#3f3f43"
  muted: "#5f5f63"
  rule: "#d8d8d3"
  rule-strong: "#b9b9b2"
  amber: "#e8a010"
  amber-ink: "#6f4300"
  amber-wash: "#fbefd0"
  red: "#b3261e"
  red-wash: "#fbe5e2"
  green: "#1d6b39"
  green-wash: "#e1f1e6"
  page-dark: "#0b0b0b"
  plate-dark: "#131313"
  rail-dark: "#0f0f0f"
  ink-dark: "#ececec"
  text-dark: "#c4c4c8"
  muted-dark: "#8f8f94"
  rule-dark: "#2a2a2a"
  rule-strong-dark: "#424242"
  amber-dark: "#f2b530"
  amber-ink-dark: "#f2b530"
  amber-wash-dark: "#2a2109"
  red-dark: "#ff8078"
  red-wash-dark: "#2c1513"
  green-dark: "#62d084"
  green-wash-dark: "#102418"
typography:
  headline:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", Roboto, \"Helvetica Neue\", sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: "28px"
    letterSpacing: "-0.01em"
  title:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", Roboto, \"Helvetica Neue\", sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.45
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", Roboto, \"Helvetica Neue\", sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", Roboto, \"Helvetica Neue\", sans-serif"
    fontSize: "12px"
    fontWeight: 600
  mono:
    fontFamily: "ui-monospace, \"SF Mono\", Menlo, Consolas, monospace"
    fontSize: "12.5px"
    fontWeight: 400
  stat:
    fontFamily: "ui-monospace, \"SF Mono\", Menlo, Consolas, monospace"
    fontSize: "30px"
    fontWeight: 600
    lineHeight: 1.05
---

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

## Colors

The palette is paper and ink with one lit accent. The frontmatter holds the values: light keys have no suffix, and every `-dark` key is the dark-theme value of the same name, taken from the `[data-theme="dark"]` block in `ui/app/app.css`.

### Neutral
- **Page** (`page`): the page background.
- **Plate** (`plate`): tables, cards and the top bar.
- **Rail** (`rail`): the left rail and expanded detail rows.
- **Ink** (`ink`): headings, strong text and the solid primary button.
- **Text** (`text`): body copy.
- **Muted** (`muted`): labels, times and hints.
- **Rule** (`rule`) and **Rule strong** (`rule-strong`): hairlines, and the borders of chips, buttons and the table header.

### Accent
- **Amber** (`amber`): only "this needs Alex": the alert badge, a waiting or stuck session wash, the selection highlight.
- **Amber ink** (`amber-ink`): amber text, such as warnings, the low timer and send-back outcomes. Dark theme keeps it equal to amber.
- **Amber wash** (`amber-wash`): the fill behind amber chips and the needs-you wash.

### Status
- **Red** (`red`) and **Red wash** (`red-wash`): failed, denied or blocked, on text, chips and outcomes.
- **Green** (`green`) and **Green wash** (`green-wash`): a passing proof, a sent answer, and "now" times.

**The One Lit Accent Rule.** Amber means only "needs Alex". Do not use it for decoration or for plain emphasis.

## Type

System sans for text, system mono for ids, times and code. Numbers use tabular figures. Page title 20px, body 14px, labels 12px. The dashboard keeps rows at 13 to 14px and the one question text at 16px; the health counts are 30px mono. No display type.

## Typography

**Text font:** system sans (`--sans`). **Mono font:** system mono (`--mono`) for ids, times and code. Both stacks are in the frontmatter. There is no web font and no display face.

### Hierarchy
- **Headline** (600, 20px, 28px line, -0.01em): the page title in each view.
- **Title** (400, 16px, 1.45): the one question text on the dashboard and the health state, at max 68ch.
- **Body** (400, 14px, 1.45): the base text and the dashboard panels.
- **Label** (600, 12px): table headers and section labels in the views. Muted colour.
- **Mono** (400, 12.5px): ids, times, file lists and tail rows. Tabular figures.
- **Stat** (600, 30px, 1.05 line, mono): the health counts.

**The No Display Type Rule.** The working views have no display type. Hierarchy comes from weight 600 and ink colour, not from size.

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
