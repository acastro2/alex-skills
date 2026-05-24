# SharePoint Page Creator & Editor

Manages SharePoint pages via REST API with cookie-based auth. Creates professional, visually polished pages that use the full range of SharePoint modern page features — not just dumped text.

## When to Use

- Creating or editing SharePoint modern pages
- When the user asks to make a SharePoint page for status updates, announcements, dashboards, documentation, or any content
- When delegated to via the `@sharepoint` agent

## Design Philosophy

**Every page must look intentionally designed, not auto-generated.** Follow the "Corporate Wiki" design system — an aesthetic engineered for high-utility internal documentation that aligns with the Microsoft 365 ecosystem. The brand personality is institutional, reliable, and invisible — prioritizing content clarity over decorative flair.

The emotional response should be focused productivity. Heavy whitespace and systematic information arrangement reduce cognitive load. The style is strictly functional, leveraging SharePoint's native patterns to eliminate learning curves.

Principles:
1. **6+6 by default** — Use equal two-column layouts for all content sections. Content left, criteria/context right. Full-width only for hero, diagrams, and dividers
2. **Alternating rhythm** — Follow the pattern: full-width → 6+6 → divider → 6+6 → divider. This fills the content well and creates a magazine-style balanced feel
3. **Styled tables over plain text** — Tables are the primary visual tool. Use primary-colored headers, generous padding, subtle borders, and tinted columns
4. **Breathing room** — Use dividers between major sections
5. **Minimal emphasis bands** — Prefer `zoneEmphasis: 0` and `1` only. Avoid `2` and `3` (theme colors may clash). Alternate `0` and `1` for subtle rhythm
6. **Color-coded meaning** — Primary for headings, on-surface-variant for secondary text, error for critical items, success for positive indicators

## Reference Files

Load these for detailed JSON schemas:
- `references/web-parts.md` — All web part GUIDs and configuration (VERIFIED against tenant)
- `references/page-layouts.md` — Section layouts, positioning, page headers
- `references/rich-text-formatting.md` — HTML formatting in text controls

## Auth & API

### Authentication
Cookie-based auth using `FedAuth` + `rtFa` cookies extracted via Playwright.

```bash
# Extract cookies (opens browser for login)
python3 ~/.config/opencode/scripts/sharepoint/auth.py "https://attainfinance.sharepoint.com/sites/SITE_NAME"

# API operations
SHAREPOINT_SITE_URL="https://attainfinance.sharepoint.com/sites/SITE_NAME" \
  python3 ~/.config/opencode/scripts/sharepoint/sharepoint_api.py <command> [args]
```

### Available Commands
| Command | Args | Description |
|---------|------|-------------|
| `list` | `[count]` | List pages (default 10) |
| `get` | `<page_id>` | Get page details including CanvasContent1 |
| `create` | `<title>` | Create a new draft page |
| `update-content` | `<page_id> <canvas_json>` | Update page body content |
| `update-title` | `<page_id> <title>` | Update page title |
| `publish` | `<page_id>` | Publish a draft page |
| `delete` | `<page_id>` | Delete a page |

### Default Site
`https://attainfinance.sharepoint.com/sites/InformationTechnology-SeniorLeadership`

## Page Design Patterns

### Pattern 1: Status Update / Announcement
Use for weekly updates, project status, team announcements.

**Structure:**
1. **Section 1** (full-width, `zoneEmphasis: 1`) — Hero text with key message
2. **Section 2** (6+6) — Details left, key metrics right
3. **Divider**
4. **Section 3** (6+6, `zoneEmphasis: 0`) — Action items left, timeline/owners right
5. **Section 4** (full-width) — CTA button

### Pattern 2: Documentation / How-To
Use for procedures, guides, reference docs.

**Structure:**
1. **Section 1** (full-width) — Overview paragraph
2. **Section 2** (6+6, `zoneEmphasis: 1`) — Main content left, quick links/context right
3. **Divider**
4. **Sections 3-N** (6+6) — Each topic: explanation left, examples/code right
5. **Section N+1** (full-width) — Reference table

### Pattern 3: Dashboard / Overview
Use for team dashboards, metric summaries, hub pages.

