# Root TODO board — rules

Every rule here is binding on a sweep. `bard/SKILL.md` points here; this file owns the
board's formats and decisions.

## Contents

- Identity
- Ownership split
- Board structure
- Line format and parser constraint
- Priority
- Topic emoji
- Horizon derivation and seeding
- Ordering, completion, and curation
- Alex edits this board by hand
- Bulk clear

## Identity

`<vault>/Todo.md` is the root-vault operational board. The exact filename is `Todo.md`
(capital T only), not `TODO.md`. It is Alex's file, seeded from swept sessions. Alex
curates; bard is the scribe. It has no frontmatter and is not a knowledge note.

## Ownership split

**Hard rule.** Everything above the `<!-- BARD:START -->` marker belongs to Alex. bard
never edits it, reorders it, or reads it as task input. bard edits ONLY from the marker
down and never adds frontmatter to this file. If the marker is absent, bard appends the
whole block at the END of the file — never at the top. The retired `Bard/TODO.md` is a
pointer stub only; it is not the board.

## Board structure

Below the marker: `# BARD List`, then `## Open` holding horizon headings
(`### <emoji> <name>`), each holding topic headings (`#### <emoji> <name>`) with the
task lines, then a flat `## Done`. The full block template lives in
[obsidian-setup.md](obsidian-setup.md).

## Line format and parser constraint

Open lines are exactly:

```text
- [ ] <short imperative description> `(<session id>)` <priority emoji>
```

Done lines are exactly:

```text
- [x] <topic emoji> <short description> `(<session id>)` <priority emoji> ✅ YYYY-MM-DD
```

Descriptions are short imperatives. Target 80 characters or fewer; hard cap 90. Drop
detail — the session id is the record. The breadcrumb is the session id only, backticked.
It has no `session ` prefix, repo, or ` · ` separator. The `####` heading carries the
topic emoji, so open lines have no topic emoji. The priority emoji is the last token on
an open line. On a done line, the priority emoji and `✅ YYYY-MM-DD` are the last two
fields. The installed Obsidian Tasks plugin (v8.3.0) parses trailing fields with
`$`-anchored regexes in a loop. Any text after the priority emoji stops it parsing. Put
the breadcrumb before the priority, never after it. Every line carries exactly one
priority emoji.

## Priority

Use Obsidian Tasks native symbols:

| emoji | level | when |
|---|---|---|
| 🔺 | Highest | a hard deadline within ~7 days **whether or not a date string appears** ("needs it today", "2.1 days before retention", "before Friday's freeze"); an exposed credential or secret; production broken; a legal, regulatory, or counsel deliverable |
| ⏫ | High | a **named person or team is waiting on you** (Jeremy, Tyler, counsel, CAB, the DBAs); OR it blocks a specific PR, ticket, or someone else's work; OR it is tied to a real-world event — townhall, forum, review, release — even with no written date |
| 🔼 | Medium | real work, nobody named is waiting, no deadline |
| 🔽 | Low | cleanup or hygiene, no consequence if it slips a month |
| ⏬ | Lowest | someday/maybe, parked with no owner |

Grade from the EVIDENCE, not the wording. A deadline counts even when it is implied
rather than written as a date. A person counts when they are named anywhere in the
thread, not only when the session proves they are blocked.

**Direction test for ⏫ — read this before you grade.** The named party must be waiting on
**YOU**: you owe them something. **You** waiting on a named person is NOT ⏫. Grade that on
its own merit (usually 🔼) and file it under `⏳ Waiting on others`. The names in the table
are illustrations of who might be owed, not tokens to match on. A session saying "Tyler
must approve X, Alex will wait" is Alex waiting on Tyler — 🔼, not ⏫.

**Spread check — both directions.** A one-sided cap fails: capping only the top drains
everything into 🔼, which is just as useless as marking everything ⏫. After grading,
check the distribution against these targets and re-grade before writing if it misses:

| priority | target share of open items |
|---|---|
| 🔺 | 5–12% |
| ⏫ | 15–25% |
| 🔼 | 45–65% |
| 🔽 + ⏬ | the remainder |

**⏫ must never be 0.** Zero high means the bar was read as demanding proof no real
board ever has. Report the final distribution in the sweep report.

**Count the spread in Python, never with `grep -o`.** BSD `grep -o '🔺\|⏫\|🔼'` does not
alternate correctly over these multi-byte symbols: on 2026-09-04 it reported all 115
open items as ⏫, and only the implausibility of a 100% result caught it. A subtly wrong
count would have "confirmed" a bad board. Read the file, take the LAST priority symbol
on each `- [ ]` line, and tally with `collections.Counter`.

