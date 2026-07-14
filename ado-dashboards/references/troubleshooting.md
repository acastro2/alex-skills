# Troubleshooting

## Query Results widget (WitViewWidget) renders blank / stuck loading / "Widget failed to load"

Worked example from a real incident, **now root-caused** (RestructureSandbox, "Change Control Overview" dashboard, `WitViewWidget` bound to query "All Change Controls").

**Root cause: `settings` missing `selectedColumns`.** A WitViewWidget created via API with only the bare `{"query":{"queryId","queryName"}}` settings passes every server-side check but the browser client fails to render it ("Widget failed to load"). An org-wide sweep of 37 live, human-added, confirmed-in-use WitViewWidget instances showed **every single one** carries a `selectedColumns` array (plus `lastArtifactName`) in settings — see `widget-catalog.md` for the full required shape.

**How the wrong reference fooled two rounds of diagnosis:** the "known-good reference" widget used for comparison came from Microsoft's DemoAgile demo-generator project — itself API-generated with the same incomplete bare settings, and never visually verified. Byte-identical-to-reference proved nothing because the reference was equally broken. Lesson (now in Rule Zero): harvest only from widgets a human added via the UI on a dashboard someone actually uses.

**Diagnostic path — data-layer checks that pass and are NOT the cause (don't loop on these):**
1. `GET .../wit/queries/{queryId}` — query exists, correct project GUID, `isPublic: true`.
2. `GET .../wit/wiql/{queryId}` — query actually executes and returns real rows.
3. Spot-check one returned work item ID — resolves fine, has valid Title/Type/State.
4. `settingsVersion` (`1.0.0`) matches working instances.
5. `contributionId` spelled exactly right — and NOT legacy: `ms.vss-mywork-web.Microsoft.VisualStudioOnline.MyWork.WitViewWidget` is the current, only Query Results id in use org-wide (verified against 37 live instances, 2026-07).
6. Full non-settings field set (`lightboxOptions`, `isNameConfigurable`, `configurationContributionId`) matches — ruled out empirically as a cause; a widget with all of these correct still failed to load.

Then check the actual cause: **parse the `settings` string and confirm `selectedColumns` is present.** If missing, PATCH settings to the full shape in `widget-catalog.md`.

If `selectedColumns` is present and it still fails, only then move to UI-layer debugging:

**Next steps (UI-layer, needs a human with a browser):**
- Open the dashboard, open browser devtools → Network tab, reload, find the iframe/XHR call the widget makes to load its data — check for a 403/401 (permission issue: does the viewing user/team have read access to the query's folder, e.g. "Shared Queries"?) or a 5xx.
- Check devtools Console for a JS error thrown by the widget's iframe content.
- Try a hard refresh / clear the dashboard's client-side cache — widgets added via direct API (bypassing the normal "Add Widget" UI flow) sometimes render once, cache a bad state, and never re-fetch until forced.
- Confirm the user viewing the dashboard is actually a member of the team the dashboard is scoped to (`dashboardScope: project_Team`) — team-scoped dashboards can behave oddly for non-members even with project-level read access.

**Causes ruled out empirically during the real incident** (don't re-chase these): stale/deleted queryId, zero-row query, settingsVersion mismatch, contributionId typo, legacy contributionId, and missing non-settings fields (`lightboxOptions`/`isNameConfigurable`/`configurationContributionId` — rebuilding the widget with all of those correct changed the symptom from infinite-spinner to an explicit "Widget failed to load," but didn't fix it; only adding `selectedColumns` to `settings` addressed the actual gap the client chokes on).

## General API gotchas

- Every dashboard/widget call needs a **preview** api-version suffix (`7.1-preview.2` or `.3`) — a bare `7.1` 404s.
- `settings` is a JSON-encoded **string**, not a nested object — you must serialize/escape it before sending in the request body, and `JSON.parse()` it after reading.
- `_apis/dashboard/widgettypes` (both list and single-lookup) 404s on Azure DevOps Services hosted orgs in practice — don't build automation that depends on it working; see `api-reference.md`.
- Stale `dashboard.eTag` on a write → optimistic-concurrency failure. Always GET fresh immediately before a write.
- **PATCH response echo is unreliable** — observed live: the immediate PATCH response body showed `isEnabled: false` and nulled `typeId`/`configurationContributionId`/`loadingImageUrl`/`lightboxOptions`, but a fresh GET right after showed everything correctly persisted. Never judge a write's outcome from the PATCH response body; always do the round-trip GET.
- **`409 WidgetCollisionException` when repositioning multiple widgets** — moves are validated one at a time against current positions, so swapping/shuffling widgets can transiently collide depending on the order you PATCH them. Sequence moves so no intermediate state overlaps (move to free space first, then into final slots), and check HTTP status per call — observed live during a layout rebuild, fixed by resequencing.
- PUT (Replace all widgets) is destructive to any widget not included in the payload — use PATCH per-widget instead unless a full rebuild is intended.
