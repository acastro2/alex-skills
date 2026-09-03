# bard — one-time Obsidian setup assets

Scaffolding written once during `/bard bootstrap`. Create `Done Archive.md` from its
template even when it has no entries, so the board link resolves. After that bard
maintains the root `Todo.md` board per `SKILL.md`; it does not rewrite these setup assets.

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
> - **Hubs (`type: hub`) and board notes inside `Bard/` are excluded base-wide** so
>   they don't false-positive as orphans (neither carries an `up`).
> - The root `<vault>/Todo.md` is outside `file.inFolder("Bard")`, so it is already
>   excluded and `Bard.base` needs no filter change.
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

## 2b. Root TODO board (`Todo.md`) template

Write once to `<vault>/Todo.md`, the root of the vault. The exact filename is `Todo.md`
(capital T only), not `TODO.md`. This is Alex's file: it gets **no frontmatter**, and
bard must not add YAML to it. The `Bard.base` block above already uses
`file.inFolder("Bard")`; that filter excludes a root-level `<vault>/Todo.md`, so
`Bard.base` needs no filter change.

Everything above the `<!-- BARD:START -->` marker belongs to Alex. bard never edits,
reorders, or reads it as task input. bard edits only from the marker down. If the marker
is absent, append the whole block at the END of the file, never at the top. Alex curates;
bard is the scribe. New items go at the top of their topic group within the derived
horizon. Finished items move to the top of flat `## Done`. Items older than ~4 weeks roll
to `Bard/Done Archive.md`; moving replaces pruning, and nothing is deleted.

```markdown
<!-- BARD:START — bard owns everything below this line. Alex owns everything above. -->

# BARD List

_Seeded by `/bard` from swept sessions. Newest first in each topic group. Alex curates, bard is the scribe. The priority emoji at line end is Obsidian Tasks syntax._

## Open

### 🔥 This week
#### 📊 Grafana
- [ ] Send Tyler the alerting done message `(01a025e2)` ⏫
#### 🔐 Security
- [ ] Rotate the Snowflake SCIM token `(8bf834c5)` 🔺

### 📅 This month
#### 🏛️ Enterprise Architecture
- [ ] Fix the 5 overdue EA milestones `(da41d7ea)` 🔼

### ⏳ Waiting on others
#### ☁️ AWS
- [ ] Bucket-policy owner repoints aws:SourceVpce `(aa2f6ad0)` 🔼

### 🧊 Someday
#### 🔐 Security
- [ ] Scope the org-wide Firemon decommission `(f1fd2740)` 🔽

## Done

_Last ~4 weeks. Older rolls to [[Done Archive]]._

- [x] 🏛️ Published the 08-19 AAB recap `(da41d7ea)` ⏫ ✅ 2026-08-21
```

Apply the horizon derivation table and fixed topic-map order in `SKILL.md`. Test
`⏳ Waiting on others` first. Omit empty horizon and topic headings.

Open lines use this exact format:

```text
- [ ] <short imperative description> `(<session id>)` <priority emoji>
```

Done lines use this exact format:

```text
- [x] <topic emoji> <short description> `(<session id>)` <priority emoji> ✅ YYYY-MM-DD
```

Descriptions are short imperatives. Target 80 characters or fewer; hard cap 90. Drop
detail — the session id is the record. The breadcrumb is the session id only, backticked.
It has no `session ` prefix, repo, or ` · ` separator. The `####` heading carries the
topic emoji, so open lines have no topic emoji. The priority emoji is the last token on an
open line. On a done line, the priority emoji and `✅ YYYY-MM-DD` are the last two fields.
The installed Obsidian Tasks plugin (v8.3.0) uses `$`-anchored trailing-field regexes in a
loop. Any text after the priority emoji stops it parsing. Put the breadcrumb before the
priority, never after it. Every line carries exactly one priority emoji.

Priority symbols: 🔺 Highest, ⏫ High, 🔼 Medium, 🔽 Low, ⏬ Lowest. Use the meanings in
`SKILL.md`. Reuse the fixed topic map in `SKILL.md`; never invent a topic emoji.

Optional priority-sorted view for the root board:

```tasks
not done
path includes Todo.md
sort by priority
```


---

## 2c. Done Archive (`Done Archive.md`) template

Write rollover entries to `<vault>/Bard/Done Archive.md`. This is a board file inside
`Bard/`, not a knowledge note. Use frontmatter `type: board`. The verified `Bard.base`
filter includes `file.inFolder("Bard")` and excludes `type == "board"`, so the archive
stays out of the base by type. The folder filter excludes the root `<vault>/Todo.md`, not
the archive.

Use `# Done Archive`, then `## YYYY-MM` sections. List months newest first. List items
newest first inside each month. Keep the same flat Done line format as `## Done`.

```markdown
---
type: board
---

# Done Archive

## 2026-08

- [x] 🏛️ Published the 08-19 AAB recap `(da41d7ea)` ⏫ ✅ 2026-08-21
```

Rolling over means moving, not deleting. A future full retrospective rebuild writes its
finished-work haul here, never into `Todo.md`. The roll-over/prune step never deletes
archive content.

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
