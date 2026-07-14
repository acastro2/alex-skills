# Widget Catalog — confirmed contributionIds and settings shapes

Confirmed = pulled from a live widget instance that a **human added via the UI on an actively-used dashboard** — not guessed, not from training-data memory. Warning learned the hard way: Microsoft's demo-generator projects (`DemoAgile`/`DemoScrum`) contain API-generated widgets whose settings are *incomplete relative to what the client needs to render* (e.g. WitViewWidget missing `selectedColumns`) — they pass every API-level check and still fail to load in the browser. Harvest from real human-built dashboards (e.g. Tiger's SRE/team Overview dashboards), never from demo-generator ones.

## Confirmed widgets

| Widget (human name) | contributionId | settings (raw JSON string content) | notes |
|---|---|---|---|
| Query Results | `ms.vss-mywork-web.Microsoft.VisualStudioOnline.MyWork.WitViewWidget` | `{"query":{"queryId":"<guid>","queryName":"<name>"},"selectedColumns":[{"name":"ID","referenceName":"System.Id"},{"name":"Work Item Type","referenceName":"System.WorkItemType"},{"name":"Title","referenceName":"System.Title"},{"name":"State","referenceName":"System.State"},{"name":"Assigned To","referenceName":"System.AssignedTo"}],"lastArtifactName":"<queryName>"}` | nested `"query"` wrapper. **`selectedColumns` is required in practice** — present in all 37 live human-added instances swept org-wide (2026-07); a widget with only the bare `{"query":{...}}` shape shows "Widget failed to load" in the browser even though every API check passes. `lastArtifactName` mirrors the query name. `configurationContributionId` ends `...WitViewWidget.Configuration`. `isNameConfigurable: true`. `lightboxOptions: {width:900, height:700, resizable:true}`. `loadingImageUrl: .../_static/MyWork/queryResultsLoading.png`. |
| Chart for Work Items | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.WitChartWidget` | `null` when unconfigured. **Configured** (harvested 2026-07 from Tiger project "Card Products" " Dashboard", human-built, 2 live instances): `{"scope":"WorkitemTracking.Queries","groupKey":"<queryId guid>","title":"<chart title>","chartType":"PieChart"\|"ColumnChart","transformOptions":{"filter":"<same queryId guid>","groupBy":"<field refname, e.g. System.AssignedTo or System.WorkItemType>","orderBy":{"direction":"descending","propertyName":"value"},"measure":{"aggregation":"count","propertyName":""},"historyRange":null,"groupByTags":false},"userColors":[{"value":"<group value string>","backgroundColor":"#RRGGBB"}, ...],"lastArtifactName":"<title>"}` | 9 live instances swept, 2 configured found (both in Card Products). `chartType` observed values: `PieChart`, `ColumnChart` (bar/column). `groupKey` and `transformOptions.filter` both hold the **query's GUID** (not a separate id) — chart is always query-scoped, same query referenced twice. `groupBy` takes a plain field reference name (`System.AssignedTo`, `System.WorkItemType` both confirmed working) — ordinary string/identity fields work, no evidence needed for special field types. `measure.aggregation: "count"` with empty `propertyName` in both samples (no sum/avg observed). `userColors` is an array of `{value, backgroundColor}` pairs keyed by the group-by value's string label — optional, empty array `[]` is valid (first sample had none configured). `settingsVersion` is `{3,0,0}` for this widget (not `{1,0,0}`). Both live instances used size `{rowSpan:2, columnSpan:2}`; a create at `{rowSpan:3, columnSpan:3}` was accepted and rendered data correctly in a round-trip GET (API-confirmed only, UI-unverified) — `allowedSizes` is not populated by this org's API on either list or single-widget GET, so exact valid combos still aren't independently discoverable; treat sizes as trial-and-error against a round-trip GET, not guessable from the field. |
| Markdown | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.MarkdownWidget` | **raw Markdown string, NOT JSON** | 13 live instances (harvested 2026-07 from Tiger "Tiger Team" / "Tiger - Stakeholders", human-built, 4 instances on that one dashboard alone). Confirms settings field is literally the markdown text with no wrapper object. Sizes observed in the wild: `{1,2}`, `{2,2}` (x2), `{3,2}` — **columnSpan 2 in every sample**, rowSpan varies 1-3; never seen at columnSpan 1. `isNameConfigurable: false` (title isn't user-editable the way other widgets are). `lightboxOptions: {width:600, height:500, resizable:true}`. `loadingImageUrl: .../_static/Widgets/markdownLoading.png`. A create at `{rowSpan:1, columnSpan:2}` in RestructureSandbox round-tripped correctly (API-confirmed, UI-unverified). |
| Query Tile (count/scalar) | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.QueryScalarWidget` | `{"queryId":"<guid>","queryName":"<name>"}` | **flat**, no `"query"` wrapper — different shape from WitViewWidget despite both referencing a query. Confirmed identically shaped across two independent live instances. No threshold/conditional-coloring field was observed in any real instance sampled (8 dashboards checked) — see Gotcha below. **Size is locked to 1×1** — a live create attempt at 2×1 was rejected server-side with `VS402508: size (2x1) not supported for widgets of that type`. Don't request a non-1x1 size for this widget type. |
| Other Links | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.OtherLinksWidget` | `null` | `allowedSizes: [{rowSpan:1, columnSpan:2}]` — single fixed size only. |
| Team Members | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.TeamMembersWidget` | `null` | |
| New Work Item | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.NewWorkItemWidget` | `null` | no configuration UI |
| Assigned to Me | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.AssignedToMeWidget` | `null` | `configurationContributionId: null` — genuinely unconfigurable |
| Sprint Burndown | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.SprintBurndownWidget` | not captured | doc-example only |
| Visual Studio Shortcuts | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.VSLinksWidget` | not captured | doc-example only |
| Welcome | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.HowToLinksWidget` | not captured | doc-example only |
| Work Links | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.WorkLinksWidget` | not captured | doc-example only |
| Team Room (deprecated) | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.TeamRoom` | n/a | feature removed from product; contributionId still appears in old doc examples |

## contributionIds confirmed via org sweep (2026-07, 22 Tiger dashboards, 127 widget instances) — settings shapes NOT yet captured

| Widget | contributionId | instances |
|---|---|---|
| Sprint Burndown (Analytics) | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.AnalyticsSprintBurndownWidget` | 13 |
| Velocity | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.VelocityWidget` | 13 |
| Release Pipeline Overview | `ms.vss-releaseManagement-web.release-definition-summary-widget` | 9 |
| Code Tile | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.CodeScalarWidget` | 5 |
| Build History | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.BuildChartWidget` | 4 |
| Sprint Overview | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.SprintOverviewWidget` | 4 |
| Cycle Time | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.CycleTimeWidget` | 2 |
| Embedded Webpage | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.IFrameWidget` | 2 |
| Burndown (Analytics, legacy variant) | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.BurndownWidget` | 1 |
| Lead Time | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.LeadTimeWidget` | 1 |
| Sprint Capacity | `ms.vss-dashboards-web.Microsoft.VisualStudioOnline.Dashboards.SprintCapacityWidget` | 1 |
| Pull Request | `ms.vss-mywork-web.Microsoft.VisualStudioOnline.MyWork.PullRequestWidget` | 1 |
| Sprint Goal (3rd-party marketplace) | `keesschollaart.sprint-goal.SprintGoalWidget` | 5 |

For these, the contributionId is trustworthy but the settings shape is not yet documented — before creating one via API, GET a configured live instance and copy its settings verbatim.

## Not confirmed at all — must harvest before use

Still zero sightings in any sampled dashboard: Cumulative Flow Diagram, Burnup, Deployment status, Requirements quality, Chart for Test Plans, Test Results Trend (+ Advanced), New Work Item's configured shape.

To use one of these: add it manually once via the ADO web UI to any test dashboard, then `GET .../dashboards/{dashboardId}/widgets` and read its `contributionId` + `settings` straight from the response. Save the result back into this table. Do not guess the shape from the widget's name or from training-data memory — every widget type defines its own private settings schema and there is no public reference for these.

## Query Tile conditional coloring (threshold red/yellow/green)

Not confirmed. No live instance sampled had threshold config present in `settings` — every QueryScalarWidget seen was a bare `{"queryId", "queryName"}` pair. Two explanations are equally plausible from available evidence: (a) the feature isn't configured anywhere sampled, or (b) it's UI-only theming not persisted in `settings` the way you'd expect. If you need conditional coloring, configure one manually via the ADO web UI on a test tile, then GET its widget object and diff the `settings` string against the bare shape above — that diff is the answer. Don't assume a field name and ship it unverified.

## Harvesting procedure (Rule Zero, operationalized)

```bash
# 1. find a dashboard that already renders the widget type you want
GET https://dev.azure.com/{org}/{project}/{team}/_apis/dashboard/dashboards?api-version=7.1-preview.3

# 2. pull its widgets
GET https://dev.azure.com/{org}/{project}/{team}/_apis/dashboard/dashboards/{dashboardId}/widgets?api-version=7.1-preview.2

# 3. read contributionId + settings verbatim from the response — settings is a JSON string, parse it to see the real shape
```
`_apis/dashboard/widgettypes` (the "proper" catalog endpoint) 404s on this org — don't rely on it, this harvesting procedure is the reliable path. See `api-reference.md` Gotchas.
