# ADO Dashboards/Widgets REST API — Reference

Confirmed against Microsoft Learn (as of 2026-07) plus live calls against org `CuroFinTech`. Where the two disagree, the live-call result wins and is marked accordingly.

## Endpoints

All require api-version with a **preview suffix** — there is no GA version of this API surface.

| Operation | Method + path | api-version | Scope |
|---|---|---|---|
| Create dashboard | `POST /{org}/{project}/{team}/_apis/dashboard/dashboards` | `7.1-preview.3` | `vso.dashboards_manage` |
| Get dashboard | `GET /{org}/{project}/{team}/_apis/dashboard/dashboards/{dashboardId}` | `7.1-preview.3` | `vso.dashboards` |
| List dashboards (team/project) | `GET /{org}/{project}/{team}/_apis/dashboard/dashboards` | `7.1-preview.3` | `vso.dashboards` |
| Create widget | `POST /{org}/{project}/{team}/_apis/dashboard/dashboards/{dashboardId}/widgets` | `7.1-preview.2` | `vso.dashboards_manage` |
| Get widgets (all on dashboard) | `GET /{org}/{project}/{team}/_apis/dashboard/dashboards/{dashboardId}/widgets` | `7.1-preview.2` | `vso.dashboards` |
| Get single widget | `GET /{org}/{project}/{team}/_apis/dashboard/dashboards/{dashboardId}/widgets/{widgetId}` | `7.1-preview.2` | `vso.dashboards` |
| Update widget (partial) | `PATCH /{org}/{project}/{team}/_apis/dashboard/dashboards/{dashboardId}/widgets/{widgetId}` | `7.1-preview.2` | `vso.dashboards_manage` |
| Replace all widgets | `PUT /{org}/{project}/{team}/_apis/dashboard/dashboards/{dashboardId}/widgets` | `7.1-preview.2` | `vso.dashboards_manage` — destructive, drops any widget not in the payload |
| Delete widget | `DELETE /{org}/{project}/{team}/_apis/dashboard/dashboards/{dashboardId}/widgets/{widgetId}` | `7.1-preview.2` | `vso.dashboards_manage` |
| Widget type metadata (single) | `GET /{org}/{project}/_apis/dashboard/widgettypes/{contributionId}` | `7.1-preview.1` | `vso.dashboards` — **404 confirmed on CuroFinTech, see Gotcha below** |
| Widget type catalog (all) | `GET /{org}/_apis/dashboard/widgettypes` | `7.1-preview.1` | `vso.dashboards` — **404 confirmed on CuroFinTech, every variant tried, see Gotcha below** |

`{team}` is optional in the path for project-scoped dashboards but the URL segment is still accepted/expected either way.

## Object schemas

**Dashboard**
```
id (uuid), eTag (string), name (string), description (string),
dashboardScope (enum: "project" | "project_Team" | "collection_User" [deprecated]),
groupId (string), ownerId (string), position (int32),
refreshInterval (int32, minutes), widgets (Widget[]),
_links, url
```

**Widget**
```
id (uuid), name (string), contributionId (string),
position (WidgetPosition), size (WidgetSize), allowedSizes (WidgetSize[]),
settings (string — JSON-serialized text, NOT a nested object),
settingsVersion (SemanticVersion),
configurationContributionId (string), configurationContributionRelativeId (string),
isNameConfigurable (bool), isEnabled (bool), areSettingsBlockedForUser (bool),
artifactId (string), contentUri (string), typeId (string), url (string),
lightboxOptions (LightboxOptions), loadingImageUrl (string),
dashboard (Dashboard — partial, used ONLY to pass eTag on write), eTag (string), _links
```

**WidgetPosition** — `{ row: int32, column: int32 }`. 1-based in every observed example (`{row:1, column:1}` = top-left). No documented min/max.

**WidgetSize** — `{ rowSpan: int32, columnSpan: int32 }`. `columnSpan` = width in grid columns, `rowSpan` = height in grid rows. No documented global grid width; valid combos are per-widget-type via `allowedSizes` (not independently discoverable here since `widgettypes` 404s — harvest from a working instance of that widget type instead, see SKILL.md Rule Zero).

**SemanticVersion** — `{ major, minor, patch }` (all int32). Most widget types use `{1,0,0}`, but NOT all — `WitChartWidget` (Chart for Work Items) uses `{3,0,0}` in every live instance. Copy the value from a harvested instance of the same widget type; don't assume 1.0.0.

**LightboxOptions** — `{ height: int32 (px), width: int32 (px), resizable: bool }`. Only present on widgets that open a detail popout (e.g. Query Results / `WitViewWidget`).

## Concurrency (eTag)

Both `Dashboard.eTag` and `Widget.eTag` exist for edit-collision detection. When creating or updating a widget, nest the dashboard's current eTag under `"dashboard": {"eTag": "<value>"}` in the request body. The response's `dashboard.eTag` increments after each widget-level write. Always GET the dashboard (or its widgets, which embed the parent eTag) immediately before a write to avoid a stale-eTag conflict.

## Create widget — verified request/response shape

```json
POST .../dashboards/{dashboardId}/widgets?api-version=7.1-preview.2
{
  "name": "All Change Controls",
  "position": { "row": 1, "column": 1 },
  "size": { "rowSpan": 4, "columnSpan": 4 },
  "settings": "{\"query\":{\"queryId\":\"<guid>\",\"queryName\":\"All Change Controls\"}}",
  "settingsVersion": { "major": 1, "minor": 0, "patch": 0 },
  "dashboard": { "eTag": "18" },
  "contributionId": "ms.vss-mywork-web.Microsoft.VisualStudioOnline.MyWork.WitViewWidget"
}
```
Response: 200, full Widget object including server-assigned `id`, `eTag`, `allowedSizes`.

`settings` is a **string containing JSON**, not a JSON object — serialize it before sending (double-encode), matches confirmed live behavior.

## Gotchas specific to this API surface

- **`_apis/dashboard/widgettypes` (both the catalog list and the single-contributionId lookup) 404s on Azure DevOps Services org `CuroFinTech`** — tried every reasonable variant (org-only, project-scoped, multiple api-version revisions down to 5.0, `$scope` query param, casing variants). Some variants return a JSON `VSSF` error, others return a raw HTML "page not found" — meaning the route isn't recognized at all for some combos, not just permission-denied. Microsoft Learn documents this endpoint but it is **not reliably usable in practice**. Do not build automation that depends on it. Treat the widget catalog as something you harvest empirically (see SKILL.md Rule Zero), not something you query live.
- **No canonical contributionId → widget-name lookup table is published anywhere.** The human-readable widget catalog page (learn.microsoft.com widget-catalog) never prints a single contributionId string. The only ones documented are those that leak incidentally into REST API example payloads (~9 of the ~30+ OOB widgets). See `widget-catalog.md` in this folder for the confirmed list.
- **PATCH (Update Widget) partial-update semantics are undocumented.** The one official example sends a nearly-complete Widget object, not a true minimal diff. Don't assume unlisted fields are preserved — send the full known-good object (id, eTag, name, position, size, settings, settingsVersion, dashboard.eTag, contributionId) on every write.
- **`Replace all widgets` (PUT) is destructive** — any widget on the dashboard not included in the payload is dropped. Use PATCH-per-widget unless you intend a full rebuild.
