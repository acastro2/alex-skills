# EA Projects board: list, views and columns

Read this before any write to the EA Projects list, before adding or changing a column or view, and when a write is rejected (the schema can drift). The rules for what goes in each column are in SKILL.md, Field mapping.

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