**Structure:**
1. **Hero web part** — Key links/highlights (3-5 tiles)
2. **Section** (6+6, `zoneEmphasis: 1`) — Metric summaries left, status right
3. **Divider**
4. **Section** (6+6) — News feed left, Events right
5. **Quick Links** — Resource grid

### Pattern 4: Project Kickoff / Initiative Page
Use for new projects, proposals, initiative tracking.

**Structure:**
1. **Section 1** (full-width, `zoneEmphasis: 1`) — Project overview, goals
2. **Section 2** (6+6) — Timeline left, Team (People web part) right
3. **Divider**
4. **Section 3** (6+6, `zoneEmphasis: 0`) — Milestones left, risks/dependencies right
5. **Section 4** (full-width) — Next steps CTA

### Pattern 5: Interview / Assessment Wiki
Use for interview rubrics, evaluation guides, assessment frameworks.

**Structure:**
1. **Section 1** (full-width, `zoneEmphasis: 1`) — Title + design philosophy blockquote
2. **Section 2** (full-width, `zoneEmphasis: 0`) — Overview process table (styled with primary headers)
3. **Section 3** (full-width) — Diagram (Image web part with D2/SVG)
4. **Divider**
5. **For each interview stage:**
   - **Section N** (6+6, `zoneEmphasis: 0 or 1`, alternating) — Scenario/questions LEFT, rubric table RIGHT
   - **Callout row** — blockquote tips/warnings within the same section or as a follow-up full-width
   - **Divider**
6. **Final Section** (full-width, `zoneEmphasis: 1`) — Evaluation & Decision with threshold table

## Design Rules

### Visual Design System — "Corporate Wiki"

Engineered for high-utility internal documentation. The brand personality is institutional, reliable, and invisible — prioritizing content clarity over decorative flair. Pages should evoke focused productivity through heavy whitespace, systematic information arrangement, and native SharePoint continuity.

### Design Tokens

**Colors — use `rgb()` values in inline styles:**

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `primary` | #005faa | `rgb(0,95,170)` | Interactive elements, primary actions, nav wayfinding |
| `primary-container` | #0078d4 | `rgb(0,120,212)` | Table headers, button fills, accent backgrounds |
| `on-primary` | #ffffff | `rgb(255,255,255)` | Text on primary backgrounds |
| `on-surface` | #1a1c1c | `rgb(26,28,28)` | Primary text, headings |
| `on-surface-variant` | #404752 | `rgb(64,71,82)` | Secondary text, sub-labels, metadata |
| `secondary` | #605e5c | `rgb(96,94,92)` | Muted UI text, timestamps |
| `outline` | #717783 | `rgb(113,119,131)` | Borders, separators |
| `outline-variant` | #c0c7d4 | `rgb(192,199,212)` | Subtle borders, dividers between cells |
| `surface` | #faf9f8 | `rgb(250,249,248)` | Page background |
| `surface-container-lowest` | #ffffff | `rgb(255,255,255)` | Content cards, table cells |
| `surface-container-low` | #f4f3f2 | `rgb(244,243,242)` | Alternate row, light callout bg |
| `surface-container` | #efeeed | `rgb(239,238,237)` | Neutral section backgrounds, process table headers |
| `surface-container-high` | #e9e8e7 | `rgb(233,232,231)` | Hover states, active rows |
| `surface-container-highest` | #e3e2e1 | `rgb(227,226,225)` | Strong neutral surfaces |
| `error` | #ba1a1a | `rgb(186,26,26)` | Red flags, critical failures, do-not-proceed |
| `error-container` | #ffdad6 | `rgb(255,218,214)` | Error callout backgrounds |
| `on-error-container` | #93000a | `rgb(147,0,10)` | Text on error backgrounds |
| `tertiary` | #1160a4 | `rgb(17,96,164)` | Distinguished column tint, secondary links |
| `tertiary-fixed-dim` | #a2c9ff | `rgb(162,201,255)` | Light blue highlight cells |
| `primary-fixed` | #d3e3ff | `rgb(211,227,255)` | Distinguished column background |
| `inverse-surface` | #2f3130 | `rgb(47,49,48)` | Dark callout backgrounds |
| `inverse-on-surface` | #f1f0ef | `rgb(241,240,239)` | Text on dark backgrounds |

