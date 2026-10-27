# ADO ↔ EA Projects schema

How ADO and the EA Projects board line up, and what the curator may read and write on each. Model decided by Alex on 2026-10-09; ADO facts verified live the same day.

## The rule

**The EA Projects board holds what Enterprise Architecture impacts or influences. ADO holds what EA does** (hands-on work).

| Layer | Where | Holds | Answers |
|---|---|---|---|
| **Portfolio** | SharePoint list `EA Projects` | One row per initiative: Title, Theme, Status (display Stage), EA role, AAB items, Impact, KeyArtifact, ExecutionLink, NextMilestone (display Milestone), MilestoneDate, Sponsor | Why, who decides, what it unlocks |
| **Work** | ADO, the EA areas below | Epic, User Story, Spike, Request, Operational Work | Who does it, what state it is in, what moved this week |

Two kinds of row:

- **Delivery row**: EA does the work. One or more EA epics roll up to it.
- **Influence row**: another team does the work (an AAB review, a standard, advice). No EA epic; `ExecutionLink` points to the owning team's epic or document.

## EA areas

The curator sweeps and writes only these area paths in project `Information Technology`:

| Area path | Team | Since |
|---|---|---|
| `Information Technology\Enterprise Architecture` | Enterprise Architecture | 2026-09-16 |

A team's area joins this list only when Alex says its reporting change is official. Until then, never name it as an EA team in any org-visible text.

## The join: a Hyperlink on the epic

Every epic in an EA area carries **exactly one** Hyperlink to its row:
`https://example.sharepoint.com/sites/Architecture/Lists/EA%20Portfolio/DispForm.aspx?ID=<rowId>`.

- **Many epics, one row.** A program with several epics (the 7 SOW epics of the Pinnacle work) rolls up to its rows without one row per epic.
- **Run work rolls up too.** EA itself and each team that reports to EA have one operations epic and row for keep-the-lights-on work. EA's standalone Requests get the **EA operations** epic as parent, so they roll up too (Alex, 2026-10-09).
- **The link lives in ADO only.** A Hyperlink is one-way, so the curator builds the "epics for this row" view from the epics' relations. `ExecutionLink` on the row holds the main epic only.
- **Matching order** for an epic with no link: a row whose `ExecutionLink` is this epic, then epic title vs row title, then the `SOW-<n>` tag vs the row's SOW. Report an ambiguous match; never guess.
- **Recognize a row link by its URL.** Only a Hyperlink whose URL contains `/sites/Architecture/Lists/EA%20Portfolio/DispForm.aspx` counts. Epics carry other hyperlinks (SOW documents, briefs) that are not row links.
- **No link is a finding.** An epic with no row link, or more than one, goes in the ADO control table.

## Verified ADO facts (2026-10-09)

- Project: resolve with `scripts/resolve_ado.py projects`; never carry its id. Team and area: read them from the project's classification nodes. Team `Enterprise Architecture`, area `Information Technology\Enterprise Architecture`, `includeChildren: false`. Item count moves daily (75 in the morning, 97 by the evening); never quote a fixed number.
- **Inherited process** (custom `Information Technology`). Field and state changes are process edits, and the curator never makes them.
- **Read access is org-wide** for all licensed people in Information Technology, so every comment and title is org-visible.
- **Epic states:** `New` · `Active` · `Resolved` · `Closed` · `Removed`, one step at a time.
- **Story states:** `New` · `Ready` · `In Progress` · `Validating` · `Pending` · `Closed` · `Removed`.
- **Required fields per move** (the AAB gate on `Active`, validation on `Closed`): see [write-shapes.md](write-shapes.md#process-rules-the-dry-run-will-enforce-verified-2026-10-09).
- Stories carry `System.Parent` → the epic. Fold every story up; only epics map to rows.

### Epic fields that matter

Reference names carry the org's custom prefix, which is a per-installation fact: resolve each one from `get_type` before you write. The display names below are stable; the prefix is not.

| Field (display name) | Resolved reference | Use for the curator |
|---|---|---|
| `System.Title` | Title | Epic naming, e.g. `SOW 3 · Change control automation` |
| `System.State` | State | Truth-check against the row's `Status` (map below) |
| `System.AssignedTo` | Assigned To | The doer. The board has no doers column since 2026-10-12, so this is where it lives; never maps to *Sponsor* |
| `System.Tags` | Tags | In use: `AI-DLC`, `enterprise-architecture`, `Pinnacle`, `SOW-<n>`, `Wave-<n>`, plus a domain tag |
| `Microsoft.VSTS.Scheduling.TargetDate` | Target Date | The epic's date. The board has no finish-date column since 2026-10-12, so this is where the date lives |
| Current Status | resolved with `get_type` | Picklist: `Not Started`, `Reqts`, `Reqts+Approval`, `Waiting for Dev Capacity`, `Dev`, `UAT`, `Deployment`, `Done`, `On Track`, `At Risk`, `Blocked`. Set with the weekly epic update. On 2026-10-09 both `Active` EA epics still read `Not Started` |
| Statement of Work (+ its `…Html` pair) | resolved with `get_type` | The SOW behind the epic |
| Project Brief (+ its `…Html` pair) | resolved with `get_type` | Product's brief, upstream of the SOW |
| Architecture Review Approved (date and by) | resolved with `get_type` | The AAB gate; required before `Active`. Values come from a `Decided` AAB Intake item |
| ELT Priority | resolved with `get_type` | The ELT stack rank (1 = highest) |
| OnQuarterlyPlan | resolved with `get_type` | `true` puts the epic in the Engineering Insights quarterly view |
| T-Shirt Size | resolved with `get_type` | Sizing |

## Stage mapping (truth-check only)

The board `Status` is Alex's column and is **never** derived from ADO. The mapping exists so the curator can flag a disagreement. A row with several epics checks against the most advanced live epic.

| ADO epic state | Board stage it supports | Flag when |
|---|---|---|
| `New` | `1. Exploring`, `2. Committed` | Row is `3. Delivering` or later but every epic is still `New` |
| `Active` | `3. Delivering` | Row is `1. Exploring` while an epic is `Active` (work started before the decision), or `4. Delivered` while an epic is `Active` |
| `Resolved` | `3. Delivering` (live, outcome not yet checked) | — |
| `Closed` | `4. Delivered` | Row is before `4. Delivered` while every epic is `Closed` (understating done work is as bad as overstating it) |
| `Removed` | `5. Stopped` + Milestone `Stopped: <why>` | Row still open with no other live epic |

An influence row has no EA epic, so it has no truth-check here. A `2. Committed` row with no epic is normal until building starts.

## Each fact is typed once

Theme, EA role, Impact, KeyArtifact, Sponsor, AAB items, NextMilestone and MilestoneDate stay **only** in SharePoint (decisions live in AAB Intake). Who does the work, state, epic dates and progress stay **only** in ADO, and the weekly epic comment is the progress narrative. If a future field seems needed in both places, the test is: does ADO need it to *do the work*? If not, it stays on the row.

## Tag vocabulary

The tags in use are `AI-DLC` / `enterprise-architecture` / `Pinnacle` / `SOW-<n>` / `Wave-<n>` plus one domain tag (`change-control`, `sql-server`, `agent-platform`, `dependencies`). Tags hint at the Theme; they never decide it.
