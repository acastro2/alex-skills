# projects-curator: maintain a team's portfolio (wiki board + tracker)

Status: P0 to P2 built, 2026-11-13. Org facts (team, project key, page IDs, people) live only in
the gitignored ledger `projects-curator/curated.json` under `config`, never here.

## Why

Alex now works on a team whose tracker is the source of truth and whose roadmap page has gone
stale. projects-curator already separates board (bets), tracker (work) and forum (decisions), and
holds no org facts. It needs three changes to run a team's portfolio instead of Alex's own record.

## Decisions (Alex, 2026-11-13)

- **Board home: a wiki page, the tracker stays the tracker.** Stage, Sponsor, Impact and Role have no
  field on a tracker epic without admin custom fields. The page holds one row per bet; each epic links
  to its row.
- **No forum yet.** The forum control is skipped. A stage move rests on the owner's written yes.
- **Scope: P0 to P2.** Config and probes, a read-only maintain run, then gated tracker writes.

## Facts found live that shape the design

- The tracker is worked by agents that auto-claim tickets through a **frozen label contract** (a file
  in the team's repo). Adding or removing a contract label can make an agent start or drop work. The
  contract also says not to invent a second taxonomy.
- The existing roadmap page says it "stays vision" and that the tracker "is law". A board must not
  overwrite the vision page.
- Labels already carry a theme-like track and a system-like grouping. No components, no level above
  epic.
- Another team already shows a flow dashboard for this team. The board shows bets,
  not flow; a run must say what the dashboard already covers.

## Design

```
 evidence                         curate                     review gate          write (approved lines only)
 weekly-report collect.py  ──┐                                                    ┌─► tracker: comment, row link,
 (team PRs, tracker, bulk)   ├─► cluster · team-mode screen ─► B#/W# lines ─► y/n ─┤    parent link (ticket-writer
 tracker epics + children  ──┤   · shape · match ledger                            │    Jira adapter)
 bard notes, archeologist  ──┘                                                    └─► board page: table rows
                                                                                       (board_table.py render)
```

### Change 1: team mode

Config `scope: team`. Inclusion rule 3 (owner of record) becomes "the team owns it"; delivery verbs
and the exclusion screen are unchanged. State truth-ups stay limited to items assigned to Alex: an item
assigned to someone else is theirs to move.

### Change 2: reuse, do not copy

- Tracker reads and writes follow `ticket-writer/references/jira.md` (write path proven 2026-11-13).
- Team evidence comes from `weekly-report/scripts/collect.py` facts (`team` block): merged and open PRs,
  tracker tickets with bulk flags, gaps. One team config, read from the weekly-report config file.

### Change 3: board adapter (the only new code)

`projects-curator/scripts/board_table.py`: parse the board page's table into rows (JSON) and render
rows back into the same table, so a write changes only approved cells and a diff can be shown first.
Seam: page HTML in, rows out, and rows in, HTML out. Tests: round trip leaves an unchanged page
byte-identical; one approved cell change changes only that cell; an unknown column fails loudly.

### Hard rules added

1. **Never add or remove a label named in the tracker's label contract.** Config lists the contract
   path; the run reads it every time. A line that would touch one is dropped and reported.
2. **Never write the vision page.** Config names the board page; any other page is read-only.
3. **Tracker writes are comments and links only in P2**: weekly epic comment, row link, parent link.
   No state moves on other people's items, no label changes, no new tickets without a Needs-you line.

## Phases and acceptance

| Phase | Does | Done when |
|---|---|---|
| P0 | Ledger config; probe board page read, tracker read, label contract read; overlap check with the other team's dashboard | Every `config` key filled from evidence or Alex; probes logged in the run report |
| P1 | Team-mode change; `board_table.py` with tests; one real `--maintain` run, zero writes | Tests pass; review shows B#/W# lines on real data; Alex judges it |
| P2 | Approved writes: board rows, epic comments, links | Each write read back and verified; first write on a scratch copy of the page; ledger updated |

## Open

- The page owner must agree before the board page is created or edited. Alex asks; the skill never does.
- Whether the overnight agents still run on the contract (affects how strict rule 1 must be: it stays
  strict regardless).
- P3 (other surfaces, a generated exec view) is out of scope.

## Revision 2026-11-13: database board

- The board is one Confluence database, one row per initiative, all stages (1. Exploring to 5. Stopped).
- From 2. Committed on, a row links exactly one anchor epic in Jira. Other epics link to the anchor with `tracker.anchor_link_type`.
- One owner per field. Row: Title, Theme, Stage, Role, Sponsor, Impact, Milestone, Milestone date, Key Artifact, Decisions. Anchor epic: status, due date, child epics. The epic's theme label (a `config.themes` value) echoes Theme. A mismatch fixes the side that does not own the fact.
- Stage to anchor status: Committed = To Do; Delivering = In Progress; Delivered = Done; Stopped = Done plus a "won't do" comment. Exploring has no epic.
- Promotion to 2. Committed: pick or propose an anchor epic (Needs-you lines), set the row's Jira work item field, add the row URL as a remote link on the epic. The row is never deleted.
- New hard rule, all modes: never write board fields into a Jira description (no version check, so it races other editors).
- Rows are edited by position, so the database has a `Row ID` field (`R-<n>`). Every write matches Row ID on a fresh CSV read, then reads back. Whether `snapshotToken` guards database writes is unverified; Row ID plus read-back is the real guard.
- Never `delete_entry`; a row leaves only through 5. Stopped. The first write goes to a scratch database until Alex approves the real one.
- `board_table.py` and its tests are deleted. Which wiki content may be written is SKILL.md hard rule 2 (database board, roll-up draft, and the `wiki.pages` buckets that allow writes).

## Revision 2026-11-13: wiki pass

- Pages come from config `wiki.pages` (id, title, bucket, scope). Buckets: portfolio (curator owns; Alex lifted read-only), status, mirror (GitHub wins; never edit GitHub), check (broken-link fixes only), retire (listed once; Alex archives by hand).
- The wiki pass runs in the weekly session after the project pass and board lines, with the same review gate. Lines are `P#`; order R, F, W, B, P. Team mode answers go through the `question` tool.
- Evidence order: live Jira (`getJiraIssue`, view full, never a search), canonical GitHub doc at its default branch, then the facts file. No live evidence: leave alone, report UNVERIFIED.
- Cross-page contradiction: live evidence decides; fix every stale page and quote both lines in the Why. "Last reviewed" changes only with an approved edit on that page.
- Every page edit passes the full exclusion screen: plain text, no @-mentions, vendor-neutral names.
- Write path: no whole-body writes. Read html, keep the snapshotToken, use `edits` on the full `data-local-id`, dry run first, write with the latest token, re-read on `snapshot_stale`, read back and check only target nodes changed.
- Seen 2026-11-13: the space has no space instructions; databases are off, so the board waits for a space admin and the scratch database lives in Alex's personal space.
- Ledger: page writes go under `wiki.<pageId>.updates` (date, node, old, new), so a rerun posts nothing twice.
