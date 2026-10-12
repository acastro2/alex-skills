# Connections pass — ideas Alex would not see from a glance

Reference for the **Connections pass** section of `SKILL.md` (decided by Alex on 2026-10-12).

The run is prescriptive: it checks rules and fills review tables. That finds what is wrong with a
row, but not what is true *between* rows. This pass is the one place where the curator looks across
everything it gathered and brings Alex new relations, risks and ideas. It is bounded on purpose:
it suggests, and it never writes.

## When it runs

- Last, after every review table (recap, `A#`, `D#`, `W#`, `E#`) is built. The tables, their order,
  and the approval rules do not change. The run still stops for Alex's answers.
- In every run mode that builds review tables: the weekly maintenance run, a full audit, and a
  board population run. A run that only applies Alex's dictated updates skips it.
- Once per run. If Alex asks for "more ideas" in the same session, run it again on the same evidence.

## The engine

**In Claude Code, use the `advisor` tool.** It takes no parameters and reads the whole session
transcript, so it sees every row, epic, AAB item, comment and document this run pulled, with no
evidence pack to build. Before the call, write this brief as plain text in the session, so the
advisor knows the job:

> Connections pass. The review tables above are done. Look across everything gathered in this run
> for relations that no single row, epic or AAB item shows on its own. For each idea, name what
> connects to what, cite at least two pieces of evidence from this run by name, say why it matters
> to Enterprise Architecture or to the CTO, and give one cheap next step. Prefer three strong ideas
> over ten weak ones. "Nothing new this week" is a valid answer.

**Where there is no advisor** (OpenCode, Pi, or a Claude Code session without it), spawn one
fresh-context subagent on the strongest model the host offers, with the same brief plus a short
evidence summary: the live rows (title, stage, EA role, theme, milestone, sponsor), the EA epics and
their states, the open AAB items, and the comments and documents this run read. Scrub the summary
first: no URLs to internal hosts, no person names beyond the ones the board already shows, nothing
the exclusion screen blocks.

The advisor is a reviewer, not a source. Its ideas are inputs to the filter below, never facts.
Never cite the advisor as evidence for anything.

## What to look for

Examples, not a closed list:

- One row blocks or depends on another, and neither row says so.
- Two teams build the same thing, or one platform could serve two rows.
- An AAB decision affects a row that does not link the AAB item.
- One sponsor or one person carries too many live bets at once.
- Milestones bunch up in the same week, or a date contradicts a dependency's date.
- An Exploring row hit an AAB trigger (spend, cross-team, security, one-way door) with no AAB item.
- Work in ADO points to a bet that has no row.
- A Parked idea's blocker cleared, or new evidence supports it.

## The filter

Run every candidate idea through these steps, in order. An idea that fails a step is dropped and
listed under the ideas table as "Filtered out" with the step that stopped it.

1. **Evidence.** The idea cites at least two pieces of evidence from this run, and each one is real:
   a row, epic, AAB item, comment or document you actually read this run. Check each citation
   yourself. One source, or a source you did not read, is a guess.
2. **Exclusion screen.** The idea and its next step pass the same screen as a board row
   (privileged, vendor-sensitive, scope-claiming, HR). The I# table is for Alex only, but he forwards
   things.
3. **Not already declined.** Not in `not_doing`, and not the same idea as a `Drop` entry in the
   ledger `ideas` key. When you are not sure two ideas are the same, ask Jev `same_idea`.
4. **Jev grades it** with the Connections pass questions in [jev-gates.md](jev-gates.md):
   `evidence_supports`, `non_obvious`, `actionable`. Any answer at or below 0.20 drops the idea.
   Every other idea is shown, with its numbers. Ideas where all three are at or above 0.80 come first.

There is **no cap** on the number of ideas (Alex, 2026-10-12). Show every idea that passes. Zero is a
valid result: write "No connection cleared the bar this run" and the filtered-out list. Never pad.

## The I# table

The last table in the run report, after the five review tables, under the heading
**Ideas (hypotheses, not approved work)**. Lines are numbered `I1`, `I2`, ...:

| # | Idea | Connection | Evidence | Why it matters | Cheap next step | Jev |
|---|---|---|---|---|---|---|
| I1 | One line, plain words | What links to what, by name | The cited sources, by name | One line | One concrete step for this week | evidence 0.91 · non-obvious 0.84 · actionable 0.88 |

- Name rows, epics and AAB items by name, never bare IDs.
- A returning Parked idea says so in the Idea cell: "Parked 2026-10-19, back because <new evidence>".
- Alex answers per line: **Act**, **Park** (with what would bring it back, if he says), or **Drop**.
  No answer means the idea stays undecided and comes back next run only if it passes the filter again.

## The ledger and what happens next

Record every idea shown in `curated.json` under `ideas`, keyed `YYYY-MM-DD-I<n>` (the run date and
the line number):

```json
{
  "2026-10-19-I1": {
    "date": "2026-10-19",
    "text": "Agent Platform and Enterprise Knowledge Agent wait on the same POC readout; one AAB item could decide both",
    "evidence": ["row:Agent Platform, production", "row:Enterprise Knowledge Agent, Cleo successor", "ado:257369"],
    "decision": null,
    "decided": null,
    "revisit_when": null
  }
}
```

- **Act:** set `decision` and `decided`. The next run turns the idea into real `A#`, `D#`, `W#` or
  `E#` lines, and each line's `Why` cell cites the idea key. Acting on an idea never skips the review
  tables.
- **Park:** set `revisit_when` to the evidence that would reopen it, in Alex's words when he gave
  them. Every run checks the parked ideas against the new evidence and re-shows one only when that
  evidence changed.
- **Drop:** the idea never comes back, in any wording.

## Hard limits

- The curator never writes an idea to a list, a page, an ADO item, a comment or the newsletter. Ideas
  live in the run report and the ledger, nowhere else.
- An idea never changes a review table that is already built, and never adds a line to one in the
  same run.
- Jev and the advisor judge fit. The rules (evidence, exclusion screen, `not_doing`, Drop) decide
  what Alex sees.
