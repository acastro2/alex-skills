# Team mode and the database board

Read this when `config.scope` is `team`, or when `config.board` is a Confluence database. The hard rules
stay in `SKILL.md`, because they must load on every run.

## Team mode (`scope: team`)

The board holds the team's bets, not Alex's record. What changes:

- **Owner of record.** The team is the owner: work a teammate drove qualifies on the same terms
  as Alex's own (inclusion rule 3).
- **Evidence.** Read `evidence.team_facts` first: team PRs merged and open, tracker tickets
  resolved and created, and `bulk` flags. A ticket closed in a bulk run is not delivery evidence
  on its own; judge it as `weekly-report` step 5 says.
- **State truth-ups cover the whole project.** Alex treats the team's areas as his project
  (2026-11-13), so a state move or field edit on a teammate's item is proposed like his own:
  one Needs-you line each, with the assignee named in the Why line.
- **Sponsor and stage come from the owners.** With no forum, a stage move needs the owner's
  written yes, quoted in the Why line.

## Writing the database board

The board is one Confluence database, one row per initiative, all stages. Which other wiki
content may be written is SKILL.md hard rule 2; page writes follow `wiki-pass.md`.

Not yet tried live on a database: row comments and restore from history. Test both on the
scratch database before the first real write; until then, a row comment goes on the anchor
epic, and a failed write is fixed by a second approved edit.

Database rows are edited by 1-based position (`entry_index`), not by a stable id. So the
database has a `Row ID` text field (`R-<n>`; a new row takes the next free integer). Every
write finds its row by Row ID in a fresh CSV read taken right before the write, then reads
back. Whether `snapshotToken` guards database writes is UNVERIFIED: the tool doc says it is not
used for csv, the format guide says to pass it. Pass it, but the Row ID match plus the
read-back is the real guard.

A row never leaves by `delete_entry`; it leaves only through `5. Stopped`. The first write
goes to `board.scratch_database_id`, a private scratch database, until Alex approves the real
one.

1. **Read the rules.** Once per run, read the space's instructions with `getConfluenceSpace`
   before authoring. Call `getContentFormatGuide` with `toolName: "updateConfluenceDatabase"`,
   then with `reference: "references/database/database-csv/references/update-format-reference.md"`.
   Read `.../values.md` before writing cell values (not yet read live: say so, and read it
   first).
2. **Read the database fresh** with `getConfluenceContent`, `content_format: csv`. Keep the
   `snapshotToken`. Find each target row by Row ID, and note its position.
3. **Build the edit envelope.** `<metadata>` with header `operation_type,target,property,value`,
   then `<data>` with header `operation_type,entry_index,<field_1>,...,<field_N>`. No prose, no
   fences. Cells: `""` leaves unchanged, `NULL` clears, a literal sets. `add_entry` appends at
   the end with all fields. `edit_entry` has exactly the header's cell count. Touch only
   approved cells.
4. **Write** with `updateConfluenceContent`: `contentId`, the `snapshotToken` from step 2,
   `body.format: "csv"`, and the envelope in `body.value`, unwrapped.
5. **Read back** with `getConfluenceContent`, `content_format: csv`. Check every approved cell,
   and that no other row changed. Any difference is a failed write: report it, and fix it as the
   note above says.
6. **Anchor link.** The database has a `jira-work-item` field for the anchor epic (the
   Execution Link column). Create it with
   `add_field,<field>,jira-work-item,"cloud_id:<cloud_id>"`. Take the cloud id from the
   connector at run time; never write it into this repo.

Before the first write, check that the space allows databases (`getConfluenceSpace`,
`enabledContentTypes.isDatabasesEnabled`). If not, the board waits for a space admin; record that in
the ledger under `config.wiki.space_notes`, not here.
