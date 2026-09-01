---
name: ea-projects-curator
description: >
  Curate, update, or audit Alex's EA Projects SharePoint board (EA Portfolio) and AAB operating
  surfaces on /sites/Architecture. Use for board population, weekly maintenance, full audits, row
  comments, AAB Intake close-outs, forum checks, Architecture Weekly recap creation, or requests to
  recap an Architecture Review Forum or AAB meeting. Finds the Architecture Advisory Board calendar
  event, pulls and verifies its Teams transcript, drafts the structured forum recap and the
  evidence-backed "What Enterprise Architecture shipped" section, checks that due recaps are
  published, closes due intake items, and flags an empty next-week schedule. Collects evidence from
  ADRs, ADO, GitHub, prior sessions, and Microsoft 365. Requires a numbered user-review table before
  any org-visible list write; recap pages are staged as drafts for Alex to publish.
---

# EA Projects Curator

Turn the scattered evidence of what Enterprise Architecture actually did — prior AI sessions, ADRs/SADs, ADO epics, GitHub PRs — into a small set of executive-legible rows on the EA Projects board. You are a **filter and transformer**, not a retriever and not a scribe: you receive raw signals, decide what qualifies, shape it for a non-architect CTO, and then **ask** before you write.

```
Teams transcript ─→ recap ─→ verify vs transcript ─→ docs-reviewer ─→ fix ─→ STAGE ─→ hand back link
archeologist     ─┐
ADO + GitHub     ─┴─→ curate: cluster · screen · shape ─→ REVIEW TABLE ─→ write ─→ report
                       (board rows, intake, comments)     (approve by line)
```
The recap goes straight to a staged SharePoint draft; only board/intake/comment writes wait on the
numbered table. Never paste the recap into the terminal.

**Every weekly run owes TWO deliverables, and the board is the SECOND one.** The first is that week's **Architecture Weekly** News page (`SitePages/Recaps/YYYY-MM-DD-AAB-Recap.aspx`; keep this filename for cadence compatibility): the **Forum recap** component plus the generated evidence-backed **What Enterprise Architecture shipped** panel, staged as an unpublished draft with `PromotedState=1` set via CSOM. Hand Alex the link; he publishes org-visible comms himself. Gather evidence once, compose both components, use one review table, and stage once. A plain publish without `PromotedState` never reaches the Home News rollup, which reads exactly like the update never happened. Missed on the 2026-07-28 run; see memory `arf-notes-two-deliverables`.

**The Forum recap component is GENERATED from the Teams meeting transcript by default** — you fetch the transcript yourself, you do not wait for Alex to paste notes. See **Forum recap — generate it from the meeting transcript** below for how to find the meeting, pull the transcript, and the exact recap prompt. Two overrides: if Alex pastes his own forum notes, render those **verbatim** instead (his text always wins over your generated recap, per the template in the SharePoint agent doc — `~/.claude/agents/sharepoint.md` for Claude Code, `~/.pi/agent/agents/sharepoint.md` for Pi); if no transcript exists and he pasted nothing, build the delivery-only draft and say plainly that it carries no forum record.

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

**Auth preflight FIRST (2026-08-10 lesson):** before any retrieval, check the cookie cache age —
`stat -f %m ~/.claude/scripts/sharepoint/.cookies.json` vs `date +%s`; TTL is ~7h. If it's older
than ~6h, ask Alex to run `python3 ~/.claude/scripts/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/Architecture" --refresh`
NOW and run the live-list read + writes after he confirms — while retrieval (ADO/GitHub/archeologist
sweeps) runs in parallel. Reactively discovering a 403 after the sweep wastes the whole run.

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

## Weekly AAB control — the second operating surface

