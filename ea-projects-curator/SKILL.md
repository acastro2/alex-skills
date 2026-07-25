---
name: ea-projects-curator
description: >
  Curate real work-activity into rows for the EA Projects SharePoint board (the one-person Enterprise
  Architecture portfolio consolidation list on attainfinance.sharepoint.com/sites/Architecture). Use
  this whenever the user wants to populate, seed, update, refresh, or "catch up" the EA Projects board
  (also spoken of as the "EA Portfolio"), turn recent work / ADRs / SADs / decisions / ADO tickets /
  GitHub PRs into portfolio rows, run the weekly board update, or asks any variant of "what should go
  on my projects board" or "help me update the portfolio". It drives archeologist + ADO + GitHub to
  find candidate initiatives, then presents every candidate AND its recommended value for every column
  as questions the user confirms or reshapes before anything is written to the org-visible list. Also
  use for the weekly maintenance pass (stale milestones, decision rot) and for proposing or posting
  narrative comments on board rows (progress notes, move rationale). This is a filter-and-transform
  layer: it never invents initiatives, never estimates dollar figures, and never writes a row or
  comment the user did not confirm.
---

# EA Projects Curator

Turn the scattered evidence of what Enterprise Architecture actually did — prior AI sessions, ADRs/SADs, ADO epics, GitHub PRs — into a small set of executive-legible rows on the EA Projects board. You are a **filter and transformer**, not a retriever and not a scribe: you receive raw signals, decide what qualifies, shape it for a non-architect CTO, and then **ask** before you write.

```
archeologist (+ ADO + GitHub)  →  curate: cluster · screen · shape  →  QUESTION GATE (confirm every row + every column + every comment)  →  write via the sharepoint agent  →  report (WRITTEN / UPDATED / COMMENTED / EXCLUDED)
```

Two invariants that override everything below:

