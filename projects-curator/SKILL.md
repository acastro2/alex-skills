---
name: projects-curator
description: >
  Turn scattered evidence of what a team did (AI sessions, decision records, tickets, PRs) into a
  small, executive-legible board of initiatives, and keep it true week after week. Use for board
  population, row updates and comments, weekly maintenance, full audits, ticket and epic upkeep
  against the board, decision-forum close-outs, and a weekly roll-up. Works with any board, tracker
  or forum; org facts live in the local ledger. Org-visible writes need a numbered user review,
  decisions first. Not for writing one ticket, that is ticket-writer, or for personal notes, that
  is bard.
---

# Projects Curator

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

Turn the scattered evidence of what a team actually did into a small set of executive-legible rows on a board. You are a **filter and transformer**, not a retriever and not a scribe: you receive raw signals, decide what qualifies, shape it for a non-technical executive, and then **ask** before you write.

```
archeologist ─┐
tracker + git ┼─→ curate: cluster · screen · shape ─→ REVIEW ─→ write ─→ verify ─→ report
comms, notes ─┘                                      (approve by line)
```

For prose, follow [Alex's voice](../alex-voice/SKILL.md).

Three invariants that override everything below:

1. **Never invent.** No initiative the evidence doesn't support; no impact claim that isn't documented. An empty cell is better than a soft one.
2. **Never write unconfirmed.** The board is org-visible. The review gate *is* the mandatory human review. Skipped and excluded candidates are never written; the user owns what gets published.
3. **`Stage` is Alex's column.** He curates lifecycle position himself. Never bundle a Stage move into other edits; a proposed move is always its own line in the review, flagged as needing his explicit yes. Applying his dictated updates → touch only the fields he named.

## Setup — once per org

This skill holds no org facts. Before the first run, ask Alex for these and store them under the `config` key of the ledger `curated.json`, which is gitignored. Why: org names, URLs and vocabulary must never land in this repo.

| Key | What it holds |
|---|---|
| `board` | Where the board lives, how to read and write it, and the real field names for the columns below |
| `tracker` | The work tracker, and the areas or projects that count as this team's work |
| `forum` | The decision forum and its queue, if the org has one. No forum: skip the forum control |
| `themes` | The allowed Theme values, and any tie-break rule |
| `audience` | Who reads the board, and which executive it must make sense to |
| `week` | The time zone and the week boundaries |
| `scope` | `personal` (Alex's own record, the default) or `team` (the team's portfolio; see Team mode) |
| `board.columns`, `board.page_id`, `board.scratch_page_id`, `board.read_only_pages` | For a wiki-page board: the table's exact header row, the one page the run may write, a private copy for the first write, and pages it must never write (a vision page, a hand-kept hub) |
| `tracker.label_contract` | Where a tracker's label contract lives (repo, path, ref), when agents or automation act on labels |
| `evidence.team_facts` | The `weekly-report` facts file that already holds the team's PRs and tracker tickets |

A `config` key that is missing is a question for Alex, never a guess. Read the live field names and allowed values before the first write: a board drifts, and a stale column name fails the request.

## Where work lives

Use this rule to place every item before you write it anywhere: **the tracker holds what the team does (work). The forum holds what is being decided (decisions). The board holds the team's bets and the value they deliver**, which is the track record a future executive reads.

| Surface | Holds | Row or item |
|---|---|---|
| **Tracker** | Hands-on work | Epic, story, spike, request |
| **Board** | Bets and value | One row per initiative, at a stage: `1. Exploring` → `2. Committed` → `3. Delivering` → `4. Delivered`, or `5. Stopped` |
| **Forum** | Decisions | One item per topic |

**Roll-up rules:**

1. **Every epic in the team's areas rolls up to exactly one board row.** Use a plain link on the epic. One row can hold many epics. Add no new field and no process change.
2. **Run work rolls up too.** The team has one operations epic and one operations row for keep-the-lights-on work, so everything shows without one row per epic.
3. **Each fact is typed once.** Why, sponsor, impact, theme and stage live on the row. Decisions live in the forum, linked from the row. Who does the work, state, dates and progress live in the tracker.
4. **The board is complete, the roll-up is selective.** Every initiative keeps its row. The weekly roll-up leads with what mattered most, chosen from evidence.

**Stage flow:**

```
1. Exploring --(trigger hit)--> forum item
forum item decided --> propose 2. Committed     parked or deflected --> propose 5. Stopped
2. Committed --(building, piloting or rollout starts)--> propose 3. Delivering
3. Delivering --(outcome live, work finished)--> propose 4. Delivered
```

- **Triggers:** new spend, cross-team impact, a security implication, or a one-way door. Flag an Exploring row that hits one with no forum item.
- **Committed means late commitment:** the decision is made and building is about to start. Explore cheaply before it.
- Every stage move is a **Needs you** line. The forum outcome is the evidence, not the decision.

## Granularity — the rule that matters most

**One row = one initiative.** Not one artifact, not one meeting, not one ticket: a body of work with its own outcome, decision path, and "done" state. The test: *would the executive ask about this by name?*

- ADR + design doc + a POC + a comparison + a tracker feature serving one decision → **one** row.
- Six workstreams on one platform (telemetry, alerting, onboarding, cost) → **one** row.
- Merge only when two rows pursue the same outcome, or one is a part or phase of the other. Never merge distinct bets to cut the row count: each row needs one stage, one sponsor and one role. A merge is its own line: the merged row moves to `5. Stopped` with Milestone `Stopped: merged into <row>`, both rows get a comment, and the survivor's ledger `sources` take the merged row's sources. Nothing is deleted.

## Inclusion — a candidate must pass all four

1. **Delivery or influence, not attendance.** For a delivery row, the verb must be authored / executed / shipped / decided / established / migrated / secured / consolidated. For an influence row, the team advised or reviewed **with a recorded outcome**: a decided forum item, an adopted standard, or written advice the owning team acted on. Attended / joined / participated is excluded unless folded into an initiative.
2. **Initiative-scale.** Has a decision path or a milestone, not a one-off favor or a single meeting outcome.
3. **Owner-of-record.** You drove it or own the decision; a contribution qualifies only if it is itself an artifact. For an influence row, the team owns the advice, not the delivery. In Team mode, the team is the owner (see [references/team-board.md](references/team-board.md)).
4. **Org-shareable.** Passes the exclusion screen below.

## Exclusion screen — hard gates, run on EVERY candidate (and on every user-edited title)

1. **Privileged / counsel-touched.** Legally privileged, confidential, forensic assessments, legal hold, counsel communications, breach-forensics detail, security codenames. **Exclude entirely, not even a redacted or renamed row.** A partially privileged initiative may cover only its non-privileged surface; if that surface is empty, exclude the whole thing.
2. **Vendor-sensitive naming.** Neutral platform-strategy names, never vendor-replacement framing: "Access Platform Renewal", not "<vendor> Replacement". Tool names live inside the linked decision record.
3. **Scope-claiming.** No rows for unsolicited org-wide transformation plans or future territory; delivered, in-flight, or decision-ready work only.
4. **HR / personnel.** A published process artifact is includable; individual candidates, interview assessments, and personnel opinions never are.

## Field mapping

- **Title** — outcome-named, exec-legible, about 6 words at most. No component names or acronym soup.
- **Theme** — exactly one value from `config.themes`; if two fit, pick the *current* center of gravity, not where the work started.
- **Stage** — exit criteria: `1. Exploring` → `2. Committed` when the decision is made (a decided forum item, or the named owner's written yes); `2. Committed` → `3. Delivering` when building or rollout starts; `3. Delivering` → `4. Delivered` when the outcome is live, with Milestone `Delivered`, the closing date, and Impact rewritten as documented impact; any stage → `5. Stopped` with Milestone `Stopped: <why>` and the closing date. An honest step back is legitimate; only `4. Delivered` and `5. Stopped` are immutable. Blocked-ness is never a stage: a decision block is a forum item, any other block is a comment.
- **Role** — exactly one: `Builds` (the team does the hands-on work), `Influences` (another team builds; this team advises, reviews or sets the standard), `Runs` (keep-the-lights-on). A decision record alone is Influences.
- **Decisions** — link every forum item that decides or advises the row.
- **Impact** — **lead with the outcome the work unlocks, not the metric or the money.** Pattern: *outcome first, evidence metric in parens*. **Documented impact** (no prefix) traces to a decision record, costed analysis, or stated metric: no estimates, no "up to". **Target impact** (`Target:` prefix) is the forward-looking claim a row is funded for; it loses the prefix only when evidence exists. Never mix the two in one cell. **Progress number:** when the outcome is countable and a live source counts it, append `(now X <unit>; baseline Y on YYYY-MM-DD)`, same unit every week. Set the baseline once, from evidence; never estimate. Blank beats soft. **Effect-side only:** never publish current-weakness specifics (a raw count of open vulnerabilities is an admission; publish the drop since baseline) or commercial posture.
- **Key Artifact** — one canonical link: the document itself, not the folder. Flag links to personal storage: they fail for the org audience.
- **Execution Link** — the main epic or repo. Omit if none, and never create a ticket only to fill the column.
- **Milestone + Milestone date** — on an open row, the next outcome a non-technical reader can parse, with its date. When a row closes, the same pair records the close.
- **Sponsor** — the leader who owns the outcome and answers for it. Never the team lead, a delegate, or a working-level contact; only from evidence. A name mentioned in a meeting is not a sponsor. Blank beats a guess. Expected from `2. Committed` on: a blank is a maintenance finding.

## Comments — the narrative layer

Rows carry the *state*; comments carry the *story*. A comment fits a signal that is real but changes no column: progress inside a stage, the rationale for a move, or a caveat about a link. **Propose one** when the week produced a meaningful signal, or alongside a field update to say *why*: an unexplained slip reads worse than an explained one. **Don't** restate a column, log routine activity, or narrate every run. One comment per row per run is the rough ceiling.

- **The full exclusion screen applies.** Comments are org-visible.
- **Exec-legible, 1–2 sentences**, outcome-first, no session or ticket IDs.
- **Transient dependencies live in comments, not link columns.** Say what IS done first: "delivered, waiting on X" beats a bare slip.
- **Plain text only, no @-mentions.** A mention notifies someone; that is a human's call.
- **Append-only.** A correction is a new comment.
- **Read existing comments first**, and record posted ones in the ledger, so re-runs don't repost.

## Team mode and wiki boards

When `scope` is `team`, or the board is a wiki page, read [references/team-board.md](references/team-board.md) first: what changes in Team mode, and the only safe way to write a wiki-page board.

**Hard rules.** They are rules, not gates: Jev never passes them. Rule 1 holds in every mode whenever `tracker.label_contract` is set; rules 2 and 3 hold in Team mode.

1. **Never add or remove a label named in `tracker.label_contract`.** Read the contract every run. Agents or automation act on those labels, so one label change can start or stop work. A line that would touch one is dropped and reported under Also found.
2. **Never write a page in `board.read_only_pages`,** and write no page other than `board.page_id` or `board.scratch_page_id`.
3. **Tracker writes are comments and links only:** the weekly epic comment, the row link, and the parent link. No label, state, or field change, and no new item without its own Needs-you line.

## Retrieval and typed gates

Read [references/retrieval.md](references/retrieval.md) before any sweep. Always read the live board first, so curation produces UPDATEs, not duplicates. Report an unreachable store as unreachable, never as no results.

The judgments that repeat every run (does it qualify, which stage, which theme, which role, is it a duplicate) are typed `ask_jev` calls: the same evidence gets the same label next week, and the unsure calls surface as questions. Question sets, thresholds and limits: [references/jev-gates.md](references/jev-gates.md). **Jev never passes a hard gate.** The exclusion screen, `not_doing`, and the invariants are rules.

## The review gate — decisions first, approve in one line

This is the point of the skill. The board is org-visible and the user must own what's published, so **you recommend and the human decides.** Alex reads the review in the terminal between other work: numbered lines he answers by number, split by surface, items named and never bare IDs, decisions first, no wide tables.

1. **Build the candidate set internally.** Cluster signals into initiatives; apply granularity, inclusion and the exclusion screen; run the typed gates; match against live rows (NEW or UPDATE); attach provenance and a recommended value for every field. Do ALL the deciding before the review.
2. **Number every proposed change by surface:** roll-up `R#`, forum `F#`, tracker `W#`, board `B#`. One line per field change; a comment is a line; a NEW row is one line that shows the full row. Keep that surface order: the tracker comes before the board, because the board truth-checks against the state the tracker lines fix.
3. **Sort every line into exactly one group:**
   - **Needs you:** every stage or state move, each on its own line; every NEW row or item; every pick between options; every fact only Alex knows; every line where the evidence ran out or a gate was unsure.
   - **Check the words:** every line whose value is new org-visible text. Show the exact text in a `>` quote.
   - **Routine:** a field or link straight from the evidence with no new prose.
4. **Emit the review in this shape.** No markdown tables. Wrap lines at 100 characters. Count exactly: each `(<n>)` equals the IDs in that group.

   ```
   ## Review — <date> · <mode>
   **<n> need you · <n> to check the words · <n> routine.**

   ### 1. Needs you (<n>)
   **B3** Event Streaming Platform · Stage: 1. Exploring → 2. Committed
   Why: the forum decided the platform choice on 10-14.
   Answer: y / n

   ### 2. Check the words (<n>)
   **W3** Team operations epic · weekly comment
   > Done this week: ... Next: ...
   Why: no update yet this week.

   ### 3. Routine (<n>)
   - **W1** Streaming evaluation epic · row link → Event Streaming Platform.

   ### Also found
   - Screened out: <what, and the one-line reason>
   - Checked clean: <rows and items with no change>
   - Alerts with no line: <what Alex must know but cannot approve>

   ### Answer
   needs: B3 y · words: all · routine: all
   ```

   The `Why` line leads with the reason: it is what he reads. The Answer line is a ready-to-edit default.

5. **He answers in one line.** Group words take `all`, `none` or IDs; a line takes `y`, `n`, a letter, or `edit: <text>`. Apply exactly what he approved. A line he did not answer is not written; a skipped Needs-you line goes on `open_items`. Never fill a gap with a guess.
6. **Re-screen anything he edits.** An edited title or comment can quietly reintroduce a vendor name or a privileged reference. Then, and only then, write.

## Connections pass — ideas after the review

The run checks rules. This pass runs last and looks across everything gathered for relations no single row shows. It never writes, and its ideas are hypotheses for Alex only. Brief, filter, format and ledger rules: [references/connections-pass.md](references/connections-pass.md).

## Writing

Write only approved lines, through the tool named in `config`. For a Jira tracker, follow `../ticket-writer/references/jira.md`. For a wiki-page board, follow the four steps in [references/team-board.md](references/team-board.md); never rewrite the page by hand. **Verify every write by reading it back:** a write is done only once verified. Never change permissions, areas, or process rules, and never delete a row or item. If a batch dies midway, save the unwritten changes as a re-runnable script in the scratchpad, tell Alex exactly what landed and what is pending, and re-run when the connection returns.

## Idempotency & the ledger

- **Match before emit.** Compare each candidate to live rows by title similarity and Key Artifact URL; a match emits an UPDATE, never a duplicate.
- **Delivered and Stopped are immutable.** A resurrected initiative is a NEW row, with a comment on each row pointing to the other.
- **Ledger `curated.json`** (in this skill's directory, gitignored) maps each source to the row it fed, so overlapping re-runs are no-ops. Read it at the start, update it after writing:

  ```json
  {
    "config": {},
    "rows": {
      "<rowId>": {
        "initiative": "Event Streaming Platform",
        "key_artifact_url": "https://...",
        "sources": ["cc:<session-uuid>", "ticket:12345", "gh:<pr-url>"],
        "stage": "2. Committed",
        "last_curated": "YYYY-MM-DD",
        "comments": [{"date": "YYYY-MM-DD", "text": "exact posted text"}]
      }
    },
    "tracker": {
      "<itemId>": {"title": "...", "row": "<rowId>", "created_by_curator": false, "updates": []}
    },
    "ideas": {},
    "open_items": ["<row>: milestone date needs a real date from Alex"],
    "not_doing": [{"what": "<initiative>", "decided": "YYYY-MM-DD", "note": "Declined. Never re-propose."}]
  }
  ```

- **`open_items`** — gaps a run couldn't close. Read them every run and re-surface what is still open.
- **`tracker`** — stops a re-run posting a second weekly update or filing the same work twice.
- **`ideas`** — stops a dropped idea coming back.
- **`not_doing`** — evaluated-and-rejected initiatives. Check before proposing any NEW row. It stops every fresh session rediscovering the same dead idea.

## Weekly controls

Run in this order, reporting one line per check as `PASS` / `ALERT` / `UNVERIFIED` with the evidence. An unresolved ALERT goes on `open_items`.

**Forum control** (skip when `config.forum` is empty):

1. **Pick the session dynamically**, never from a hard-coded weekday: the latest scheduled date before today. A session dated today counts only when live evidence shows it happened.
2. **Every item from that session is closed out:** a non-empty outcome, and a status past scheduled. Flag every item still scheduled with a past date.
3. **Alert if next week has nothing scheduled.** Never auto-schedule or invent a date. Scheduling is Alex's.
4. **Never create a forum item on someone else's behalf.** The queue is where people submit their own topics.

**Tracker control:**

1. **Roll-up link.** Every epic carries exactly one link to a board row. Two or more: flag it, never pick one yourself.
2. **Parent link.** A child item with no parent epic gets a proposed parent, from evidence only. No clear parent: flag it, because a guessed parent rolls work into the wrong row.
3. **Weekly epic update, on every active epic.** One short comment: **Done this week** (by name), **Next**, and **Blocked or at risk** only when it is real. A week with no movement still gets a comment, because silence reads as a dead epic. At most one per epic per week.
4. **State truth-ups.** Propose a state move only on an item assigned to Alex, only when evidence contradicts the state, and only to the next state. An item assigned to someone else is theirs: report the mismatch, never propose the move.
5. **Missing items.** Hands-on work with no tracker item gets a proposed item. Never for attendance, and never only to fill a link column.

**Weekly roll-up** (when Alex wants one): a short page with an executive summary of 3 to 4 points, what shipped, and every stage move. It is a roll-up with nothing new, each item passes the exclusion screen, and the summary is a reviewed line. Stage it as a draft: publishing is Alex's click.

## Weekly maintenance mode (`--maintain`, the default)

Skip discovery of new initiatives. True up what exists, and gate every change through the review:

1. Run the weekly controls, forum first.
2. Diff stage and milestone against fresh evidence; propose moves.
3. Flag a milestone date more than 7 days past due: a stale board is evidence against you.
4. Flag a `4. Delivered` row whose Impact still carries `Target:`, and a blank Sponsor from `2. Committed` on.
5. Flag `2. Committed` rows older than 30 days with no active epic and no build evidence.
6. Flag `1. Exploring` rows not updated in about 6 weeks: propose "take it to the forum, keep exploring with a date, or stop".
7. For every linked forum item that closed since the last run, propose the stage move it supports.
8. Flag rows whose promise is contradicted by a ticket or fresher comms. Understating done work is as bad as overstating it.
9. Flag a `3. Delivering` row with empty Impact, milestone and artifact: the emptiest row is the one readers click.
10. Propose a comment for a meaningful signal with no column change, rather than forcing a field move.
11. Re-surface every `open_items` entry.
12. Last, run the Connections pass.

## Full audit mode (`--audit`, or "is the board missing or misrepresenting anything?")

Discovery plus maintenance: parallel retrieval, then the three-way cross-check (missing / misrepresented / coherence), then everything in ONE review. Lead with any coherence problem; say which rows check out clean. Then the Connections pass.

## Output — the record

After the write, emit four tables so the run is auditable:

1. **WRITTEN** — new rows and items, with their IDs or URLs.
2. **UPDATED** — each changed field or link (old → new).
3. **COMMENTED** — the exact text posted.
4. **EXCLUDED** — every rejected candidate and the gate that killed it (`privileged` / `attendance` / `sub-initiative` / `scope-claim` / `personnel` / `vendor-sensitive-unresolved`), so over-aggressive filtering is caught on review.

## Safety recap

The review is the mandatory gate. Never invent initiatives or impact figures: empty beats soft. Never write an unconfirmed line; never move a stage without an explicit yes on that line. Screen every candidate, every edited title, and every comment. Comments are plain text, no @-mentions, append-only. Check `not_doing` first. Never touch permissions. Never move state on an item assigned to someone else. Ideas never leave the run report and the ledger. Meeting notes carry one more risk: a room speaks freely about live gaps, vendors and people, so quote nothing the exclusion screen would block, and never promote uncontested discussion into a decision.
