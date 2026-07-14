# Verify (local-on-VPN, then confirm in Grafana)

Instrumentation is not done until you have seen all four signals in Grafana. You do not have to deploy first: on the Attain VPN you can run the app locally, point it at the gateways, send traffic, and confirm.

## 1. Run locally with a local identity

Set a `local` identity so test telemetry does not pollute prod dashboards, and export direct to the gateways (no local collector needed):

```bash
export OTEL_SERVICE_NAME=myservice-local
export OTEL_RESOURCE_ATTRIBUTES=service.namespace=lending,deployment.environment=local
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
# Per-signal endpoint vars are used EXACTLY as given (the SDK does NOT append /v1/<signal>),
# so include the full path. (Only the base OTEL_EXPORTER_OTLP_ENDPOINT gets /v1/<signal> appended.)
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://tempo.observability-internal.attainfinance.com/v1/traces
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://mimir.observability-internal.attainfinance.com/otlp/v1/metrics
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://loki.observability-internal.attainfinance.com/otlp/v1/logs
export PYROSCOPE_SERVER_ADDRESS=https://pyroscope.observability-internal.attainfinance.com
export PYROSCOPE_APPLICATION_NAME=myservice-local
dotnet run
```

(On VPN. If DNS does not resolve `*.observability-internal.attainfinance.com`, you are off VPN.)

## 2. Generate traffic

Hit the real endpoints so spans/metrics/logs/profiles are produced:

```bash
for i in $(seq 1 50); do curl -s http://localhost:5000/your-endpoint > /dev/null; done
# include an error path so you get error spans/logs:
curl -s http://localhost:5000/known-bad
```

Wait ~30 to 60 seconds for the first batches to export.

## 3. Confirm each signal in Grafana (via the grafana MCP)

Use the `grafana-selfhosted` MCP tools (read-only):

**Metrics (Mimir):**
```
query_prometheus  datasourceUid=eeou8qj3gbvgge
  expr: http_server_request_duration_count{service_name="myservice-local"}
  expr: process_runtime_dotnet_gc_collections_count{service_name="myservice-local"}
```
Non-zero = metrics flow.

**Logs (Loki):**
```
query_loki_logs  datasourceUid=eeou8ipbcojcwc
  query: {service_name="myservice-local", deployment_environment="local"}
  query: {service_name="myservice-local"} | trace_id != ""    # confirms trace correlation
```
Lines present and carrying `trace_id` = logs flow and correlate.

**Traces (Tempo):** search by service in Grafana Explore (Tempo, uid `aeou8l7tjqk8wd`):
```
{resource.service.name="myservice-local" && resource.deployment.environment="local"}
```
Or confirm span metrics exist in Mimir: `traces_spanmetrics_calls_total{service="myservice-local"}`.

**Profiles (Pyroscope):**
```
list_pyroscope_profile_types  data_source_uid=bfojmhghtbhtsc
```
then query a profile filtered to `service_name="myservice-local"`; confirm a `process_cpu` profile exists.

## 4. Confirm correlation (the payoff)

In Tempo, open a trace, then:
- follow a span's log link to Loki (tracesToLogsV2),
- see RED metrics for the span (tracesToMetrics),
- open the CPU flame graph for a span (tracesToProfiles, requires the Pyroscope span processor from `profiling.md`).

If all four resolve, the service is fully instrumented.

## 5. Common "no data" causes

| Symptom | Cause | Fix |
|---|---|---|
| Nothing anywhere | off VPN / DNS not resolving | connect VPN; `nslookup mimir.observability-internal.attainfinance.com` |
| Metrics but no traces | no `AddSource` / instrumentation, or sampled out | register sources; sample 100% locally |
| Logs but no `trace_id` | logging not wired to OTel, or logging outside a span | use the OTel logging provider (`logs.md`) |
| `service_name` wrong case / missing | not lowercase, or resource not set on the signal | lowercase `OTEL_SERVICE_NAME`; `SetResourceBuilder` on every signal |
| No profiles | profiler not loaded (`CORECLR_*` unset) or Lambda | set profiler env (`profiling.md`); profiling N/A on Lambda |
| Metrics missing `deployment_environment` | resource attr not promoted | ensure `deployment.environment` in `OTEL_RESOURCE_ATTRIBUTES` |

## 6. Before calling it done

- All four signals visible for the service, filtered to your env.
- Logs carry `trace_id`; at least one trace links to logs and (non-Lambda) to a profile.
- No PII in any attribute, label, or log body (spot-check a few spans/logs).
- Then deploy with the real `deployment.environment` (`Prod`/`NONPROD`) and the target's export path (`deployment-targets.md`).
