# Design notes: what makes a plan page read well

Distilled from broader frontend-design and dataviz guidance, adapted for this
one context: an engineering plan a reviewer reads once, carefully, to make a
decision. A plan document earns trust through restraint and precision, not
visual ambition. Intentionality over intensity: the template already commits
to one aesthetic (quiet panels, one accent, system type); your job is to
execute it precisely, not to redecorate it.

## Layout and typography

- The craft is hierarchy and rhythm, not fonts. The system font stack is
  deliberate (self-contained file, no webfont fetch); create emphasis with
  size, weight, and space, never by introducing new faces or colors.
- Prose stays at the template's measure (~70ch). Long lines are the fastest
  way to make a careful reviewer skim.
- Never stack blocks back-to-back. Every block (diagram, chart, table, code)
  gets one sentence of prose before it saying what to notice; a block the text
  never mentions is decoration and should be cut.
- Whitespace is load-bearing: it groups related sections and gives the eye a
  resting point between decisions. Do not compress the page to make it look
  denser or more thorough.
- Use the CSS custom properties (`var(--accent)`, `var(--panel)`, `--wf`
  tokens) for any inline styling, never hardcoded hex. The tokens are what
  keep dark mode, light mode, and print all working.

## Color discipline

- One accent for interactive/structural emphasis, green for additions/reuse,
  red for deletions/risk, amber for warnings. That is the whole palette;
  meaning stays stable across the page.
- Color follows meaning, never rank or mood. If two things are the same kind
  of thing, they are the same color everywhere in the document.
- Status colors (risk/warn) are reserved: never use them to make a neutral
  block "pop", and never rely on color alone; the callout label carries the
  meaning for print and colorblind readers.

## Charts (Mermaid xychart/pie/gantt)

Form first, color last. The data's job picks the form:

- Compare magnitudes across a few options: bar (`xychart-beta`).
- Change over time: line (`xychart-beta`).
- Share of a whole: pie, only with 5 or fewer slices; otherwise a bar.
- Phases and dependencies in time: `gantt`.
- One important number (a count, a cost, a p95): not a chart. Put the number
  in prose or a callout; a single-value chart is padding.

Rules that always hold:

- Chart only what you measured or counted during research. Real units on the
  axis title. A chart of estimated or invented numbers misleads a reviewer
  precisely because it looks authoritative.
- One axis. Two measures of different scale are two charts, never a dual-axis
  chart.
- One chart per decision, same bar as diagrams. If no decision hinges on the
  numbers, the chart is decoration.
- Mermaid's default theming (wired to dark/light in the template init) is
  fine; do not fight it with per-chart theme overrides. Keep titles short and
  factual: "p95 latency by approach (ms)", not narrative captions.

## Diagrams

- Node labels are real file/symbol/service names, so the reviewer can grep
  for them.
- Keep a diagram to roughly a dozen nodes. Past that, split by concern or
  collapse a region into one labeled node; a diagram that needs panning has
  failed at its one job.
- Direction should mean something: left-to-right for request/data flow,
  top-down for layers/ownership. Before/after pairs beat one diagram with
  conditional annotations.

## Images and wireframes

- A screenshot's caption states the point of showing it ("current empty
  state: dead end for new users"), not what the image obviously is. Always
  set `alt`.
- Wireframes stay grey-box: structure, states, and density of the real app,
  none of the final visual polish. Polish in a wireframe reads as a promise
  the plan is not making.

## The self-check

Skim the finished page at arm's length: you should be able to reconstruct the
plan's shape from headings, block captions, and callouts alone. If any visual
element does not survive the question "which decision does this help the
reviewer make?", delete it.
