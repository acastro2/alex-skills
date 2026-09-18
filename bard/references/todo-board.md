# Root TODO board — rules

Every rule here is binding on a sweep. `bard/SKILL.md` points here; this file owns the
board's formats and decisions.

## Contents

- Identity
- Ownership split
- Intake gate, caps, and the backlog
- Board structure
- Line format and parser constraint
- Priority
- Topic emoji
- Horizon derivation and seeding
- Ordering, completion, aging, and curation
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

## Intake gate, caps, and the backlog

The board is the short list of things that hurt if they fall through the cracks. It is
NOT a record of everything a session deferred. Decided 2026-09-18 after the board hit 108
open items and stopped being readable.

**Gate.** An item goes on the board only when ALL of these hold:

1. **Consequence if dropped.** At least one: a deadline (written or implied), a named
   person or team waiting on Alex, production or a secret at risk, or a promise Alex made
   to a named person. Unanswered "want me to X?" offers, `PARKED`/`DRAFTED` ideas, open
   questions with no owner, and hygiene never pass the gate on their own.
2. **One next action.** The line is a single step Alex can finish in one sitting. A
   project, epic, or multi-step effort is not a board item. It lives in the backlog as one
   line, and ONLY its next step sits on the board. Split before you place.
3. **Evidence is reachable.** The line carries the source session id, and a wikilink to
   the Bard note written from that session whenever one exists (see line format). When
   no note exists yet, the item may still go on the board with the session id alone, but
   the sweep report lists it under "board items without a note" and the NEXT sweep writes
   that note. Hand-added items with no session id are exempt.

**Caps.** Hard limits, checked after every sweep and before the write:

| scope | cap |
|---|---|
| `🔥 This week` | 5 |
| all `## Open` lines | 12 |

Over a cap, move lines to the backlog until under it: lowest priority first, then oldest
source session first. Never bump an item Alex added or edited by hand; ask instead.
Report every moved line in the sweep report.

**Backlog.** Everything that fails the gate or falls off a cap goes to
`<vault>/Bard/Backlog.md`. It is uncapped and uses the same line format as an open board
line (wikilink, session id, priority), so no context is lost. Structure: frontmatter
`type: board` (keeps it out of `Bard.base`), `# Backlog`, then one flat list in the same line format, sorted by priority then
topic-map order, the same as the board. The backlog is the only place high recall
lives. When a later session shows a backlog item now passes the gate (a name appears, a
date appears, a step becomes concrete), promote it to the board. bard reads the backlog
on every sweep for exactly that check.

## Board structure

Below the marker: `# BARD List`, then `## Open` holding horizon headings
(`### <emoji> <name>`), each holding a flat list of task lines, then a flat `## Done`,
then `## Legend` (three italic lines: topic emoji map, priority scale, line anatomy).
The legend is the LAST thing in the file; bard keeps it there and keeps it in sync with
the maps in this file. `Bard/Backlog.md` ends with the same legend.
There are NO topic sub-headings (decided 2026-09-18: with a 12-item board, a `####`
heading per single item doubled the visual noise). The topic emoji is the first token of
every line instead. The full block template lives in
[obsidian-setup.md](obsidian-setup.md).

## Line format and parser constraint

Open lines are exactly:

```text
- [ ] <topic emoji> <next action> [[<Bard note title>]] `(<session id>)` <priority emoji>
```

Done lines are exactly:

```text
- [x] <topic emoji> <next action> [[<Bard note title>]] `(<session id>)` <priority emoji> ✅ YYYY-MM-DD
```

The description is a short imperative naming ONE next action. Target 60 characters or
fewer for the description, hard cap 90. There is no cap on the whole line: the wikilink
carries the full note title so Alex sees which note it opens.

**Evidence link (mandatory).** `[[<Bard note title>]]` is a wikilink to the Bard note
written from the source session; find it by matching the line's session id against the
note's `source:` frontmatter (the 8-char id is the prefix of the full id). One click in
Obsidian gives Alex the What, the decisions, and the people. If several notes share the
session, link the one whose title best matches the action. If no note exists yet, omit
the wikilink, keep the session id, report the gap, and write the note on the next sweep
(see gate). The backticked session id stays beside the link so
`claude --resume <id>` still works when the note is not enough. The id has no `session `
prefix, repo, or ` · ` separator.

