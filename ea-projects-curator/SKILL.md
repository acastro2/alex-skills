---
name: ea-projects-curator
description: >
  Curate Alex's EA Projects SharePoint board (EA Portfolio), the EA areas in Azure DevOps, and AAB
  surfaces on /sites/Architecture. Use for board population, updates and row comments; ADO epic and
  story upkeep (epic-to-row links, parent links, weekly epic update comments, Current Status, state
  truth-ups, filing missing work); weekly maintenance; full audits; AAB Intake
  close-outs and forum checks; writing forum advice back into the RFCs and ADRs people bring
  (copying off-site pre-reads into the Architecture library); or Architecture Weekly, Architecture Review Forum and AAB meeting
  recaps. Org-visible list writes require a numbered user-review table; recap pages are staged
  drafts for Alex to publish.
---

# EA Projects Curator

Turn the scattered evidence of what Enterprise Architecture actually did — prior AI sessions, ADRs/SADs, ADO epics, GitHub PRs — into a small set of executive-legible rows on the EA Projects board. You are a **filter and transformer**, not a retriever and not a scribe: you receive raw signals, decide what qualifies, shape it for a non-architect CTO, and then **ask** before you write.

```
scribe note + meeting chat ─→ recap (deep topics) ─→ verify vs note ─→ docs-reviewer ─→ fix ─→ alex-voice pass ─→ RENDER ─→ STAGE ─→ hand back link
archeologist     ─┐                                                                               ▲
ADO + GitHub     ─┴─→ curate: cluster · screen · shape ─→ REVIEW TABLES ─→ write ─→ report ──────┘
                       (ADO items, epic updates,          (approve by line)   (what moved rolls up
                        board rows, intake, comments)                          into the recap)
```
The page body is rendered from content by `references/render_page.py`, and the **Executive Summary
band is a reviewed line** because the ELT reads it. ADO, board, intake, and comment writes wait on the
numbered tables; the recap's other sections do not. Never paste the recap into the terminal.

