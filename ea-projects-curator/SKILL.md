---
name: ea-projects-curator
description: >
  Curate Alex's EA Projects SharePoint board (EA Portfolio) and AAB surfaces on /sites/Architecture.
  Use for board population, updates and row comments; weekly maintenance; full audits; AAB Intake
  close-outs and forum checks; writing forum advice back into the RFCs and ADRs people bring
  (copying off-site pre-reads into the Architecture library); or Architecture Weekly, Architecture Review Forum and AAB meeting
  recaps. Org-visible list writes require a numbered user-review table; recap pages are staged
  drafts for Alex to publish.
---

# EA Projects Curator

Turn the scattered evidence of what Enterprise Architecture actually did — prior AI sessions, ADRs/SADs, ADO epics, GitHub PRs — into a small set of executive-legible rows on the EA Projects board. You are a **filter and transformer**, not a retriever and not a scribe: you receive raw signals, decide what qualifies, shape it for a non-architect CTO, and then **ask** before you write.

```
scribe note ─→ recap + exec summary ─→ verify vs note ─→ docs-reviewer ─→ fix ─→ RENDER ─→ STAGE ─→ hand back link
archeologist     ─┐
ADO + GitHub     ─┴─→ curate: cluster · screen · shape ─→ REVIEW TABLE ─→ write ─→ report
                       (board rows, intake, comments)     (approve by line)
```
The page body is rendered from content by `references/render_page.py`, and the **Executive Summary
band is a reviewed line** because the ELT reads it. Board/intake/comment writes wait on the numbered
table; the recap's other sections do not. Never paste the recap into the terminal.

**Every weekly run owes THREE components, and the board is the SECOND deliverable.** The first is that week's **Architecture Weekly** News page (`SitePages/Recaps/YYYY-MM-DD-AAB-Recap.aspx`; keep this filename for cadence compatibility). The page carries the **Executive Summary** band (the ELT reader's gate), the **Forum recap**, and the evidence-backed **What Enterprise Architecture shipped** panel, staged as an unpublished draft with `PromotedState=1` set via CSOM and the page title area hidden. Hand Alex the link; he publishes org-visible comms himself. The page body is rendered by [references/render_page.py](references/render_page.py) from a content JSON — never written by hand. Use one review table and stage once. A plain publish without `PromotedState` never reaches the Home News rollup, which reads exactly like the update never happened. Missed on the 2026-07-28 run; see memory `arf-notes-two-deliverables`.

**The Forum recap component is GENERATED from the scribe transcript note by default** — you read the note the `scribe` skill already wrote, you do not fetch or parse the Teams transcript yourself, and you do not wait for Alex to paste notes. See **Forum recap — generate it from the scribe transcript note** below for shared note lookup; read [references/recap.md](references/recap.md) when drafting or reviewing the recap for the exact prompt and all recap checks. Two overrides: if Alex pastes his own forum notes, render those **verbatim** instead (his text always wins over your generated recap, per the template in the SharePoint agent doc — `~/.claude/agents/sharepoint.md` for Claude Code, `~/.pi/agent/agents/sharepoint.md` for Pi); if no scribe note exists and he pasted nothing, build the delivery-only draft and say plainly that it carries no forum record.