**Re-grading moves the item.** Horizon is derived from priority, so demoting ⏫→🔼 to
land inside the band also moves that line out of `🔥 This week` into `📅 This month`
(or into `⏳ Waiting on others` if the next action turned out to be someone else's).
Do the spread pass BEFORE placing lines, or re-place every line you re-graded.

## Topic emoji

Fixed map. Reuse these symbols. Never invent a new one:

`☁️` AWS / cloud · `❄️` Snowflake · `🏗️` Terraform / IaC · `📊` Grafana /
observability · `🔐` security / access / credentials · `🏛️` enterprise architecture /
governance / docs · `🎫` Azure DevOps / process · `🐙` GitHub · `🧪` testing / QA · `🤖`
AI / agents / skills · `👥` people / hiring / comms · `💰` cost / licensing · `🗄️`
databases / SQL Server · `📦` anything else.

## Horizon derivation and seeding

Horizon is DERIVED, never guessed from prose. The fixed horizon set and order are:
`### 🔥 This week`, `### 📅 This month`, `### ⏳ Waiting on others`, `### 🧊 Someday`.
Test `⏳ Waiting on others` FIRST — ownership beats priority.

| horizon | rule |
|---|---|
| 🔥 This week | priority 🔺 or ⏫ AND the next action is Alex's |
| 📅 This month | priority 🔼 AND the next action is Alex's |
| ⏳ Waiting on others | the next action belongs to someone else, at any priority |
| 🧊 Someday | priority 🔽 or ⏬, or parked with no owner |

Topic sub-headings use the fixed topic-emoji map, written as `#### <emoji> <name>`
(e.g. `#### ❄️ Snowflake`). Order them in fixed map order for predictable scanning,
not by size. Omit any heading with zero items — horizon and topic alike. The board never
shows an empty section.

Use high recall. Seed everything bard seeds today: Alex's commitments, unanswered
"want me to X?" offers, `PARKED`/`DRAFTED`/gated items, open questions, and handoffs.
Never invent a task. If the session did not defer it, it does not go on the board.

## Ordering, completion, and curation

A new item goes at the TOP of its `####` topic group, never appended at the bottom. Create
horizon and topic headings only when they contain an item. Keep both heading levels in
fixed order. `## Done` stays flat; insert a newly completed item at the top of `## Done`.
On every sweep, bard re-checks every open item against the swept sessions. When a session
clearly shows an item finished — for example, a merged PR, applied change, shipped report,
or sent message — bard checks the box, restores the topic emoji from its `####` heading,
appends `✅ <ISO date>`, and MOVES the line to the top of `## Done`. This is mandatory,
not best effort.

`## Done` holds only the last ~4 weeks. Anything older rolls over to
`<vault>/Bard/Done Archive.md`; pruning now means moving, not deleting. The archive is
never deleted or shortened. It has frontmatter `type: board`, `# Done Archive`, and
`## YYYY-MM` month sections, newest month first, with newest items first inside each
month. Archive lines use the same flat Done format. The verified `Bard.base` filter uses
`file.inFolder("Bard")` and excludes `type == "board"`, so the archive stays out of the
base by type; that folder filter excludes the root `<vault>/Todo.md`, not the archive.
A future full retrospective rebuild writes its finished-work haul into `Done Archive.md`,
never into `Todo.md`. The roll-over/prune step never deletes archive content.

bard adds items, marks done, and rolls over old `## Done` entries. It never deletes an
open item Alex has not actioned. Secrets, PII, and regulated specifics stay off the board,
the same as notes.

## Alex edits this board by hand — re-read it immediately before writing

`Todo.md` is a live file Alex works in Obsidian between sweeps. He ticks items off
himself, adds his own, and edits text. **Never write the board from state read earlier in
the run.** Re-read it as the last step before the write, and diff against what the sweep
started with.

- An item Alex checked himself is a REAL completion. Keep his `✅ <date>` and move it to
  `## Done`. Never revert it to `- [ ]`, and never restamp it with a different date.
- An item Alex added by hand stays, even with no breadcrumb and no priority emoji. Grade
  and file it, do not delete it for failing the format.
- An item Alex edited keeps his wording.

This is a data-loss class, not a style rule: a sweep that trusts stale state silently
erases work Alex already did.

## Bulk clear (only when Alex asks)

When Alex asks to clear the board, archive it — do not mark it done.
Read [Bulk clear](bulk-clear.md) only for that request, before changing
`Todo.md` or `Bard/Done Archive.md`. A bulk clear never deletes items or invents
completion dates; keep real completions separate from unverified cleared items.