**Every weekly run updates three surfaces and rolls them up into one page.** It updates **ADO** (what EA does: epics, stories, and a weekly update comment on every active epic), the **EA Projects** board (what EA impacts or influences), and **AAB Intake** (the forum queue). See [Where EA work lives](#where-ea-work-lives--ado-ea-projects-aab-decided-2026-10-09). Everything that moved on those three surfaces rolls up into that week's **Architecture Weekly** News page (`SitePages/Recaps/YYYY-MM-DD-AAB-Recap.aspx`; keep this filename for cadence compatibility). The page carries the **Executive Summary** band (the ELT reader's gate), the **Forum recap**, and the evidence-backed **What Enterprise Architecture shipped** panel, staged as an unpublished draft with `PromotedState=1` set via CSOM and the page title area hidden. Hand Alex the link; he publishes org-visible comms himself. The page body is rendered by [references/render_page.py](references/render_page.py) from a content JSON — never written by hand. Use one review table and stage once. A plain publish without `PromotedState` never reaches the Home News rollup, which reads exactly like the update never happened. Missed on the 2026-07-28 run; see memory `arf-notes-two-deliverables`.

**The Forum recap component is GENERATED from the scribe transcript note by default** — you read the note the `scribe` skill already wrote, you do not fetch or parse the Teams transcript yourself, and you do not wait for Alex to paste notes. See **Forum recap — generate it from the scribe transcript note** below for shared note lookup; read [references/recap.md](references/recap.md) when drafting or reviewing the recap for the exact prompt and all recap checks. Two overrides: if Alex pastes his own forum notes, render those **verbatim** instead (his text always wins over your generated recap, per the template in the SharePoint agent doc — `~/.claude/agents/sharepoint.md` for Claude Code, `~/.pi/agent/agents/sharepoint.md` for Pi); if no scribe note exists and he pasted nothing, build the delivery-only draft and say plainly that it carries no forum record.

For prose, follow [Alex's voice](../alex-voice/SKILL.md).

Three invariants that override everything below:

1. **Never invent.** No initiative the evidence doesn't support; no impact claim that isn't documented. An empty cell is better than a soft one.
2. **Never write unconfirmed.** The list is readable by the entire Technology org, and so is every ADO board (all licensed people can read Information Technology). The review gate *is* the mandatory human review. Skipped and excluded candidates are never written; the user owns what gets published.
3. **`Status` is Alex's column.** He curates lifecycle position himself. Never bundle a Status move into other edits; a proposed Status change is always its own line in the review table, flagged as needing his explicit yes. Applying his dictated updates → touch only the fields he named.

## Where EA work lives — ADO, EA Projects, AAB (decided 2026-10-09)

Alex's rule (refined 2026-10-10): **ADO holds what EA does (work). AAB Intake holds what is being decided (decisions). The EA Projects board holds EA's bets and the value they deliver**: a view of where each initiative stands and what it unlocked, which is the track record a future CTO reads. ("Radar" is Alex's metaphor for this view, not a technology radar.) Architecture Weekly rolls up all three. Use the rule to place every item before you write it anywhere. Evidence behind the design: `enterprise-architecture/research_notes/EA portfolio radar/synthesis.md`.

| Surface | Holds | Row or item |
|---|---|---|
| **ADO**, EA areas | Hands-on work by EA and the teams that report to EA | Epic, User Story, Spike, Request, Operational Work |
| **EA Projects** | EA's bets and the value they deliver | One row per initiative, at a stage: `1. Exploring` → `2. Committed` → `3. Delivering` → `4. Delivered`, or `5. Stopped`. A **delivery row** (`EA role = Builds`) rolls up EA's own epics. An **influence row** (`EA role = Influences`: AAB review, standard, advice) has no EA epic and links to the owning team's epic or document. Run work is `EA role = Runs` |
| **AAB Intake** | Decisions: the forum queue | One item per topic. An Exploring board entry becomes an AAB item when it is ready for a decision (see the board-to-AAB flow below) |
| **Architecture Weekly** | The roll-up of all three for the org | One page per week |

**Roll-up rules:**

1. **Every epic in an EA area rolls up to exactly one EA Projects row.** The link is a **Hyperlink on the epic in ADO** that points to the row's `DispForm.aspx?ID=<n>` URL. One row can hold many epics. There is no new field and no process change (Alex, 2026-10-09: "just use links in ADO").
2. **Run work rolls up too.** EA itself and each team that reports to EA have one operations epic and one operations row for keep-the-lights-on work. EA's standalone Requests get the **EA operations** epic as their parent (Alex, 2026-10-09). So everything EA does shows in the portfolio, without one row per epic. If the EA operations epic or row does not exist yet, propose them first (`W#` and `E#`, both **Needs you** for the title and Theme).
3. **Each fact is typed once.** Why, sponsor, impact, theme and stage (`Status`) live on the row. Decisions live in AAB Intake, linked from the row's `AAB items`. Who does the work, state, dates and progress live in ADO. The weekly epic comment is the progress narrative.
4. **The board is complete, the newsletter is selective** (Alex, 2026-10-09). The board is updated as updates come, and every initiative keeps its row. The newsletter leads with what mattered most that week, chosen from evidence (see the newsletter ranking rule).
5. **The EA areas list is in [ado-ea-portfolio-schema.md](references/ado-ea-portfolio-schema.md).** Today it is `Information Technology\Enterprise Architecture` only. A team's area joins the list only when Alex says the reporting change is official. Never name a team as EA's in org-visible text before that.

### Board to AAB flow (decided 2026-10-10)

```
1. Exploring --(trigger hit)--> AAB item (Design question early, Decision when ready)
AAB item Decided --> propose 2. Committed     AAB item Parked or Deflected --> propose 5. Stopped
2. Committed --(building, piloting or rollout starts)--> propose 3. Delivering
3. Delivering --(outcome live, work finished)--> propose 4. Delivered (Milestone `Delivered` + date, Impact documented)
```

- **Triggers** (Richards and Ford, plus the AAB form's Reversibility): new spend, cross-team impact, a
  security implication, or a one-way door. When an Exploring entry hits one, flag it, and for **Alex's
  own entries** propose its AAB item as an `A#` line (see the AAB control exception). The AAB form
  already carries Item type (Decision / Design question / FYI), Reversibility and Affected domains.
- **The link** is the row's `AAB items` lookup (multiple values allowed). Every stage move is still a
  **Needs you** line, because Status is Alex's column; the AAB outcome is the evidence, not the decision.
- **Committed means late commitment:** the decision is made and building is about to start. Explore
  cheaply before it (Mowbray and Malveau: "During the architecture phase, the commitments are very low").
- A decision a leader makes (CTO, a business owner) still goes through AAB, with an outcome that names
  who decides, the way break-glass went to Becca Fox. The newsletter footer shows who it is waiting on.

The weekly ADO work is the [Weekly ADO control](#weekly-ado-control--what-ea-does) below. Field map, join rules and the state-to-Status check are in the schema reference.

## The board you write to

Live target (verify against the list if a write is rejected — schema can drift):

- Site: `https://attainfinance.sharepoint.com/sites/Architecture` (group Team site, already org-readable).
- List display name **EA Projects**, GUID `d2c0a30a-dab4-40a7-bc63-7268736473f2`, URL slug still `/Lists/EA Portfolio` (internal name `EA_x0020_PortfolioList`).
- Page: `SitePages/EA-Portfolio.aspx`. Views (rebuilt 2026-10-12): **leadership views show EA role + Sponsor + Impact; the working view shows milestones + ExecutionLink; All Items shows everything.** List default view is **All Items** (unfiltered, grouped by Stage, keep it default — Alex's rule; 11 columns: Title, Theme, Status, EARole, AAB items, Sponsor, Impact, NextMilestone, MilestoneDate, KeyArtifact, ExecutionLink). **Current bets** (`2c97ee1e-b6ab-4835-bb44-2b8e6ffb8663`, the old CTO view renamed in place, URL still `/Lists/EA Portfolio/CTO view.aspx` so shared links work; filter Status = `2. Committed` OR `3. Delivering`, sorted by MilestoneDate): Title, Status, EARole, Sponsor, Impact, NextMilestone, MilestoneDate, AAB items, KeyArtifact. **Track record** (`4ab8cb26-fc06-4392-ab04-fc7256455404`, filter Status = `4. Delivered`, sorted by MilestoneDate newest first; closing dates backfilled from version history on 2026-10-12): Title, Theme, EARole, Impact, MilestoneDate (the delivered date), KeyArtifact, Sponsor — the page for a future CTO. **AI Program** (`25d2983e-48b7-404e-913e-701266410ec3`, URL `/Lists/EA Portfolio/AI Program.aspx`, filter `Theme eq 'AI Program'`, sorted by Status then MilestoneDate): Title, Status, EARole, AAB items, Sponsor, Impact, NextMilestone, MilestoneDate, KeyArtifact — the leadership AI stack-rank view; an AI initiative not tagged `Theme = AI Program` is invisible there, so check the Theme on every AI row. **Full projects** (`3589d875-06f1-4d2a-b05e-28ce16b97851`, grouped by Theme, sorted by MilestoneDate): Title, Status, EARole, AAB items, NextMilestone, MilestoneDate, ExecutionLink, KeyArtifact — the delivery view. All views RowLimit 100. Modern SharePoint orders view tabs alphabetically with no order setting. When adding a column, add it to the views whose audience needs it, never to all of them by default.

Columns (internal name → type → allowed values). Use internal names for any write:

| Internal | Display | Type | Values / rule |
|---|---|---|---|
| `Title` | Initiative | Text | Outcome title (see field mapping) |
| `Theme` | Theme | Choice | `Security Hardening` / `Platform Foundations` / `AI Program` / `Governance` / `Business Initiatives` (EA supporting a business move — market expansion, M&A, vendor due-diligence; named "Initiatives" not "Priorities" so other themes don't read as non-priorities). Cut from 8 to 5 on 2026-10-12: Observability and Tech Recruiting had one row each, and Modernization Enablement ("EA advises") is now `EARole = Influences`, not a theme |
| `Status` | Stage | Choice | `1. Exploring` / `2. Committed` / `3. Delivering` / `4. Delivered` / `5. Stopped` (since 2026-10-10; default `1. Exploring`; numbered so alphabetical sort = lifecycle order; `2. Committed` is the commitment point: before it "should we?", after it "we're doing it". Pills are outlined before it and solid from it. Display name `Stage` since 2026-10-12; the internal name stays `Status`) |
| `AABItems` | AAB items | Lookup (multi) to AAB Intake (`Title`) | The AAB items that decide or advise this entry. Write as `AABItemsId` (see write-shapes) |
| `EARole` | EA role | Choice | `Builds` / `Influences` / `Runs` (added 2026-10-12). Exactly one per row; see field mapping |
| `Impact` | Impact | Text (single line) | Documented impact, financial or non-financial; OR a forward-looking target prefixed `Target:` while the entry is before `4. Delivered`; blank if neither |
| `KeyArtifact` | Key Artifact | Hyperlink | One canonical ADR/SAD URL |
| `ExecutionLink` | Execution Link | Hyperlink | ADO epic/feature or GitHub URL |
| `NextMilestone` | Milestone | Text | Open rows: the next outcome, one line. Closed rows: `Delivered`, or `Stopped: <why in a few words>` |
| `MilestoneDate` | Milestone date | Date | Open rows: the date that milestone is due. Closed rows: the date the row closed (Track record's delivered date) |
| `Sponsor` | Sponsor | Person (single) | The business or technology leader who owns the outcome and answers for it; blank if EA is the only stakeholder. Expected from `2. Committed` on (Alex, 2026-10-12) |

> **Cut on 2026-10-12 (Alex):** `DecisionNeeded`, `Outcome`, `TargetDate` and `Who_x0020_is_x0020_Responsible` are deleted from the list. Never write or `$select` them: the request fails. Their last values are in the snapshot `~/.agents/skill-workspace/alex-skills/ea-projects-curator/backups/ea-portfolio-before-colphase-2026-10-12T0920.json` (`rows`). Who does the work lives in ADO (`AssignedTo`), the finish date lives on the epic, and the stop reason lives in the Milestone and the closing comment.

> Note: `Decision-Ready` was once a Theme and later a Status; both are gone. If you ever see it proposed, it is stale. The old six statuses (Proposed, In Analysis, Decision-Ready, In Progress, Verifying, Closed) were remapped on 2026-10-10; the old values are in each row's version history (the list keeps 50 versions) and the ledger rows still carry old names as history.

## Granularity — the rule that matters most

**One row = one initiative.** Not one artifact, not one meeting, not one ticket: a body of work with its own outcome, decision path, and "done" state. The test: *would the CTO ask about this by name?*

- ADR + SAD + a POC + a comparison doc + an ADO feature serving one decision → **one** row ("Privileged Access Renewal"), not five.
- Six Grafana workstreams (telemetry, profiling, alerting, IaC, onboarding, cost) → **one** row ("Observability Platform").
- Merge only when two rows pursue the same outcome, or one is a part or a phase of the other (a POC that exists to pick a platform belongs on the platform's row). Never merge distinct bets to cut the row count: each row needs one stage, one sponsor and one EA role (Alex, 2026-10-12, when he dropped a ~20-row target). A merge is an `E#` line: the merged row moves to `5. Stopped` with Milestone `Stopped: merged into <row>` and the merge date, both rows get a comment, and the surviving row's ledger `sources` take the merged row's sources, so later evidence matches the survivor. Nothing is deleted.

## Inclusion — a candidate must pass all four

1. **Delivery or influence, not attendance.** For a delivery row, the verb must be authored / executed / shipped / decided / established / migrated / secured / consolidated. For an influence row (see [Where EA work lives](#where-ea-work-lives--ado-ea-projects-aab-decided-2026-10-09)), EA advised or reviewed **with a recorded outcome**: a `Decided` AAB item, an adopted standard, or written advice the owning team acted on. Attended / joined / participated is excluded unless folded into an initiative.
2. **Initiative-scale.** Has a decision path or a milestone, not a one-off favor or a single meeting outcome. This applies to influence rows too: one AAB review is usually a row comment on an existing initiative, not a new row.
3. **Owner-of-record.** You drove it or own the decision; a contribution qualifies only if it is itself an artifact (e.g. a section of a hardening report). For an influence row, EA owns the advice on record, not the delivery; the owning team's epic is the Execution Link.
4. **Org-shareable.** Passes the exclusion screen below.

## Exclusion screen — hard gates, run on EVERY candidate (and on every user-edited title)

1. **Privileged / counsel-touched.** Legally privileged, confidential, forensic assessments, legal hold, counsel communications, breach-forensics detail, security codenames. **Exclude entirely — not even a redacted or renamed row.** A partially privileged initiative may cover only its non-privileged surface and link only to non-privileged artifacts; if that surface is empty, exclude the whole thing.
2. **Vendor-sensitive naming.** Neutral platform-strategy names, never vendor-replacement framing:
   - "Privileged Access Renewal" — not "<PAM vendor> Replacement".
   - "Data Warehouse Platform Strategy" — not "<warehouse vendor> Migration/Exit".
   - No named open-source replacements in titles or milestones; tool names live inside the linked ADR.
3. **Scope-claiming.** No rows for unsolicited org-wide transformation plans or future territory; delivered, in-flight, or decision-ready work only.
4. **HR / personnel.** A published process artifact (e.g. a hiring-process improvement) is includable; individual candidates, interview assessments, and personnel opinions never are.

## Field mapping

- **Initiative (`Title`)** — outcome-named, exec-legible, ≤ ~6 words. No component names or acronym soup: "GitHub Access Governance", not "ADR-0004 Entra-Synced Teams".
- **Theme** — exactly one value; if two fit, pick the *current* center of gravity, not where the work started. **One exception: AI wins the tie.** If the work delivers an AI agent, model, or assistant, or a control on AI use or AI spend, `Theme = AI Program`, even when the domain is security, ops, or governance (e.g. Security Findings Triage Agent, GenAI Controls). Why: the AI Program view filters on Theme only, and it is the leadership AI stack-rank. An AI row under another theme is invisible to the CTO there; an extra AI Program tag only moves the row to another group in Full projects.
- **Status (stage)** — exit criteria: `1. Exploring` → `2. Committed` when the decision is made (an AAB item `Decided`, or the named owner's written yes); `2. Committed` → `3. Delivering` when building, piloting, configuring or rollout starts (an Active epic, a merged PR, a pilot live); `3. Delivering` → `4. Delivered` when the outcome is live and the work is finished, with Milestone `Delivered`, Milestone date = the day it closed, and Impact rewritten as documented impact; any stage → `5. Stopped` with Milestone `Stopped: <why>` (killed or superseded, e.g. `Stopped: superseded by four delivery projects`) and the closing date. A step back (Delivering to Committed) is legitimate when honest; only `4. Delivered` and `5. Stopped` are immutable. Blocked-ness is never a stage: a decision block is an AAB item; a non-decision block (vendor, dependency) goes in a comment. When Jev's stage answer and the evidence disagree, the evidence wins and the line says why.
- **AAB items (`AABItems`)** — link every AAB item that decides or advises the entry. A new link is an `E#` line. An Exploring entry that hits a trigger with no AAB item is a finding; for Alex's own entries propose the item (`A#`) and the link (`E#`) together.
- **EA role (`EARole`)** — exactly one value. `Builds`: EA does the hands-on work, and an epic in an EA area links to the row. `Influences`: another team builds; EA advises, reviews or sets the standard, the Execution Link is the owning team's epic, and the row needs a recorded outcome (inclusion gate). `Runs`: keep-the-lights-on work EA runs, like the Architecture Advisory Board and the EA operations row. Set it on every new row; a change is its own `E#` line. When the evidence is mixed, ask Jev (`ea_role` in [references/jev-gates.md](references/jev-gates.md)); a Builds answer needs an EA-area epic or hands-on work by EA people (PRs, configuration, infrastructure, a pilot EA ran); an ADR, RFC or standard alone is Influences.
- **Impact (`Impact`, text)** — **lead with the outcome the work unlocks, not the metric or the money** ("Unblocks the upgrade to the latest .NET" beats "699 USD per dev license avoided"). Pattern: *outcome first, evidence metric in parens* (e.g. "Real production visibility org-wide (1→23 accounts, ~5K→127K signals) at ~70% lower run-cost"). **Documented impact** (no prefix) traces to an ADR, costed analysis, invoice delta, or stated metric — no estimates, no "up to". **Target impact** (`Target:` prefix) is the forward-looking claim a pre-Closed initiative is funded for, traceable to a BRIEF, RFC, or costed options analysis. A target loses its prefix only when evidence exists, rewritten then as documented impact. Never mix the two in one cell. **Progress number** (Alex, 2026-10-09): when the outcome is countable and a live source counts it (ADO, GitHub, a scanner, a report), append `(now X <unit>; baseline Y on YYYY-MM-DD)`, with the unit written once, right after X, and the same unit every week (`(now 4 services; baseline 0 on 2026-09-28)`); no "of N", no extra words, so readers can compare week to week. Set the baseline once, from evidence; update `now` when the source changes; never estimate. It reports progress, not a claim, so it can follow a `Target:` impact without mixing the two. **The number passes the exclusion screen first:** a count of open weaknesses (open CVEs, unrotated credentials, failing controls) is a current-weakness specific, so publish the effect side, the share closed or the drop since the baseline (`critical CVEs down 30% since 2026-09-16`), and keep the raw counts in the run record for Alex. A count of delivered things (services moved, repositories covered) is safe as it is. If the outcome isn't obvious, ASK "what does this unlock?" rather than defaulting to the metric. Blank beats soft. **Effect-side only:** never publish current-weakness specifics ("creds unrotated 2+ yrs" is a timestamped vulnerability admission) or commercial posture ("ends vendor lock-in" telegraphs to Procurement). Describe what the work closes, not the live hole or the leverage play.
- **Key Artifact (`KeyArtifact`)** — one canonical link: the ADR/SAD itself, not the folder. Flag personal-OneDrive URLs (`-my.sharepoint.com`) for re-homing; they 403 for the org audience.
- **Execution Link (`ExecutionLink`)** — the main ADO epic, or a GitHub location. A delivery row with several epics links its main epic here; the full set comes from the Hyperlinks on the epics, so never try to list them in this cell. An influence row links the owning team's epic. Omit if none, and never create a ticket only to fill the column: a missing-item story is for real hands-on work (see the ADO control).
- **Milestone (`NextMilestone`) + Milestone date (`MilestoneDate`)** — on an open row, the next outcome a non-architect can parse, with the date in the date column: "Options memo to the CTO" + `2026-07-25`, not "Finalize Raft topology". When a row closes, the same pair records the close: `Delivered` or `Stopped: <why>`, plus the closing date. Track record sorts on that date, so it is the delivered date a future CTO reads.
- **Sponsor (`Sponsor`, person)** — the leader who owns the outcome and answers for it: the P&L/budget holder for business work, the technology VP for platform work. Never the EA lead, a delegate, or a working-level contact; only from evidence (a BRIEF sponsor line, an AAB recap, a written commitment) — a name mentioned in a meeting is not a sponsor. Blank beats a guess. **Expected from `2. Committed` on** (Alex, 2026-10-12): a Committed, Delivering or Delivered row with a blank Sponsor is a maintenance finding; ask Alex who it is, never guess.

## Comments — the narrative layer

Rows carry the *state*; item comments carry the *story*. A comment fits a signal that is real but
changes no column: progress inside a status, the rationale for a status or milestone move, a
verification note, or a caveat about a link (e.g. "Key Artifact is a working folder — will swap to
the ADR when it exists").

**Propose one when** the week produced a meaningful signal for a row whose columns don't move, or
**alongside** a field update to say *why* (an unexplained slip reads worse than an explained one).
**Don't** restate a column, log routine activity, or narrate every run: one comment per row per run
is the rough ceiling; skip rows with nothing worth saying.

Rules (same stakes as the row — comments are org-visible):

- **Full exclusion screen applies:** no privileged/counsel references, sensitive vendor naming,
  current-weakness specifics, or personnel opinions.
- **Exec-legible, 1–2 sentences**, outcome-first, same voice as `NextMilestone`. No acronym soup, no
  session/ticket IDs.
- **Transient dependencies live in comments, not link columns.** A firewall change request or
  approval ticket belongs in a comment, not `KeyArtifact` or `ExecutionLink`, and it will be stale in
  weeks. Say what IS done first ("runner pool is live") — "delivered, waiting on X" beats a bare slip.
- **Plain text only, no @-mentions** — a mention emails someone; that is a human's call.
- **Append-only.** Never edit or delete an existing comment; a correction is a new comment.
- **Question-gate every comment**, and re-screen text Alex edits.
- **Idempotency:** GET existing comments first (others may have already said it, and replies are
  signals too); record posted comments in the ledger (`comments` per row) so re-runs don't repost.

REST shapes for reading/posting comments live in `references/write-shapes.md`.

## Retrieval — where candidates come from

**Auth preflight FIRST (2026-08-10 lesson):** before any retrieval, check the cookie cache age —
`stat -f %m <scripts>/sharepoint/.cookies.json` vs `date +%s`, then **probe** with one
live GET on the EA Projects list (`$top=1`), where `<scripts>` is the sharepoint scripts tree your
tool runs — `~/.claude/scripts` in Claude Code, `~/.config/opencode/scripts` in OpenCode and Pi.
The cookie lifetime is not a fixed 7h: on 2026-09-04 a 28h-old cookie read, staged a page, and
MERGEd rows without a single 401. Ask Alex to run
`python3 <scripts>/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/Architecture" --refresh`
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
  **Field map, the epic-to-row Hyperlink join, and the state-to-Status truth-check live in [ado-ea-portfolio-schema.md](references/ado-ea-portfolio-schema.md)** — read it before mapping an EA-board epic to a portfolio row, and before proposing any field that ADO does not already carry (the portfolio-only columns must not be duplicated into ADO).
  **Ticket state truth-checks the row:** a milestone in days while the ticket sits in `New` is a
  slip; a "Closed" row with an `Active` ticket may not be closed; the same check runs on the EA-board story or SOW epic behind the row's Execution Link.
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
REST), the ADO saved-query agent, and an archeologist sweep of the last ~8 weeks (sorted by recent
activity, anything privileged quarantined in a flagged section). Then cross-check three ways:
- **Missing** — evidence-backed initiatives with no row (check `not_doing` first).
- **Misrepresented** — rows contradicted by fresher evidence: milestone already delivered or sent
  (email/Teams beats a stale field), Closed row with a live ticket or future-dated milestone,
  In-Progress row with empty Impact/milestone/artifact.
- **Coherence** — does the portfolio read as one story? Rows investing in a platform while an
  exit/replacement decision is pending; themes that bury work where the CTO won't look
  (privileged-access rows outside Security Hardening; AI rows outside AI Program, which hides
  them from the AI Program view). Coherence outranks any single-row fix.

## Typed gates — `ask_jev`

Three judgments run on every candidate every run — does it qualify, which stage (`Status`), which
`Theme` — and dedupe runs on every match. Make them typed `ask_jev`
calls instead of prose. Why: a typed answer returns a value **plus a confidence**, so the
same evidence gets the same label next week and the uncertain calls surface as questions
instead of hiding in a paragraph. A prose label drifts, and a board that disagrees with
itself costs more than a wrong row.

Question sets and copy-paste request bodies: [references/jev-gates.md](references/jev-gates.md).

- **One call per candidate**, in the same parallel batch as retrieval. `state` carries the
  clustered evidence plus the matched live row; Jev sees only what is in `state`, and the
  questions in one call cannot see each other.
- **Gate on confidence.** `row_qualifies` ≥ 0.80 → propose; ≤ 0.20 → screened out, with the
  reason in the report's screened-out list; between → `Needs you? yes`. A `choice` at ≥ 0.80
  confidence → recommend that value; below → still propose, but `Needs you? yes` with the
  confidence and the runner-up in the `Why` cell. These thresholds are defaults; move them
  deliberately, never per run.
- **Jev never passes a hard gate.** The exclusion screen, `not_doing`, and the three
  invariants above are rules. A probability must never admit a privileged row, revive a
  declined idea, or justify a write. Jev judges fit; the rules judge admissibility.
- **`Status` stays a proposal.** Jev's answer becomes its own `E#` line marked **Needs you** —
  never an applied value (invariant 3).
- **`Title` wording is not a Jev question.** Voice and brevity stay with the field mapping.
- **A low-confidence stop goes on `open_items`**, so the next run re-asks instead of
  re-guessing. Add no new ledger keys; the Connections pass `ideas` key is the one exception.
- **How to call Jev, read its answers, what may go in `state`, and what to do when it is
  unavailable:** follow [`../jev/SKILL.md`](../jev/SKILL.md); an unavailable Jev goes in the
  report. Here, `state` carries the initiative, its artifacts, and the row, never a raw
  transcript or privileged text: the exclusion screen applies to the request too.

## The review gate — one table, approve by line

This is the point of the skill. The board is org-visible and the user must own what's published, so **you recommend and the human decides.** Alex's confirmed preference (2026-07-28, after rejecting an `AskUserQuestion` batch): **numbered markdown tables** he can scan in seconds and answer with line numbers ("1 to 13 are good, 15 skip"). Refined 2026-09-04 after he rejected a 32-line merged table ("makes it confusing for me... I need it break down by recap, aab intake updates and ea portfolio updates"): **one table per surface, never one merged list.**

1. **Build the candidate set internally.** Cluster the retrieved signals into initiatives; apply granularity, inclusion, and the exclusion screen; run the typed gates on each candidate; match each against existing list rows (→ NEW or UPDATE); attach provenance and a fully recommended value for every column. Do ALL the deciding before the table — the table is for his review, not your thinking. A low-confidence gate verdict is what the `Why` cell is for.

**Name items, never bare IDs** (Alex, 2026-09-28: "Row 47 means nothing to me"): the `Row` column and every report line lead with the initiative or intake item's name; an ID may follow in parentheses.

2. **Emit FIVE sections, one table each, in this order.** (a) **Recap**: the staged page link, what you fixed before staging, and the one action (his Publish click). No lines to approve. (b) **AAB Intake updates**: lines numbered `A1, A2, ...`. (c) **Brought documents**: lines numbered `D1, D2, ...` (copies and document edits, with the drafted author messages below the table; see [references/brought-docs.md](references/brought-docs.md)). (d) **ADO updates**: lines numbered `W1, W2, ...` (epic-to-row Hyperlinks, parent links, the weekly epic comments, Current Status, state truth-ups, new items; see the [Weekly ADO control](#weekly-ado-control--what-ea-does)). (e) **EA Projects updates**: lines numbered `E1, E2, ...`. ADO comes before EA Projects because the E lines truth-check rows against the epic state the W lines fix. Same columns in (b) to (e): `# | Row | Field | Now | → Proposed | Why | Needs you?`; for a W line, `Row` is the work item title with the ID in parentheses. He answers per table ("A: all. D: 1–4. W: 1–6. E: 1–3, 5"). One line per field change; comments get a line too (proposed text in the → column); a NEW row is one line with the full recommended row summarized in →. The `Why` cell carries the reason (lead with the why — it's what he reads). `Needs you?` marks the lines he must explicitly decide: every Status move, every date only he knows, every row where the evidence ran out. Below the table, list what you screened out and why, and which rows checked out clean — the absence of a change is also a finding.

3. **He answers by line number.** Apply exactly the approved lines. A line needing input he didn't give (e.g. "yes" to a milestone rewrite but no date) → apply what you can, keep the gap on the open-items list; never fill it with a guess.

4. **Re-screen anything he edits** — an edited title or comment can quietly reintroduce a vendor name or a privileged reference. Then, and only then, write.

After the five tables, the [Connections pass](#connections-pass--ideas-after-the-review-tables) adds the `I#` ideas table. It asks Alex to judge ideas, not to approve writes, so it never delays or changes the five tables.

`AskUserQuestion` remains a fallback for a single fork mid-run (one decision, 2–4 options); never use it to triage the candidate set.

## Connections pass — ideas after the review tables

The run is prescriptive: it checks rules and fills tables. This pass is the one place where the curator looks across everything it gathered for relations no single row, epic or AAB item shows, and brings Alex ideas he would not see from a glance (Alex, 2026-10-12). It runs last, after every review table is built, and it never writes.

- **Engine.** In Claude Code, write the brief from the reference into the session, then call the `advisor` tool: it reads the whole run, so it sees every row, epic, AAB item and comment you pulled. Without an advisor (OpenCode, Pi), a fresh-context subagent gets the same brief and a scrubbed evidence summary. The advisor is a reviewer: its ideas are inputs, not facts.
- **Filter, in order.** Each idea cites at least two pieces of evidence from this run, and you read and checked each one; it passes the exclusion screen; it is not in `not_doing` and not a dropped idea; Jev grades it (`evidence_supports`, `non_obvious`, `actionable`), and any answer at or below 0.20 drops it.
- **Output.** An `I#` table, last in the report, headed "Ideas (hypotheses, not approved work)". No cap, and zero is a valid answer: never pad. Alex answers Act, Park or Drop per line.
- **Ledger.** Every idea shown goes in `ideas`. Act: the next run turns it into real lines whose `Why` cell cites the idea key. Park: it comes back only when its `revisit_when` evidence changes. Drop: never again, in any wording.

Brief text, what to look for, table columns and ledger rules: [references/connections-pass.md](references/connections-pass.md).

## Writing to the list

Hand confirmed rows to the **`sharepoint` agent**, or write a small batch inline with the helper
(`sys.path` → `<scripts>/sharepoint`, module **`sharepoint_api`** — not `sharepoint_helper`;
`make_session()` no args + `get_request_digest(session, site)`; CLI verbs need `SHAREPOINT_SITE_URL`
exported or they exit with "Set SHAREPOINT_SITE_URL"); one script MERGE-ing all approved items beats
N agent round-trips. Payloads and field shapes live in `references/write-shapes.md`; read it before
writing, and read `ListItemEntityTypeFullName` live rather than hardcoding it. **Verify every write:**
MERGE → 204, comment POST → 201, then GET the changed fields back. If a call 401/403s, ask Alex to
run `python3 <scripts>/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/Architecture" --refresh`
(headed passkey — a human step). **Never change list or site permissions.**

**If the network dies mid-batch** (TLS aborts, curl showing HTTP 000 — usually the corporate security
stack, not auth): save the confirmed-but-unwritten changes as an idempotent script in the scratchpad
(checks existing comments before posting; safe to re-run twice), tell Alex exactly which writes
landed and which are pending, and re-run when connectivity returns. A write is only "done" once
verified.

## Idempotency & the ledger

- **Match before emit.** Compare each candidate to existing rows by title similarity + Key Artifact URL; a match emits an UPDATE of changed fields, never a duplicate.
- **Delivered and Stopped are immutable.** An initiative that ends becomes `4. Delivered` (Milestone `Delivered` + date) or `5. Stopped` (Milestone `Stopped: <why>` + date); never deleted, never reopened — a resurrected initiative is a NEW row, with a comment on each row pointing to the other. Pre-Closed rows may step back one stage when honest; nothing disappears silently.
- **Ledger `curated.json`** (in this skill's directory) maps each source artifact ID → the row it fed, so overlapping re-runs are no-ops. Read it at the start, update it after writing. Shape:
  ```json
  {
    "list_guid": "d2c0a30a-dab4-40a7-bc63-7268736473f2",
    "rows": {
      "<listItemId>": {
        "initiative": "Privileged Access Renewal",
        "key_artifact_url": "https://...",
        "sources": ["cc:<session-uuid>", "ado:12345", "gh:https://github.com/<org>/<repo>/pull/42", "adr:OneDrive/Architecture/<file>.docx"],
        "status": "2. Committed",
        "last_curated": "YYYY-MM-DD",
        "comments": [
          {"date": "YYYY-MM-DD", "text": "exact posted text"}
        ]
      }
    },
    "ado": {
      "<workItemId>": {
        "title": "SOW 2 · CVE remediation",
        "row": "<listItemId>",
        "created_by_curator": false,
        "sources": ["gh:https://github.com/<org>/<repo>/pull/42"],
        "updates": [
          {"date": "YYYY-MM-DD", "text": "exact posted comment", "current_status": "On Track"}
        ]
      }
    },
    "ideas": {
      "YYYY-MM-DD-I1": {
        "date": "YYYY-MM-DD",
        "text": "Two rows wait on the same POC readout; one AAB item could decide both",
        "evidence": ["row:Agent Platform, production", "row:Enterprise Knowledge Agent, Cleo successor"],
        "decision": null,
        "decided": null,
        "revisit_when": null
      }
    },
    "open_items": ["Row 20: MilestoneDate needs a real date from Alex - ..."],
    "not_doing": [
      {"what": "ADR-0003 Data Warehouse Platform Strategy (Redshift migration)", "decided": "2026-07-28", "note": "Staying on Snowflake - Alex declined even a Closed/Killed record row. Never re-propose."}
    ]
  }
  ```
- **`open_items`** — gaps a run couldn't close (a date only Alex knows, an empty row he's handling). Read them every run, re-surface what is still open; resolve or re-write at the end.
- **`ado`** — one entry per work item the curator linked, commented on, or created: its row, the evidence that justified a created item, and every weekly update posted. It stops a re-run posting a second update in the same week or filing the same work twice.
- **`ideas`** — one entry per idea the Connections pass showed, with Alex's `decision` (`Act`, `Park` or `Drop`, or null until he answers), the date he `decided`, and for a Parked idea the evidence that would reopen it (`revisit_when`). It stops a dropped idea coming back and lets a parked one return only on new evidence. Rules: [references/connections-pass.md](references/connections-pass.md).
- **`docs`** — one entry per intake item whose pre-read was placed or edited; stops a re-run copying twice or adding the same advice row twice. Shape in [references/brought-docs.md](references/brought-docs.md).
- **`not_doing`** — evaluated-and-rejected initiatives and declined candidates. Check before proposing any NEW row; never re-propose an entry. It stops every fresh session rediscovering the same dead idea.

## Weekly AAB control — the second operating surface

Alex curates a second list alongside the EA Projects board: **AAB Intake** (the Architecture Advisory
Board forum queue), plus the weekly **AAB Recap** News post (you generate its forum recap from the
scribe note; publishing stays Alex's action). This control runs **first**, before any EA Projects
check, in both `--maintain` and `--audit`.

- **AAB Intake list:** `https://attainfinance.sharepoint.com/sites/Architecture/Lists/AAB%20Intake/AllItems.aspx`, GUID `80c68e54-eadf-4cf3-946a-3c0e432056a5`, entity `SP.Data.AAB_x0020_IntakeListItem`. Fields: `Title`, `Status` (`New` / `Triaged` / `Scheduled` / `Decided` / `Parked` / `Deflected`), `Scheduledfor` (DateTime, **DateOnly**), `Outcomenotes`, `Modified`.
- **Recaps folder:** `/sites/Architecture/SitePages/Recaps`, page name `YYYY-MM-DD-AAB-Recap.aspx`. Browse view: `https://attainfinance.sharepoint.com/sites/Architecture/SitePages/Forms/ByAuthor.aspx?id=%2Fsites%2FArchitecture%2FSitePages%2FRecaps&viewid=a74d565d%2Da0da%2D444e%2Daae0%2D092bef143ca8`.
- **Timezone/week:** read `RegionalSettings/TimeZone` live (Central Time, America/Chicago). A calendar week is Monday–Sunday; if the timezone no longer maps to America/Chicago, report UNVERIFIED instead of guessing date boundaries.

Use [references/write-shapes.md](references/write-shapes.md) for the control's REST read/write shapes.
Run these checks before EA Projects checks; [Weekly newsletter](#weekly-newsletter--architecture-weekly)
owns page assembly, not session selection or intake control.

**1. Pick the session to verify — dynamically, never a hard-coded weekday.** Prefer the latest `Scheduledfor` before today: the current week, else the previous week's latest. A session dated **today** counts as due only when live evidence shows it happened (the exact-date recap exists, or an intake item carries a same-day outcome); otherwise label today upcoming/UNVERIFIED and verify the previous session, so a morning run raises no false alerts. If neither week has a date, derive the expected forum date from the last 3–4 published recap filenames and flag that the intake list has no anchor; never silently skip the check.

**2. Verify the recap was published, not staged.** A filename under `Recaps/` is not enough: require `PromotedState=2`, `OData__ModerationStatus=0`, and a `FirstPublishedDate`. `PromotedState=1` is a draft — report it as unpublished, don't treat it as done.

**3. Verify every intake item for that session was closed out.** For each item whose site-local `Scheduledfor` equals the session date: non-empty `Outcomenotes`, a status other than `New`/`Triaged`, and no past-dated `Scheduled` state. Normal outcome is `Decided`; `Parked`/`Deflected` are valid with notes. `Modified` must be on or after the session date (a sanity check, not proof). A future re-`Scheduled` item is valid only when version history or the ledger proves it moved from the session date and the notes explain why; otherwise UNVERIFIED. **Separately, always flag every item globally where `Status=Scheduled` and `Scheduledfor` is past** — SharePoint's agenda and decision-log views both hide that state.

**3a. Write the forum back into the documents people brought.** For every closed-out item, sort its `Pre-read links`: edit documents already in Architecture Shared Documents, copy off-site ones into the right type folder first (behind the content screen and sharing-scope gate), and alert on the rest. RFCs get `AAB Session`, `Status` Draft → Open for Advice, and advice rows from the scribe note; a Proposed ADR gets advice rows; nothing else is edited. See [references/brought-docs.md](references/brought-docs.md). Every copy and edit is a `D#` review line.

**4. Alert if next calendar week has nothing scheduled.** Check for at least one intake item with `Status=Scheduled` and `Scheduledfor` in `[next Monday, following Monday)`. None found → prominent alert to Alex to schedule or confirm nothing. Never auto-schedule or invent a date.

> **Scheduling is Alex's, by default.** (2026-09-04: "don't touch the other stuff I will schedule
> it manually.") An empty next week and unscheduled `New` items are an **alert** listing the
> candidates. Propose `Scheduledfor` + `Status=Scheduled` on an existing item only when Alex named
> the date himself, and then as its own `A#` line marked **Needs you**. Never infer a date from cadence.
>
> **Never create an AAB Intake item on anyone else's behalf.** One exception (Alex, 2026-10-10): for
> **Alex's own** board entries that hit a trigger, propose the item as an `A#` line marked **Needs you**,
> with Alex as the requester, filled from the entry (Title, "What do you want the board to decide?",
> Item type, Affected domains, Reversibility, Pre-read links). The intake list is **the queue people submit their own
> topics to**, not a scheduling table for the curator. An empty next week is an **alert only**, never
> a proposed row. The curator's writes here close out items that already exist: `Status`,
> `Outcomenotes`, and `Scheduledfor` on an item somebody else raised.

**Report before EA Projects findings under this exact heading:**

### AAB WEEKLY CONTROL

| Check | Result | Evidence |
|---|---|---|
| Recap published | PASS / ALERT / UNVERIFIED | date, page Id/URL, PromotedState |
| Intake close-out | PASS / ALERT / UNVERIFIED | item Ids/titles still open, with Status/Scheduledfor |
| Brought documents | PASS / ALERT / UNVERIFIED | per item: in place / copied / alert (off-site, screened out, scope unverified, unresolvable) |
| Next-week schedule | PASS / ALERT / UNVERIFIED | next-week range and items found, or none |

Any unresolved ALERT goes on `curated.json` `open_items` (cleared only after live re-verification). **Intake field changes are writes to an org-visible list**: propose them through the numbered review table, one line per field (`Status` / `Outcomenotes` / `Scheduledfor`), and apply only what Alex approves by line. Never invent `Outcomenotes` or a `Scheduledfor` date, and never publish the recap yourself — flag it as his action.

## Weekly ADO control — what EA does

ADO is where EA's hands-on work lives, so the run updates it before the board: the E lines read the
state the W lines fix. Sweep every area on the EA areas list in
[ado-ea-portfolio-schema.md](references/ado-ea-portfolio-schema.md) (see Retrieval), then run these
checks in order and turn each finding into a `W#` line.

1. **Roll-up link.** Every epic carries exactly one Hyperlink to an EA Projects row. A row link is a
   Hyperlink whose URL contains `/sites/Architecture/Lists/EA%20Portfolio/DispForm.aspx`; count only
   those, because epics also carry other hyperlinks (SOW documents, briefs). No row link: propose
   it to the matching row (match rules in the schema reference). No row fits: propose a NEW row as an
   `E#` line, plus the link as a `W#` line that waits on it. Two or more links: flag it and never pick
   one yourself, because the wrong row misreports the initiative.
2. **Parent link.** A Story, Spike or Operational Work item with no parent epic gets a proposed
   parent, from evidence only (title, a `SOW-<n>` tag, the description). No clear parent: flag it,
   because a guessed parent rolls the work into the wrong row. A **Request** is fulfilled in its own
   ticket (the IT Request model) and never gets child items. Propose a parent for a Request: the epic
   its scope plainly belongs to, else the **EA operations** epic (roll-up rule 2). Engineering
   Insights then shows the Request inside that epic instead of in its intake panel.
3. **Weekly epic update, on every active epic, every week** (Alex, 2026-10-09). For each epic in
   `Active` or `Resolved`, propose ONE comment on the epic that says what moved since the last update.
   Keep it short, in this shape:
   - **Done this week:** children closed, PRs merged, artifacts shipped, by name, not ID.
   - **Next:** the next outcome, with its date when one is known.
   - **Blocked or at risk:** only when it is real; otherwise leave the line out.

   A week with no movement still gets a comment that says so, with the reason when known, because
   silence reads as a dead epic. Pair the comment with a **`Curo.CurrentStatus`** line whenever the
   value is wrong for the evidence (allowed values in the schema reference; `Not Started` on an
   `Active` epic is always wrong). Current Status rides with the weekly update, so it is proposed on
   every active EA epic; `System.State` is not (check 4). Read the epic's existing comments first and
   post at most one update per epic per week. A week is the AAB control's calendar week (Monday to
   Sunday, America/Chicago), so a Sunday run and a Monday run are two different weeks. The update also feeds the recap's shipped panel, so
   write it once for both.
4. **State truth-ups.** Propose a `System.State` move only on an item assigned to Alex, and only when
   evidence contradicts the state: a merged PR on a story still `New`, every child closed on an epic
   still `Active`. Each move is its own line marked **Needs you**. Propose the next state, not a jump
   across several, and report a refused write instead of forcing it. An item assigned to someone else
   is theirs: report the mismatch in the control table and never propose the move. ADO refuses an
   epic move to `Active` without the Architecture Review Approved date and approver, so take both
   from a `Decided` AAB Intake item. An epic with work started but no AAB decision is an AAB finding
   for Alex, not a `W#` line. Required fields per move: [write-shapes.md](references/write-shapes.md).
5. **Missing items.** Hands-on work EA did that has no ADO item (a merged PR, a shipped artifact,
   work done in an AI session) gets a proposed new item: type (Story for delivery, Spike for a
   timeboxed investigation, Request when another team asked for it), title, area, parent epic,
   assignee (the person who did the work), and state (`Closed` when the evidence shows it is done).
   Why: ADO is what EA does, and the Engineering Insights quarterly view counts closed ADO items, so
   unfiled work is invisible to leadership. Never create an item for attendance or a meeting, or only
   to fill a link column. Check the ledger `ado` key first, so a re-run never files the same work
   twice.

**Writes.** REST shapes are in [references/write-shapes.md](references/write-shapes.md); verify every
write by reading it back. ADO comments follow the same rules as row comments: plain text, no
@-mentions (an ADO mention notifies the person), append-only, and the full exclusion screen. Never
delete a work item, and never change an area, iteration, process rule, or permission.

**Report after the AAB control, under this exact heading:**

### ADO WEEKLY CONTROL

| Check | Result | Evidence |
|---|---|---|
| Roll-up links | PASS / ALERT | epics with no row link, or more than one |
| Parent links | PASS / ALERT | items with no parent epic |
| Epic updates | PASS / ALERT | active epics, and which have this week's update proposed |
| State mismatches | PASS / ALERT | items whose state contradicts evidence, with the assignee |
| Missing items | PASS / ALERT | hands-on work with no ADO item |

## Forum recap — generate it from the scribe transcript note

The forum's own record is the note the `scribe` skill writes from the Teams transcript. Read that
note; never wait for pasted notes, and never fetch or parse the transcript yourself.

### Step 1 — read the scribe transcript note

Path: `<vault>/Scribe/Meetings/Transcripts/<YYYY-MM-DD HHMM> <Meeting title>.md`, meeting start in
America/Chicago, e.g. `2026-09-02 1500 Architecture Advisory Board.md`.

The forum runs **Wednesdays, 3:00–4:00pm Central** (verified across 8 sessions), subject
**`Architecture Advisory Board`** (never "Architecture Review Forum" on the note). Match on the
Wednesday date of the forum you're recapping.

**Read the `## Transcript` section in full before drafting**; never summarize from grep hits. The
frontmatter `speakers` list is your attendance line: who actually spoke, not who was invited.

**If the note does not exist, stop the recap** and tell Alex to run `/scribe teams` for that date; a
note you have not looked for is not an absence.

### Recap drafting and review

For drafting, verification, or page assembly (including delivery-only drafts and Alex's
pasted-note override), read [references/recap.md](references/recap.md): proper-noun handling, Alex's
exact prompt, recap gates, note verification, and the mandatory `docs-reviewer` pass. Board-only
tasks do not need it.

A missing note stops the forum recap component, not the whole page. If Alex supplied no notes either,
follow the newsletter gates for a delivery-only draft and state that it carries no forum record.

## Weekly newsletter — Architecture Weekly

Every weekly page carries THREE components under the title **Architecture Weekly — Month D, YYYY**:
the **Executive Summary** band at the top (see the gate below), the **Forum recap** (generated from
the scribe note via [references/recap.md](references/recap.md), or Alex's pasted notes rendered
verbatim), and the generated **What Enterprise Architecture shipped** panel at the bottom. They
answer different questions: the band is for the executive leadership team who read the page but were
not in the room; the forum record says what the group decided; the panel says what EA shipped. Drop
any delivery item that restates the forum recap.

### The page body is rendered, never written

**Run [references/render_page.py](references/render_page.py); do not write page HTML.** The run's job
is content, the script's job is markup:

```
recap-content.json  →  render_page.py  →  canvas.json  →  stage_news_recap.py --canvas
```

The script owns every tag, style and colour. Read its docstring for the content schema. There is
**no "SharePoint-native markup only" rule any more** (Alex, 2026-09-28: "that doesn't hold"): the page
may use whatever styling the design needs. The only markup the script refuses is `<script>` and
`javascript:`, for safety. Hand-written HTML is what produced the drift between the 09-09 and
09-16 pages; two files cannot disagree if only one holds markup.

[references/example-content.json](references/example-content.json) is a complete, valid input: copy
it to start a week, and render it after any change to the script to prove the script still works.

**It refuses on content shape too, not just markup.** Missing `exec_summary`, a band outside 3 to 4
points, a blank `footer`, an unknown `outcome.tag`, a decision with no `rationale`: each is a named
error naming the exact key. Fix the content; do not reach past the script. The safety scan reads
the MARKUP only, so ordinary prose is safe. Escaping keeps content out of the markup.

`python3 references/render_page.py --text canvas.json` prints the rendered page as plain text, the
input to `voice_check.py`; see [references/recap.md](references/recap.md) for the commands.

**Design and colour are fixed** (Alex, 2026-09-28, from the Claude Design mock "Architecture Weekly
Recap"; it replaced the 09-18 design). Sections, in order: navy header band with a blue accent rule,
Executive Summary band (the `footer` renders as a status chip top right: green when it starts "No"/"Nothing", amber otherwise, so write it short and without a period; points carry a coloured dot and lead: Decided/Also agreed green, Shipped navy, Still open amber), Forum recap (Objective, Outcome callout, TL;DR), **Decisions made** as cards
(Decided chip + topic chip, then Rationale / Owner rows), **Action items** table (owner initials
avatars, a dashed avatar for Unassigned, a "From meeting chat" chip, grey "No date"), **Topics
discussed** as cards (title, summary, owner avatar, status chip, then Label / Explanation rows),
**Open questions and risks** as a numbered list with a next-step chip, **Artifacts referenced** as two-column icon cards (always
linked), the speakers line, and the navy **What Enterprise Architecture shipped** panel with a gold rule,
a delivery count, and a category chip per item. Section titles carry a count badge. Palette: `#17375E`
navy, `#2A9FD6` accent, `#DFD4B8` gold, `#E8F0F7` light, `#1F2A37` body, `#5F6670` muted, `#0B5CAD`
links, `#D7DEE6` borders; chips green / amber / gray / blue. Every colour is a named constant in
`render_page.py`.

**What SharePoint really does to this markup (measured 2026-09-28, throwaway page, then the live
draft):** it KEEPS `<style>`, `class=`, `display:flex|grid`, `border-radius`, `font-family`; it
silently STRIPS `gap` and `grid-template-columns`; and its page CSS OVERRIDES `margin` on `<div>` at
render time (stored, not applied). Text inside a `<div>` does NOT inherit that div's `color` or `font-size` either (the action table header rendered dark-on-navy and the rows at ~17px): set colour and size on the text's own `<span>`/`<p>`. Real `<table>` cells get forced dark gridlines, so tables are built from flex `<div>` rows. Inline `<svg>` icons survive and render (artifact cards). Two-column card layouts = `flex-wrap` with 50%-wide cells padded apart. So the renderer inlines every style, spaces blocks with padding or
`spacer()`, and builds two-column rows from fixed-width flex children. `render_page.py` refuses
`gap:`, `grid-template` and any `<div>` margin, so this cannot regress. Storage is not proof: always
screenshot the read view after a renderer change (browser-control, scroll to each heading).

**Print (Save as PDF), measured 2026-09-28:** SharePoint fixes the body height, so a long page printed ONE page. The renderer opens every body with `<div class="aw-recap">` plus a print-only `<style>` (`PRINT_CSS`): it resets html/body so the issue flows, keeps cards whole (`page-break-inside`) and starts the shipped panel on a new page. `validate()` refuses a body without it. SharePoint's sanitizer strips `:has()`, `@page`, `break-*` and `print-color-adjust` on save, so the page cannot force backgrounds to print. Instead a print theme (Alex, 2026-09-28) turns dark bands white with a navy border and navy text, so the page reads the same with or without **Background graphics**. Any new light-on-dark element needs a print-theme class (`aw-band`, `aw-inv`, `aw-olive`, `aw-avatar`, `aw-tint`, `aw-rule`). Check a change on the SAVED draft (CDP `Page.printToPDF`, with `emulateMedia` cleared), never only on an injected DOM.

New optional content fields (see the `render_page.py` docstring): `decisions[].chip`,
`actions[].source: "chat"`, `topics[].owner`, `topics[].points[] = {lead, text}`,
`open_questions[] = {text, next, source}`, `shipped.items[].category`, `artifacts[] = {label, url,
note}` (url required).

**Fonts default to the site theme** (Segoe UI). A `font-family` is allowed when a design change
calls for one; it is no longer banned.

### The SharePoint editor does not show this page faithfully (measured 2026-09-18)

The read view renders fully styled; **144 of 147 inline `style` attributes survived an edit and save,
including the navy band's `background-color`.** The editor's own view drops backgrounds, borders and
heading sizes while leaving them in the stored page. So:

- **Never judge this page in edit mode.** Use Preview or the read view. Tell Alex this when he edits a
  page; it will look broken and he will say so.
- **A `class=` attribute in a read-back canvas is SharePoint's, not drift.** `render_page.py
  --check-only` validates the RENDERED canvas; do not "fix" what SharePoint adds on save.
- The page's inline styles are durable across edits, so it is safe for Alex to edit by hand. There
  is no `<table>` on the page any more (the action table is `<div>` rows).

### Visual verification — the run can look at the page itself

A read-back proves storage, not appearance. Use the **`browser-control` skill** to see the rendered
page: it drives Alex's own Chromium browser with his profile and cookies, so SharePoint renders
authenticated. The OpenCode `tools.browser.*` catalog needs the desktop app plus an experimental
setting and is usually unavailable.

Two gotchas that cost real time on 2026-09-18:

- **`fullPage: true` does not capture the whole page.** The scroll container is inner, so a full-page
  shot matches a viewport shot. Scroll the container instead:
  `await page.getByRole("heading", { name: "Topics discussed" }).scrollIntoViewIfNeeded()`, then take
  viewport shots.
- **`page.goto` churns through SharePoint's auth redirect query strings** before settling on the real
  URL. Wait, then read `page.url()`; a noisy redirect chain is normal.

**When to run it:** mandatory whenever the renderer or the page layout changed, and once before Alex's
first publish of a new format. A content-only week does not need it. Always hand Alex the link anyway;
his eyes are the final check, and he catches things the shot does not.

### The page title area is hidden

The navy band carries the page title, so the SharePoint title must not repeat above it. **Verified
2026-09-18:** a page storing `LayoutWebpartsContent = [{"controlType":0}]` shows no title region (the
09-16 page rendered with the navy band first); the default (`null`) renders the title twice.
`stage_news_recap.py` sets the field by default and exits non-zero if it did not stick. If a staged
draft shows a duplicated title, report it; the fallback is to drop "Architecture Weekly" from the
band, never to accept the duplicate.

**This skill is shared between tools; the scripts it calls are not.** `stage_news_recap.py` exists
once per tool, and the copies drifted before: the title region was added to one only, so a Pi or
OpenCode run staged a page with a duplicated title and said nothing. Both carry `--hide-title` and
its verification as of 2026-09-19. Check the copy your tool runs before trusting any script claim in
this file; `auth.py` and `sharepoint_api.py` still differ between the trees, which is open and
belongs to Alex.

**Sources — reuse the run's retrieval sweep, never double-fetch:** the ADO control first (items in EA
areas closed this week, grouped by their EA Projects row, and the approved weekly epic updates), the
run's own WRITTEN / UPDATED / COMMENTED changes (a row that changed stage this week IS news), the
AAB decisions, direct GitHub retrieval
(`gh search prs --author "@me" --updated ">=$SINCE"`), ADO epic/feature movement, and verified
artifacts from the archeologist. The archeologist does not give a complete GitHub feed; query GitHub
directly. Same auth preflight as everything else.

**Portfolio movement** (Alex, 2026-10-10): every board entry that changed stage this week goes in the
content key `portfolio_moves` (`[{title, from, to, url}]`, at most 8; see the `render_page.py` docstring).
Read the moves from the list's version history or the run's own approved `E#` stage lines, never from
memory. No moves: leave the key out, and the section is not rendered. Each move is a review line
(`Row` = `Recap page`, `Field` = `portfolio move`).

**What leads the page: evidence decides each week** (Alex, 2026-10-09: the board holds everything,
the newsletter "can focus on the things that matter"). Rank the week's items in this order, and use
the same order every week so the choice is repeatable: (1) a decision waiting on leadership; (2) a
forum decision; (3) an EA Projects row that moved Status; (4) a progress number that moved; (5)
closed ADO work, grouped by its row. The Executive Summary and the shipped panel take the top items.
Everything else stays on the board and in ADO, not on the page. Put the ranking in the review table's
`Why` cell for each shipped line, so Alex sees why an item led.

**Shape:** the shipped panel is the navy band with a gold top rule and a delivery count, as the
renderer builds it. Add 3–6 items; a thin week gets 2 or none. Each item contains:
- A `category` (Process, Infrastructure, AI tooling, Data, ...), shown in small caps beside a gold
  check square.
- One outcome-first sentence, ≤ ~20 words, exec-legible in the voice of `NextMilestone`, rendered
  bold navy. No session IDs, ticket IDs, or technical provenance.
- One or two evidence links, rendered as bordered link buttons with an arrow, pointing at the
  primary org-readable record: merged PR, closed ADO item, portfolio row, the RFC/ADR this work
  resolves into. Labels describe the destination (`Runtime migration`, `Portfolio outcome`), never
  raw URLs or naked IDs; the recap's **Artifacts referenced** section follows the same rule — see
  [references/recap.md](references/recap.md).

### Readership — report it to Alex every run (Alex, 2026-10-09)

People read this page, so watch the trend. Every run, read views and unique viewers for the last
three published issues and put them in the run record for Alex only, never on the page.

**Verified 2026-10-10 with the curator's cookie:** the SharePoint search API returns the counts.

```
GET /sites/Architecture/_api/search/query
    ?querytext='path:"https://attainfinance.sharepoint.com/sites/Architecture/SitePages/Recaps" FileExtension:aspx'
    &selectproperties='Title,Path,ViewsLifeTime,ViewsLifeTimeUniqueUsers,ViewsRecent,ViewsRecentUniqueUsers'
    &rowlimit=50&trimduplicates=false
Accept: application/json;odata=nometadata
```

Read `PrimaryQueryResult.RelevantResults.Table.Rows[].Cells` (Key/Value pairs). `ViewsLifeTime` is
views, `ViewsLifeTimeUniqueUsers` unique viewers; the `ViewsRecent` pair is a short recent window.
Search counts lag (a page published days ago can still show recent views only), so compare issues of
similar age. Baseline on 2026-10-10: 66 to 79 unique viewers and 90 to 145 views per issue from
2026-07-29 to 2026-09-30. **Do not use Graph or `_api/v2.1` `itemAnalytics` with the cookie:** it
returns 403 `OAuth only flow is enabled` (tested 2026-10-10). If search fails, report UNVERIFIED,
never zero.

### Planned absence — skip, with a one-line note (Alex, 2026-10-09)

When Alex says he will be out, there is no weekly run for those weeks. Before he leaves, stage one
short News post saying when Architecture Weekly is back (`Architecture Weekly is back on <date>.`),
with the date he gives, `PromotedState=1`, for him to publish. It is the one page not built by
`render_page.py`: one sentence of plain text, no styling. The board and ADO wait for his return.

### Executive Summary — the ELT reader's gate (new 2026-09-18)

**Why it exists:** the executive leadership team reads this page, was not in the room, and does not
know the project vocabulary. The band answers "what did this mean, and does anyone need me?" in the
first ten seconds.

Generated by the run, and it is the **highest-scrutiny line in the whole review table**:

- **`headline`** — one sentence, plain words: what was decided and what it changes, in the voice of a
  `NextMilestone`. No acronym or codename a non-engineer would not know; gloss any unavoidable term.
- **`points`** — 3 to 4, each a bold two-or-three-word lead plus one or two plain sentences. Cover
  **both halves of the week: what the forum decided, and what EA shipped.** Order: decisions, then
  shipped, then still open, with the footer's ask last (the order of the published 2026-09-16 issue).
  Shipped goes before "Still open", so the delivery is not pushed below the asks. *Why it matters* beats *what was configured*. Do not restate the TL;DR.
- **Composition rule: the summary is a roll-up, nothing new.** Every sentence must trace to a decision,
  an action, an open item, or a shipped item already on the page. A stated **consequence** of a
  documented decision is fine ("rotating a credential no longer needs a code change"); a new fact,
  judgement, or recommendation is not. If the summary needs a fact the recap lacks, the recap is
  missing it, not the summary.
- **Compress the shipped half to one line; never list the shipped items.** The navy panel already
  lists them; a full list in the band makes the reader read the same nouns twice. Name the headline
  delivery and the theme of the rest (`The new US brand's non-prod network went live, and the Claude
  and Snowflake tooling picked up three more deliveries.`).
- **`footer`** — the line that says whether leadership must act: `No decision is waiting on
  leadership this week.` or the named decision and the person holding it. Never blank, never silence a
  real pending decision. `Still open` covers EA-internal loose ends; the footer covers leadership.
  Keep both.
- Put it through the review table as its own numbered line (`Row` = `Recap page`, `Field` =
  `executive summary`). Never stage a page with an unreviewed summary.

**Gates (all mandatory):**
- **Scope is EA's own delivery, and the heading says so:** **What Enterprise Architecture shipped**,
  never "What Architecture shipped" (corrected 2026-08-28; bare "Architecture" reads as every
  architect in the company). Include only work EA owns or drove: Alex-authored PRs, EA-owned ADO
  epics/features, EA board rows that moved, EA-authored artifacts. Another team's delivery does not go
  in, however good it is.
- Full exclusion screen applies to the sentence and every linked artifact: no privileged/counsel
  references, sensitive vendor naming, current-weakness specifics, personnel, personal-OneDrive
  links, or access-restricted evidence. If no safe evidence link exists, drop the item.
- **Every number and every "each" in a shipped sentence is checked against the live list, not the
  plan.** Count from the dump you already pulled; if a column is partly blank, the sentence cannot say
  "each".
- Put each complete item through the review table as one line (`Row` = `Recap page`, `Field` =
  `shipped item`), with the exact sentence, link labels, and target URLs. Apply only approved lines
  and re-screen anything Alex edits.
- Stage with `--stage` / `PromotedState=1`; publishing stays Alex's click. `stage_news_recap.py` needs an existing page `--id`: for a new week, create a blank page first with `sharepoint_api.create_page(site, title)` and pass its `Id` (done for the 09-23 page, Id 61). Never re-stage a page whose
  `FirstPublishedDate` is set, because that demotes a live News post.
- Build the delivery-only draft, flagged as carrying no forum record, ONLY when the forum genuinely
  produced nothing to recap: no scribe note exists and Alex pasted no notes. A note you have not
  looked for is not an absence.

## Weekly maintenance mode (`--maintain`, and the default for a bare `/ea-projects-curator`)

A bare invocation runs this mode; only `--audit` (or "is the board missing anything?") widens to discovery. Skip discovery of new initiatives; true up what exists, and still gate every change through the review table:

1. Run the **Weekly AAB control** above and report it before any EA Projects finding.
2. If the latest due forum has no published recap, **read that session's scribe note and draft the recap now** ([references/recap.md](references/recap.md)), and carry it into the same review table: a missing recap is work, not a line item. If the note itself is missing, tell Alex to run `/scribe teams` for that date. A past-dated `Scheduled` item plus a real note means the close-out was missed, not the meeting.
2a. Run control check 3a: write the forum advice back into the brought documents ([references/brought-docs.md](references/brought-docs.md)) as `D#` lines.
2b. Run the **Weekly ADO control** and emit its `W#` lines, including the update comment for every active epic, before any EA Projects check.
3. Diff `Status` / `NextMilestone` / `MilestoneDate` against the latest archeologist / ADO / GitHub signals; propose moves.
4. Flag any `MilestoneDate` more than 7 days past due: a stale board is evidence against you.
4a. Flag any `4. Delivered` row whose Impact still carries `Target:` — delivering requires documented impact. Flag any row from `2. Committed` on with a blank Sponsor.
5. Flag `2. Committed` rows older than 30 days with no Active epic and no build evidence: commitment rot, surface for the 1:1.
6. Flag `1. Exploring` rows not updated in ~6 weeks: propose "take it to the AAB, keep exploring with a date, or stop". Flag every Exploring row that hits a trigger (board-to-AAB flow) and has no AAB item.
6a. For every linked AAB item that reached `Decided`, `Parked` or `Deflected` since the last run, propose the stage move it supports (`2. Committed` or `5. Stopped`) as its own **Needs you** line.
7. Flag any `4. Delivered` or `5. Stopped` row whose Milestone is not `Delivered` or `Stopped: …`, or whose Milestone date is blank. Flag any row with a blank `EARole`.
8. Flag rows whose promise is contradicted by a ticket or fresher comms: a milestone in days with a ticket still `New`, or a review already sent — understating done work is as bad as overstating it.
9. Flag any `3. Delivering` row with empty Impact + milestone + artifact; the emptiest row is the one readers click.
10. For a meaningful weekly signal with no column change, propose a comment (see Comments) rather than forcing a field move; read existing comments first to avoid repeats and catch replies.
11. Re-surface every unresolved ledger `open_items` entry.
12. Last, after the review tables are built, run the [Connections pass](#connections-pass--ideas-after-the-review-tables) and emit the `I#` table at the end of the report. Record Alex's Act / Park / Drop answers in the ledger `ideas` key.

## Full audit mode (`--audit`, or "is the board missing or misrepresenting anything?")

Discovery + maintenance combined: parallel retrieval (live list + ADO saved query + 8-week archeologist sweep), then the three-way cross-check (missing / misrepresented / coherence), then everything — new rows, field fixes, comments, theme moves — in ONE review table. Lead with any coherence problem; rows that check out clean get said so explicitly. Then run the [Connections pass](#connections-pass--ideas-after-the-review-tables), last.

## Output — the record

After the gate and the write, emit four markdown tables so the run is auditable:

1. **WRITTEN** — new rows and new ADO items: all columns or fields + the new Id/URL.
2. **UPDATED** — row or work item title + each changed field or link (old → new).
3. **COMMENTED** — row or epic title + the exact comment text posted.
4. **EXCLUDED** — every rejected candidate + the one-line gate that killed it (`privileged` / `attendance` / `sub-initiative` / `scope-claim` / `personnel` / `vendor-sensitive-unresolved`), so the screen is auditable and over-aggressive filtering is caught on review.

## Safety recap

Org-visible list. The review table is the mandatory gate. Never invent initiatives or impact figures — empty beats soft. Never write an unconfirmed row or comment; never move `Status` without an explicit yes on that line. Screen every candidate, every edited title, and every comment's text. Comments: plain text, no @-mentions, append-only. Check `not_doing` before proposing rows. Flag personal-OneDrive artifact links instead of publishing them. Never touch list or site permissions. Never copy a document into the library that fails the exclusion screen or whose sharing scope is unverified: a restricted copy gives the whole org access. Never write the author's response column, never edit an Accepted ADR, never send the author message. Connections pass ideas are hypotheses for Alex only: never write one to a list, page, ADO item, comment or the newsletter; an idea he marks Act becomes real lines in the next run's tables.

ADO carries the same stakes, because every Information Technology board is readable by the whole org. Every ADO write is an approved `W#` line. Never move `System.State` on an item assigned to someone else; report it instead. Never delete a work item, and never change an area, iteration, process rule, or permission. Epic comments are plain text, no @-mentions, append-only, at most one weekly update per epic, and they pass the exclusion screen.

The recap carries the same stakes plus one risk: it comes from a verbatim transcript of a room that speaks freely about live gaps, vendors and people. **Quote nothing the exclusion screen would block as a board row.** Attribute only what a named person said; never publish a garbled proper noun, promote uncontested discussion into "Decided", or invent an owner or date. The recap goes out staged (`PromotedState=1`) for Alex to publish; any unsure line belongs in the review table as its own question, not softened onto the page.
