---
name: dashboarding
license: Apache-2.0
description:
  Create, modify, and organise Grafana dashboards including panels, variables, transformations,
  thresholds, and annotations. Use when the user asks to create a Grafana dashboard, add a panel,
  configure a time series or stat panel, add template variables, set up dashboard linking, use
  transformations, configure thresholds, build a dashboard for a service, debug a "No data"
  dashboard, or export/push dashboard JSON. Triggers on phrases like "create dashboard", "add
  panel", "time series panel", "Grafana dashboard JSON", "template variables", "dashboard
  variable", "panel transformation", "threshold", "stat panel", "table panel", "Grafana
  annotations", or "dashboard folder".
---

# Grafana Dashboard Authoring

Dashboards are JSON documents stored in Grafana. Every dashboard has panels, variables, time
range, and refresh settings. Understanding the JSON schema lets you programmatically create and
modify dashboards via the API or Grafana Assistant tools.

---

## Rule zero: clone, don't author

**Before you write a single line of dashboard JSON, find a dashboard that already works in the target Grafana instance and clone its variable schema.** Authoring vars from scratch is where you'll waste 2 hours pushing v2, v3, v4, v5, v6, v7 to chase silent `$__all` expansion bugs.

```bash
# Pull a known-good reference dashboard
curl -s -H "Authorization: Bearer $GRAFANA_TOKEN" \
  "$GRAFANA_URL/api/dashboards/uid/<known-good-uid>" \
  | jq '.dashboard.templating.list' > /tmp/reference-vars.json
```

Match its `templating.list` shape exactly: same keys, same `query` field type (string vs object), same `current` shape, same `schemaVersion`. The dashboarding API accepts several variable shapes that all validate, but only some expand `$__all` correctly at panel render time. The reference dashboard tells you which one your Grafana likes.

