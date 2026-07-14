# Attain Observability Reference

Attain's production Grafana conventions (grafana.attainfinance.com). This file holds the
instance-specific values (datasource UIDs, the installed plugin catalog, naming conventions)
that the generic `dashboarding`, `grafana-oss`, and `promql` skills deliberately keep out of
their teaching content. When you author against Attain's Grafana, look here for the real values.

## Core datasource UIDs

Datasource UIDs are opaque, not the literal type name. Hardcoding `"uid": "loki"` or
`"uid": "prometheus"` works on no real Grafana. Confirm a UID at runtime with
`curl /api/datasources/name/<name> | jq .uid` or via the MCP `grafana_get_datasource` tool
before relying on the values below.

| Datasource | Type | UID |
|---|---|---|
| Mimir (metrics) | `prometheus` | `eeou8qj3gbvgge` |
| Loki (logs) | `loki` | `eeou8ipbcojcwc` |

## Installed Grafana plugins (Attain Finance)

Use this for *what's available*. Don't waste tokens listing plugins inline in dashboards — the
deployment-truth lives in `grafana-plugins.yaml` (Helm values) and can be queried at runtime.

### High-signal plugins (the ones we actually use in dashboards)

| Kind | Plugin | Used for |
|---|---|---|
| Datasource | `prometheus` (Mimir UID `eeou8qj3gbvgge`) | All metric queries |
| Datasource | `loki` (UID `eeou8ipbcojcwc`) | Log panels, log-derived annotations |
| Datasource | `tempo` | Trace panels, exemplar links |
| Datasource | `mysql`, `mssql`, `grafana-postgresql-datasource` | Dedicated DBA-scoped query dashboards only — **not** on a monitoring/exporter dashboard (see anti-patterns) |
| Datasource | `cloudwatch` | YACE-imported AWS metrics, AWS log groups |
| Datasource | `yesoreyeram-infinity-datasource` | Ad-hoc HTTP/JSON sources |
| App | `grafana-metricsdrilldown-app`, `grafana-lokiexplore-app`, `grafana-exploretraces-app`, `grafana-pyroscope-app` | Drilldown links from dashboard panels |
| App | `grafana-synthetic-monitoring-app` | Synthetics dashboards |
| Panel | `vonage-status-panel` | Compact health indicators |
| Panel | `grafana-polystat-panel` | Hex-grid fleet health |
| Panel | `marcusolsson-treemap-panel` | Resource breakdowns (cost, RDS sizes) |
| Panel | `grafana-clock-panel` | Dashboard headers |
| Panel | `grafana-graphviz-panel` | Service maps from Tempo metrics-generator |

### Special-plugin panels (hard-won schemas)

Third-party panels do **not** follow the built-in `options` conventions. Read the plugin's
`src/module.ts` (the `setPanelOptions` builder) before authoring, and clone a working instance
if one exists. Two we use, with the traps that cost real time:

**`grafana-polystat-panel`** (hex-grid fleet health — one polygon per series):

- All config lives under `panel.options.*` (the normal place).
- One target, a **range** query (`instant: false`), `legendFormat: "{{label}}"` — one polygon per returned series.
- Thresholds use the plugin's own shape, not Grafana's: `globalThresholdsConfig: [{ "color": "#f53636", "state": 2, "value": 0 }, { "color": "#299c46", "state": 0, "value": 1 }]` where `state` is `0=ok, 1=warn, 2=crit, 3=custom`.
- **Landmine:** `globalTextFontFamily` is a `Select` bound to a fixed enum — only `Arial | Helvetica | Helvetica Neue | Inter | Roboto | Roboto Mono` are valid. Passing a CSS font stack (`"Inter, Roboto, sans-serif"`) **crashes the panel to a blank render**, no error.
- **Safe baseline** (don't fight it): leave `globalAutoScaleFonts: true`, `globalGradientsEnabled: true`, `globalTextFontAutoColorEnabled: true`, `autoSizeColumns/Rows/Polygons: true`, and set **no** `globalTextFontColor`, `globalTextFontFamily`, `globalPolygonSize`, `layoutNumColumns`, or font-size keys. Theme-aware text never crashes and looks fine.
- Best with a real fleet (5+ instances). One lonely hexagon looks silly — use a `stat` instead until the fleet grows.

**`vonage-status-panel`** (compact multi-metric health card):

- **All options live at the panel ROOT, not under `panel.options.*`.** `colorMode: "Panel"`, `colors: { ok, warn, crit, disable }` as `rgba(...)`, `flipCard`, `isGrayOnNoData`, `maxAlertNumber` are all siblings of `type`/`title`. `options` and `fieldConfig` stay minimal (`{}` / `{defaults:{},overrides:[]}`).
- Each target is a normal `{refId, expr, legendFormat}` **plus** a merged display block on the same object: `aggregation: "Last"`, `valueHandler: "Number Threshold"`, `crit`, `warn`, `units`, `decimals`, `display: true`, `displayType: "Regular"`.
- **Landmine:** a "down count" target written as `count(metric == 0)` returns an **empty vector** when nothing is down, which `isGrayOnNoData` then grays out. Write it as `count(metric) - sum(metric)` so it's always a real number.

> General rule reinforced by both: **never splice a multi-value template var into the middle of a regex matcher** (`pod=~"prefix-$var.*"`). When the var resolves to `All` it interpolates badly and matches nothing. Anchor on a static label prefix instead.

### Looking up what's installed (live)

```bash
# All plugins, kind + id + version
curl -s -H "Authorization: Bearer $GRAFANA_TOKEN" \
  "$GRAFANA_URL/api/plugins" | jq -r '.[] | "\(.type)\t\(.id)\t\(.info.version)"' | sort

# Just configured datasources (with UIDs)
curl -s -H "Authorization: Bearer $GRAFANA_TOKEN" \
  "$GRAFANA_URL/api/datasources" | jq -r '.[] | "\(.type)\t\(.uid)\t\(.name)"' | sort
```

> The full Attain catalog is large (~85 datasource plugins, ~33 panel plugins enabled). Don't memorize it; query it.
