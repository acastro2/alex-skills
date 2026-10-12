# Architecture Weekly: page, gates and readership

Read this before you build, render, stage or check an Architecture Weekly page, write its Executive Summary or shipped panel, report readership, or stage a planned-absence note. The forum recap component has its own reference: [recap.md](recap.md).

The page's three components (Executive Summary band, Forum recap, **What Enterprise Architecture
shipped** panel) are listed in SKILL.md. They answer different questions: the band is for the executive leadership team who read the page but were
not in the room; the forum record says what the group decided; the panel says what EA shipped. Drop
any delivery item that restates the forum recap.

### The page body is rendered, never written

**Run [references/render_page.py](render_page.py); do not write page HTML.** The run's job
is content, the script's job is markup:

```
recap-content.json  →  render_page.py  →  canvas.json  →  stage_news_recap.py --canvas
```

The script owns every tag, style and colour. Read its docstring for the content schema. There is
**no "SharePoint-native markup only" rule any more** (Alex, 2026-09-28: "that doesn't hold"): the page
may use whatever styling the design needs. The only markup the script refuses is `<script>` and
`javascript:`, for safety. Hand-written HTML is what produced the drift between the 09-09 and
09-16 pages; two files cannot disagree if only one holds markup.

[references/example-content.json](example-content.json) is a complete, valid input: copy
it to start a week, and render it after any change to the script to prove the script still works.

**It refuses on content shape too, not just markup.** Missing `exec_summary`, a band outside 3 to 4
points, a blank `footer`, an unknown `outcome.tag`, a decision with no `rationale`: each is a named
error naming the exact key. Fix the content; do not reach past the script. The safety scan reads
the MARKUP only, so ordinary prose is safe. Escaping keeps content out of the markup.

`python3 references/render_page.py --text canvas.json` prints the rendered page as plain text, the
input to `voice_check.py`; see [references/recap.md](recap.md) for the commands.

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
memory. Only versions after `newsletter.moves_baseline` in the ledger count (2026-10-12, Alex): the 2026-10-10 remap renamed every status, and those renames are not moves. No moves: leave the key out, and the section is not rendered. Each move is a review line
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
  [references/recap.md](recap.md).

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