Every line, open or done, starts with its topic emoji from the fixed map. The
priority emoji is the last token on an open line. On a done line, the priority emoji and
`✅ YYYY-MM-DD` are the last two fields. The installed Obsidian Tasks plugin (v8.3.0) parses trailing fields with
`$`-anchored regexes in a loop. Any text after the priority emoji stops it parsing. Put
the wikilink and the session id before the priority, never after it. Every line carries exactly one
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

**Re-grading moves the item.** Horizon is derived from priority, so demoting an item can
move it out of `🔥 This week` (or into `⏳ Waiting on others` if the next action turned
out to be someone else's). Do the spread pass BEFORE placing lines, or re-place every line
you re-graded. With a 12-item board the spread targets are a sanity check, not a quota:
a board of 12 real consequences may legitimately be mostly 🔺/⏫.

## Topic emoji

Fixed map. Reuse these symbols. Never invent a new one:

`☁️` AWS / cloud · `❄️` Snowflake · `🏗️` Terraform / IaC · `📊` Grafana /
observability · `🔐` security / access / credentials · `🏛️` enterprise architecture /
governance / docs · `🎫` Azure DevOps / process · `🐙` GitHub · `🧪` testing / QA · `🤖`
AI / agents / skills · `👥` people / hiring / comms · `💰` cost / licensing · `🗄️`
databases / SQL Server · `📦` anything else.

## Horizon derivation and seeding

Horizon is DERIVED, never guessed from prose. The fixed horizon set and order are:
`### 🔥 This week`, `### 📅 This month`, `### ⏳ Waiting on others`.
Test `⏳ Waiting on others` FIRST — ownership beats priority.

| horizon | rule |
|---|---|
| 🔥 This week | the top 5 Alex-owned items by priority (🔺 before ⏫), ties broken by the nearest deadline or event |
| 📅 This month | every other Alex-owned item: 🔺/⏫ that missed the top 5 sort first as "next up", then 🔼 |
| ⏳ Waiting on others | the next action belongs to someone else, at any priority |

There is no `🧊 Someday` horizon any more. Priority 🔽 or ⏬, or parked with no owner, means
the item failed the gate: it belongs in `Bard/Backlog.md`, not on the board.

Inside a horizon, order lines by priority (🔺 first), then by fixed topic-map order, then
newest first. Omit any horizon heading with zero items. The board never shows an empty
section.

Seed with high recall into the BACKLOG, then let the gate pick the board. Capture every
commitment, unanswered "want me to X?" offer, `PARKED`/`DRAFTED`/gated item, open question,
and handoff, but only the ones that pass the intake gate land on `Todo.md`. Never invent
a task. If the session did not defer it, it goes nowhere.

## Ordering, completion, aging, and curation

A new item goes into its horizon at the position its priority and topic dictate (see
ordering above). Create a horizon heading only when it contains an item. `## Done` stays flat; insert a newly completed item at the top of `## Done`.
On every sweep, bard re-checks every open item against the swept sessions. When a session
clearly shows an item finished — for example, a merged PR, applied change, shipped report,
or sent message — bard checks the box, keeps the topic emoji, appends `✅ <ISO date>`, and MOVES the line to the top of `## Done`. This is mandatory,
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

**Aging.** An open board item with no evidence in any swept session for 30 days (count
from the source session's timestamp, or from the last session that mentioned it) moves to
`Bard/Backlog.md` with its wikilink and session id intact, and is listed in the sweep
report. Items Alex added or edited by hand are exempt: bard never ages them out, it asks.

bard adds items, marks done, promotes from and demotes to the backlog, and rolls over
old `## Done` entries. It never deletes an item anywhere: off the board means into the
backlog. Secrets, PII, and regulated specifics stay off the board,
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