Alex curates a second list alongside the EA Projects board: **AAB Intake** (the Architecture Advisory Board forum queue), plus the weekly **AAB Recap** News post (the "newsletter" — you generate its forum recap from the meeting transcript, and publishing the page stays Alex's action). This control runs **first**, before any EA Projects check, in both `--maintain` and `--audit`.

- **AAB Intake list:** `https://attainfinance.sharepoint.com/sites/Architecture/Lists/AAB%20Intake/AllItems.aspx`, GUID `80c68e54-eadf-4cf3-946a-3c0e432056a5`, entity `SP.Data.AAB_x0020_IntakeListItem`. Fields: `Title`, `Status` (`New` / `Triaged` / `Scheduled` / `Decided` / `Parked` / `Deflected`), `Scheduledfor` (DateTime stored as **DateOnly**), `Outcomenotes` (text), `Modified`.
- **Recaps folder:** `/sites/Architecture/SitePages/Recaps` — page name pattern `YYYY-MM-DD-AAB-Recap.aspx`. Browse view: `https://attainfinance.sharepoint.com/sites/Architecture/SitePages/Forms/ByAuthor.aspx?id=%2Fsites%2FArchitecture%2FSitePages%2FRecaps&viewid=a74d565d%2Da0da%2D444e%2Daae0%2D092bef143ca8`.
- **Timezone/week:** read SharePoint `RegionalSettings/TimeZone` live; verified 2026-08-10 as Central Time (America/Chicago). A calendar week is Monday–Sunday. If the site timezone no longer maps to America/Chicago, report UNVERIFIED instead of guessing date boundaries.

## Forum recap — generate it from the meeting transcript

The forum's own record is the Teams meeting transcript. Fetch it and write the recap yourself; do
not wait for pasted notes. Verified end-to-end 2026-08-28 against the 2026-08-26 forum.

### Step 1 — find the meeting (calendar, not SharePoint)

The M365 connector tools are deferred: load them first with
`ToolSearch("select:mcp__claude_ai_Microsoft_365__outlook_calendar_search,mcp__claude_ai_Microsoft_365__read_resource")`.

**The calendar subject is `Architecture Advisory Board`, NOT "Architecture Review Forum."** Searching
the forum's public name returns zero events and reads like the meeting never happened. Search the
real subject, or use `query: "*"` with a one-day `afterDateTime`/`beforeDateTime` window around the
session date and pick it out of the day's events.

The forum runs **Wednesdays, 3:00–4:00pm Central** (verified cadence across 8 sessions), organizer
Alex, location Microsoft Teams Meeting. It regularly runs over; the 08-26 session ran 85 minutes.

### Step 2 — get the transcript URL from the event

`read_resource` on `calendar:///events/{eventId}` returns a **`meetingTranscriptUrl`** field. Pass
that value **verbatim** to `read_resource`. It looks like
`meeting-transcript:///events/{base64urlJoinUrlToken}?start={iso}&end={iso}` — the `start`/`end`
params scope a recurring series to the one occurrence. **Keep them.** Drop them and you get the most
recent transcripts of the whole series, capped, and you will summarize the wrong meeting.

### Step 3 — expect the response to be too big, and parse it

The transcript comes back as JSON (~114KB for 85 minutes), which exceeds the tool output limit, so
the harness saves it to a file and tells you the path. Do NOT `Read` that file: it is one enormous
line and offset/limit will not help. Parse it with python.

Shape: `{"meeting": {...}, "transcripts": [{"createdDateTime", "endDateTime", "content"}]}` where
`content` is WEBVTT with `<v Speaker Name>text</v>` cues.

> **The outer `meeting.startDateTime` is the SERIES start date, not this occurrence.** On the 08-26
> run it read `2026-07-08`. Confirm which session you actually have from
> `transcripts[].createdDateTime` / `endDateTime`, never from the outer object.

Parse into a readable transcript before reasoning over it: extract each cue's timestamp, speaker and
text, then **merge consecutive cues from the same speaker into one turn**. Teams emits one cue per
breath (729 cues collapsed to 409 turns on 08-26), and unmerged cues read as noise.

Use the bundled parser rather than rewriting it:

```bash
python3 references/parse-teams-transcript.py <saved-raw.json> <out.txt>
```

It prints the occurrence window, cue/turn counts and speaker list to stderr so you can confirm you
have the right session, and warns if you got the whole series instead of one occurrence. **Then read
the output file in full before drafting** — the recap has to be faithful, so do not summarize from
grep hits. The speaker list is also your attendance line; it is who actually spoke, which is not the
same as who was invited.

### Do not chase the OneDrive recordings

`~/Library/CloudStorage/OneDrive-Attainfinance.com/Recordings/` holds
`Architecture Advisory Board-<YYYYMMDD>_<HHMMSS>UTC-Meeting Recording.mp4` files, and they are a
dead end for transcription: **every AAB recording has no audio stream at all** (verified with
`ffprobe -select_streams a` across all 8; they are video-only static screen-shares, ~1.4MB for 85
minutes). There is no `.vtt` on disk and `sharepoint_search` does not index the transcripts either.
The connector path above is the only working route. Do not offer local transcription as a fallback.

### Teams garbles proper nouns — verify or omit, never publish a guess

Auto-transcription mangles names, and a garbled proper noun in an org-visible post is worse than no
noun. Observed on 08-26: `loose chart`/`LCLC` → Lucidchart, `fire monitor`/`fire money`/`fire mall`
→ FireMon, `Avanti`/`Vivanti` → Ivanti, `SC` → SE, `ADL` → ADO, `Creo` → CURO, `five nine` → Five9,
`Broz book` → the feature-flag system (still unidentified — so it stayed unnamed in the recap).
Correct only what you can confirm; otherwise describe the thing without naming it. The transcript
may also end mid-sentence, as 08-26 did. Say so in the recap footer rather than inventing an ending.

### The recap prompt (Alex's wording — use it as-is)

> Create a shareable post-meeting recap for the Architecture Review Forum. Be concise and factual —
> pull only from what was actually said. Use this exact structure and these headings:
>
> **Architecture Review Forum — [Meeting Date]**
> Put the actual meeting date on this header line.
>
> **Objective** — 1-2 sentences: what this session set out to accomplish.
>
> **Outcome** — one line stating whether the objective was met: [Achieved] / [Partially achieved] /
> [Not achieved], followed by a one-sentence why. If the objective was never clearly stated, write
> "No explicit objective set" and infer the de facto purpose from the discussion.
>
> **TL;DR** — 2-3 sentences: the most important thing that happened and what it means for the group.
>
> **Decisions Made** — a table with columns: Decision | Rationale | Owner. Include only firm
> decisions, not discussion. If none, write "No formal decisions this session."
>
> **Action Items** — a table with columns: Action | Owner | Due (if stated). List every commitment
> made, with the named owner. Mark owner as "Unassigned" if no one was named.
>
> **Topics Discussed** — one bullet per topic. For each: a one-line summary, then the outcome tag in
> brackets — [Decided], [Needs follow-up], or [Parked]. Keep each to two sentences max.
>
> **Open Questions / Risks** — bullets for anything raised but unresolved, including who needs to
> weigh in to close it.
>
> **Artifacts Referenced** — list any docs, decks, diagrams, or links mentioned, with the file name.
>
> Rules: Attribute decisions and actions to the specific person who owns them. Do not invent owners
> or dates. Skip pleasantries, tangents, and status updates that led nowhere. Write in plain, direct
> prose — no filler like "the team discussed the importance of." Keep the whole recap under one
> screen.

Load the `alex-voice` skill (comms register) before drafting: this is internal comms in Alex's name.
No em dashes.

### Recap gates (on top of the prompt)

- **The full exclusion screen applies to every line of the recap**, same as board rows. The forum
  discusses live security detail; the recap is org-visible. Keep it effect-side: never name a
  specific exposed endpoint, a live unremediated weakness, vendor-commercial posture, or personnel
  criticism. Where a topic cannot be described safely, drop it and tell Alex why in your report
  rather than softening it onto the page.
- **Decision versus discussion is the highest-risk call.** Promoting an uncontested assertion into
  "Decided" misleads everyone who reads it. If Alex asserted a scope boundary and nobody objected,
  that is not the same as the group deciding; say what actually happened. When the session ends with
  "let's circle back next week," the Outcome is at best [Partially achieved].
- **Never invent an owner or a due date.** "Unassigned" and "Not stated" are correct answers.
  Attribute to the person who actually spoke the commitment.
- **Do not print the recap into the terminal.** Alex does not read it there, and a 1,300-word page
  pasted into a CLI is noise. Generate it, verify it against the transcript, run `docs-reviewer`,
  address the findings, stage it to SharePoint, and hand back **the link plus a short summary of
  what you fixed**. The staged draft is the review surface: he reads it rendered, where the layout
  problems are actually visible, and clicks Publish there. Reading back the stored
  `CanvasContent1` is not a substitute for him seeing it.
- The recap therefore does **not** go through the numbered review table line by line; staging it is
  safe because `PromotedState=1` is a draft nobody else sees, and he approves by publishing. What
  still goes in the review table: **intake close-outs, board rows, comments, and any recap judgment
  call you could not resolve yourself** (a confidentiality trade-off, a finding that conflicts with
  a house rule, a decision-versus-discussion call you are not sure about). Everything else you fix
  and report.
- A generated recap also gives you the real `Outcomenotes` for that session's AAB Intake items and
  the evidence to close them out. Propose those as review-table lines too, never write them blind.

### Verify the draft against the transcript before showing it to Alex

Every one of these was a real error in the first generated recap (2026-08-26), caught by an
adversarial pass, not by re-reading. Run the check; do not trust the draft.

- **No spoken name means Unassigned.** "Take one person from your team and ask them to try it" said
  to the room is not an assignment to the four managers you infer were present. Never derive an
  owner from who attended, who runs a team, or who the ask logically lands on. Only a name actually
  spoken in connection with the commitment becomes an owner.
- **Read the turns AFTER an apparent decision before recording it.** A scope boundary Alex states
  can be reversed in the very next turn. In the 08-26 draft "firewall changes stay out of ITCC" was
  recorded as decided while the next speaker offered to move firewall tracking IN and drop the
  separate product, which made the recap contradict itself.
- **Cross-check the Decisions table against the Action Items table.** If a row says something is
  settled and an action item says someone is looking into changing it, one of them is wrong. That
  contradiction is the cheapest error to catch and the most embarrassing to publish.
- **Conditional agreement is not agreement.** "I agree, but it still needs X" is a condition; carry
  the condition or do not claim the agreement.
- **Driving the screen is not authorship.** Alex demoing someone's ticket does not make it his, and
  someone answering questions about their own artifact did not necessarily present it.
- **Never stitch two remarks into one quote.** If the phrasing spans utterances minutes apart, write
  it as prose, not as a quotation.
- **Carry the counter-evidence, not just the loudest thread.** A recap that reports only the
  pushback misrepresents the room. The 08-26 draft omitted the emergency change type, the fact the
  ticket never blocks the work, and that PCI already requires recording cardholder-environment
  changes; all three narrow the overhead objection it led with.
- **A speaker with no visible contribution is a smell.** Diff the transcript's speaker list against
  the names appearing in the recap. On 08-26 that gap hid the originator of an action item, credited
  to Alex instead. Either credit them or knowingly decide they added nothing.
- **Leadership criticism goes ownerless.** "Rick asked me why we didn't know before they did" names
  a senior leader challenging a named manager over a security miss. Keep the question, drop the
  people: "leadership has asked how we catch this ourselves."

Cheapest reliable form of this check: spawn independent verifiers with distinct lenses (attribution,
numbers and quotes, decision-versus-discussion, omissions and confidentiality), each given the
transcript path and told to find errors rather than approve. Fix what they confirm, and tell Alex
what you changed and why.

### Then run `docs-reviewer`, and address everything, before it goes anywhere

**Mandatory, every recap, no exceptions.** Transcript verification proves the recap is *true*;
`docs-reviewer` proves it is *readable*. They catch different things: the adversarial pass never
noticed that the Decisions table claimed four decisions while Topics Discussed tagged zero as
`[Decided]`, and it never noticed the recap was three times its own stated length limit.

Run it via the Skill tool (`attain-docs:docs-reviewer`) against the assembled page content, not the
markdown draft, so the shipped panel and the rendered structure are in scope. Then **fix every
BLOCKER and SIGNIFICANT finding before staging.** Do not hand Alex a review and ask what to do with
it; he asked for the finished thing. Bring him a decision only when a finding conflicts with an
established house rule (see the em-dash exception below) or when fixing it would change what the
meeting actually decided.

Known findings this review reliably surfaces on a first draft, so pre-empt them:

- **Outcome tags must actually vary.** If every topic is `[Needs follow-up]`, the tag carries no
  information. Any topic matching a Decisions row is `[Decided]`; make the tables and the tags agree.
- **Every Decisions row needs a matching topic bullet**, or the decision only exists in a table
  nobody reads twice.
- **Honour the "under one screen" line in the prompt.** A faithful record of a 90-minute meeting will
  not hit 400 words, but it should not hit 1,500 either. Merge topics that are one thread (the
  release model and the approval gap are the same story), and fold an open question into the topic
  that already covers it rather than saying it twice.
- **Do not bold both the topic lead-in and the tag** on every bullet. That is the inline-header
  vertical-list tell (humanizer 15 and 16). Lead-in bold, tag in muted Deck Slate.
- **Do not repeat "Not stated" down a whole column.** Leave the cell empty and put one footnote under
  the table.
- **Keep attribution out of the action text.** "Proposed by X" belongs in the Owner cell.

> **Documented em-dash exception.** `docs-reviewer` flags every em dash as a BLOCKER, and the
> humanizer rule behind it is correct for prose. The `<h1>` title is the one allowed exception:
> `Architecture Weekly &mdash; Month D, YYYY` is the house format, fixed by the template and by
> Alex's own recap prompt, and eight published issues already use it. Keep it there and keep prose
> free of them. Do not re-litigate this every week; note the exception in your report and move on.

## Weekly newsletter — Architecture Weekly

Every weekly page carries TWO components under the title **Architecture Weekly — Month D, YYYY**.
Component 1 is the **Forum recap** (generated from the transcript per the section above, or Alex's
pasted notes rendered verbatim when he supplies them). Component 2 is the generated **What Enterprise
Architecture shipped** panel at the bottom. They answer different questions: the forum record says
what the group decided; the delivery panel says what EA shipped. Drop any delivery item that
restates the forum recap.

**Sources — reuse the run's retrieval sweep, never double-fetch:** the curation run's own WRITTEN /
UPDATED / COMMENTED changes (a row moved to Decision-Ready this week IS news), direct GitHub
retrieval (`gh search prs --author "@me" --updated ">=$SINCE"` plus commit lookup when needed),
ADO epic/feature movement, and verified artifacts found by the archeologist. The archeologist does
not provide a complete GitHub activity feed; query GitHub directly. Use the same auth preflight as
everything else.

**Shape:** use the approved light-blue information surface (`#C9E7F4`), Venice Blue left edge
(`#094682`), dark text (`#1D3E50`), and Deck Slate evidence text (`#325477`). Add 3–6 items; a thin
week gets 2 or none. Each item contains:
- One bold, outcome-first sentence, ≤ ~20 words and exec-legible in the same voice as
  `NextMilestone`. No session IDs, ticket IDs, or technical provenance in the sentence.
- An `Evidence:` line with one or two descriptive, underlined Venice Blue links. Link directly to
  the primary org-readable record: merged PR, closed ADO item, current portfolio row, ADR, or
  equivalent artifact. Labels describe the destination (`Runtime migration`, `Portfolio outcome`),
  never raw URLs, `click here`, or naked IDs.

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
- Put each complete item through the review table as one line (`Row` = `Recap page`, `Field` =
  `shipped item`), including the exact sentence, link labels, and target URLs. Apply only approved
  lines and re-screen anything Alex edits.
- Stage with `--stage` / `PromotedState=1`; publishing stays Alex's click. Never re-stage a page
  whose `FirstPublishedDate` is already set because that demotes a live News post.
- Build the delivery-only draft, and flag clearly that it contains no forum record, ONLY when the
  forum genuinely produced nothing to recap: no transcript exists (meeting not recorded, or it did
  not run) and Alex pasted no notes. A transcript you have not tried to fetch is not an absence.

**1. Pick the session to verify — dynamically, never a hard-coded weekday.** Use site-local dates. Normally select the latest `Scheduledfor` before today: prefer the current week, otherwise the previous week's latest. Treat a session scheduled for **today** as due only when live evidence shows it has happened (the exact-date recap exists, or an intake item already carries a same-day forum outcome); otherwise label today upcoming/UNVERIFIED and verify the previous session so a morning run does not raise three false alerts. If neither current nor previous week has a date, derive the expected forum date from the cadence of the most recent 3–4 published recap filenames and flag that the intake list has no anchor — don't silently skip the check.

**2. Verify the recap was actually published, not staged.** A filename existing under `Recaps/` is not enough — check the page is real News: `PromotedState=2`, `OData__ModerationStatus=0`, and `FirstPublishedDate` present. `PromotedState=1` is still a draft (see the newsletter section above) — report it as unpublished, don't treat it as done.

**3. Verify every intake item for that session was closed out.** For each item whose site-local `Scheduledfor` date equals the selected session date, require a forum outcome: non-empty `Outcomenotes`, a status other than `New`/`Triaged`, and no past-dated `Scheduled` state. The site-local `Modified` date must be on or after the session date as a sanity check, but it does not prove the exact meeting time. Normal outcome is `Decided`; `Parked`/`Deflected` are valid with explanatory notes. A future re-`Scheduled` item is valid only when item version history or the ledger proves it moved from the selected session date and the notes explain why; otherwise report UNVERIFIED. **Separately, always query and flag every item globally where `Status=Scheduled` and `Scheduledfor` is in the past** — SharePoint's own agenda and decision-log views both hide this state (agenda filters `>= today`, log filters `Status=Decided`), so it's invisible unless this check catches it.

**4. Alert if next calendar week has nothing scheduled.** Check for at least one `AAB Intake` item with `Status=Scheduled` and `Scheduledfor` in `[next Monday, following Monday)`. None found → prominent alert to Alex to schedule the forum or confirm there isn't one. Never auto-schedule or invent a date.

> **Never create an AAB Intake item. Ever.** (Corrected 2026-08-28, after a run proposed one as a
> review-table line and Alex rejected it outright.) The intake list is **the queue people submit
> their own topics to** — it is their to-do surface, not a scheduling table for the curator to
> populate. An empty next week is an **alert only**; it never becomes a proposed row, not even a
> gated one. The curator's writes to this list are limited to closing out items that already exist:
> `Status`, `Outcomenotes`, and `Scheduledfor` on an item somebody else raised.

**Report before EA Projects findings under this exact heading:**

## AAB WEEKLY CONTROL

| Check | Result | Evidence |
|---|---|---|
| Recap published | PASS / ALERT / UNVERIFIED | date, page Id/URL, PromotedState |
| Intake close-out | PASS / ALERT / UNVERIFIED | item Ids/titles still open, with Status/Scheduledfor |
| Next-week schedule | PASS / ALERT / UNVERIFIED | next-week range and items found, or none |

Any unresolved ALERT goes on `curated.json` `open_items` (cleared only after live re-verification) — same idempotency discipline as EA Projects. **Intake field changes are writes to an org-visible list**: propose them through the same numbered review table as board changes, one line per field (`Status` / `Outcomenotes` / `Scheduledfor`), and apply only what Alex approves by line. Never invent `Outcomenotes` text or a `Scheduledfor` date, and never publish the recap yourself — flag it as his action.

## Weekly maintenance mode (`--maintain`)

Skip discovery of new EA Projects initiatives; only true up what exists. Still gate every proposed change through the review table, and write only what the user confirms:

1. Run the **Weekly AAB control** above and report it before any EA Projects finding.
2. If the control shows the latest due forum has no published recap, **fetch that session's transcript and draft the recap now** (see **Forum recap — generate it from the meeting transcript**), and carry it into the same review table. A missing recap is work to do this run, not just a line item to report. The transcript is also the truth-check for whether the forum actually ran: a past-dated `Scheduled` intake item plus a real transcript means the close-out was missed, not the meeting.
3. Diff `Status` / `NextMilestone` / `MilestoneDate` against the latest archeologist / ADO / GitHub signals; propose moves.
4. Flag any row whose `MilestoneDate` is > 7 days past due — a stale board is evidence against you.
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

Org-visible list. The review table is the mandatory gate. Never invent initiatives or impact figures — empty beats soft. Never write an unconfirmed row or comment; never move `Status` without an explicit yes on that specific line. Run the exclusion screen on every candidate, on every title the user edits, and on every comment's text. Comments: plain text, no @-mentions, append-only. Check `not_doing` before proposing new rows. Flag personal-OneDrive artifact links instead of publishing them. Never touch list or site permissions.

The forum recap carries the same stakes and one extra risk: it is built from a verbatim transcript of a room where people speak freely about live security gaps, vendors and each other. **Quote nothing that the exclusion screen would block as a board row.** Attribute only what a named person actually said, never publish a garbled proper noun, never promote uncontested discussion into "Decided", and never invent an owner or a date. The recap goes out staged (`PromotedState=1`) for Alex to publish, and any line you are unsure about belongs in the review table as its own question, not softened onto the page.
