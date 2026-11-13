# The weekly email

Read this at step 10. The email shows the written report's words in a designed template.
`render_email.py` computes every number from the facts: header counts, reply codes, the
merges-per-day bars, the ticket-flow bars, the backlog line, the cleanup note, and the footer.

```
report-<week>.json (words) ─┐
                            ├─> render_email.py ─> <week>.email.html ─> Outlook draft (--draft)
facts-<week>.json ──────────┘     assets/email/<template>.html
```

## The report file

Same words as the markdown report, as JSON. The fixture
`tests/fixtures/email/report.json` is a full example.

| Field | Shape | Limit |
| --- | --- | --- |
| `from` | Alex's first name | |
| `preview` | one line the inbox shows under the subject, for example "2 decisions need you: X, Y." | |
| `decisions` | `[{ask, options: [{label, detail?, picked}], why}]` | 5; exactly one `picked` |
| `done` | `[{theme, items: [{text, ref, url}]}]` | 7 items in total |
| `next` | `["..."]` | 5 |
| `blocked` | `[{text, waiting_on}]`, `waiting_on` is a first name | |
| `team` | `[{text, ref, url}]`, never a line with `mine: true` | |

A decision with no options gets one option: the recommendation, `picked: true`. Options keep
their A, B order; the picked one is shaded, wherever it sits. Over a limit, the script exits 2
and names the field.

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
