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
