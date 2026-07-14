---
name: ado-dashboards
description: Build and fix Azure DevOps dashboards and widgets via the REST API — dashboard/widget JSON shapes, contributionId catalog, layout/grid mechanics, team-vs-project scoping, and diagnosing a blank/stuck "Query Results" widget. Use when adding a widget, creating a dashboard, a widget renders blank or won't load, or you need a count tile / query results grid / chart on a cross-team view. Works with @ado for auth/org mechanics.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: dashboard-management
---

# ADO Dashboards & Widgets

Azure DevOps's Dashboards/Widgets REST API is real but thinly documented: Microsoft Learn describes the `Dashboard`/`Widget` object shapes and the Create/Update/Get endpoints, but **never publishes a canonical list of widget `contributionId` strings or their `settings` JSON schemas**, and the one endpoint that's supposed to provide that catalog live (`_apis/dashboard/widgettypes`) 404s in practice (confirmed against org `CuroFinTech`, every variant tried). This skill exists to close that gap.

## Rule Zero: Harvest, Don't Guess

Never invent a `contributionId` or a `settings` JSON shape. Before creating any widget type you haven't used before:

1. Check `references/widget-catalog.md` — it may already be confirmed.
2. If not listed, or listed as "not confirmed," add one instance of that widget type via the ADO web UI to any dashboard, then `GET .../dashboards/{dashboardId}/widgets` and read the real `contributionId` + `settings` off the response.
3. Save what you found back into `widget-catalog.md` so the next session doesn't repeat the harvest.

**Harvest source matters**: only clone from a widget a **human added via the UI** on a dashboard people actually use (check `lastAccessedDate`/`eTag` on the dashboard). Microsoft's demo-generator projects (DemoAgile/DemoScrum) contain API-generated widgets whose settings are incomplete — they pass every API check and still fail to render ("Widget failed to load"). This burned a real diagnosis once: a broken widget was diff'd byte-for-byte against a DemoAgile "reference" and matched perfectly, because the reference had the same missing-`selectedColumns` defect. See `references/troubleshooting.md`.

This mirrors the Grafana `dashboarding` skill's "clone, don't author" rule — same failure mode (under-documented widget config), same fix (copy from something that's already proven to render).

## API surface

Full endpoint table, object schemas, request/response examples, and eTag/concurrency mechanics: `references/api-reference.md`.

Quick facts:
- Base: `https://dev.azure.com/{org}/{project}/{team}/_apis/dashboard/...`
- Every call needs a **preview** api-version (`7.1-preview.2` for widgets, `7.1-preview.3` for dashboards) — bare `7.1` 404s.
- Auth: same `$AZURE_DEVOPS_PAT` pattern as the `ado` agent (`~/.claude/agents/ado.md`) — this skill doesn't own auth, it owns dashboard/widget authoring on top of it.
- `settings` is a JSON-encoded **string** field, not a nested object — serialize before writing, parse after reading.
- Writes need the dashboard's current `eTag` nested as `"dashboard": {"eTag": "..."}` in the request body (optimistic concurrency) — GET fresh immediately before writing.

## Widget catalog

Confirmed `contributionId` + `settings` shapes for ~10 widget types (Query Results, Query Tile, Other Links, Team Members, New Work Item, Assigned to Me, and others), plus the explicit list of widget types that are NOT yet confirmed and must be harvested per Rule Zero before use (Chart for Work Items, Markdown, CFD, Velocity, Burndown/Burnup, and more): `references/widget-catalog.md`.

## Layout & grid mechanics

- `position: {row, column}` — 1-based in every observed example (`{1,1}` = top-left).
- `size: {rowSpan, columnSpan}` — height/width in dashboard grid units.
- Valid size combinations are per-widget-type (`allowedSizes`), not a global rule — since the catalog endpoint doesn't work here, read `allowedSizes` off a real widget instance of that type, or trial-and-error with the UI.
- No published global grid width — infer from a working dashboard's widest row if you need to know.

## Dashboard scoping (team vs. project, cross-team visibility)

`Dashboard.dashboardScope` is `project` or `project_Team` (a third value, `collection_User`, is deprecated). The URL path always includes a `{team}` segment regardless of scope. A **team-scoped** dashboard is what you get from Team Settings → Dashboards; a **project-scoped** one shows under the project's Overview → Dashboards and is visible to the whole project regardless of team membership.

If the goal is "see work items across multiple teams in one place," a project-scoped dashboard (or a cross-team Query behind a Query Results/Query Tile widget) is usually the right tool — it doesn't require creating a dedicated team just to get a board, which is a real but heavier-weight alternative (team's Area Path scope + `includeChildren: true`, documented in `RECOMMENDATIONS.md` in the ado-restructuring project).

## Gotchas & troubleshooting

Full table and a worked, root-caused diagnostic example for the single most common failure (Query Results widget rendering blank / "Widget failed to load") in `references/troubleshooting.md`. Short version: an API-created WitViewWidget with only `{"query":{...}}` in settings fails to render — the client requires `selectedColumns` (present in every human-added instance org-wide). Check settings completeness against `widget-catalog.md`'s full shape before suspecting UI-layer causes.

## Verification workflow

Same discipline as the rest of this project's ADO work — **API-confirmed is not UI-verified**:

1. After every write, `GET` the widget/dashboard back and confirm the response matches what you sent (round-trip check).
2. If the widget is query-backed, independently run the WIQL for its `queryId` and confirm it returns the expected rows/count — don't just trust the queryName string.
3. The final check is always a human loading the dashboard in a browser and confirming it actually renders. Report data-confirmed vs. UI-pending explicitly — don't claim a dashboard "works" off API responses alone.
