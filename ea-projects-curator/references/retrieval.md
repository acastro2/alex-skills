# Retrieval: where candidates come from

Read this before a retrieval sweep: every `--audit`, and any run that pulls ADO, GitHub, Microsoft 365 or the archeologist. SKILL.md keeps the order (auth probe, live list, parallel sweep, three-way cross-check); this file holds the commands and the source details.

**Auth preflight FIRST (2026-08-10 lesson):** before any retrieval, check the cookie cache age —
`stat -f %m ~/.cache/ea-projects-curator/cookies.json` vs `date +%s`, then **probe** with one
live GET on the EA Projects list (`$top=1`), where `scripts/sharepoint` is this
skill's own folder — `~/.claude/scripts` in Claude Code, `~/.config/opencode/scripts` in OpenCode and Pi.
The cookie lifetime is not a fixed 7h: on 2026-09-04 a 28h-old cookie read, staged a page, and
MERGEd rows without a single 401. Ask Alex to run
`python3 scripts/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/Architecture" --refresh`
only when the probe fails (401/403), and say so at the top of the report so he can do it while
retrieval (ADO/GitHub/archeologist sweeps) runs in parallel. Reactively discovering a 403 after the
sweep wastes the whole run; asking for a refresh the probe shows is unnecessary wastes his.

Always **read the live list first** (existing rows) so curation produces UPDATEs, not duplicates.

- **archeologist** (primary). Ask it a scoped question, e.g. *"What architecture initiatives, ADRs/SADs, and decisions has Alex driven in the last N weeks?"* It returns a markdown briefing with predictable headers — `### Referenced Files` (Obsidian / Developer / OneDrive-Architecture), `### Evidence Chain` (a table), and `### Verification Status` (HIGH / MEDIUM / LOW). Parse loosely by header. The Evidence Chain and Referenced Files are your initiative candidates and your Key-Artifact candidates (ADR/SAD paths, especially OneDrive/Architecture `.docx`). Treat **LOW confidence** findings as questions to ask, never as asserted fact.
- **ADO** (`ado` agent — org `CuroFinTech`; living projects are `Software Engineering`, `Information Technology`, `Change Control`, `Incident Response`, `Enterprise Portfolio`; Tiger, Risk Analytics and Marketing are closed to new work and hold legacy items only). WIQL for items created-by / assigned-to
  `alexandrecastro@attainfinance.com`: run it org-wide (`POST /_apis/wit/wiql` with no `[System.TeamProject] = @project` filter), then `workitemsbatch`,
  and pull `System.Description` — it carries scope the titles hide. The old saved query **"My Open Tickets"** (`fe9c1f44-8a0c-4f68-b0b1-bf8741eed4fd`) is scoped by `@project`, so it only sees one project; do not use it for a cross-project sweep.
  **EA team board — sweep on every run** (verified 2026-10-09): project `Information Technology`, team `Enterprise Architecture`, board `Stories` (`https://dev.azure.com/CuroFinTech/Information%20Technology/_boards/board/t/Enterprise%20Architecture/Stories`; the SOW epics sit on the sibling `Epics` board). EA's day-to-day delivery is filed under area path `Information Technology\Enterprise Architecture`, so run
  `[System.TeamProject] = 'Information Technology' AND [System.AreaPath] UNDER 'Information Technology\Enterprise Architecture'` → `workitemsbatch` (≤ 200 ids per call). It is the one pull that returns EA's whole delivery ledger — the SOW 1–7 epics plus their stories (the count moves daily: 75 items in the morning of 2026-10-09 and 97 by the evening, so never quote a fixed number) — and it catches what the created-by/assigned-to sweep cannot: work teammates file themselves, created and assigned outside Alex. The team runs fortnightly iterations (`Information Technology\Sprint\<year>\<end-date>`; `Information Technology\Sprint\2026\2026-10-20` was current on 2026-10-09), but only 1 of the 97 items sat in the current one — scope by area path, never by iteration. Run the same pull for every area in the EA areas list of the schema reference.
  **Epics/features** are
  initiative-level → candidate Execution Links; stories/tasks fold up into the parent — an EA-board story nested under a SOW epic carries it in `System.Parent`, so the area pull collapses to the epics plus the standalone items.
  **Field map, the epic-to-row Hyperlink join, and the state-to-Status truth-check live in [ado-ea-portfolio-schema.md](ado-ea-portfolio-schema.md)** — read it before mapping an EA-board epic to a portfolio row, and before proposing any field that ADO does not already carry (the portfolio-only columns must not be duplicated into ADO).
  **Ticket state truth-checks the row:** a milestone in days while the ticket sits in `New` is a
  slip; a `4. Delivered` row with an `Active` ticket may not be delivered; the same check runs on the EA-board story or SOW epic behind the row's Execution Link.
- **GitHub** (`gh`, authed as `AlexandreCastro_attain`). `gh pr list --author @me --state all` / `gh search prs` across the Attain orgs. PRs are artifacts → fold into their initiative; the repo or the ADO epic is the Execution Link.
- **Microsoft 365** — two paths, one read-only rule. In Claude Code, the `claude_ai_Microsoft_365`
  MCP connector (tools are deferred; load via ToolSearch). Everywhere else, the **`m365` CLI** —
  check it with `command -v m365 && m365 --json doctor`, then `m365 sharepoint search`,
  `m365 teams search`, `m365 teams chats`, `m365 mail search`, `m365 calendar search`. READ-ONLY on
  both: search/list/read only, never send/create/delete. Three uses:
  - `sharepoint_search` — the canonical **org-shared** copy of an ADR/SAD across ALL sites (better
    Key Artifact candidates than Internal-library or personal links; fastest answer to "has this doc
    been re-homed yet?").
  - `chat_message_search` / `teams_list_chats` — Teams evidence of initiative movement: decisions
    agreed in chat, sponsor pings, follow-ups.
  - `outlook_email_search` / `outlook_calendar_search` — sent proposals, sign-off threads, and the
    real dates of working sessions → grounded `MilestoneDate` values.
  The connector is interactively authenticated and may be absent in headless runs; try the connector,
  then the CLI, and if neither answers say so and fall back to the other three sources — never report
  an unreachable store as no results. The CLI needs a one-time `m365 login`; if `doctor` reports
  `no_token`, ask Alex to run it. Graph throttles at 50 req/min — a 429 carries `retryAfterSeconds`;
  wait it out. Comms content is evidence, not board text: no chat/email quotes in org-visible fields,
  and nothing privileged or counsel-touched at all. The archeologist searches M365 natively (SOURCE
  G), so use the direct tools for targeted lookups only.

**Fire retrieval in parallel.** For a full audit, launch in ONE message: the live-list read (inline
REST), the ADO sweep (the org-wide WIQL plus the EA area pull above, never a saved query), and an archeologist sweep of the last ~8 weeks (sorted by recent
activity, anything privileged quarantined in a flagged section). Then cross-check three ways:
- **Missing** — evidence-backed initiatives with no row (check `not_doing` first).
- **Misrepresented** — rows contradicted by fresher evidence: milestone already delivered or sent
  (email/Teams beats a stale field), a `4. Delivered` row with a live ticket or future-dated milestone,
  a `3. Delivering` row with empty Impact/milestone/artifact.
- **Coherence** — does the portfolio read as one story? Rows investing in a platform while an
  exit/replacement decision is pending; themes that bury work where the CTO won't look
  (privileged-access rows outside Security Hardening; AI rows outside AI Program, which hides
  them from the AI Program view). Coherence outranks any single-row fix.