**Semantic color mappings (for quick reference):**
- **Table headers:** `primary-container` bg + `on-primary` text
- **Table cells:** `surface-container-lowest` bg + `on-surface-variant` text
- **Distinguished column:** `primary-fixed` bg
- **Process/overview headers:** `surface-container` bg + `primary` text
- **Red flags/errors:** `error` text, or `error-container` bg + `on-error-container` text
- **Success/positive:** `rgb(16,124,16)` (SharePoint theme green)
- **Warning/pending:** `rgb(216,59,1)` (SharePoint theme amber)
- **Dimension names:** `on-surface` with `font-weight:600`
- **Sub-labels:** `on-surface-variant` with `font-style:italic`

**Typography — Segoe UI (native to SharePoint):**

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Display | 42px | 600 | 52px | Hero headlines only |
| Headline LG | 32px | 600 | 40px | Major section headers (`<h2>`) |
| Headline MD | 24px | 600 | 32px | Subsection headers (`<h3>`) |
| Headline SM | 20px | 600 | 28px | Minor headings (`<h4>`) |
| Title | 18px | 600 | 24px | Card titles, numbered item labels |
| Body LG | 16px | 400 | 22px | Introductory summaries, hero subtitles |
| Body MD | 14px | 400 | 20px | Standard body text (default) |
| Label MD | 12px | 400 | 16px | Sub-labels, metadata, timestamps |
| Label SM | 10px | 700 | 12px | Uppercase tags, status badges |

**Spacing — 8px base unit:**
- Stack SM: 8px (between related items)
- Stack MD: 16px (between components)
- Stack LG: 24px (between sections)
- Cell padding: 12px 16px (table cells)
- Container padding: 16px (callout boxes)
- Gutter: 24px (between columns)

**Elevation — Tonal layers, not shadows:**
- Level 0: Page background (`surface`)
- Level 1: Content containers (`surface-container-lowest` with `1px solid outline-variant`)
- Level 2: Interactive hover only — minimal shadow (`0px 2px 4px rgba(0,0,0,0.05)`)

**Shapes — Soft edges:**
- Small components (buttons, badges): 2px radius
- Containers (cards, callouts): 4px radius

### Section Background Strategy
- **None (0):** Default — use for most content sections
- **Neutral (1):** Light gray — use for hero, alternating sections, and final sections
- **Soft (2):** Avoid — renders in the site's theme color (often teal/dark) which clashes with styled tables
- **Strong (3):** Avoid — same issue as Soft but darker. Text becomes white, table headers become invisible

**Recommended pattern:** Alternate between `0` and `1` only:
```
ze:1 (hero) → ze:0 → ze:1 → ze:0 → ze:1 (footer)
```

### Column Usage & Page Rhythm

**Default to 6+6 two-column layouts.** Equal columns fill the content well better than asymmetric splits and give a balanced, magazine-style feel. Reserve full-width for hero sections, diagrams, and standalone tables only.

**The alternating rhythm pattern:**
```
Full-width (hero/diagram) → 6+6 text → Divider → 6+6 text → Divider → 6+6 text → ...
```

This is the core layout principle. Every content section should pair related content side-by-side:
- **Left column:** Questions, scenarios, descriptions, task details
- **Right column:** Rubric tables, callouts, scoring criteria, context

**Column options (in order of preference):**
1. **Two-column (6+6):** Default for all content sections — content left, rubric/criteria right
2. **Full-width (12):** Hero sections, process overview tables, diagrams, dividers only
3. **Two-column (8+4):** Only when the right column is genuinely a narrow sidebar (metadata, format callout)
4. **Three-column (4+4+4):** Resource cards, metric tiles — use sparingly

### Styled Tables — The Core Visual Tool

Tables are the primary vehicle for professional-looking content. Style them aggressively with inline CSS using the design tokens above.