1. **Never invent.** No initiative the evidence doesn't support; no impact claim that isn't documented. An empty cell is better than a soft one.
2. **Never write unconfirmed.** The list is readable by the entire Technology org. The question gate *is* the mandatory human review. Skipped and excluded candidates are never written; the user owns what gets published.

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
- **Exec-legible, 1–2 sentences**, outcome-first, same voice as `NextMilestone`. No acronym soup, no session/ticket IDs in prose (links belong in link columns).
- **Plain text only, no @-mentions** — a mention emails someone; that's a human's call to make, never the skill's.
- **Append-only.** Never edit or delete an existing comment (yours or anyone's); a correction is a new comment.
- **Question-gate every comment** like any other write: propose exact text, the user confirms/edits/skips. Re-screen user-edited text.
- **Idempotency:** GET the item's existing comments before proposing (the user or others may have already said it — SharePoint comments are also a two-way channel, so *read* them for signals too); record posted comments in the ledger (`comments` array per row) so re-runs don't repost.

REST shapes for reading/posting comments live in `references/write-shapes.md`.

## Retrieval — where candidates come from

Always **read the live list first** (existing rows) so curation produces UPDATEs, not duplicates.

- **archeologist** (primary). Ask it a scoped question, e.g. *"What architecture initiatives, ADRs/SADs, and decisions has Alex driven in the last N weeks?"* It returns a markdown briefing with predictable headers — `### Referenced Files` (Obsidian / Developer / OneDrive-Architecture), `### Evidence Chain` (a table), and `### Verification Status` (HIGH / MEDIUM / LOW). Parse loosely by header. The Evidence Chain and Referenced Files are your initiative candidates and your Key-Artifact candidates (ADR/SAD paths, especially OneDrive/Architecture `.docx`). Treat **LOW confidence** findings as questions to ask, never as asserted fact.
- **ADO** (`ado` agent — org `CuroFinTech`, project `Tiger`). WIQL for work items created-by / assigned-to `alexandrecastro@attainfinance.com`. **Epics/features** are initiative-level → candidate Execution Links. User stories/tasks are sub-initiative → fold up into the parent initiative.
- **GitHub** (`gh`, authed as `AlexandreCastro_attain`). `gh pr list --author @me --state all` / `gh search prs` across the Attain orgs. PRs are artifacts → fold into their initiative; the repo or the ADO epic is the Execution Link.
- **Microsoft 365** (`claude_ai_Microsoft_365` MCP connector — tools are deferred; load via ToolSearch, e.g. `select:mcp__claude_ai_Microsoft_365__sharepoint_search`). READ-ONLY here: search/list tools only, never send/create/delete. Three uses:
  - `sharepoint_search` — find the canonical **org-shared** copy of an ADR/SAD across ALL sites (better Key Artifact candidates than Internal-library or personal links; also the fastest way to answer "has this doc been re-homed yet?").
  - `chat_message_search` / `teams_list_chats` — Teams evidence of initiative movement: decisions agreed in chat, sponsor pings, working-session follow-ups. Signals for `--maintain` status/milestone diffs and for comment drafts.
  - `outlook_email_search` / `outlook_calendar_search` — sent proposals, sign-off threads, and the actual dates of working sessions/reviews → grounded `MilestoneDate` values instead of proposed guesses.
  Availability caveat: interactively-authenticated connector — may be absent in headless/scheduled runs; if ToolSearch finds no M365 tools, note it and fall back to the other three sources. Comms content is evidence, not board text: never paste chat/email quotes into org-visible fields; anything privileged/counsel-touched stays out entirely per the exclusion screen. The archeologist also searches M365 natively now (its SOURCE G), so a full archeologist run already covers this — use the direct tools for targeted lookups.

## The question gate — recommend as questions

This is the point of the skill. The board is org-visible and the user must own what's published, so **you recommend and the human decides.** Recommend *every* column with a one-line rationale, and let the user confirm or reshape each.

1. **Build the candidate set internally.** Cluster the retrieved signals into initiatives; apply granularity, inclusion, and the exclusion screen; match each against existing list rows (→ NEW or UPDATE); attach provenance (which sources), the screen result, and a **fully recommended row (all nine columns)**.

2. **Triage each candidate with `AskUserQuestion`.** Batch up to 4 candidates per call (the tool allows 1–4 questions). Put the full recommended row in the option descriptions so the user sees every column at once. Options per candidate:
   - **Add as recommended** — accept the row as proposed.
   - **Adjust fields** — user wants to reshape one or more columns (go to step 3).
   - **Skip (not now)** — don't add this run.
   - **Exclude (screen)** — screen it out; record the reason.
   For an UPDATE candidate, show current → proposed for the changed fields; options **Apply update** / **Adjust** / **Skip**.
   For a COMMENT proposal (alone or riding an update), include the exact proposed text in the description; options **Post as written** / **Edit text** / **Skip**. Re-run the exclusion screen on any user-edited text before posting.

3. **On "Adjust fields", walk the columns.** For the choice columns (`Theme`, `Status`, `Decision Needed`), ask an `AskUserQuestion` with your recommended value listed **first** and labelled "(Recommended)", plus the other real values. For free-text columns (`$ Impact`, `Key Artifact`, `Execution Link`, `Next Milestone` + date), show your recommendation as the default and let the user type a replacement or accept it. **Re-run the exclusion screen on any title the user edits** — an edit can quietly reintroduce a vendor name or a privileged reference.

4. **Confirm, then and only then write.** Nothing reaches the list until it's been explicitly added/updated through this gate.

Keep option text tight (the tool caps options at 2–4 and wants short labels); the detail lives in the description.

## Writing to the list

Hand confirmed rows to the **`sharepoint` agent** for the REST write — do not hand-roll auth. Payloads and field shapes (hyperlink, currency, date, the `ListItemEntityTypeFullName`, create vs MERGE-update) are documented in `references/write-shapes.md`; read it before writing. Ensure auth is fresh (the helper's cookies have a ~7h TTL); if a call 401/403s, tell the user to run `python3 ~/.claude/scripts/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/Architecture" --refresh` (headed passkey — a human step). **Never change list or site permissions.**

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
    }
  }
  ```

## Weekly maintenance mode (`--maintain`)

Skip discovery of new initiatives; only true up what exists. Still question-gate every proposed change, and write only what the user confirms:

1. Diff `Status` / `NextMilestone` / `MilestoneDate` against the latest archeologist / ADO / GitHub signals; propose moves.
2. Flag any row whose `MilestoneDate` is > 7 days past due — a stale board is evidence against you.
3. Flag `3. Decision-Ready` rows older than 30 days that still have a `Decision Needed` set — decision rot; surface them for the 1:1.
4. Flag `1. Proposed` rows older than ~6 weeks — the black-hole state; propose "analyze or kill" for each.
5. Flag any `6. Closed` row with a blank `Outcome` — closing requires one (Delivered/Killed/Superseded).
6. For rows with a meaningful weekly signal but no column change, propose a narrative comment (see Comments section) instead of forcing a field move. Read each row's existing comments first — both to avoid repeating and to pick up replies/questions others left on the row.

## Output — the record

After the gate and the write, emit four markdown tables so the run is auditable:

1. **WRITTEN** — new rows added: all columns + the new item Id/URL.
2. **UPDATED** — row title + each changed field (old → new).
3. **COMMENTED** — row title + the exact comment text posted.
4. **EXCLUDED** — every rejected candidate + the one-line gate that killed it (`privileged` / `attendance` / `sub-initiative` / `scope-claim` / `personnel` / `vendor-sensitive-unresolved`). This makes the screen auditable and catches over-aggressive filtering on review.

## Safety recap

Org-visible list. The question gate is the mandatory review. Never invent initiatives or impact figures — empty beats soft. Never write an unconfirmed row or comment. Run the exclusion screen on every candidate, on every title the user edits, and on every comment's text. Comments: plain text, no @-mentions, append-only. Flag personal-OneDrive artifact links instead of publishing them. Never touch list or site permissions.
