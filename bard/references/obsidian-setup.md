# bard — one-time Obsidian setup assets

Scaffolding written once during `/bard bootstrap`. After that bard only writes
notes; it never rewrites these.

> Verified against the live vault: `bases: true`, `properties: true`, `sync: true`,
> wikilinks default, no community plugins (no Dataview — Bases only).

---

## 1. `Bard.base`

Write to `<vault>/Bard/Bard.base`. Bases is a core plugin; any teammate opens it
with zero setup. Three views: the dashboard, a confidential audit, and the health
view that auto-detects orphans / unreviewed notes.

```yaml
filters:
  and:
    - 'file.inFolder("Bard")'
    - 'file.ext == "md"'
    - 'type != "hub"'
    - 'type != "board"'
views:
  - type: table
    name: Dashboard
    groupBy:
      property: type
      direction: ASC
    order:
      - file.name
      - type
      - up
      - timestamp
  - type: table
    name: Confidential
    filters:
      and:
        - 'confidential == true'
    order:
      - file.name
      - classification
      - timestamp
  - type: table
    name: Health (unreviewed / orphans)
    filters:
      and:
        - 'file.hasTag("bard/unreviewed")'
    order:
      - file.name
      - type
      - tags
```

> Syntax verified against obsidian.md/help/bases/syntax (2026-06):
> - Folder filter is the function `file.inFolder("Bard")`, not `file.folder ==`.
> - Grouping is `groupBy: {property, direction}` (an object), not `group_by:` (string).
> - There is no separate row-`sort:` key in the documented schema — `order` lists
>   columns; sort rows in-GUI by clicking a column header.
> - **Hubs (`type: hub`) and the board (`type: board`) are excluded base-wide** so
>   they don't false-positive as orphans (neither carries an `up`).
> - **The orphan signal is the `bard/unreviewed` tag**, tested with the documented
>   `file.hasTag("bard/unreviewed")`. A no-hub note OMITS `up` and is always tagged
>   `bard/unreviewed`, so the tag arm catches it (empty/null `up` testing isn't in
>   the docs, so we don't rely on it).
>
> Still confirm the views render in-app — the Bases parser is the final judge.

---

## 2. Topic Hub note template

One per approved hub. Filename = hub name verbatim (e.g. `Bard/AWS.md`). Hubs are
entry points, not essays — keep them minimal. Members appear automatically:

- in the hub's **Backlinks pane** (every note with `up: "[[AWS]]"` shows there,
  zero config), and
- in `Bard.base` Dashboard (grouped by type).

```markdown
---
type: hub
title: AWS
description: Hub — AWS work, decisions, and lessons.
tags: [hub]
---

# AWS

Entry point for AWS knowledge. Notes filed here set `up: "[[AWS]]"`; they appear in
the **Backlinks** pane (right sidebar) and in **Bard.base**.

%% Optional: embed a live members list (uncomment if desired).
```base
filters:
  and:
    - file.folder == "Bard"
    - up == "[[AWS]]"
views:
  - type: table
    name: Notes
    order: [file.name, type, timestamp]
```
%%
```

Note: a hub itself has no `up` (it is the top of its spoke), which is why the
`Bard.base` filter excludes `type == "hub"` base-wide — otherwise every hub would
read as a false orphan.

---

## 2b. Weekly TODO board template

Write once to `<vault>/Bard/TODO.md`. `type: board` keeps it out of `Bard.base`
(excluded base-wide alongside hubs), so it never reads as an orphan. Both Alex and
bard edit it; bard appends candidate tasks + marks done items each sweep, Alex curates.
No `up`, no per-item type — just two checkbox buckets.

```markdown
---
type: board
title: TODO
description: Weekly operational board — next-week tasks and recently done. Alex + bard both edit.
tags: [bard/board]
---

# TODO

Weekly board for the work bard sees in swept sessions. **Alex curates; bard is the
scribe** (appends candidate tasks with a source breadcrumb, moves finished items to
Done). Curate freely — delete anything stale.

## Next week

_Open threads and follow-ups. bard seeds these from deferred "want me to…" offers,
parked/gated items, and open questions in the week's sessions._

- [ ] _(nothing yet — first sweep will populate this)_

## Done

_Finished, newest first. Prune entries older than ~4 weeks._

- [ ] _(nothing yet)_
```

---

## 3. Graph color groups (one-time, manual)

bard NEVER writes `.obsidian/graph.json`. Apply once via **Graph view → settings
(gear) → Groups**. Order matters (first match wins) — put the unreviewed group at
the TOP so un-integrated notes light up:

| Order | Query | Color | Purpose |
|-------|-------|-------|---------|
| 1 (top) | `tag:#bard/unreviewed` | bright red/orange | notes with no fitting hub — triage or drop |
| 2 | `tag:#bard/new` | yellow | freshly captured, not yet reviewed |
| 3+ | `tag:#topic/aws`, `tag:#topic/terraform`, … | per topic | cluster by subject |

`showTags` is already `false` in `graph.json` (good — keeps tag nodes out of the
graph). Treat the global graph as a **health check** (spot orphans / clusters),
not navigation; navigation is search + `Bard.base` + backlinks.

Equivalent `colorGroups` block if editing `graph.json` by hand (Alex's call, not
bard's):

```json
"colorGroups": [
  { "query": "tag:#bard/unreviewed", "color": { "a": 1, "rgb": 15695415 } },
  { "query": "tag:#bard/new",        "color": { "a": 1, "rgb": 15779635 } }
]
```
