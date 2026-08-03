---
name: ea-projects-curator
description: >
  Curate, update, or audit the EA Projects SharePoint board (also called the "EA Portfolio") on
  /sites/Architecture. Use for any board request: populate or refresh rows from recent work / ADRs /
  ADO tickets / PRs, the weekly maintenance pass, a full audit ("is the board missing or
  misrepresenting anything?"), or posting row comments. Everything is user-approved via a review
  table before writing to the org-visible list.
---

# EA Projects Curator

Turn the scattered evidence of what Enterprise Architecture actually did — prior AI sessions, ADRs/SADs, ADO epics, GitHub PRs — into a small set of executive-legible rows on the EA Projects board. You are a **filter and transformer**, not a retriever and not a scribe: you receive raw signals, decide what qualifies, shape it for a non-architect CTO, and then **ask** before you write.

```
archeologist (+ ADO + GitHub)  →  curate: cluster · screen · shape  →  REVIEW TABLE (one table, every proposed change, user approves by line)  →  write  →  report (WRITTEN / UPDATED / COMMENTED / EXCLUDED)
```

Two invariants that override everything below:

1. **Never invent.** No initiative the evidence doesn't support; no impact claim that isn't documented. An empty cell is better than a soft one.
2. **Never write unconfirmed.** The list is readable by the entire Technology org. The review gate *is* the mandatory human review. Skipped and excluded candidates are never written; the user owns what gets published.
3. **`Status` is Alex's column.** He curates lifecycle position himself. Never bundle a Status move into other edits; a proposed Status change is always its own line in the review table, flagged as needing his explicit yes. Applying his dictated updates → touch only the fields he named.

## The board you write to

Live target (verify against the list if a write is rejected — schema can drift):

- Site: `https://attainfinance.sharepoint.com/sites/Architecture` (group Team site, already org-readable).
- List display name **EA Projects**, GUID `d2c0a30a-dab4-40a7-bc63-7268736473f2`, URL slug still `/Lists/EA Portfolio` (internal name `EA_x0020_PortfolioList`).
- Page: `SitePages/EA-Portfolio.aspx`. Default view **CTO view** (`2c97ee1e-b6ab-4835-bb44-2b8e6ffb8663`); reference view **Full projects** (`3589d875-06f1-4d2a-b05e-28ce16b97851`).

Columns (internal name → type → allowed values). Use internal names for any write:

| Internal | Display | Type | Values / rule |
|---|---|---|---|
| `Title` | Initiative | Text | Outcome title (see field mapping) |
| `Theme` | Theme | Choice | `Security Hardening` / `Platform Foundations` / `AI Program` / `Governance` / `Observability` / `Tech Recruiting` / `Modernization Enablement` (EA advising work another team owns — tech briefs, library recs, unblocking reviews) / `Business Initiatives` (EA supporting a business move — market expansion, M&A, vendor due-diligence; named "Initiatives" not "Priorities" so other themes don't read as non-priorities) |
| `Status` | Status | Choice | `1. Proposed` / `2. In Analysis` / `3. Decision-Ready` / `4. In Progress` / `5. Verifying` / `6. Closed` (default `1. Proposed`; numbered so alphabetical sort = lifecycle order; `3. Decision-Ready` is the commitment point — before it "should we?", after it "we're doing it") |
| `DecisionNeeded` | Decision Needed | Choice | `None` / `CTO` / `Advisory Board` / `Business Owner` / `Process Owner` (default `None`) |
| `Outcome` | Outcome | Choice | `Delivered` / `Killed` / `Superseded` — set ONLY when a row reaches `6. Closed`, blank otherwise. Shows the portfolio actually kills bad ideas. |
| `Impact` | Impact | Text (single line) | Documented impact, financial or non-financial, or blank |
| `KeyArtifact` | Key Artifact | Hyperlink | One canonical ADR/SAD URL |
| `ExecutionLink` | Execution Link | Hyperlink | ADO epic/feature or GitHub URL |
| `NextMilestone` | Next Milestone | Text | Outcome, one line |
| `MilestoneDate` | Milestone Date | Date | The date that milestone is due |

> Note: `Theme` value `Platform Foundations` replaced an earlier `Decision-Ready` theme (it collided with the Status value of the same name). If you ever see `Decision-Ready` proposed as a *theme*, that's stale — it is a Status only.

## Granularity — the rule that matters most

**One row = one initiative.** Not one artifact, not one meeting, not one ticket. An initiative is a body of work with its own outcome, its own decision path, and its own "done" state. The test: *would the CTO ask about this by name?*

- ADR + SAD + a POC + a comparison doc + an ADO feature that all serve the same decision → **one** row ("Privileged Access Renewal"), not five.
- Six Grafana workstreams (telemetry, profiling, alerting, IaC, onboarding, cost) → **one** row ("Observability Platform").
- When in doubt, merge. A 40-row list is a task tracker; a ~15-row list is a portfolio.

## Inclusion — a candidate must pass all four

1. **Delivery, not attendance.** The strongest true verb must be authored / executed / shipped / decided / established / migrated / secured / consolidated. If it's attended / reviewed / joined / participated, exclude it (or fold it into an initiative where a delivery verb applies).
2. **Initiative-scale.** Has a decision path or a milestone; not a one-off favor or a single meeting outcome.
3. **Owner-of-record.** The user drove it or owns the architecture/decision. A contribution qualifies only if it's itself an artifact (e.g. authored a section of a hardening report).
4. **Org-shareable.** Passes the exclusion screen below.

## Exclusion screen — hard gates, run on EVERY candidate (and on every user-edited title)

1. **Privileged / counsel-touched.** Anything legally privileged, marked confidential, or referencing forensic assessments, legal hold, counsel communications, breach-forensics detail, or a security codename. **Exclude entirely — not even a redacted or renamed row.** If an initiative is partially privileged, the row may cover only its non-privileged surface and link only to non-privileged artifacts; if that surface is empty, exclude the whole thing.
2. **Vendor-sensitive naming.** Where a vendor relationship is commercially or legally sensitive, titles use neutral platform-strategy naming, never vendor-replacement framing:
   - "Privileged Access Renewal" — not "<PAM vendor> Replacement".
   - "Data Warehouse Platform Strategy" — not "<warehouse vendor> Migration/Exit".
   - No named open-source replacements in titles or milestones. The specific tool names live inside the linked ADR, not on the board.
3. **Scope-claiming.** No rows for unsolicited org-wide transformation plans or future territory. Rows describe delivered, in-flight, or genuinely decision-ready work only.
4. **HR / personnel.** A published process artifact (e.g. a hiring-process improvement) is includable. Individual candidates, interview assessments, and personnel opinions never are.

## Field mapping

- **Initiative (`Title`)** — outcome-named, exec-legible, ≤ ~6 words. No component names, no acronym soup. "GitHub Access Governance", not "ADR-0004 Entra-Synced Teams".
- **Theme** — exactly one value. If two fit, pick by the *current* center of gravity, not where the work started.
- **Status** — `3. Decision-Ready` requires a costed or documented options analysis to actually exist; aspiration doesn't qualify. Work executed but not yet evidence-verified is `5. Verifying`, not `6. Closed`. Exit criteria: 1→2 when the problem justifies analysis time; 2→3 when a decision-maker could act without further digging; 3→4 when the named owner says yes; 4→5 when the change is live; 5→6 when the outcome is checked against what was promised. A `5. Verifying` → `4. In Progress` step-back is legitimate when verification finds gaps (honest reporting beats forward-only); only `6. Closed` is immutable. Closing a row REQUIRES setting `Outcome`. Blocked-ness is never a status — decision blocks live in `DecisionNeeded`; if a non-decision block (vendor, dependency) ever needs tracking, add a `Blocked` yes/no attribute per the rationale doc, not a state.
- **Decision Needed** — set `CTO` only when the decision is genuinely his to make. Inflating this column burns credibility fast; when unsure, `None`. `Business Owner` = the P&L/budget holder; `Process Owner` = the person who owns the process/workflow being changed (sometimes not the budget holder) — pick whichever actually owes the answer. **Convention: `3. Decision-Ready` + `None` = EA decides** (advice process — no external party owes anything, the proposer decides). Never add an "EA" value to this column: waiting-on-yourself reads as stalling on an org-visible board, and it would split one meaning across two encodings.
- **Impact (`Impact`, text)** — **lead with the outcome the work unlocks, not the mechanical metric or the money.** "Unblocks the upgrade to the latest .NET" beats "$699/dev license avoided"; "democratizes code with auditable role-based access" beats "485 repos internal-by-default". Pattern: *outcome first, evidence metric in parens as support* (e.g. "Real production visibility org-wide (1→23 accounts, ~5K→127K signals) at ~70% lower run-cost"). The evidence must still be documented — traceable to an ADR, costed analysis, invoice delta, or a stated metric; no estimates, no "up to", no aspirational targets dressed as results. If the outcome isn't obvious from the sources, ASK the user "what does this unlock?" rather than defaulting to the metric. Blank beats soft. **Effect-side only:** never publish current-weakness specifics ("creds unrotated 2+ yrs" is a timestamped vulnerability admission, quotable in audit or breach discovery) or commercial/negotiating posture ("ends vendor lock-in" telegraphs intent to Procurement and vendor-friendly readers). Describe what the work closes or unlocks, not the live hole or the leverage play.
- **Key Artifact (`KeyArtifact`)** — one canonical link: the ADR/SAD itself, not the folder. Screen for personal-OneDrive URLs (`-my.sharepoint.com`) and flag them for re-homing to an org-shared location before using — a personal link will 403 for the org audience.
- **Execution Link (`ExecutionLink`)** — the ADO epic/feature or GitHub location. Omit if none exists; never create a shadow ticket just to fill the column.
- **Next Milestone (`NextMilestone`) + Milestone Date (`MilestoneDate`)** — phrase the milestone as an outcome a non-architect can parse, and put the date in the date column. "Options memo to the CTO" + `2026-07-25`, not "Finalize Raft topology".

## Comments — the narrative layer

Rows carry the *state*; item comments carry the *story*. A comment is the right vehicle when a signal is real but doesn't change any column: progress inside a status, the rationale for a status/milestone move, a verification note, or a caveat about a link (e.g. "Key Artifact is a working folder — will swap to the ADR when it exists"). The row answers "where is this?"; its latest comment answers "what happened lately?".

**Propose a comment when** the week produced a meaningful signal for a row whose columns don't move (work advanced inside `4. In Progress`, evidence gathered inside `5. Verifying`), or **alongside** a field update to say *why* (especially status step-backs and milestone slips — an unexplained slip reads worse than an explained one).

**Don't** comment to restate a column, log routine activity ("worked on this"), or narrate every run — a row with ten comments is a task tracker again. Rough ceiling: one comment per row per run; skip rows with nothing worth saying.

Rules (same stakes as the row — comments are org-visible):

- **Full exclusion screen applies to comment text** — no privileged/counsel references, no sensitive vendor naming, no current-weakness specifics, no personnel opinions. A clean row with a dirty comment is a dirty row.
- **Exec-legible, 1–2 sentences**, outcome-first, same voice as `NextMilestone`. No acronym soup, no session/ticket IDs in prose.
- **Transient dependencies live in comments, not link columns.** A firewall change request, an approval ticket, a temporary blocker reference — these belong in a comment ("blocked on outbound firewall rules; change request is open: <url>"), because `KeyArtifact` is the canonical ADR/SAD and `ExecutionLink` is where the work lives; a dependency ticket is neither and will be stale in weeks. A blocker comment should say what IS done first ("runner pool is live") — "delivered, waiting on X" reads far better than a bare slip.
- **Plain text only, no @-mentions** — a mention emails someone; that's a human's call to make, never the skill's.
- **Append-only.** Never edit or delete an existing comment (yours or anyone's); a correction is a new comment.
- **Question-gate every comment** like any other write: propose exact text, the user confirms/edits/skips. Re-screen user-edited text.
- **Idempotency:** GET the item's existing comments before proposing (the user or others may have already said it — SharePoint comments are also a two-way channel, so *read* them for signals too); record posted comments in the ledger (`comments` array per row) so re-runs don't repost.

REST shapes for reading/posting comments live in `references/write-shapes.md`.

## Retrieval — where candidates come from

Always **read the live list first** (existing rows) so curation produces UPDATEs, not duplicates.

- **archeologist** (primary). Ask it a scoped question, e.g. *"What architecture initiatives, ADRs/SADs, and decisions has Alex driven in the last N weeks?"* It returns a markdown briefing with predictable headers — `### Referenced Files` (Obsidian / Developer / OneDrive-Architecture), `### Evidence Chain` (a table), and `### Verification Status` (HIGH / MEDIUM / LOW). Parse loosely by header. The Evidence Chain and Referenced Files are your initiative candidates and your Key-Artifact candidates (ADR/SAD paths, especially OneDrive/Architecture `.docx`). Treat **LOW confidence** findings as questions to ask, never as asserted fact.
- **ADO** (`ado` agent — org `CuroFinTech`, project `Tiger`). WIQL for work items created-by / assigned-to `alexandrecastro@attainfinance.com`. Fastest path: Alex's saved query **"My Open Tickets"**, GUID `fe9c1f44-8a0c-4f68-b0b1-bf8741eed4fd` (run via `_apis/wit/wiql/{guid}`, then `workitemsbatch`; also pull `System.Description` — the descriptions carry scope/non-goals the titles hide). **Epics/features** are initiative-level → candidate Execution Links. User stories/tasks are sub-initiative → fold up into the parent initiative. **Ticket state is truth-check material:** a row promising a milestone in days while its ticket sits in `New` is a slip (or the milestone text is stale); a "Closed" row whose ticket is `Active` may not be closed.
- **GitHub** (`gh`, authed as `AlexandreCastro_attain`). `gh pr list --author @me --state all` / `gh search prs` across the Attain orgs. PRs are artifacts → fold into their initiative; the repo or the ADO epic is the Execution Link.
- **Microsoft 365** (`claude_ai_Microsoft_365` MCP connector — tools are deferred; load via ToolSearch, e.g. `select:mcp__claude_ai_Microsoft_365__sharepoint_search`). READ-ONLY here: search/list tools only, never send/create/delete. Three uses:
  - `sharepoint_search` — find the canonical **org-shared** copy of an ADR/SAD across ALL sites (better Key Artifact candidates than Internal-library or personal links; also the fastest way to answer "has this doc been re-homed yet?").
  - `chat_message_search` / `teams_list_chats` — Teams evidence of initiative movement: decisions agreed in chat, sponsor pings, working-session follow-ups. Signals for `--maintain` status/milestone diffs and for comment drafts.
  - `outlook_email_search` / `outlook_calendar_search` — sent proposals, sign-off threads, and the actual dates of working sessions/reviews → grounded `MilestoneDate` values instead of proposed guesses.
  Availability caveat: interactively-authenticated connector — may be absent in headless/scheduled runs; if ToolSearch finds no M365 tools, note it and fall back to the other three sources. Graph throttles at 50 req/min per user — a 429 carries `retryAfterSeconds`; wait it out, don't hammer. Comms content is evidence, not board text: never paste chat/email quotes into org-visible fields; anything privileged/counsel-touched stays out entirely per the exclusion screen. The archeologist also searches M365 natively now (its SOURCE G), so a full archeologist run already covers this — use the direct tools for targeted lookups.

**Fire retrieval in parallel.** For a full audit ("is the board missing or misrepresenting anything?"), launch in ONE message: the live-list read (inline REST), the ADO saved-query agent, and an archeologist sweep scoped to the last ~8 weeks (ask it to sort candidates by most-recent activity and to quarantine anything privileged in a separate flagged section). Then cross-check three ways:
- **Missing** — evidence-backed initiatives with no row (check the `not_doing` register before proposing).
- **Misrepresented** — rows contradicted by fresher evidence: milestone already delivered or already sent (email/Teams beats a stale field), Closed row with a live ticket or a future-dated milestone, In-Progress row with empty Impact/milestone/artifact that no evidence corroborates.
- **Coherence** — does the portfolio read as one story? Rows investing in a platform while an exit/replacement decision is pending elsewhere; theme distribution that buries work where the CTO won't look for it (privileged-access rows filed outside Security Hardening). Coherence problems outrank any single-row fix — surface them first.

## The review gate — one table, approve by line

This is the point of the skill. The board is org-visible and the user must own what's published, so **you recommend and the human decides.** Alex's confirmed preference (2026-07-28, after rejecting an `AskUserQuestion` batch): **give him everything in a single numbered markdown table** he can scan in seconds and answer with line numbers ("1 to 13 are good, 15 skip").

1. **Build the candidate set internally.** Cluster the retrieved signals into initiatives; apply granularity, inclusion, and the exclusion screen; match each against existing list rows (→ NEW or UPDATE); attach provenance and a fully recommended value for every column. Do ALL the deciding before the table — the table is for his review, not your thinking.

2. **Emit ONE consolidated table.** Columns: `# | Row | Field | Now | → Proposed | Why | Needs you?`. One line per field change; comments get a line too (proposed text in the → column); a NEW row is one line with the full recommended row summarized in →. The `Why` cell carries the reason (lead with the why — it's what he reads). `Needs you?` marks the lines he must explicitly decide: every Status move, every date only he knows, every row where the evidence ran out. Below the table, list what you screened out and why, and which rows checked out clean — the absence of a change is also a finding.

3. **He answers by line number.** Apply exactly the approved lines. A line needing input he didn't give (e.g. "yes" to a milestone rewrite but no date) → apply what you can, keep the gap on the open-items list; never fill it with a guess.

4. **Re-screen anything he edits** — an edited title or comment can quietly reintroduce a vendor name or a privileged reference. Then, and only then, write.

`AskUserQuestion` remains a fallback for a single fork mid-run (one decision, 2–4 options); never use it to triage the candidate set.

## Writing to the list

Hand confirmed rows to the **`sharepoint` agent** for the REST write, or for a small confirmed batch, write inline with the helper (`sys.path` → `~/.claude/scripts/sharepoint`, `make_session()` — no args — + `get_request_digest(session, site)`); one script MERGE-ing all approved items beats N agent round-trips. Payloads and field shapes (hyperlink, currency, date, the `ListItemEntityTypeFullName` — read it live, don't hardcode; create vs MERGE-update) are documented in `references/write-shapes.md`; read it before writing. **Verify every write:** MERGE → 204, comment POST → 201, then GET the changed fields back. Ensure auth is fresh (the helper's cookies have a ~7h TTL); if a call 401/403s, tell the user to run `python3 ~/.claude/scripts/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/Architecture" --refresh` (headed passkey — a human step). **Never change list or site permissions.**

**If the network dies mid-batch** (TLS/connection aborts — GETs and POSTs both failing, curl showing TCP connect then HTTP 000 — usually the corporate security stack, not auth): don't lose confirmed-but-unwritten changes. Save them as an idempotent script in the scratchpad (checks existing comments before posting, safe to re-run twice), tell the user exactly which writes landed (verified) and which are pending, and re-run the script when connectivity returns. A write is only "done" once verified.

## Idempotency & the ledger

- **Match before emit.** Compare each candidate to existing rows by title similarity + Key Artifact URL. A match → emit an UPDATE of changed fields only, never a duplicate.
- **Closed is immutable.** An initiative that ends becomes `6. Closed` + an `Outcome` (Delivered/Killed/Superseded); it is never deleted and never reopened — a resurrected initiative is a NEW row referencing the old (whose Outcome becomes `Superseded`). Pre-Closed statuses may step back one stage when honest (e.g. Verifying→In Progress); a row never silently disappears.
- **Ledger `curated.json`** (kept in this skill's directory) maps each source artifact ID → the list row it fed, so overlapping re-runs are no-ops. Read it at the start, update it after writing. Shape:
  ```json
  {
    "list_guid": "d2c0a30a-dab4-40a7-bc63-7268736473f2",
    "rows": {
      "<listItemId>": {
        "initiative": "Privileged Access Renewal",
        "key_artifact_url": "https://...",
        "sources": ["cc:<session-uuid>", "ado:12345", "gh:https://github.com/<org>/<repo>/pull/42", "adr:OneDrive/Architecture/<file>.docx"],
        "status": "Decision-Ready",
        "last_curated": "YYYY-MM-DD",
        "comments": [
          {"date": "YYYY-MM-DD", "text": "exact posted text"}
        ]
      }
    },
    "open_items": ["Row 20: MilestoneDate needs a real date from Alex - ..."],
    "not_doing": [
      {"what": "ADR-0003 Data Warehouse Platform Strategy (Redshift migration)", "decided": "2026-07-28", "note": "Staying on Snowflake - Alex declined even a Closed/Killed record row. Never re-propose."}
    ]
  }
  ```
- **`open_items`** — gaps a run couldn't close (a date only Alex knows, an empty row he's handling himself). Read them at the start of every run and re-surface any still open; resolve or re-write them at the end.
- **`not_doing`** — decisions to keep something OFF the board (evaluated-and-rejected initiatives, declined candidates). Check it before proposing any NEW row; never re-propose an entry. This is what stops every fresh session from re-discovering the same dead idea.

## Weekly maintenance mode (`--maintain`)

Skip discovery of new initiatives; only true up what exists. Still gate every proposed change through the review table, and write only what the user confirms:

1. Diff `Status` / `NextMilestone` / `MilestoneDate` against the latest archeologist / ADO / GitHub signals; propose moves.
2. Flag any row whose `MilestoneDate` is > 7 days past due — a stale board is evidence against you.
3. Flag `3. Decision-Ready` rows older than 30 days that still have a `Decision Needed` set — decision rot; surface them for the 1:1.
4. Flag `1. Proposed` rows older than ~6 weeks — the black-hole state; propose "analyze or kill" for each.
5. Flag any `6. Closed` row with a blank `Outcome` — closing requires one (Delivered/Killed/Superseded).
6. Flag any row whose promise is contradicted by its linked ticket or fresher comms evidence (milestone in days, ticket still `New`; "next milestone: X review" when X was already sent for approval) — the board understating done work is as bad as overstating it.
7. Flag any `4. In Progress` row with empty Impact + milestone + artifact — the emptiest-looking row is the one a reader clicks.
8. For rows with a meaningful weekly signal but no column change, propose a narrative comment (see Comments section) instead of forcing a field move. Read each row's existing comments first — both to avoid repeating and to pick up replies/questions others left on the row.
9. Re-surface every ledger `open_items` entry still unresolved (undated milestones, empty rows Alex said he'd handle).

## Full audit mode (`--audit`, or "look at everything we're doing — is the board missing or misrepresenting anything?")

Discovery + maintenance combined: parallel retrieval (live list + ADO saved query + 8-week archeologist sweep, per the Retrieval section), then the three-way cross-check (missing / misrepresented / coherence), then everything — new rows, field fixes, comments, theme moves — in ONE review table. Lead the report with any coherence problem; it's worth more than any single row. Rows that check out clean get said so explicitly.

## Output — the record

After the gate and the write, emit four markdown tables so the run is auditable:

1. **WRITTEN** — new rows added: all columns + the new item Id/URL.
2. **UPDATED** — row title + each changed field (old → new).
3. **COMMENTED** — row title + the exact comment text posted.
4. **EXCLUDED** — every rejected candidate + the one-line gate that killed it (`privileged` / `attendance` / `sub-initiative` / `scope-claim` / `personnel` / `vendor-sensitive-unresolved`). This makes the screen auditable and catches over-aggressive filtering on review.

## Safety recap

Org-visible list. The review table is the mandatory gate. Never invent initiatives or impact figures — empty beats soft. Never write an unconfirmed row or comment; never move `Status` without an explicit yes on that specific line. Run the exclusion screen on every candidate, on every title the user edits, and on every comment's text. Comments: plain text, no @-mentions, append-only. Check `not_doing` before proposing new rows. Flag personal-OneDrive artifact links instead of publishing them. Never touch list or site permissions.
