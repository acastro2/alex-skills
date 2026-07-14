# Block vocabulary

Every block below is plain HTML the template already styles. Copy the class,
fill it in, delete what you don't use. Pick a block only when it earns its place:
prose is the default; a block is for something prose explains badly.

## diagram: Mermaid via CDN

Use for architecture, request/data flow, state machines, sequence. One diagram
per decision or relationship; do not draw a flowchart of something a sentence
covers.

```html
<div class="diagram">
  <pre class="mermaid">
flowchart LR
  A[Client] --> B[createWidget action]
  B --> C[(widgets table)]
  </pre>
</div>
```

Common Mermaid shapes: `flowchart LR/TD`, `sequenceDiagram`, `stateDiagram-v2`,
`erDiagram`. Keep node labels to real symbol/file names. If the CDN is blocked
the raw text still reads as an indented outline (acceptable degradation).

## steps: the plan itself

Numbered, one concern each. Lead with what each step **reuses** before what it
adds. Never ship a single-step plan; never pad.

```html
<ol class="steps">
  <li>
    <strong>Add createWidget server action</strong>
    <p>New action validating input and writing one row.</p>
    <p class="reuses">Reuses: <code>db.insert</code>, <code>WidgetInput</code> zod schema</p>
  </li>
</ol>
```

## file-tree: what changes where

Mark new with `.add`, modified with `.mod`, read-only/reused with `.cmt`.

```html
<pre class="tree">
src/
├── actions/<span class="add">createWidget.ts   + new</span>
└── components/<span class="mod">WidgetList.tsx   ~ empty state</span>
</pre>
```

## code / annotated-code

`<span class="cap">path</span>` is the file caption. For annotations, wrap the
container in `class="ann"` and mark comment lines with `class="note"`.

```html
<pre class="code"><span class="cap">actions/createWidget.ts</span>export async function createWidget(input) { ... }</pre>
```

## diff: before/after

`.h` header lines, `.a` additions, `.d` deletions. Escape `<` as `&lt;`.

```html
<pre class="diff"><span class="d">- old line</span>
<span class="a">+ new line</span></pre>
```

## data-model: table shape

Wrap in `.block` with a `.label`. Flag hard-to-reverse fields (public ids, wire
format, ownership) in the Notes column: those are the bets to get right now.

## api-endpoint: verb + path

`<span class="verb get|post|put|patch|delete">`. One line per route.

## wireframe: UI plans only

Hand-built grey-box HTML inline-styled with the `--wf/--panel` tokens. Show
structure and states (default / empty / loading / error / overflow), not final
visual polish. One block per user-visible state; match the real app's chrome and
density. Do not embed callout prose inside the mock; put notes beside or below.

## callout: decisions & risks

`.callout` (info), `.callout.warn`, `.callout.risk`. Use for the hard-to-reverse
bets and what could go wrong plus mitigation.

## open-questions: single block, bottom only

One `.qform` at the end. Each `<details>` is a question that would actually
change the design, with context and a **recommended default**. If a question
does not change the design, decide it in the plan instead of asking.
