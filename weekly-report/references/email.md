# The weekly email

Read this at step 10. The email shows the report in a designed template.
`render_email.py` computes every number from the facts: header counts, reply codes, the
merges-per-day bars, the ticket-flow bars, the backlog line, the cleanup note, and the footer.

```
report-<week>.json (words) ─┐
                            ├─> render_email.py ─> <week>.email.html ─> Outlook draft (--draft)
facts-<week>.json ──────────┘     assets/email/<template>.html
```

## The report file

The same content as the markdown report, as JSON, plus the diagram rows. The fixture
`tests/fixtures/email/report.json` is a full example.

| Field | Shape | Limit |
| --- | --- | --- |
| `from` | Alex's first name | |
| `preview` | one line the inbox shows under the subject, for example "2 decisions need you: X, Y." | |
| `decisions` | `[{ask, options: [{label, detail?, picked}], why}]` | 5; exactly one `picked` |
| `shipped` | `[{theme, headline, features: [{text, refs: [{ref, url}]}]}]`; replaces `done` in the body | |
| `done` | `[{theme, items: [{text, ref, url}]}]`; old shape, used when `shipped` is absent | 7 items in total |
| `in_flight` | `[{title, lines: ["..."], url?, ref?, diagram?}]`, optional; ongoing work, shown between Shipped and Next; omit or leave empty to hide | 3 items, 1 to 3 lines each |
| `in_flight[].diagram` | `[[cell, ...], ...]`: rows of cells. A cell is `{label, tone}` (`hi`, `plain`, `dashed`) or `{arrow}` | one per big item |
| `next` | `["..."]` | 5 |
| `ideas` | `["..."]`, optional; omit when the week has no ideas | 3 |
| `blocked` | `[{text, waiting_on}]`, `waiting_on` is a first name | |
| `team` | `[{text, ref, url}]`, never a line with `mine: true` | |

A decision with no options gets one option: the recommendation, `picked: true`. Options keep
their A, B order; the picked one is shaded, wherever it sits. Over a limit, the script exits 2
and names the field.

`done` is optional when `shipped` is present. The header done count is the number of shipped
features. An empty `shipped` counts as absent. A missing moves page shows "Moved this week:
not fetched" in the email.

The email is the full report. The script also draws, from the facts and not from the report
file: a stats panel, top-10 repo bars, and a Jira card that shows "Moved this week" (from
`--jira-moved`, see [team-jira.md](team-jira.md)), not only resolved. A day with zero merges
draws no bar: a 2 px cell showed as an empty box in Outlook.

## Content rules

- **Features, never PR titles.** A line says what a person can now do, or what changed for
  them. PR refs sit after it as small evidence links. Why: "these PRs don't mean anything, he
  wants to know features/actuals" (Alex, 2026-11-25).
- **In flight is features too.** Never a list of services or settings. Why: Alex rejected
  such lines as "too down in the weeds".
- **Diagrams are table boxes.** Give each big in-flight item one. Sketch it in mermaid first,
  then fill `diagram` with the same boxes and labels. Outlook drops SVG, so the script draws
  tables.
- **Color and marks.** Orange only for In flight; green stays for shipped. Use Unicode
  markers on items that need attention. No icon images: images from a signed-in host break
  for the reader. No decorative figures: an isometric illustration was rejected as "garbage".
- **Screen before anything leaves.** Drop live weaknesses (an exposed secret to rotate, an
  open vulnerability count) and tool plumbing gaps (which local login failed) from anything
  the manager reads. Keep gaps that change how to read the numbers: a truncated search is a
  lower bound.
- **Review.** Render without `--draft` first, then run the `reviewer` skill on the email. Check sections against each other. If a
  bug sits on a part the same report says was removed, mark it "likely moot". Do not hide it.

## Never paste a web page into Outlook

Outlook strips CSS classes and SVG. The email goes only through `render_email.py` and its
draft step. When the run host is not the Mac, render without `--draft` and say the HTML file
is waiting. On the Mac, open it as a draft with `render_email.open_draft(<path>, <subject>)`.

## Why a script and AppleScript

- **Numbers in code.** Bar heights, widths, and the busiest day are counted, not written by
  the model, so a wrong chart cannot reach the manager.
- **The Microsoft 365 connector cannot send the design.** Its draft tool rejects every
  `style=` attribute (proven 2026-11-13), and the design is made of inline styles.
- **An `.eml` file opens as a received message**, not a draft, in new Outlook for Mac.
- **AppleScript `make new outgoing message` keeps the styles**, in a plain
  `<html><head><style>…</style></head><body>` document. A doctype or `<!--[if mso]>`
  comments give an empty draft, and a `<style>` inside the body shows up as visible CSS
  text. Proven 2026-11-13 on Outlook 16.115, read back in Outlook on the web.
- **The draft saves only once its window opens**, so `--draft` always opens it.

## Templates

`assets/email/light.html` is the designer's template (v1.3), cut into named blocks, with two
local changes the swatch tests forced (both pinned by `tests/test_email.py`):

1. Card and panel are `#050505` in dark, not transparent.
2. Rules inside `@media (prefers-color-scheme: dark)` use `[class~="bt-x"]`, not `.bt-x`.

Inline styles carry the light palette; every colored element has a `bt-*` class. White is
`#FFFFFE`, never `#FFFFFF` (Apple Mail). Colors live in the template, not the script, so
another template with the same blocks drops in with `--template <name>`.
`assets/email/theme-briefing.json` holds both palettes and their contrast checks.

What each Outlook does in dark mode (swatch emails, 2026-11-13, Outlook 16.115 and the web):

| Client | Dark trigger | Fires | Quirk |
| --- | --- | --- | --- |
| Outlook for Mac | the media query, in its own dark mode | attribute selectors in the media block; never `[data-og*]` | forces every painted background to one mid-dark tint; only `transparent` and near-black `#050505` pass |
| Outlook on the web | its own dark theme stamps `[data-ogsb]` | `[data-ogsb]` hooks, but they lose | rewrites class selectors, so a `.bt-x` media rule fires on a dark OS even in its light theme; an attribute selector does not. Its dark theme writes the recolor as an inline `!important` style on each element, which beats every stylesheet rule: surfaces come out blue-grey, and no CSS can fix that |
| Outlook compose window | none | nothing | always shows Outlook's own recolor: never judge the design there |

The card is filled, not transparent, because the dark CSS can fire over a light pane. Light
text on a transparent card there is unreadable.

Not verified: phones, and classic Outlook for Windows (it ignores all of this and
recolors on its own). Check a new template by self-sending one copy and opening it in
each reader; test what a client does with a swatch email of known colors before you
change the design.