**Rubric table pattern:**
```html
<table style="width:100%; border-collapse:collapse;">
  <tbody>
    <tr style="background-color:rgb(0,120,212);">
      <th style="padding:12px 16px; color:rgb(255,255,255); font-size:13px; font-weight:600; text-align:left; border-bottom:2px solid rgb(0,95,170);">Dimension</th>
      <th style="padding:12px 16px; color:rgb(255,255,255); font-size:13px; font-weight:600; text-align:center; border-left:1px solid rgba(255,255,255,0.2);">1-2: Emerging</th>
      <th style="padding:12px 16px; color:rgb(255,255,255); font-size:13px; font-weight:600; text-align:center; border-left:1px solid rgba(255,255,255,0.2);">3: Proficient</th>
      <th style="padding:12px 16px; color:rgb(255,255,255); font-size:13px; font-weight:600; text-align:center; border-left:1px solid rgba(255,255,255,0.2); background-color:rgb(0,95,170);">4-5: Distinguished</th>
    </tr>
    <tr style="border-bottom:1px solid rgb(192,199,212);">
      <td style="padding:12px 16px;"><strong style="color:rgb(26,28,28);">Dimension Name</strong><br/><span style="font-size:12px; color:rgb(64,71,82); font-style:italic;">Guiding question?</span></td>
      <td style="padding:12px 16px; color:rgb(64,71,82); border-left:1px solid rgb(192,199,212);">Emerging description</td>
      <td style="padding:12px 16px; color:rgb(64,71,82); border-left:1px solid rgb(192,199,212);">Proficient description</td>
      <td style="padding:12px 16px; color:rgb(64,71,82); border-left:1px solid rgb(192,199,212); background-color:rgb(211,227,255);">Distinguished description</td>
    </tr>
  </tbody>
</table>
```

**Key table styling rules:**
1. **Primary header row** (`primary-container` bg) with white text
2. **Distinguished column** header gets darker primary (`primary` bg), cells get `primary-fixed` bg
3. **Dimension names** are bold `on-surface` with italic `on-surface-variant` sub-labels
4. **Red flag text** uses `error` color for critical items
5. **Cell padding** is generous: `12px 16px`
6. **Border between cells**: `1px solid outline-variant`
7. **No outer table border** — relies on section background for framing

**Process/overview table pattern:**
```html
<table style="width:100%; border-collapse:collapse;">
  <tbody>
    <tr style="background-color:rgb(239,238,237);">
      <th style="padding:10px 16px; font-size:13px; font-weight:600; color:rgb(0,95,170); text-align:left;">Step</th>
      <th style="padding:10px 16px; font-size:13px; font-weight:600; color:rgb(0,95,170); text-align:left;">Stage</th>
      <th style="padding:10px 16px; font-size:13px; font-weight:600; color:rgb(0,95,170); text-align:left;">Details</th>
    </tr>
    <tr style="border-bottom:1px solid rgb(192,199,212);">
      <td style="padding:10px 16px; font-weight:600; color:rgb(0,95,170);">0</td>
      <td style="padding:10px 16px; color:rgb(26,28,28);">Phone Screen</td>
      <td style="padding:10px 16px; color:rgb(64,71,82);">30-minute initial assessment</td>
    </tr>
  </tbody>
</table>
```

### Callout Boxes

Use `<blockquote>` for callouts — SharePoint renders a theme-colored left border. Enhance with inline styles using design tokens:

**Tip callout:**
```html
<blockquote>
  <p><strong style="color:rgb(0,95,170);">💡 Interviewer Tip</strong></p>
  <p style="color:rgb(64,71,82); font-size:14px;">Watch for how they handle the OOM error. A great candidate will immediately suggest moving data processing out of XComs.</p>
</blockquote>
```

**Warning callout:**
```html
<blockquote>
  <p><strong style="color:rgb(186,26,26);">⚠️ Critical Fail Criteria</strong></p>
  <p style="color:rgb(64,71,82); font-size:14px;">Hardcoding credentials should result in a maximum score of 2.</p>
</blockquote>
```

**Decision gate callout:**
```html
<blockquote>
  <p><strong style="color:rgb(16,124,16);">✅ Decision Gate</strong></p>
  <p style="color:rgb(64,71,82); font-size:14px;">Average score ≥ 3.0 to proceed. Below 3.0 = no advance.</p>
</blockquote>
```

### Numbered List Items (Bento-Style)

For structured prompts with numbered items, use bold numbers with descriptions:

