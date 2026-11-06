# Retrieval: where candidates come from

Read this before a sweep: every `--audit`, and any run that pulls the tracker, GitHub, comms or the archeologist.

**Probe auth first.** Before any retrieval, make one live read of the board. If it fails, say so at the top of the report, so Alex can fix it while the other sweeps run. Discovering a failure after the sweep wastes the whole run.

- **archeologist** (primary). Ask it a scoped question, such as *"What initiatives and decisions has Alex driven in the last N weeks?"* Its evidence chain and referenced files are your initiative and Key Artifact candidates. Treat **LOW confidence** findings as questions to ask, never as fact.
- **Tracker.** Pull two sets on every run: items created by or assigned to the signed-in account, across all projects, and everything under the team's areas from `config.tracker`. The second catches work teammates file themselves. Scope by area, never by iteration or a saved query. Read descriptions: they carry scope the titles hide. Epics are initiative-level; stories fold up into their parent.
- **Ticket state truth-checks the row.** A milestone in days with a ticket still new is a slip; a `4. Delivered` row with an active ticket may not be delivered.
- **GitHub** (`gh`). `gh pr list --author @me --state all` and `gh search prs` across the work orgs. PRs are artifacts: fold them into their initiative.
- **Comms, read-only.** On Microsoft 365, use the connector, else the `m365` CLI. Look for the canonical shared copy of a document, decisions agreed in chat, and the real dates of working sessions. Comms are evidence, not board text: no chat or email quotes in org-visible fields, and nothing privileged at all.

**Fire retrieval in parallel**, then cross-check three ways:

- **Missing** — evidence-backed initiatives with no row (check `not_doing` first).
- **Misrepresented** — rows contradicted by fresher evidence: a milestone already delivered, a `4. Delivered` row with a live ticket, a `3. Delivering` row with empty Impact, milestone and artifact.
- **Coherence** — does the portfolio read as one story? Rows investing in a platform while an exit decision is pending; themes that bury work where the executive won't look. Coherence outranks any single-row fix.