For prose, follow [Alex's voice](../alex-voice/SKILL.md).

Two invariants that override everything below:

1. **Never invent.** No initiative the evidence doesn't support; no impact claim that isn't documented. An empty cell is better than a soft one.
2. **Never write unconfirmed.** The list is readable by the entire Technology org. The review gate *is* the mandatory human review. Skipped and excluded candidates are never written; the user owns what gets published.
3. **`Status` is Alex's column.** He curates lifecycle position himself. Never bundle a Status move into other edits; a proposed Status change is always its own line in the review table, flagged as needing his explicit yes. Applying his dictated updates → touch only the fields he named.

## The board you write to

Live target (verify against the list if a write is rejected — schema can drift):

- Site: `https://attainfinance.sharepoint.com/sites/Architecture` (group Team site, already org-readable).
- List display name **EA Projects**, GUID `d2c0a30a-dab4-40a7-bc63-7268736473f2`, URL slug still `/Lists/EA Portfolio` (internal name `EA_x0020_PortfolioList`).
- Page: `SitePages/EA-Portfolio.aspx`. Views follow one rule (set 2026-09-03, research-backed: 4-7 columns per purpose-built view, decision column early for executives): **leadership views show Sponsor + TargetDate + Impact + DecisionNeeded; the working view shows Who is Responsible + milestones + ExecutionLink; All Items shows everything.** List default view is **All Items** (unfiltered, grouped by Status, keep it default — Alex's rule; 13 columns: Title, Theme, Status, DecisionNeeded, Sponsor, Impact, TargetDate, NextMilestone, MilestoneDate, KeyArtifact, ExecutionLink, Who is Responsible, Outcome). **CTO view** (`2c97ee1e-b6ab-4835-bb44-2b8e6ffb8663`, filter `DecisionNeeded = CTO` OR `Status = 3. Decision-Ready`, sorted by MilestoneDate): Title, DecisionNeeded, Sponsor, Impact, TargetDate, NextMilestone, MilestoneDate, KeyArtifact — no Status (the filter already says why the row is there) and no doers. **AI Program** (`25d2983e-48b7-404e-913e-701266410ec3`, URL `/Lists/EA Portfolio/AI Program.aspx`, filter `Theme eq 'AI Program'`, sorted by Status then TargetDate): Title, Status, DecisionNeeded, Sponsor, Impact, TargetDate, NextMilestone, MilestoneDate, KeyArtifact — the leadership-facing AI stack-rank view; an AI initiative not tagged `Theme = AI Program` is invisible there, so check the Theme on every AI row. **Full projects** (`3589d875-06f1-4d2a-b05e-28ce16b97851`, grouped by Theme, sorted by MilestoneDate): Title, Status, Who is Responsible, NextMilestone, MilestoneDate, ExecutionLink, KeyArtifact, Outcome — the delivery view, no executive columns. All views RowLimit 100 (was 30 on CTO view and Full projects; the board hit 30 rows). Modern SharePoint orders view tabs alphabetically with no order setting (verified 2026-09-03), so tab order is AI Program > All Items > CTO view > Full projects by name only. When adding a column, add it to the views whose audience needs it, never to all of them by default.

Columns (internal name → type → allowed values). Use internal names for any write:

| Internal | Display | Type | Values / rule |
|---|---|---|---|
| `Title` | Initiative | Text | Outcome title (see field mapping) |
| `Theme` | Theme | Choice | `Security Hardening` / `Platform Foundations` / `AI Program` / `Governance` / `Observability` / `Tech Recruiting` / `Modernization Enablement` (EA advising work another team owns — tech briefs, library recs, unblocking reviews) / `Business Initiatives` (EA supporting a business move — market expansion, M&A, vendor due-diligence; named "Initiatives" not "Priorities" so other themes don't read as non-priorities) |
| `Status` | Status | Choice | `1. Proposed` / `2. In Analysis` / `3. Decision-Ready` / `4. In Progress` / `5. Verifying` / `6. Closed` (default `1. Proposed`; numbered so alphabetical sort = lifecycle order; `3. Decision-Ready` is the commitment point — before it "should we?", after it "we're doing it") |
| `DecisionNeeded` | Decision Needed | Choice | `None` / `CTO` / `Advisory Board` / `Business Owner` / `Process Owner` (default `None`) |
| `Outcome` | Outcome | Choice | `Delivered` / `Killed` / `Superseded` — set ONLY when a row reaches `6. Closed`, blank otherwise. Shows the portfolio actually kills bad ideas. |
| `Impact` | Impact | Text (single line) | Documented impact, financial or non-financial; OR a forward-looking target prefixed `Target:` while the initiative is pre-Closed; blank if neither |
| `KeyArtifact` | Key Artifact | Hyperlink | One canonical ADR/SAD URL |
| `ExecutionLink` | Execution Link | Hyperlink | ADO epic/feature or GitHub URL |
| `NextMilestone` | Next Milestone | Text | Outcome, one line |
| `MilestoneDate` | Milestone Date | Date | The date that milestone is due |
| `Who_x0020_is_x0020_Responsible` | Who is Responsible | Person (multi) | The people doing the work (EA lead plus named collaborators). Pre-existing column, present in both views; it is the *doers*, not the sponsor |
| `Sponsor` | Sponsor | Person (single) | The business or technology leader who owns the outcome and answers for it; blank if EA is the only stakeholder. Distinct from Who is Responsible (doers) |
| `TargetDate` | Target Date | Date | The finish line for the whole initiative (FY-level), distinct from the next milestone |

> `Sponsor` and `TargetDate` were added to the schema on 2026-09-03 for the FY27 stack-rank (leadership asks per initiative: goal, sponsor, impact, finish date). If a write to either is rejected, the column has not been created in the list yet — create it first, never silently drop the value.

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
- **Impact (`Impact`, text)** — **lead with the outcome the work unlocks, not the mechanical metric or the money.** "Unblocks the upgrade to the latest .NET" beats "$699/dev license avoided"; "democratizes code with auditable role-based access" beats "485 repos internal-by-default". Pattern: *outcome first, evidence metric in parens as support* (e.g. "Real production visibility org-wide (1→23 accounts, ~5K→127K signals) at ~70% lower run-cost"). Two kinds of entry share this column, and the prefix keeps them apart. **Documented impact** (no prefix): traceable to an ADR, costed analysis, invoice delta, or a stated metric; no estimates, no "up to". **Target impact** (prefix `Target:`): the forward-looking claim a pre-Closed initiative is being funded or staffed for, in the same outcome-first pattern, traceable to a BRIEF, RFC, or costed options analysis (e.g. "Target: Live-Check follow-up scope in production with measured exception yield, within 90 days of the AI Engineer's start"). A target never loses its prefix by the passage of time — only when the evidence exists, at which point the entry is rewritten as documented impact. Never mix the two in one cell, and never write a target without a `TargetDate`. If the outcome isn't obvious from the sources, ASK the user "what does this unlock?" rather than defaulting to the metric. Blank beats soft. **Effect-side only:** never publish current-weakness specifics ("creds unrotated 2+ yrs" is a timestamped vulnerability admission, quotable in audit or breach discovery) or commercial/negotiating posture ("ends vendor lock-in" telegraphs intent to Procurement and vendor-friendly readers). Describe what the work closes or unlocks, not the live hole or the leverage play.
- **Key Artifact (`KeyArtifact`)** — one canonical link: the ADR/SAD itself, not the folder. Screen for personal-OneDrive URLs (`-my.sharepoint.com`) and flag them for re-homing to an org-shared location before using — a personal link will 403 for the org audience.
- **Execution Link (`ExecutionLink`)** — the ADO epic/feature or GitHub location. Omit if none exists; never create a shadow ticket just to fill the column.
- **Next Milestone (`NextMilestone`) + Milestone Date (`MilestoneDate`)** — phrase the milestone as an outcome a non-architect can parse, and put the date in the date column. "Options memo to the CTO" + `2026-07-25`, not "Finalize Raft topology".
- **Who is Responsible (`Who_x0020_is_x0020_Responsible`, multi-person)** — everyone doing the work, EA lead first, then named collaborators from other teams. Set from evidence of actual work (ADR authorship, PRs, a runbook, a named workstream), not attendance. Keep it to people who would be asked "how is it going?", not everyone consulted.
- **Sponsor (`Sponsor`, person)** — the leader who owns the outcome and would be asked about it by name: the P&L/budget holder for business-facing work, the technology VP for platform work. Never the EA lead (that is the whole board), never a delegate or working-level contact. Only set from evidence — a BRIEF sponsor line, an AAB recap, a written commitment; a name mentioned in a meeting is not a sponsor. Leave blank rather than guess.
- **Target Date (`TargetDate`)** — the initiative's finish line, i.e. when the `Target:` impact is expected to be documented. FY-level horizon, set from a BRIEF/RFC timeline or a stated leadership deadline; move it only with a comment saying why. Distinct from `MilestoneDate`, which is the next step. A `Target:` impact without a `TargetDate` is incomplete — propose both together.

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

**Auth preflight FIRST (2026-08-10 lesson):** before any retrieval, check the cookie cache age —
`stat -f %m ~/.claude/scripts/sharepoint/.cookies.json` vs `date +%s`, then **probe** with one
live GET on the EA Projects list (`$top=1`). The cookie lifetime is not a fixed 7h: on 2026-09-04
a 28h-old cookie read, staged a page, and MERGEd rows without a single 401. Ask Alex to run
`python3 ~/.claude/scripts/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/Architecture" --refresh`
only when the probe fails (401/403), and say so at the top of the report so he can do it while
retrieval (ADO/GitHub/archeologist sweeps) runs in parallel. Reactively discovering a 403 after the
sweep wastes the whole run; asking for a refresh the probe shows is unnecessary wastes his.

Always **read the live list first** (existing rows) so curation produces UPDATEs, not duplicates.

- **archeologist** (primary). Ask it a scoped question, e.g. *"What architecture initiatives, ADRs/SADs, and decisions has Alex driven in the last N weeks?"* It returns a markdown briefing with predictable headers — `### Referenced Files` (Obsidian / Developer / OneDrive-Architecture), `### Evidence Chain` (a table), and `### Verification Status` (HIGH / MEDIUM / LOW). Parse loosely by header. The Evidence Chain and Referenced Files are your initiative candidates and your Key-Artifact candidates (ADR/SAD paths, especially OneDrive/Architecture `.docx`). Treat **LOW confidence** findings as questions to ask, never as asserted fact.
- **ADO** (`ado` agent — org `CuroFinTech`, project `Tiger`). WIQL for work items created-by / assigned-to `alexandrecastro@attainfinance.com`. Fastest path: Alex's saved query **"My Open Tickets"**, GUID `fe9c1f44-8a0c-4f68-b0b1-bf8741eed4fd` (run via `_apis/wit/wiql/{guid}`, then `workitemsbatch`; also pull `System.Description` — the descriptions carry scope/non-goals the titles hide). **Epics/features** are initiative-level → candidate Execution Links. User stories/tasks are sub-initiative → fold up into the parent initiative. **Ticket state is truth-check material:** a row promising a milestone in days while its ticket sits in `New` is a slip (or the milestone text is stale); a "Closed" row whose ticket is `Active` may not be closed.
- **GitHub** (`gh`, authed as `AlexandreCastro_attain`). `gh pr list --author @me --state all` / `gh search prs` across the Attain orgs. PRs are artifacts → fold into their initiative; the repo or the ADO epic is the Execution Link.
- **Microsoft 365** — two paths, one read-only rule. In Claude Code, the `claude_ai_Microsoft_365` MCP connector (tools are deferred; load via ToolSearch, e.g. `select:mcp__claude_ai_Microsoft_365__sharepoint_search`). Everywhere else, the **`m365` CLI** — check it first with `command -v m365 && m365 --json doctor`, then `m365 sharepoint search`, `m365 teams search`, `m365 teams chats`, `m365 mail search`, `m365 calendar search`. READ-ONLY on both: search/list/read only, never send/create/delete. Three uses:
  - `sharepoint_search` — find the canonical **org-shared** copy of an ADR/SAD across ALL sites (better Key Artifact candidates than Internal-library or personal links; also the fastest way to answer "has this doc been re-homed yet?").
  - `chat_message_search` / `teams_list_chats` — Teams evidence of initiative movement: decisions agreed in chat, sponsor pings, working-session follow-ups. Signals for `--maintain` status/milestone diffs and for comment drafts.
  - `outlook_email_search` / `outlook_calendar_search` — sent proposals, sign-off threads, and the actual dates of working sessions/reviews → grounded `MilestoneDate` values instead of proposed guesses.
  Availability caveat: the connector is interactively authenticated and may be absent in headless or scheduled runs. Try the connector, then the `m365` CLI; if neither answers, say so and fall back to the other three sources — never report an unreachable store as no results. The CLI needs a one-time `m365 login`; if `doctor` reports `no_token`, ask Alex to run it. Graph throttles at 50 req/min per user — a 429 carries `retryAfterSeconds`; wait it out, don't hammer. Comms content is evidence, not board text: never paste chat/email quotes into org-visible fields; anything privileged/counsel-touched stays out entirely per the exclusion screen. The archeologist also searches M365 natively now (its SOURCE G), so a full archeologist run already covers this — use the direct tools for targeted lookups.

**Fire retrieval in parallel.** For a full audit ("is the board missing or misrepresenting anything?"), launch in ONE message: the live-list read (inline REST), the ADO saved-query agent, and an archeologist sweep scoped to the last ~8 weeks (ask it to sort candidates by most-recent activity and to quarantine anything privileged in a separate flagged section). Then cross-check three ways:
- **Missing** — evidence-backed initiatives with no row (check the `not_doing` register before proposing).
- **Misrepresented** — rows contradicted by fresher evidence: milestone already delivered or already sent (email/Teams beats a stale field), Closed row with a live ticket or a future-dated milestone, In-Progress row with empty Impact/milestone/artifact that no evidence corroborates.
- **Coherence** — does the portfolio read as one story? Rows investing in a platform while an exit/replacement decision is pending elsewhere; theme distribution that buries work where the CTO won't look for it (privileged-access rows filed outside Security Hardening). Coherence problems outrank any single-row fix — surface them first.

## The review gate — one table, approve by line

This is the point of the skill. The board is org-visible and the user must own what's published, so **you recommend and the human decides.** Alex's confirmed preference (2026-07-28, after rejecting an `AskUserQuestion` batch): **numbered markdown tables** he can scan in seconds and answer with line numbers ("1 to 13 are good, 15 skip"). Refined 2026-09-04 after he rejected a 32-line merged table ("makes it confusing for me... I need it break down by recap, aab intake updates and ea portfolio updates"): **one table per surface, never one merged list.**

1. **Build the candidate set internally.** Cluster the retrieved signals into initiatives; apply granularity, inclusion, and the exclusion screen; match each against existing list rows (→ NEW or UPDATE); attach provenance and a fully recommended value for every column. Do ALL the deciding before the table — the table is for his review, not your thinking.

2. **Emit FOUR sections, one table each, in this order.** (a) **Recap**: the staged page link, what you fixed before staging, and the one action (his Publish click). No lines to approve. (b) **AAB Intake updates**: lines numbered `A1, A2, ...`. (c) **Brought documents**: lines numbered `D1, D2, ...` (copies and document edits, with the drafted author messages below the table; see [references/brought-docs.md](references/brought-docs.md)). (d) **EA Projects updates**: lines numbered `E1, E2, ...`. Same columns in (b), (c) and (d): `# | Row | Field | Now | → Proposed | Why | Needs you?`. He answers per table ("A: all. D: 1–4. E: 1–3, 5"). One line per field change; comments get a line too (proposed text in the → column); a NEW row is one line with the full recommended row summarized in →. The `Why` cell carries the reason (lead with the why — it's what he reads). `Needs you?` marks the lines he must explicitly decide: every Status move, every date only he knows, every row where the evidence ran out. Below the table, list what you screened out and why, and which rows checked out clean — the absence of a change is also a finding.

3. **He answers by line number.** Apply exactly the approved lines. A line needing input he didn't give (e.g. "yes" to a milestone rewrite but no date) → apply what you can, keep the gap on the open-items list; never fill it with a guess.

4. **Re-screen anything he edits** — an edited title or comment can quietly reintroduce a vendor name or a privileged reference. Then, and only then, write.

`AskUserQuestion` remains a fallback for a single fork mid-run (one decision, 2–4 options); never use it to triage the candidate set.

## Writing to the list

Hand confirmed rows to the **`sharepoint` agent** for the REST write, or for a small confirmed batch, write inline with the helper (`sys.path` → `~/.claude/scripts/sharepoint`, module is **`sharepoint_api`** — there is no `sharepoint_helper` — `make_session()` no args + `get_request_digest(session, site)`; the CLI verbs like `sharepoint_api.py create` need `SHAREPOINT_SITE_URL` exported or they exit with "Set SHAREPOINT_SITE_URL"); one script MERGE-ing all approved items beats N agent round-trips. Payloads and field shapes (hyperlink, currency, date, the `ListItemEntityTypeFullName` — read it live, don't hardcode; create vs MERGE-update) are documented in `references/write-shapes.md`; read it before writing. **Verify every write:** MERGE → 204, comment POST → 201, then GET the changed fields back. Ensure auth is fresh (the helper's cookies have a ~7h TTL); if a call 401/403s, tell the user to run `python3 ~/.claude/scripts/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/Architecture" --refresh` (headed passkey — a human step). **Never change list or site permissions.**

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
- **`docs`** — one entry per intake item whose pre-read was placed or edited (source, Architecture copy, edits with version). Stops a re-run from copying twice or adding the same advice row twice. Shape in [references/brought-docs.md](references/brought-docs.md).
- **`not_doing`** — decisions to keep something OFF the board (evaluated-and-rejected initiatives, declined candidates). Check it before proposing any NEW row; never re-propose an entry. This is what stops every fresh session from re-discovering the same dead idea.

## Weekly AAB control — the second operating surface

Alex curates a second list alongside the EA Projects board: **AAB Intake** (the Architecture Advisory Board forum queue), plus the weekly **AAB Recap** News post (the "newsletter" — you generate its forum recap from the scribe transcript note, and publishing the page stays Alex's action). This control runs **first**, before any EA Projects check, in both `--maintain` and `--audit`.

- **AAB Intake list:** `https://attainfinance.sharepoint.com/sites/Architecture/Lists/AAB%20Intake/AllItems.aspx`, GUID `80c68e54-eadf-4cf3-946a-3c0e432056a5`, entity `SP.Data.AAB_x0020_IntakeListItem`. Fields: `Title`, `Status` (`New` / `Triaged` / `Scheduled` / `Decided` / `Parked` / `Deflected`), `Scheduledfor` (DateTime stored as **DateOnly**), `Outcomenotes` (text), `Modified`.
- **Recaps folder:** `/sites/Architecture/SitePages/Recaps` — page name pattern `YYYY-MM-DD-AAB-Recap.aspx`. Browse view: `https://attainfinance.sharepoint.com/sites/Architecture/SitePages/Forms/ByAuthor.aspx?id=%2Fsites%2FArchitecture%2FSitePages%2FRecaps&viewid=a74d565d%2Da0da%2D444e%2Daae0%2D092bef143ca8`.
- **Timezone/week:** read SharePoint `RegionalSettings/TimeZone` live; verified 2026-08-10 as Central Time (America/Chicago). A calendar week is Monday–Sunday. If the site timezone no longer maps to America/Chicago, report UNVERIFIED instead of guessing date boundaries.

Use [references/write-shapes.md](references/write-shapes.md) for the control's REST read/write shapes.
Run these checks before EA Projects checks; [Weekly newsletter](#weekly-newsletter--architecture-weekly)
owns page assembly, not session selection or intake control.

**1. Pick the session to verify — dynamically, never a hard-coded weekday.** Use site-local dates. Normally select the latest `Scheduledfor` before today: prefer the current week, otherwise the previous week's latest. Treat a session scheduled for **today** as due only when live evidence shows it has happened (the exact-date recap exists, or an intake item already carries a same-day forum outcome); otherwise label today upcoming/UNVERIFIED and verify the previous session so a morning run does not raise three false alerts. If neither current nor previous week has a date, derive the expected forum date from the cadence of the most recent 3–4 published recap filenames and flag that the intake list has no anchor — don't silently skip the check.

**2. Verify the recap was actually published, not staged.** A filename existing under `Recaps/` is not enough — check the page is real News: `PromotedState=2`, `OData__ModerationStatus=0`, and `FirstPublishedDate` present. `PromotedState=1` is still a draft (see [Weekly newsletter](#weekly-newsletter--architecture-weekly)) — report it as unpublished, don't treat it as done.

**3. Verify every intake item for that session was closed out.** For each item whose site-local `Scheduledfor` date equals the selected session date, require a forum outcome: non-empty `Outcomenotes`, a status other than `New`/`Triaged`, and no past-dated `Scheduled` state. The site-local `Modified` date must be on or after the session date as a sanity check, but it does not prove the exact meeting time. Normal outcome is `Decided`; `Parked`/`Deflected` are valid with explanatory notes. A future re-`Scheduled` item is valid only when item version history or the ledger proves it moved from the selected session date and the notes explain why; otherwise report UNVERIFIED. **Separately, always query and flag every item globally where `Status=Scheduled` and `Scheduledfor` is in the past** — SharePoint's own agenda and decision-log views both hide this state (agenda filters `>= today`, log filters `Status=Decided`), so it's invisible unless this check catches it.

**3a. Write the forum back into the documents people brought.** For every closed-out item of that
session, sort its `Pre-read links`: edit a document already in Architecture Shared Documents, copy an
off-site one into the right type folder first (behind a content screen and a sharing-scope gate), and
alert on the rest. RFCs get `AAB Session`, `Status` Draft → Open for Advice, and advice rows from the
scribe note; a Proposed ADR gets advice rows; nothing else is edited. Read
[references/brought-docs.md](references/brought-docs.md) for the gates, folder rules, table map,
upload shape, and author message. Every copy and edit is a `D#` review line.

**4. Alert if next calendar week has nothing scheduled.** Check for at least one `AAB Intake` item with `Status=Scheduled` and `Scheduledfor` in `[next Monday, following Monday)`. None found → prominent alert to Alex to schedule the forum or confirm there isn't one. Never auto-schedule or invent a date.

> **Scheduling is Alex's, by default.** (2026-09-04: "don't touch the other stuff I will schedule
> it manually.") An empty next week and any unscheduled `New` items are an **alert** listing the
> candidates. Propose `Scheduledfor` + `Status=Scheduled` on an existing item only when Alex has
> already named the date himself (in the forum, in chat, or in this run), and even then as its own
> `A#` line marked **Needs you**. Never infer a date from cadence.
>
> **Never create an AAB Intake item. Ever.** (Corrected 2026-08-28, after a run proposed one as a
> review-table line and Alex rejected it outright.) The intake list is **the queue people submit
> their own topics to** — it is their to-do surface, not a scheduling table for the curator to
> populate. An empty next week is an **alert only**; it never becomes a proposed row, not even a
> gated one. The curator's writes to this list are limited to closing out items that already exist:
> `Status`, `Outcomenotes`, and `Scheduledfor` on an item somebody else raised.

**Report before EA Projects findings under this exact heading:**

### AAB WEEKLY CONTROL

| Check | Result | Evidence |
|---|---|---|
| Recap published | PASS / ALERT / UNVERIFIED | date, page Id/URL, PromotedState |
| Intake close-out | PASS / ALERT / UNVERIFIED | item Ids/titles still open, with Status/Scheduledfor |
| Brought documents | PASS / ALERT / UNVERIFIED | per item: in place / copied / alert (off-site, screened out, scope unverified, unresolvable) |
| Next-week schedule | PASS / ALERT / UNVERIFIED | next-week range and items found, or none |

Any unresolved ALERT goes on `curated.json` `open_items` (cleared only after live re-verification) — same idempotency discipline as EA Projects. **Intake field changes are writes to an org-visible list**: propose them through the same numbered review table as board changes, one line per field (`Status` / `Outcomenotes` / `Scheduledfor`), and apply only what Alex approves by line. Never invent `Outcomenotes` text or a `Scheduledfor` date, and never publish the recap yourself — flag it as his action.

## Forum recap — generate it from the scribe transcript note

The forum's own record is the note the `scribe` skill writes from the Teams meeting transcript. Read
that note and write the recap from it; do not wait for pasted notes, and do not fetch or parse the
Teams transcript yourself — that job belongs to `scribe` now.

### Step 1 — read the scribe transcript note

Path pattern: `<vault>/Scribe/Meetings/Transcripts/<YYYY-MM-DD HHMM> <Meeting title>.md`, where the
date/time is the meeting start in America/Chicago and the title is the calendar subject — e.g.
`2026-09-02 1500 Architecture Advisory Board.md`.

Find the right occurrence by the forum's actual date: it runs **Wednesdays, 3:00–4:00pm Central**
(verified cadence across 8 sessions), subject **`Architecture Advisory Board`** — not "Architecture
Review Forum," that public name never appears on the note. Match on the Wednesday date of the forum
you're recapping.

**Read the `## Transcript` section in full before drafting** — the recap has to be faithful, so do
not summarize from grep hits. The frontmatter `speakers` list is your attendance line; it is who
actually spoke, which is not the same as who was invited.

**If the note does not exist, stop the recap** and tell Alex to run `/scribe teams` for that date.
Do not fetch the transcript yourself as a fallback — a note you have not looked for is not an
absence.

### Recap drafting and review

For recap drafting, verification, or weekly page assembly (including delivery-only drafts and
Alex's pasted-note override), read [references/recap.md](references/recap.md). It holds proper-noun
handling, Alex's exact prompt, recap gates, note verification, and the mandatory `docs-reviewer`
pass on the assembled page. Board-only tasks do not need this reference.

A genuinely missing note stops the **forum recap component**, not the whole weekly page.
Ask Alex to run `/scribe teams` for that date. If he supplied no notes either, follow the
newsletter gates below for a delivery-only draft and state that it has no forum record.

## Weekly newsletter — Architecture Weekly

Every weekly page carries THREE components under the title **Architecture Weekly — Month D, YYYY**.
Component 1 is the **Executive Summary** band at the top (see the gate below). Component 2 is the
**Forum recap** (generated from the scribe note using
[references/recap.md](references/recap.md), or Alex's pasted notes rendered verbatim when he supplies
them). Component 3 is the generated **What Enterprise Architecture shipped** panel at the bottom.
They answer different questions: the summary is for the executive leadership team who read the page
but were not in the room; the forum record says what the group decided; the delivery panel says what
EA shipped. Drop any delivery item that restates the forum recap.

### The page body is rendered, never written

**Run [references/render_page.py](references/render_page.py); do not write page HTML.** The run's job
is content, the script's job is markup:

```
recap-content.json  →  render_page.py  →  canvas.json  →  stage_news_recap.py --canvas
```

The script owns every tag, style and colour, and it refuses to emit `class=`, `<style>`, custom
elements, `font-family` or anything else the SharePoint rich text editor would fight. Read its
docstring for the content schema. Filling in HTML by hand is what produced the drift between the
09-09 and 09-16 pages; two files cannot disagree if only one of them holds markup.

[references/example-content.json](references/example-content.json) is a complete, valid input: copy
it to start a week, and render it after any change to the script to prove the script still works.

**It refuses on content shape too, not just markup.** Missing `exec_summary`, a band outside 3 to 4
points, a blank `footer`, an unknown `outcome.tag`, a decision with no `rationale`, a shipped item
with no evidence: each is a named error naming the exact key. Fix the content; do not reach past the
script. Its forbidden-construct scan reads the MARKUP only, so ordinary prose is safe (a sentence may
say `position:` or `class=` without failing the render). What keeps content out of the markup is
escaping, not the word list.

`python3 references/render_page.py --text canvas.json` prints the rendered page as plain text. That
is the input to `voice_check.py`; see [references/recap.md](references/recap.md) for the two commands.

**The design is fixed (approved by Alex 2026-09-18, from the Claude Design mock).** Navy header band,
teal rule, Executive Summary band, Forum recap section, navy shipped panel. Section order:
Executive Summary → Forum recap (Objective, Outcome, TL;DR, Decisions made, Action items, Topics
discussed, Open questions and risks, Artifacts referenced, Spoke in this session) → What Enterprise
Architecture shipped.

**Colour is the mock's palette, deliberately not the Attain brand palette** — Alex's call
2026-09-18. `#12395C` navy band, `#0E8FA8` teal rule, `#1A4E7A` shipped band, `#E6F0F7` light
surfaces, `#23303B` body, `#55636E` muted, `#0E6E96` links, `#D4DDE4` borders. Every colour the page
emits is a named constant in the `render_page.py` palette block, with its role beside it; a bare hex
in a builder is drift. Do not substitute Venice Blue or any other brand token.

**Fonts come from the site theme.** No `font-family` is emitted anywhere. The Architecture site
renders Segoe UI and the page inherits it, so the page stays consistent with every other page on the
site. Hierarchy comes from size, weight, colour and letter-spacing.

### The SharePoint editor does not show this page faithfully (measured 2026-09-18)

Alex edited a staged page, saved it, and reported it as broken. It was not. Reading the stored canvas
back after his save: **144 of 147 inline `style` attributes survived, including the navy band's
`background-color`.** The read view renders fully styled. What he saw was the **rich text editor's own
view**, which drops backgrounds, borders and heading sizes from view while leaving them in the stored
page.

So:

- **Never judge this page in edit mode.** Use Preview, or the read view. Tell Alex this whenever he
  edits a page, because the editor will look broken and he will say so.
- **The editor's only real mutation is the Action items table.** On the first save the RTE wraps it in
  `<figure class="table canvasRteResponsiveTable" title="Table" style="width:100%;">`, adds a
  `<colgroup>` of three `33.33%` columns, and moves the table's `border-collapse` and `margin-top` out
  of the markup. SharePoint's own `canvasRteResponsiveTable` CSS then supplies the collapsed borders,
  and the three columns become equal width, so Action rows wrap to two lines more often. That is
  accepted, not fought: the table still reads correctly and the `td` styles survive.
- **A `class=` attribute in a read-back canvas is SharePoint's, not drift.** `render_page.py
  --check-only` is for the RENDERED canvas. Do not "fix" a saved page's `<figure>` wrapper, and do not
  treat it as a validation failure.
- The page's own inline styles are durable across edits. Rule 2 ("safe for Alex to edit by hand") holds,
  with the table-wrapper exception noted above.

### Visual verification — the run can look at the page itself

A read-back proves storage, not appearance. Use the **`browser-control` skill** to actually see the
rendered page: it drives Alex's own Chromium browser with his profile and cookies, so SharePoint
renders authenticated. The OpenCode `tools.browser.*` catalog needs the desktop app plus an
experimental setting and is usually unavailable; `browser-control` is the path that works.

Two gotchas that cost real time on 2026-09-18, so nobody repeats them:

- **`fullPage: true` does not capture the whole page.** The scroll container is inner, so a full-page
  shot comes back the same size as a viewport shot. Scroll the container instead:
  `await page.getByRole("heading", { name: "Topics discussed" }).scrollIntoViewIfNeeded()`, then take
  viewport shots.
- **`page.goto` churns through SharePoint's auth redirect query strings** (`?sw=bypass&bypassReason=…`)
  before settling on the real URL. Wait, then read `page.url()`; a noisy redirect chain is normal.

**When to run it:** mandatory whenever the renderer or the page layout changed, and once before Alex's
first publish of a new format. A content-only week does not need it. Always hand Alex the link anyway —
his eyes are the final check, and he catches things the shot does not.

### The page title area is hidden

The navy band carries the page title, so the SharePoint title must not repeat above it. **Verified
2026-09-18 twice:** `2026-08-12-AAB-Recap.aspx` stores `LayoutWebpartsContent = [{"controlType":0}]`
and shows no title region, and the 09-16 page staged with the same value was rendered in a browser and
shows the navy band as the first thing on the page. Pages left at the default (`null`) render the title
twice. `stage_news_recap.py` sets the field by default and exits non-zero if it did not stick. If a
staged draft ever does show a duplicated title, report it; the fallback is to drop the words
"Architecture Weekly" from the band, never to accept the duplicate.

**This skill is shared between tools; the scripts it calls are not.** `stage_news_recap.py` exists
once per tool (`~/.claude/scripts/sharepoint/` and `~/.config/opencode/scripts/sharepoint/`), and the
two copies drifted: the title region was added to one only, so a Pi or OpenCode run staged a page with
a duplicated title and said nothing. Both carry `--hide-title` and its verification as of 2026-09-19.
Before you rely on any behaviour this file claims about a script, check the copy your tool actually
runs. `auth.py` and `sharepoint_api.py` still differ between the two trees, each holding something the
other lacks; that is open, and it belongs to Alex.

**Sources — reuse the run's retrieval sweep, never double-fetch:** the curation run's own WRITTEN /
UPDATED / COMMENTED changes (a row moved to Decision-Ready this week IS news), direct GitHub
retrieval (`gh search prs --author "@me" --updated ">=$SINCE"` plus commit lookup when needed),
ADO epic/feature movement, and verified artifacts found by the archeologist. The archeologist does
not provide a complete GitHub activity feed; query GitHub directly. Use the same auth preflight as
everything else.

**Shape:** the shipped panel is the navy `#1A4E7A` band carrying the light-blue `#E6F0F7` surface, as
the renderer builds it. Add 3–6 items; a thin week gets 2 or none. Each item contains:
- One outcome-first sentence, ≤ ~20 words and exec-legible in the same voice as `NextMilestone`.
  It renders bold in `#12395C`. No session IDs, ticket IDs, or technical provenance in the sentence.
- An `Evidence:` line with one or two descriptive, underlined links in `#0E6E96`. Link directly to
  the primary org-readable record: merged PR, closed ADO item, current portfolio row, the RFC or ADR
  this work resolves into, or equivalent artifact. Labels describe the destination
  (`Runtime migration`, `Portfolio outcome`), never raw URLs, `click here`, or naked IDs. The forum
  recap's **Artifacts referenced** section carries the same linking rule — see
  [references/recap.md](references/recap.md).

### Executive Summary — the ELT reader's gate (new 2026-09-18)

**Why it exists:** the executive leadership team reads this page. They were not in the room and they
do not know the project vocabulary, so the band answers "what did this mean, and does anyone need me?"
in the first ten seconds.

Generated by the run, and it is the **highest-scrutiny line in the whole review table**:

- **`headline`** — one sentence, plain words. It says what was decided and what it changes, in the
  same voice as a `NextMilestone`. No acronym, no product codename, no vendor name that a non-engineer
  would not know. If a term is unavoidable, gloss it in the sentence.
- **`points`** — 3 to 4, each a bold two-or-three-word lead plus one or two plain sentences.
  The set must cover **both halves of the week: what the forum decided, and what EA shipped.** Order
  them decisions, then shipped, then still open, with the footer's ask last. Do not put the shipped
  point after "Still open": the band should end on delivery, not on two asks in a row. *Why it matters*
  beats *what was configured*. Do not restate the TL;DR.
- **Composition rule: the summary is a roll-up, nothing new.** Every sentence must trace to a decision,
  an action, an open item, or a shipped item that is already on the page. Alex's own framing
  (2026-09-18): *"the summary should be a combination of our decisions plus what we done, nothing really
  new or novelty."* A stated **consequence** of a documented decision is fine ("rotating a credential no
  longer needs a code change" comes from the "no code change and no key manifest" decision). A new
  fact, a new judgement, or a new recommendation is not. If the summary seems to need a fact the recap
  does not carry, the recap is missing it, not the summary.
- **Compress the shipped half to one line; never list the shipped items.** The navy panel at the bottom
  of the page already lists every item with its evidence links, so a full list in the band makes the
  reader read the same nouns twice in one scroll. Name the headline delivery and the theme of the rest
  (`The new US brand's non-prod network went live, and the Claude and Snowflake tooling picked up three
  more deliveries.`). Approved 2026-09-19, over four separate items.
- **`footer`** — the one line that says whether leadership must act: `No decision is waiting on
  leadership this week.` or the named decision and the named person holding it. Never leave it blank
  and never soften a real pending decision into silence. `Still open` in the points covers EA-internal
  loose ends; the footer covers what is waiting on leadership. They are different questions, keep both.
- Put it through the review table as its own numbered line (`Row` = `Recap page`, `Field` =
  `executive summary`). Never stage a page with an unreviewed summary.

**Gates (all mandatory):**
- **Scope is EA's own delivery, and the heading says so.** The panel is titled **What Enterprise
  Architecture shipped**, never "What Architecture shipped" (corrected 2026-08-28). Bare
  "Architecture" reads as every architect in the company, and the other architects ship work that is
  not in this panel. Only include items EA owns or drove: Alex-authored PRs, EA-owned ADO
  epics/features, EA board rows that moved, EA-authored artifacts. If another architect or team owns
  the delivery, it does not go in, however good it is. Claiming someone else's output on an
  org-visible page is both wrong and the kind of thing that gets noticed.
- Full exclusion screen applies to the sentence and every linked artifact: no privileged/counsel
  references, sensitive vendor naming, current-weakness specifics, personnel, personal-OneDrive
  links, or access-restricted evidence. If no safe evidence link exists, drop the item.
- **Every number and every "each" in a shipped sentence is checked against the live list, not
  the plan.** The 09-02 draft said "14 initiatives with a sponsor, target impact and finish line
  each"; the list had 18 AI Program rows and 11 of them had no TargetDate. Count from the dump you
  already pulled; if a column is partly blank, the sentence cannot say "each".
- Put each complete item through the review table as one line (`Row` = `Recap page`, `Field` =
  `shipped item`), including the exact sentence, link labels, and target URLs. Apply only approved
  lines and re-screen anything Alex edits.
- Stage with `--stage` / `PromotedState=1`; publishing stays Alex's click. Never re-stage a page
  whose `FirstPublishedDate` is already set because that demotes a live News post.
- Build the delivery-only draft, and flag clearly that it contains no forum record, ONLY when the
  forum genuinely produced nothing to recap: no scribe note exists (meeting not recorded, or it did
  not run) and Alex pasted no notes. A note you have not looked for is not an absence.

## Weekly maintenance mode (`--maintain`, and the default for a bare `/ea-projects-curator`)

A bare invocation with no argument runs this mode. Only `--audit` (or "is the board missing
anything?") widens to discovery.

Skip discovery of new EA Projects initiatives; only true up what exists. Still gate every proposed change through the review table, and write only what the user confirms:

1. Run the **Weekly AAB control** above and report it before any EA Projects finding.
2. If the control shows the latest due forum has no published recap, **read that session's scribe note and draft the recap now** (use shared lookup under **Forum recap — generate it from the scribe transcript note**, then [references/recap.md](references/recap.md)), and carry it into the same review table. A missing recap is work to do this run, not just a line item to report. If the note itself is missing, tell Alex to run `/scribe teams` for that date instead of fetching the transcript yourself. The note is also the truth-check for whether the forum actually ran: a past-dated `Scheduled` intake item plus a real note means the close-out was missed, not the meeting.
2a. Run control check 3a: write that session's forum advice back into the brought documents ([references/brought-docs.md](references/brought-docs.md)), as `D#` lines.
3. Diff `Status` / `NextMilestone` / `MilestoneDate` against the latest archeologist / ADO / GitHub signals; propose moves.
4. Flag any row whose `MilestoneDate` is > 7 days past due — a stale board is evidence against you.
4a. Flag any row whose `TargetDate` is in the past and Status is not `6. Closed`, and any pre-Closed row with a `Target:` impact but no `TargetDate` (or the reverse). Flag any `6. Closed` row whose Impact still carries the `Target:` prefix — closing requires the target be rewritten as documented impact or the Outcome set to Killed/Superseded.
5. Flag `3. Decision-Ready` rows older than 30 days that still have a `Decision Needed` set — decision rot; surface them for the 1:1.
6. Flag `1. Proposed` rows older than ~6 weeks — the black-hole state; propose "analyze or kill" for each.
7. Flag any `6. Closed` row with a blank `Outcome` — closing requires one (Delivered/Killed/Superseded).
8. Flag any row whose promise is contradicted by its linked ticket or fresher comms evidence (milestone in days, ticket still `New`; "next milestone: X review" when X was already sent for approval) — the board understating done work is as bad as overstating it.
9. Flag any `4. In Progress` row with empty Impact + milestone + artifact — the emptiest-looking row is the one a reader clicks.
10. For rows with a meaningful weekly signal but no column change, propose a narrative comment (see Comments section) instead of forcing a field move. Read each row's existing comments first — both to avoid repeating and to pick up replies/questions others left on the row.
11. Re-surface every ledger `open_items` entry still unresolved (undated milestones, empty rows Alex said he'd handle).

## Full audit mode (`--audit`, or "look at everything we're doing — is the board missing or misrepresenting anything?")

Discovery + maintenance combined: parallel retrieval (live list + ADO saved query + 8-week archeologist sweep, per the Retrieval section), then the three-way cross-check (missing / misrepresented / coherence), then everything — new rows, field fixes, comments, theme moves — in ONE review table. Lead the report with any coherence problem; it's worth more than any single row. Rows that check out clean get said so explicitly.

## Output — the record

After the gate and the write, emit four markdown tables so the run is auditable:

1. **WRITTEN** — new rows added: all columns + the new item Id/URL.
2. **UPDATED** — row title + each changed field (old → new).
3. **COMMENTED** — row title + the exact comment text posted.
4. **EXCLUDED** — every rejected candidate + the one-line gate that killed it (`privileged` / `attendance` / `sub-initiative` / `scope-claim` / `personnel` / `vendor-sensitive-unresolved`). This makes the screen auditable and catches over-aggressive filtering on review.

## Safety recap

Org-visible list. The review table is the mandatory gate. Never invent initiatives or impact figures — empty beats soft. Never write an unconfirmed row or comment; never move `Status` without an explicit yes on that specific line. Run the exclusion screen on every candidate, on every title the user edits, and on every comment's text. Comments: plain text, no @-mentions, append-only. Check `not_doing` before proposing new rows. Flag personal-OneDrive artifact links instead of publishing them. Never touch list or site permissions. Never copy a document into the Architecture library that fails the exclusion screen or whose sharing scope you could not verify: a copy of a restricted file gives the whole org access. Never write the author's response column, never edit an Accepted ADR, and never send the author message yourself.

The forum recap carries the same stakes and one extra risk: it is built from a verbatim scribe transcript note of a room where people speak freely about live security gaps, vendors and each other. **Quote nothing that the exclusion screen would block as a board row.** Attribute only what a named person actually said, never publish a garbled proper noun, never promote uncontested discussion into "Decided", and never invent an owner or a date. The recap goes out staged (`PromotedState=1`) for Alex to publish, and any line you are unsure about belongs in the review table as its own question, not softened onto the page.