```html
<p><strong style="color:rgb(0,95,170); font-size:18px;">01</strong> &nbsp; <strong>Loan Origination Analytics</strong></p>
<p style="color:rgb(64,71,82); font-size:14px;">Real-time processing of high-volume loan applications for executive dashboards.</p>
```

### Typography
- `<h2>` for section headings — one per section maximum
- `<h3>` for subsections within a section
- Keep paragraphs short (2-3 sentences max)
- Use bullet points for lists of 3+ items
- Use styled tables (not plain) for structured comparisons
- Use blockquotes for callouts — always with a bold colored title line
- **Hero text** in Strong (3) sections: use `<h2>` with a short `<p>` subtitle
- **Sub-labels** under dimension names: `<span style="font-size:12px; color:rgb(64,71,82); font-style:italic;">`
- **Primary text:** `color:rgb(26,28,28)` — headings, dimension names
- **Secondary text:** `color:rgb(64,71,82)` — body, descriptions, sub-labels
- **Muted text:** `color:rgb(96,94,92)` — timestamps, metadata

### Visual Breaks
- Add a **Divider** between major topic changes
- Add a **Spacer** (height 20-30) for subtle breathing room within a section
- Never put more than 3 text blocks in a row without a visual break

### Buttons & CTAs
- Use **Primary** buttons for the main action
- Use **Secondary** buttons for alternative actions
- Center-align standalone buttons
- Maximum 2 buttons per section

## Vertical Sections (Right Sidebar)

A vertical section adds a persistent right-hand sidebar to the entire page, making the main content area wider and better utilizing horizontal space. Only ONE vertical section per page.

**When to use:** Hub pages, dashboards, or any page that benefits from persistent navigation/context alongside main content.

**JSON structure:** Use `layoutIndex: 2` on controls in the vertical section:
```json
{
  "controlType": 0,
  "displayMode": 2,
  "emphasis": {"zoneEmphasis": 0},
  "position": {
    "zoneIndex": 1,
    "sectionIndex": 1,
    "sectionFactor": 12,
    "layoutIndex": 2
  }
}
```