If no reference exists, copy the canonical schema in [Template variables](#template-variables) below verbatim. Do not improvise.

---

## Dashboarding philosophy (the Datadog way)

When creating a new dashboard, default to a **service-oriented, multi-source, polished** layout. Think Datadog APM screens, not random panels stitched together. The goal is: someone unfamiliar with the service should land on the dashboard and understand its health in under 30 seconds.

### Core principles

1. **Service-oriented, not metric-oriented.** Build dashboards around a service, application, or business capability, not around a single data source. A "Checkout Service" dashboard beats a "Prometheus Metrics" dashboard every time.
2. **Multi-source where it earns its place.** Many services have metrics, logs, traces, and events; combining Prometheus + Loki + Tempo lets the operator pivot from "what's broken" to "why" without leaving the page. But add a source only when it genuinely applies — a metrics-only dashboard for a database (where the monitoring account has no log shipper or trace instrumentation) is correct, not incomplete. Don't bolt on an empty Traces row for the symmetry of it.
3. **Selectable everything.** Top of every dashboard: a small set of cascading variables (typically `datasource`, `namespace`, `instance`/`pod` or `db_instance`). Pick the smallest set that uniquely identifies the resource. **Do not invent five chained vars when two will do** — every extra chained var is another `$__all` failure mode.
4. **Pretty matters.** Dense, polished, readable. Consistent units, sensible thresholds, clean legends, intentional colors. A dashboard that looks ugly will not be trusted, even if the data is right.
5. **Top-down information density.** Headline KPIs up top, time series in the middle, deep diagnostics at the bottom. Eyes flow "is it healthy?" → "what changed?" → "where do I dig?"

### Standard service dashboard layout

Use this as the default skeleton when someone says "build a dashboard for service X":

```
┌─────────────────────────────────────────────────────────────────────┐
│ Variables: $datasource   $namespace   $instance (or $service)       │
│            (smallest set that uniquely identifies the resource)     │
├─────────────────────────────────────────────────────────────────────┤
│ Row: Overview (collapsed = false)                                   │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│ │ RPS  │ │Error%│ │ p50  │ │ p95  │ │ p99  │ │Uptime│   <- stats  │
│ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘               │
├─────────────────────────────────────────────────────────────────────┤
│ Row: Golden Signals (RED + USE)                                     │
│ ┌─────────────────────┐ ┌─────────────────────┐                     │
│ │ Request rate by     │ │ Error rate by       │   <- timeseries    │
│ │ status_code         │ │ endpoint            │                     │
│ └─────────────────────┘ └─────────────────────┘                     │
│ ┌─────────────────────┐ ┌─────────────────────┐                     │
│ │ Latency heatmap     │ │ Latency p50/p95/p99 │                     │
│ └─────────────────────┘ └─────────────────────┘                     │
├─────────────────────────────────────────────────────────────────────┤
│ Row: Resources (collapsed)                                          │
│  CPU, memory, GC, threads, connection pools, queue depth            │
├─────────────────────────────────────────────────────────────────────┤
│ Row: Dependencies (collapsed)                                       │
│  Downstream call rate/latency/errors per dependency, DB pool stats  │
├─────────────────────────────────────────────────────────────────────┤
│ Row: Logs (collapsed, if a log source applies)                      │
│  Loki logs panel filtered by $service, error rate from logs         │
├─────────────────────────────────────────────────────────────────────┤
│ Row: Traces (collapsed, if traced)                                  │
│  Tempo service map, slow traces table, exemplar links               │
└─────────────────────────────────────────────────────────────────────┘
```

Drop the Logs and Traces rows entirely when the service has no log/trace signal (common for database dashboards) — an empty row is worse than no row.

### Variables every service dashboard should have

Use this canonical shape. Keep variables few and focused: a datasource picker plus 1-2 selectors. **The `query` field is a plain string, not an object — see [Template variables](#template-variables) for why this matters.**

```json
"templating": {
  "list": [
    {
      "name": "datasource",
      "type": "datasource",
      "query": "prometheus",
      "current": { "text": "Mimir", "value": "<datasource-uid>" },
      "hide": 0
    },
    {
      "name": "namespace",
      "type": "query",
      "datasource": { "type": "prometheus", "uid": "${datasource}" },
      "query": "label_values(up, namespace)",
      "refresh": 2,
      "sort": 1,
      "includeAll": false,
      "multi": false,
      "label": "Namespace",
      "current": { "text": "monitoring", "value": "monitoring" }
    },
    {
      "name": "instance",
      "type": "query",
      "datasource": { "type": "prometheus", "uid": "${datasource}" },
      "query": "label_values(up{namespace=\"$namespace\"}, instance)",
      "refresh": 2,
      "sort": 1,
      "includeAll": true,
      "multi": true,
      "label": "Instance",
      "current": { "text": "All", "value": "$__all" }
    }
  ]
}
```

**Selector pattern in panel queries:** match panel filters to the var shape exactly:

```promql
sum by (instance) (rate(http_requests_total{namespace="$namespace", instance=~"$instance"}[5m]))
```

`$namespace` is single-value (no `=~`); `$instance` is multi (uses `=~` so `$__all` expands to a real OR-list).

### Multi-source: how to actually mix them

- **Metrics + Logs:** Add a Loki panel filtered by `{service="$service", cluster="$cluster"}` showing recent errors. Link a metrics panel's data link to the logs panel pre-filtered by time range.
- **Metrics + Traces:** Use exemplars in time series panels (Prometheus + Tempo) so users can click a latency spike and jump straight to the trace.
- **Logs + Traces:** Loki's "Derived fields" link `traceID` from log lines into Tempo. In the dashboard, surface a "Recent slow traces" table panel from Tempo right next to the logs.
- **Annotations from a different source than the panel:** A timeseries on Prometheus metrics with deployment annotations from Loki (`{job="deployments"} |= "service=$service"`) is the chef's kiss.

### Visual polish checklist

Before considering a dashboard done:

- [ ] Every panel has a title, and titles are consistent ("Request rate" not "rps_panel_3")
- [ ] Every panel has correct units (`reqps`, `ms`, `percentunit`, `bytes`, etc.) — never raw numbers when a unit applies
- [ ] Thresholds defined where they make sense (error rate, latency, saturation) with green/yellow/red
- [ ] Stat panels at the top use `colorMode: "value"` or `"background"` for at-a-glance health
- [ ] Time series legends use `displayMode: "table"` with `calcs: ["last", "mean", "max"]` so values are readable
- [ ] Panels grouped into collapsible rows so the dashboard isn't a wall of text
- [ ] Dashboard tags include `service:<name>`, `team:<owner>`, `tier:<criticality>` for discoverability
- [ ] Dashboard links at the top point to the runbook, the repo, and the on-call rotation
- [ ] Dark mode looks good (it's the default — test it)
- [ ] No "N/A" or empty panels when variables are at default values

### Anti-patterns to avoid

- ❌ **Authoring vars from scratch instead of cloning a working dashboard.** This is the #1 way to lose half a day.
- ❌ **Object-form query field** (`"query": { "query": "..." }`) — silently breaks `$__all` expansion. Always use a plain string.
- ❌ **`current.selected: true`** on query vars — pins the literal `$__all` placeholder. Omit the `selected` key entirely.
- ❌ **Custom `allValue: ".+"`** — breaks when bookmarks preserve the literal `$__all` string. Use Grafana's default expansion.
- ❌ **Splicing a multi-value var mid-regex** (`pod=~"prefix-$var.*"`) — fails on `All`. Anchor on a static label prefix.
- ❌ **Direct-DB query panels on a monitoring datasource.** Monitoring service accounts (e.g. `svc_grafana_user`) should hold metrics/exporter grants only — never `SELECT` on application schemas. If a `mysql`/`postgres` datasource panel reads `information_schema` or app tables and comes back empty, that's the privilege boundary working as intended, not a bug. Keep dashboards metrics-only. **Exception:** dedicated DBA dashboards (per-instance, SQL-Server-style) intentionally combine exporter metrics with direct-SQL panels for deep introspection (sessions, waits, locks, top queries, index health). These use a separate datasource picker scoped to DBA-specific accounts with appropriate read grants (VIEW SERVER STATE, pg_monitor). The two concerns coexist on one dashboard via two separate template variables (one for metrics, one for SQL).
- ❌ **Assuming `pg-${instance}` or any var-in-uid interpolation works.** Grafana 13 does NOT interpolate custom/query variables into a panel's datasource UID at render time (despite the panel-query resolver API claiming it does). The only thing that reliably resolves in a datasource uid field is a datasource-TYPE variable. If you need both a Prometheus label and a SQL datasource driven by one concept, use two explicit template variables: one query-type for metrics, one datasource-type for SQL.
- ❌ **Blaming the dashboard when SQL panels show "No data" or "no default database."** Always verify datasource auth first (`/api/datasources/uid/<uid>/health` or `/api/ds/query` with a trivial `SELECT 1`). Grafana's "no default database configured" error is often a misleading wrapper around a PostgreSQL auth failure (28P01) or a misconfigured datasource (`user=""` because TF nested it in the wrong field).
- ❌ Ignoring an *available* second source that would add context — if logs/traces exist for the service, link them; just don't fabricate empty rows for sources that don't exist
- ❌ Hardcoded service or cluster names in queries — use variables
- ❌ A wall of panels with no rows or grouping — even 40+ panels should collapse into labelled rows
- ❌ Inconsistent time aggregations across panels (one shows `[5m]` rate, another shows `[1m]`)
- ❌ Stat panels showing raw counts when a rate is what matters
- ❌ Tables of metrics that should be time series, or time series that should be stats
- ❌ "Catch-all" or "Everything" dashboards — build per-service, link between them

---

## Dashboard JSON structure

```json
{
  "title": "My Dashboard",
  "uid": "my-dashboard-v1",
  "tags": ["service", "production"],
  "time": { "from": "now-1h", "to": "now" },
  "refresh": "30s",
  "timezone": "browser",
  "schemaVersion": 39,
  "templating": { "list": [] },
  "annotations": { "list": [] },
  "panels": []
}
```

**Key fields:**
- `uid` - stable identifier used in URLs and API calls; keep it short and meaningful
- `schemaVersion` - **match the schemaVersion of a known-good dashboard in the same Grafana instance.** Built-in/Scenes-rendered dashboards in Grafana 11/12 commonly serialize as `39`. Newer manually-authored dashboards may use `41`. Mismatching schemaVersion against the rest of the instance is one of the silent ways `$__all` and other features start misbehaving — when in doubt, copy the value from your reference dashboard.
- `time.from` / `to` - supports relative (`now-1h`, `now-7d`) and absolute ISO timestamps
- `refresh` - auto-refresh interval (`"30s"`, `"1m"`, `"5m"`, `""` for off)

---

## Panel types and when to use them

| Panel | Use case |
|---|---|
| **Time series** | Any metric over time; the default choice for counters, rates, gauges |
| **Stat** | Single current value with optional sparkline (e.g. uptime, current RPS) |
| **Gauge** | Percent or value against a min/max (e.g. disk usage %) |
| **Bar gauge** | Compare multiple values side by side (e.g. top 10 services by RPS) |
| **Table** | Multi-column data (e.g. alert list with labels) |
| **Heatmap** | Distribution over time (e.g. request duration histogram) |
| **Histogram** | Value distribution (static, not over time) |
| **Pie chart** | Part-to-whole ratios |
| **Logs** | Loki log streams |
| **Traces** | Tempo trace search |
| **Text** | Markdown documentation panels |
| **Candlestick** | OHLC/financial data (or min/max/avg patterns) |
| **Node graph** | Service dependency graphs |
| **Geomap** | Geographic data |
| **Canvas** | Custom SVG-based layouts |
| **Flame graph** | CPU/memory profiling (Pyroscope) |
| **Alert list** | Show firing/recent alerts |

---

## Panel JSON structure

```json
{
  "id": 1,
  "type": "timeseries",
  "title": "Request Rate",
  "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 },
  "datasource": { "type": "prometheus", "uid": "${datasource}" },
  "targets": [
    {
      "expr": "sum(rate(http_requests_total{job=\"$job\"}[5m])) by (status_code)",
      "legendFormat": "{{status_code}}",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "reqps",
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "yellow", "value": 1000 },
          { "color": "red", "value": 5000 }
        ]
      }
    },
    "overrides": []
  },
  "options": {
    "legend": { "calcs": ["mean", "max", "last"], "displayMode": "table", "placement": "bottom" },
    "tooltip": { "mode": "multi", "sort": "desc" }
  }
}
```

**`gridPos`:** The dashboard uses a 24-column grid. Common widths: full-width=24, half=12, third=8, quarter=6. Height in grid units (1 unit ≈ 30px).

---

## Useful unit identifiers

```
# Rates
"reqps"      -- requests per second
"ops"        -- operations per second
"Bps"        -- bytes per second
"percentunit" -- 0.0-1.0 as percentage

# Storage
"bytes"      -- bytes (auto-scales to KB/MB/GB)
"decbytes"   -- decimal bytes (1 KB = 1000 B)

# Time
"ms"         -- milliseconds
"s"          -- seconds
"dtdurationms" -- duration in ms (shows as "1h 2m 3s")

# Counts
"short"      -- compact number (1.2k, 3.4M)
"none"       -- raw number
```

Full list: **Panel > Field > Unit** dropdown in Grafana UI, or the [units reference](https://grafana.com/docs/grafana/latest/panels-visualizations/configure-standard-options/#unit).

---

## Template variables

Variables make dashboards reusable across environments and services.

**Query variable (populates from metric labels):**

```json
{
  "name": "job",
  "type": "query",
  "datasource": { "type": "prometheus", "uid": "${datasource}" },
  "query": "label_values(up, job)",
  "refresh": 2,
  "includeAll": true,
  "multi": true,
  "sort": 1,
  "label": "Service",
  "current": { "text": "All", "value": "$__all" }
}
```

> **Critical:** `query` MUST be a plain string (not `{ query, refId }` object). The object
> form silently breaks `$__all` expansion: Grafana inlines the literal string `$__all` into
> your panel queries instead of expanding to a real OR-list of values, and every panel
> shows "No data". This bites hard because both forms validate fine and look correct in
> the UI. Always use the string form.

> **Also critical:** Do NOT set `current.selected: true`. That forces the literal `$__all`
> placeholder to stick instead of expanding. Use plain `{ text: "All", value: "$__all" }`
> with no `selected` key — that's the shape working built-in dashboards use.

> **Also critical:** Do NOT set a custom `allValue` like `".+"`. Let Grafana use its default
> `$__all` expansion. Custom allValues break when the URL preserves the literal `$__all`
> string in the variable state (which it routinely does on bookmarks and shared links).

**Constant variable:**

```json
{
  "name": "cluster",
  "type": "constant",
  "query": "production",
  "label": "Cluster"
}
```

**Custom variable (hardcoded option list):**

```json
{
  "name": "env",
  "type": "custom",
  "query": "production,staging,dev",
  "current": { "value": "production" }
}
```

**Interval variable (selectable rate/step window):**

```json
{
  "name": "interval",
  "type": "interval",
  "query": "1m,5m,15m,1h",
  "auto": true
}
```

Reference it as the range in rate queries: `rate(http_requests_total{...}[$interval])`. `auto: true` adds an `$__auto` option that scales the window to the dashboard's time range and resolution.

**Datasource variable (switch data sources without editing queries):**

Two valid shapes. Prefer the Grafana Scenes form (used by built-in dashboards):

```json
{
  "name": "datasource",
  "type": "datasource",
  "query": "prometheus",
  "current": { "text": "Mimir", "value": "<datasource-uid>" },
  "hide": 0
}
```

Legacy form (also works, but less compatible with Scenes-based panels):

```json
{
  "name": "datasource",
  "type": "datasource",
  "pluginId": "prometheus",
  "regex": "/Mimir|prometheus/",
  "includeAll": false
}
```

Reference it in panel datasource refs as `"uid": "${datasource}"`.

**Use variables in queries:**

```promql
# Reference a variable in a PromQL query
rate(http_requests_total{job=~"$job"}[5m])

# Multi-value variable uses regex OR automatically
# When $job = ["api", "worker"], it becomes job=~"api|worker"
```

**Chain variables** (second variable filters based on first):

```json
{
  "name": "pod",
  "query": "label_values(kube_pod_info{namespace=\"$namespace\"}, pod)"
}
```

---

## Transformations

Transformations run client-side after data is fetched, reshaping results without changing queries.

**Common transformations:**

```json
"transformations": [
  {
    "id": "merge",
    "options": {}
  },
  {
    "id": "organize",
    "options": {
      "renameByName": { "Value #A": "Request Rate", "Value #B": "Error Rate" },
      "excludeByName": { "Time": true }
    }
  },
  {
    "id": "calculateField",
    "options": {
      "alias": "Error %",
      "mode": "reduceRow",
      "reduce": { "reducer": "last" },
      "binary": {
        "left": "errors",
        "right": "total",
        "operator": "/"
      }
    }
  },
  {
    "id": "filterByValue",
    "options": {
      "filters": [{ "fieldName": "Error %", "config": { "id": "greater", "options": { "value": 0.01 } } }],
      "type": "include",
      "match": "any"
    }
  }
]
```

**Key transformation IDs:** `merge`, `organize`, `rename`, `calculateField`, `filterByValue`,
`groupBy`, `sortBy`, `limit`, `labelsToFields`, `seriesToRows`, `partitionByValues`.

---

## Dashboard linking

**Panel link (click a panel to go somewhere):**

```json
"links": [
  {
    "title": "Go to details",
    "url": "/d/details-dashboard?var-service=${__field.labels.service}",
    "targetBlank": false
  }
]
```

**Dashboard link (top-right corner links):**

```json
"links": [
  {
    "title": "Runbook",
    "url": "https://wiki.example.com/runbook/${job}",
    "icon": "external link",
    "targetBlank": true,
    "type": "link"
  }
]
```

**Built-in variables for links:**
- `${__value.raw}` - current data point value
- `${__field.labels.job}` - label value from current series
- `${__url.params}` - current URL query parameters (pass-through)
- `${__from}` / `${__to}` - current time range as Unix ms

---

## Annotations

Show events overlaid on time series panels (deployments, incidents, etc.).

**Query annotation from Loki:**

```json
{
  "datasource": { "type": "loki", "uid": "<loki-datasource-uid>" },
  "expr": "{job=\"deployments\"} |= \"deployed\"",
  "name": "Deployments",
  "iconColor": "blue",
  "titleFormat": "{{service}} deployed",
  "textFormat": "{{version}} by {{author}}"
}
```

> Datasource UIDs are opaque (e.g. `a1b2c3d4e5f6g7`), not the literal type name. Always look up the real UID with `curl /api/datasources/name/loki | jq .uid` or via the MCP `grafana_get_datasource` tool. Hardcoding `"uid": "loki"` works on no real Grafana.

**Query annotation from Prometheus:**

```json
{
  "datasource": { "type": "prometheus", "uid": "prometheus" },
  "expr": "changes(kube_deployment_status_observed_generation{namespace=\"production\"}[5m]) > 0",
  "step": "60s",
  "name": "Deployments",
  "iconColor": "blue",
  "titleFormat": "Deploy: {{deployment}}"
}
```

---

## Pushing dashboards: MCP vs curl

Two paths exist. They produce identical results in Grafana but cost wildly different amounts of LLM context.

| Path | When to use | Why |
|---|---|---|
| **MCP** (`grafana_update_dashboard`, `grafana_api_request`) | Surgical edits, single-panel changes, metadata tweaks (title, tags, refresh), small (<10 KB) dashboards | Tool args go inline in the tool call. Fine for small payloads. |
| **`curl -d @file`** | Whole-dashboard pushes ≥ 10 KB, regenerated dashboards, anything from a generator script | The kernel streams the file from disk to the socket; zero context cost. The MCP path inlines the entire JSON into the tool args, which can burn 15-20k tokens per push for a 60 KB dashboard. |

> **Rule of thumb:** if you produced the dashboard JSON via a Python/Jsonnet/etc. generator, push it with curl. If you're hand-tweaking one field, use MCP.

```bash
# Whole-dashboard push (curl, zero context cost)
jq -n --argfile d /tmp/my-dashboard.json '{
  dashboard: $d, folderUid: "<folder-uid>", overwrite: true,
  message: "Initial push (Datadog-style, generator v1)"
}' > /tmp/post-body.json

curl -s -X POST \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/post-body.json \
  "$GRAFANA_URL/api/dashboards/db" | jq
```

After every push, verify version bump and panel count via `grafana_get_dashboard_summary` (MCP) — much cheaper than re-reading the full JSON.

---

## No-data triage runbook

Dashboard pushed cleanly but every panel says "No data". The data exists in the data source. What now?

Walk this list in order. The first three account for ~95% of cases.

1. **Run one panel query directly against the datasource** with the variables substituted to *real* values you know exist. If this returns data, the issue is variable substitution; if it doesn't, your panel queries are wrong.

   ```python
   # via grafana_query_prometheus MCP tool
   min(mysql_up{namespace="monitoring", db_instance=~"snipeit"})
   ```

2. **Inspect `templating.list` of the live dashboard** with `grafana_get_dashboard_property uid=<uid> jsonPath=$.templating.list`. Compare keystroke-for-keystroke against a known-good dashboard's vars in the *same* Grafana instance:

   - Is `query` a plain string or an object? (Must be string.)
   - Does any var have `current.selected: true`? (Remove it.)
   - Does any var have a custom `allValue`? (Remove it.)
   - Does the datasource var use the Grafana Scenes form (`query: "prometheus"`) or the legacy form (`pluginId: "prometheus"`)? Built-in dashboards use Scenes form; mismatching can break Scenes-rendered panels.
   - Does `schemaVersion` match the working reference dashboard?

3. **Test `$__all` expansion at the URL level.** Open the dashboard with a clean URL (no `var-*` query params). If it works on a clean URL but breaks on bookmarked/shared URLs that pass `var-foo=$__all`, that's the literal-`$__all`-in-regex bug — your var has the wrong shape (objects, `selected:true`, or custom `allValue`).

4. **Stop iterating, start cloning.** If you've pushed v3+ and still see No data, **nuke the dashboard and clone a working one's `templating.list` verbatim**. Authoring-from-scratch into a Grafana with custom var schema expectations is a losing fight. Five minutes of cloning beats five hours of debugging.

   ```bash
   # Pull canonical vars from a working dashboard
   curl -s -H "Authorization: Bearer $GRAFANA_TOKEN" \
     "$GRAFANA_URL/api/dashboards/uid/<known-good-uid>" \
     | jq '.dashboard.templating.list' > /tmp/good-vars.json
   ```

5. **Check exporter labels.** Run `count by (<label>) (<metric>{})` on the data source for each label your selectors filter on. If you're selecting on `db_account` but the metric exposes `account`, no panel will ever return data. Match selectors to actual label names.

6. **Check datasource auth.** Before debugging the dashboard further, confirm the datasource itself works: `GET /api/datasources/uid/<uid>/health` or run `SELECT 1` via `/api/ds/query`. Grafana's "no default database configured" error often masks a PostgreSQL 28P01 auth failure (wrong password, user field empty because TF put it in the wrong block). If the health check fails, the problem is infra not the dashboard.

---

## Per-instance DBA dashboards (mixed metrics + SQL)

For DBA-oriented dashboards that combine exporter metrics with direct-SQL catalog queries (sessions, locks, top queries, index health), the per-instance model is the only architecture that works.

**Why:** direct SQL physically connects to ONE database on ONE instance. A fleet/All model (multi-select `db_instance`) fights this because the SQL datasource can't target "all" simultaneously. The SQL Server dashboard avoids this by monitoring one server per page.

**Two-picker model (proven on Grafana 13):**

```json
{
  "name": "db_instance", "type": "query", "label": "Instance (metrics)",
  "query": "label_values(pg_up{namespace=\"$namespace\"}, db_instance)",
  "includeAll": false, "multi": false
},
{
  "name": "pg_ds", "type": "datasource", "label": "Instance (SQL)",
  "query": "grafana-postgresql-datasource",
  "regex": "/PostgreSQL - /"
}
```

- Metric panels reference `${datasource}` (Mimir) with `db_instance=~"$db_instance"`.
- SQL panels reference `${pg_ds}` directly in their datasource uid field (datasource-type vars DO interpolate).
- The user sets both to the same instance; an in-dashboard text panel documents the pairing convention.
- Hide always-constant vars (datasource, namespace) with `hide: 2`.

**What does NOT work (Grafana 13):**
- `uid: "pg-${instance}"` concatenation in panel datasource: resolver API says yes, live render says no.
- Hidden datasource var with regex `/^pg-${instance}$/` chaining off another var: doesn't re-evaluate.
- A single custom var driving both PromQL labels and datasource uid: fundamentally impossible (two different value spaces).

**Datasource naming convention:**
- PostgreSQL: `pg-<db_instance_label>` (e.g. `pg-goalert`)
- MSSQL: `mssql-<name>` (e.g. `mssql-canld`)
- MySQL: `mysql-<name>` (e.g. `mysql-snipeit`)

**Datasource config gotcha (Grafana provider):**
The `grafana_data_source.postgres` resource requires `username` as a **top-level field**, not inside `secure_json_data_encoded`. Nesting `user` in `secure_json` silently drops it (the provider ignores it there), producing `user=""` on the live datasource. Grafana then falls back to whatever the RDS default user is (typically fails auth). Same pattern for `database_name`: must be top-level, not in `jsonData`.

---

## PostgreSQL / SQL datasource dashboards

When building dashboards sourced from a PostgreSQL (or MySQL/MSSQL) datasource rather than Prometheus, different rules apply. The GoAlert IRM dashboard is the canonical example.

### Key differences from PromQL dashboards

| Concern | Prometheus | PostgreSQL |
|---|---|---|
| Time filtering | Built-in `$__timeFilter` on every metric | You must add `WHERE $__timeFilter(column)` to every SQL query |
| Time series format | Native | Requires `format: "time_series"` + specific column naming (`time`, `metric`, `value`) |
| Table format | Use transformations | `format: "table"` + explicit `SELECT col AS "Display Name"` |
| No data | Usually means no metrics scraped | Could mean: wrong DB, no grants, empty table in time range, auth failure |
| Variables | `label_values()` queries | Raw SQL: `SELECT DISTINCT col FROM table` |

### SQL time-series panel pattern

For time series panels, Grafana's PostgreSQL plugin requires specific column naming:

```sql
SELECT
  $__timeGroup(created_at, $__interval) AS time,
  service_name AS metric,
  COUNT(*) AS value
FROM alerts
WHERE $__timeFilter(created_at)
GROUP BY 1, service_name
ORDER BY 1
```

- `time` column (timestamp): use `$__timeGroup(col, $__interval)` for adaptive granularity, or `$__timeGroup(col, '1h')` for fixed
- `metric` column (string): becomes the series legend name
- `value` column (numeric): the Y-axis value
- Always include `WHERE $__timeFilter(col)` to respect the dashboard time picker
- Always `ORDER BY 1` (time) for correct rendering

### SQL stat panel pattern

For stat panels showing a single aggregated number:

```sql
SELECT COUNT(*) AS "Active Alerts"
FROM alerts
WHERE status IN ('triggered', 'active')
```

- Name the column with a display-friendly alias (`AS "Active Alerts"`)
- Use `textMode: "auto"` to avoid showing the column name as a label
- For time-scoped stats: add `WHERE $__timeFilter(created_at)` 
- For all-time stats: omit the time filter entirely

### SQL table panel pattern

```sql
SELECT
  a.created_at AS "Created",
  a.status::text AS "Status",
  s.name AS "Service",
  a.summary AS "Summary"
FROM alerts a
JOIN services s ON s.id = a.service_id
WHERE a.status IN ('triggered', 'active')
ORDER BY a.created_at DESC
```

- Cast enum types explicitly: `status::text` (PostgreSQL enums return raw enum values otherwise)
- Use quoted column aliases for display names: `AS "Created"` (case-sensitive in PG)
- Don't use `LIMIT` unless the user wants one: Grafana tables paginate natively
- JOINs are fine: resolve IDs to human-readable names in the query, not in transformations

### Pie chart / bar gauge with SQL

Grafana's pie chart and bar gauge panels struggle with raw table output from SQL. The fix is:

1. Name columns `metric` and `value` in the query
2. Add a `rowsToFields` transformation to convert rows into named fields
3. Set `reduceOptions.values: true` so Grafana uses actual values

```json
"targets": [{
  "rawSql": "SELECT status::text AS metric, COUNT(*) AS value FROM outgoing_messages WHERE $__timeFilter(created_at) GROUP BY status ORDER BY value DESC",
  "format": "table"
}],
"transformations": [{
  "id": "rowsToFields",
  "options": {"mappings": [
    {"fieldName": "metric", "handlerKey": "field.name"},
    {"fieldName": "value", "handlerKey": "field.value"}
  ]}
}]
```

Without `rowsToFields`, pie charts show a single "count" slice (all values aggregated into one field).

### Bar chart panel: "No numeric fields found"

The `barchart` panel type is unreliable with PostgreSQL datasources. `bigint` columns from PG are often returned as strings by the Grafana PG plugin, causing "No numeric fields found" errors. 

**Workaround**: use `bargauge` panel type instead. It handles the data correctly and produces similar horizontal bar visualizations. Set `orientation: "horizontal"` and `displayMode: "gradient"`.

### Table cell styling

Rich table formatting uses `fieldConfig.overrides` with cell options:

```json
"overrides": [
  {
    "matcher": {"id": "byName", "options": "Status"},
    "properties": [
      {"id": "custom.cellOptions", "value": {"type": "color-text"}},
      {"id": "mappings", "value": [{"options": {
        "Active": {"color": "orange", "index": 0},
        "Triggered": {"color": "red", "index": 1},
        "Delivered": {"color": "green", "index": 2},
        "Failed": {"color": "red", "index": 3}
      }, "type": "value"}]}
    ]
  },
  {
    "matcher": {"id": "byName", "options": "Total"},
    "properties": [
      {"id": "custom.cellOptions", "value": {"mode": "gradient", "type": "gauge", "valueDisplayMode": "text"}},
      {"id": "color", "value": {"mode": "continuous-blues"}}
    ]
  }
]
```

Cell option types: `auto`, `color-text`, `color-background-solid`, `gauge` (with `mode: "gradient"`). Gauge cells create inline bar charts inside table cells.

### PostgreSQL datasource auth failures

The most common "No data" cause for SQL dashboards is insufficient grants. When you see empty panels but the query executes fine in Explore:

1. Check `GET /api/datasources/uid/<uid>/health` for connection errors
2. Run `SELECT current_user, pg_has_role(current_user, 'rds_superuser', 'member')` to verify permissions
3. The fix is always: `GRANT SELECT ON ALL TABLES IN SCHEMA public TO <user>; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO <user>;`
4. If using Aurora with reader endpoints: verify you're connecting to the **writer** if you need real-time data (readers may have replication lag or point to stale snapshots)

### Datasource pointing at wrong DB instance

When the GoAlert dashboard showed stale data (last entry May 29), the datasource was pointed at the Aurora cluster writer endpoint (`goalert.cluster-cksjnkohso8n.us-east-2.rds.amazonaws.com`) but the live application writes to a completely different standalone RDS instance (`rds-ue2-nonprod-goalert.cearnwjuwhd2.us-east-2.rds.amazonaws.com`). 

**Debugging approach:**
1. Query `SELECT MAX(created_at) FROM <main_table>` via the Grafana datasource
2. Compare with what the app UI shows
3. If stale: check the datasource host vs the app's actual `DB_URL` (from env, SM, or process environment)
4. Use `pg_is_in_recovery()` to check if you're on a replica
5. Use `SELECT datname FROM pg_database WHERE datistemplate = false` to verify the database exists

### Default time range for sparse data

If a dashboard sources from a system with infrequent events (on-call alerts, deployments, audit logs), set the default time range to **30 days** (`"time": {"from": "now-30d", "to": "now"}`). A 24-hour default on a system that pages twice a week will always show "No data".

### Macros reference (PostgreSQL plugin)

| Macro | Expands to | Use |
|---|---|---|
| `$__timeFilter(col)` | `col BETWEEN '...' AND '...'` | Time range filter (most common) |
| `$__timeFrom()` | Start time as string | Manual WHERE clauses |
| `$__timeTo()` | End time as string | Manual WHERE clauses |
| `$__timeGroup(col, interval)` | `floor(extract(epoch from col)/N)*N` | Time-series bucketing |
| `$__timeGroup(col, $__interval)` | Adaptive bucket size | Best for time series |
| `$__unixEpochFilter(col)` | For Unix timestamp columns | Rarely needed with PG |

---

Every dashboard pushed to a shared Grafana should have a JSON backup committed under `observability/backups/dashboards/<uid>.json`. The backup is the source of truth: dashboards drift in the UI, repos don't.

```bash
# After a successful push
curl -s -H "Authorization: Bearer $GRAFANA_TOKEN" \
  "$GRAFANA_URL/api/dashboards/uid/<uid>" \
  | jq '.dashboard' > observability/backups/dashboards/<uid>.json
```

If a dashboard is generated, commit both the generator (`build_<uid>.py`) and the rendered JSON. Reviewers diff the JSON; the generator is for the next iteration.

---

## Dashboard via API

```bash
# Create or update a dashboard
curl -s -X POST \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  "https://myorg.grafana.net/api/dashboards/db" \
  -d '{
    "dashboard": { <dashboard JSON> },
    "folderUid": "my-folder",
    "overwrite": true,
    "message": "Updated via API"
  }'

# Get a dashboard by UID
curl -s -H "Authorization: Bearer <API_KEY>" \
  "https://myorg.grafana.net/api/dashboards/uid/my-dashboard-v1" | jq '.dashboard'

# Search dashboards
curl -s -H "Authorization: Bearer <API_KEY>" \
  "https://myorg.grafana.net/api/search?query=kubernetes&type=dash-db" | \
  jq '.[] | {uid, title, folderTitle}'

# Create a folder
curl -s -X POST \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  "https://myorg.grafana.net/api/folders" \
  -d '{"uid": "platform-team", "title": "Platform Team"}'
```

---

## References

- [Grafana dashboard documentation](https://grafana.com/docs/grafana/latest/dashboards/)
- [Grafana panel types reference](https://grafana.com/docs/grafana/latest/panels-visualizations/)
- [Grafana HTTP API — dashboards](https://grafana.com/docs/grafana/latest/developers/http_api/dashboard/)
- [Dashboard variables](https://grafana.com/docs/grafana/latest/dashboards/variables/)
- [Transformations reference](https://grafana.com/docs/grafana/latest/panels-visualizations/query-transform-data/transform-data/)

---

## Attain instance specifics

> Attain instance specifics (datasource UIDs, plugin catalog, conventions) live in `references/attain-observability.md`.
