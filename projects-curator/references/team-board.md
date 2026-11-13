# Team mode and the wiki-page board

Read this when `config.scope` is `team`, or when `config.board` is a wiki page. The hard rules
stay in `SKILL.md`, because they must load on every run.

## Team mode (`scope: team`)

The board holds the team's bets, not Alex's record. What changes:

- **Owner of record.** The team is the owner: work a teammate drove qualifies on the same terms
  as Alex's own (inclusion rule 3).
- **Evidence.** Read `evidence.team_facts` first: team PRs merged and open, tracker tickets
  resolved and created, and `bulk` flags. A ticket closed in a bulk run is not delivery evidence
  on its own; judge it as `weekly-report` step 5 says.
- **State truth-ups stay Alex's only.** A teammate's item is theirs to move: report the mismatch,
  never propose the move.
- **Sponsor and stage come from the owners.** With no forum, a stage move needs the owner's
  written yes, quoted in the Why line.

## Writing a wiki-page board

Never rewrite the page by hand:

1. Read the page as HTML, note its version number, and save the body to a file.
2. Run `python3 ~/.agents/skills/projects-curator/scripts/board_table.py apply <page.html> <changes.json> --columns "<board.columns>"`
   and show the diff. The script changes only approved cells, so text and ids people added
   elsewhere on the page survive.
3. Right before the write, read the version again. If it moved, someone edited the page: start
   again at step 1 on the fresh copy, or their edit is lost.
4. Write the output file as the page body. The body is copied by hand into the write call, so a
   dropped character outside the table corrupts the page. Keep the page short around the board
   for that reason. Then read it back as markdown and check every approved cell, plus the text
   before and after the table, against the output file. Any difference is a failed write: report
   it and restore from page history. A byte-level check needs a write path that reads the file
   itself (an API token); until one exists, this check is by reading.

The first write to a new board goes to `board.scratch_page_id`, a private copy.

Seen live on 2026-11-13: the connector's HTML read-back keeps `thead` and `tbody` and writes an
empty cell as `<p></p>`, which is the shape the script expects. The adapter has no delete on
purpose: a row leaves the board through `5. Stopped`, never by removal.
