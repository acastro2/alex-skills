# The project pass: Team mode, every week

Read this on every Team-mode run (`scope: team`). It is the tracker half of `--maintain`: the
board half (rows, stages, comments) stays in `SKILL.md`. Built from the first full run on
2026-11-13, when Alex said: "this is the new project curator, this is what we should be doing
plus updating the wiki". The wiki half is the database board; see **The board** at the end.

The project in `config.tracker.areas` is Alex's project, whoever is assigned (SKILL.md hard
rule 3). Every write below is still its own review line; nothing lands without his yes.

```
gather ─┐
scribe ─┴─> bard ─> weekly-report (facts file) ─> project pass ─> review as questions ─> write ─> read back
```

## 0. Inputs

- Run after `weekly-report` in the same week: its facts file (`evidence.team_facts`) holds the
  team's merged and open PRs and the week's tickets. Missing or stale: say so at the top.
- Read the live tracker every run. Never judge from memory of last run or from the ledger.
- Manager answers count as evidence. A reply to the weekly email ("1A 2A 3A") settles the
  decisions it names: re-check `open_items` that waited on them.

## 1. Checks, in this order

Each check ends in proposed lines, or a one-line "checked clean" for the report.

1. **Keyed PRs → state.** Match every PR in the facts file whose title names a ticket key
   against that ticket. Merged work on a `To Do` ticket proposes `To Do → In Progress`.
2. **Unkeyed PRs → a home.** For each PR with no key, find the ticket it belongs to. Keys of
   other projects (another team's tracker) are tracked there: not a gap. Work with no ticket
   anywhere: propose a remote link on the ticket it serves, or a new item (a Done item for
   shipped work, assigned to its author).
3. **In Progress done-check.** Read the description of every open `In Progress` item, not its
   title, and test each "done when" line against evidence. Only a fully met list proposes Done.
   List the unmet line per item in the report; a met list with no evidence of the last step is
   "unverified", never Done.
4. **Done items with live work.** A Done item with an open PR under its key: **read its
   comments first.** The backlog cleanup closes duplicates with "Merged into <survivor>".
   For a merged duplicate, never reopen it: put the open PR on the survivor as a comment.
   Reopen only a Done item that was not merged and whose work is still live.
5. **Bulk-closed audit.** For closes in bulk runs (`jira.bulk_runs`), count how many carry the
   merge comment, then sample the rest (3 or more). A JQL `comment ~` search misses wording
   variants, so a low count is a reason to sample, not proof of a bad close.
6. **Standing-decision conflicts.** An open item that a recorded decision makes moot (on
   2026-11-13: sandbox is being decommissioned) proposes a close as won't do, with a comment
   naming the decision. A criterion that went moot inside an open item gets a comment, not a
   close. When a decision removes an environment, test whether it removes one AC or the
   item's whole purpose. Whole purpose (on 2026-11-13 one item was all preprod): propose a
   close, asked as its own question. Never rewrite its ACs: that leaves an empty item.
7. **Owners.** For each unassigned open item, propose an owner only where evidence names one:
   a handoff ticket, the PR author, the epic owner of merged work. No evidence: list it once;
   Alex decides whether it goes to his manager.
8. **Parents.** List items with no parent (`parent is EMPTY`); propose a parent only from
   evidence (the title's `[AREA]` prefix and the description's "Parent:" line).
9. **Epic weekly comment, every active epic.** Done this week by name, Next, Blocked only
   when real. A week with no movement gets "No movement this week." Read the epic's comments
   first, and skip one already posted this week. Personnel epics are out by the exclusion
   screen.
10. **Epic gap check.** For each active epic: objective (description) minus Done children
    minus open children's ACs = gaps. A gap must trace to an objective line or to this week's
    evidence, and be one ticket of work. Run it with read-only workers on a large project,
    then check their claims against the tracker before they reach the review. A quote a worker
    returns must trace to a source before Alex sees it: check the vault, then Jira, then
    Slack. A quote nobody can find does not drive a question.
11. **Anchor links.** Every epic in the areas is an anchor (linked from exactly one row) or
    links to exactly one anchor with `tracker.anchor_link_type`. Two anchor links: flag it,
    never pick. None: propose one from evidence only. Then compare each anchor with its row:
    epic status with Stage, epic due date with Milestone date (from `2. Committed`), the epic's
    theme label (a `config.themes` value) with Theme. A mismatch is a Needs-you line that fixes the side that does
    not own the fact: the epic owns status and due date; the row owns the rest.

## 2. The review, as questions

Alex answers the project pass through the `question` tool, not a one-line answer (2026-11-13:
"ask as questions"). Show the written review first, then one question per group:

- state moves (multi-select, each option names the ticket, its owner and the evidence);
- reopen or close calls (single choice, the recommended option first);
- owners, new items, links (multi-select);
- comments (one question: all, some, none), with the exact text shown above the question.

A question he skips or answers "leave it" goes on `open_items`; it is not re-asked the same week.

The `question` tool cuts long answers off in the conversation record (2026-11-13: two answers
were lost and asked again). Apply each group as soon as he answers it, or write the answers to
the ledger (`open_items` or `updates`) first. Never rebuild answers from a summary.

## 3. Writing and read-back (Jira, Atlassian connector)

Facts seen live on 2026-11-13. Each one cost a silent wrong result once:

- **Compact views hide `parent` and `description`,** in search and in `getJiraIssue` alike.
  Read a parent with `getJiraIssue` `view: full`. An empty `fields: {}` means hidden, not
  missing.
- **Assignee needs an account object:** `{"assignee": {"accountId": "<id>"}}`. A bare id string
  returns success and changes nothing. Take ids from `atlassianUserInfo` (Alex) or a reporter
  field of another ticket (teammates); never write an id into this repo.
- **Transitions:** list them per item first (`listJiraIssueTransitions`). A simplified workflow
  may have only To Do, In Progress, Done and no won't-do resolution: close as Done and say
  "won't do" in the comment, and tell Alex that Done reports will count it.
- **Remote PR links:** `addGraphContext` with `jira-work-item-links-jira-work-item-remote-link`.
- **Rewriting a description:** read it with `responseContentFormat: html`. Change only the
  lines that conflict. Add an "Updated <date>:" line that quotes the old wording, and keep any
  "Original description" section word for word. Write it back as html, so task-list
  `data-local-id` nodes survive. Board fields still never go in a description (SKILL.md hard
  rule 4).
- **Read back each touched key** with `getJiraIssue` `view: full`, never with a search. JQL
  lags fresh writes: on 2026-11-13 a `parent = <epic>` search missed three new children and one
  moved child, and the writes looked failed when they had not. Search finds work; it does not
  prove a write. An edit response can also echo the old value.

## 4. The ledger

Record every write under `tracker.<key>.updates` (date, change or comment id), so a rerun in the
same week posts nothing twice. A lesson from a mistake goes on `open_items` and, once it holds,
into this file.

## 5. The board

Board writes follow "Writing the database board" in `references/team-board.md`: find the row by
Row ID, write approved cells, read back. Until Alex approves the real database, they go to
`board.scratch_database_id`. Never write board fields into a Jira description (SKILL.md hard
rule 4).

Page writes follow `references/wiki-pass.md`; which wiki content may be written at all is
SKILL.md hard rule 2. Row comments: see the not-yet-tried note in `references/team-board.md`.