**Key rules:**
- All vertical section controls share the same `zoneIndex` as the first main content zone (typically 1)
- The vertical section `zoneEmphasis` sets its background independently
- Content in the sidebar stacks from the top — it does NOT align with specific main content zones
- Good for: navigation links, persistent reference cards, CTA buttons, metadata
- Bad for: content that should appear alongside a specific section (it won't align)

## Code Snippet Web Part

Use for displaying code with syntax highlighting instead of `<pre><code>` blocks.

**GUID:** `7b317bca-c919-4982-af2f-8399173e5a1e`

**Supported languages:** SQL, Python, JavaScript, TypeScript, Go, Java, C#, PowerShell, Bash, JSON, XML, HTML, CSS, and more.

**JSON structure:**
```json
{
  "controlType": 3,
  "displayMode": 2,
  "id": "<uuid>",
  "position": {"zoneIndex": N, "sectionIndex": 1, "controlIndex": N, "layoutIndex": 1, "sectionFactor": 12},
  "webPartId": "7b317bca-c919-4982-af2f-8399173e5a1e",
  "webPartData": {
    "id": "7b317bca-c919-4982-af2f-8399173e5a1e",
    "instanceId": "<same-uuid-as-id>",
    "title": "Code snippet",
    "properties": {
      "language": "Python",
      "theme": "Office",
      "showLineNumbers": true,
      "wrap": false
    },
    "dataVersion": "1.0",
    "serverProcessedContent": {
      "searchablePlainTexts": {
        "code": "<escaped-code-here>"
      }
    }
  }
}
```

**CRITICAL:** In `searchablePlainTexts.code`, you MUST escape:
- `<` → `&lt;`
- `&` → `&amp;`
- `>` → `&gt;`

**Multi-language code blocks:** When showing the same solution in multiple languages, use separate Code Snippet web parts with `<h4>` text control headers between them (e.g., "Python", "JavaScript", "Go"). These act as tab labels since native tabs are not available.

## Diagrams

SharePoint does not support inline SVG, Mermaid, or `<canvas>`. For diagrams:

1. **Generate SVG** using D2 (`d2 input.d2 output.svg`) — produces clean, styled diagrams
2. **Upload SVG** to Site Assets: `PUT /_api/web/GetFolderByServerRelativeUrl('.../SiteAssets')/Files/add(url='name.svg',overwrite=true)`
3. **Insert Image web part** pointing to the uploaded SVG

D2 source files should be stored in a local diagrams directory for future editing. The SVG is re-renderable from the D2 source.

## Known Limitations

### Collapsible Sections
Collapsible sections (`isCollapsibleSection` / `collapsibleSection` property) are a newer SharePoint feature that may NOT be enabled on all tenants. The JSON is accepted by the API but sections render as regular (non-collapsible) sections if the tenant feature flag is off.

**Fallback:** Move content to a separate linked page, or use styled heading sections with visual separators.

### Tabs
SharePoint has NO native tab web part. Alternatives:
- Use `<h4>` headings as visual "tab labels" above separate content blocks
- Use separate pages linked from a Quick Links web part
- Use collapsible sections (if enabled) to simulate accordion behavior

### Embed Web Part Domain Restrictions
The Embed web part only allows iframes from whitelisted domains. External tools (e.g., mermaid.live) will likely be blocked unless the tenant admin adds them to the allowed list.

### Content Well Width
SharePoint modern pages have a fixed max-width content well (~900-1100px). To make pages feel wider:
- Use a **vertical section** (adds a sidebar, pushes main content wider)
- Use **6+6 two-column layouts** (fills horizontal space better than full-width text)

## Page Naming

When creating pages, set a clean URL slug using the `Name` property:
```
create "Page Title" --name "Clean-URL-Slug"
```
This produces URLs like `/SitePages/Clean-URL-Slug.aspx` instead of random strings like `/SitePages/xk4z92mn.aspx`.

## Checkout Lock Handling

Pages can get stuck in a checked-out state (409 Conflict). To handle:
1. **Discard checkout:** `POST /_api/web/getFileByServerRelativeUrl('/sites/.../SitePages/page.aspx')/undocheckout()`
2. **Then re-checkout and update**
3. **NEVER create a new page** as a workaround for a locked page — always try to unlock first

## CanvasContent1 Construction

### Critical Rules
1. `CanvasContent1` is a **JSON array serialized as a string**
2. Every column needs a **column descriptor** (controlType: 0) BEFORE its controls
3. Every control needs a **unique id** (generate UUIDs)
4. `sectionFactor` values in a section MUST sum to 12
5. `zoneEmphasis` MUST be consistent across all controls in a `zoneIndex`
6. **pageSettingsSlice** is always the LAST element
7. `displayMode: 2` always when saving via API
8. For text controls: `id` and `anchorComponentId` must match
9. For web parts: `id` and `webPartData.instanceId` must match

### UUID Generation
Generate UUIDs in format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
Use unique values for every control instance.

## Workflow

1. **Understand the content** — What is the page about? Who is the audience?
2. **Choose a pattern** — Match content type to a design pattern above
3. **Plan the sections** — Sketch out the section structure with emphasis levels
4. **Build CanvasContent1** — Construct the JSON array following the critical rules
5. **Create the page** — `create <title>`
6. **Update content** — `update-content <id> '<json>'`
7. **Verify** — `get <id>` to confirm content saved correctly
8. **Publish** (if requested) — `publish <id>`

## Error Recovery

| Error | Fix |
|-------|-----|
| 403 Forbidden | Cookies expired — re-run `auth.py` |
| 409 Conflict | Page locked — discard checkout first (`undocheckout()`), then retry. NEVER create a new page as workaround |
| 500 with JsonReaderException | CanvasContent1 is not valid JSON — check escaping |
| Content not rendering | Verify sectionFactor sums to 12, check zoneEmphasis consistency |
| Collapsible sections not rendering | Tenant feature likely not enabled — fall back to separate pages or styled sections |
| Code blocks not syntax highlighted | Use Code Snippet web part (GUID: `7b317bca-...`) instead of `<pre><code>` |
| Embed web part blank | Domain not whitelisted — use Image web part with uploaded SVG instead |
| Page content too narrow | Add a vertical section (layoutIndex: 2) and/or use 6+6 column layouts |
