# Deployment targets

The app code (`setup.md`) is identical everywhere because it reads `OTEL_EXPORTER_OTLP_ENDPOINT` from the environment. What changes per target is **where that endpoint points** and **how profiles get out**. Pick your target.

Summary:

| Target | OTLP endpoint (app sends here) | Collector topology | Profiles |
|---|---|---|---|
| EC2 Linux | `http://localhost:4318` | local `otelcol-contrib` (systemd) to gateways | Pyroscope SDK push direct |
| EC2 Windows/IIS | `http://localhost:4318` | local `otelcol-contrib` to gateways | SDK push (see profiling.md) |
| AWS Lambda (.NET) | ADOT collector extension (local) | ADOT layer to gateways | N/A (ephemeral) |
| EKS (Docker) | `http://$NODE_IP:4318` | node Grafana Alloy DaemonSet | Pyroscope SDK push direct |
| ECS (Docker) | `http://localhost:4318` | OTel Collector sidecar in the task | Pyroscope SDK push direct |

---

## EC2, Linux

App exports OTLP to a local `otelcol-contrib` (systemd service) on `localhost:4317/4318`; the collector fans out to the four gateways. Set on the service unit or the app environment:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_SERVICE_NAME=myservice
OTEL_RESOURCE_ATTRIBUTES=service.namespace=lending,service.version=1.4.2,deployment.environment=Prod
PYROSCOPE_SERVER_ADDRESS=https://pyroscope.observability-internal.attainfinance.com
PYROSCOPE_APPLICATION_NAME=myservice
```

If no local collector exists, the app may export OTLP **directly** to the gateways (metrics to mimir `/otlp`, logs to loki `/otlp`, traces to tempo) over VPN: set per-signal endpoints (see "direct export" below). Prefer the local collector when present (batching, retries, resource detection).

## EC2, Windows / IIS

Same local-collector model. The collector and host-level receivers are already documented in the repo runbooks `observability/OTEL-ONBOARD-APP.md` and `OTEL-WINDOWS-RUNBOOK.md` (do not re-create them). For the app, set app-pool env vars:

```powershell
OTEL_EXPORTER_OTLP_ENDPOINT = http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL = http/protobuf
OTEL_SERVICE_NAME           = myservice
OTEL_RESOURCE_ATTRIBUTES    = deployment.environment=Prod
```

For **.NET Framework / OWIN / VB** apps where you cannot edit hosting code, use the zero-code agent: `references/dotnet-framework-iis.md`. **No continuous profiling on Windows** (the Pyroscope profiler is Linux-only), see `profiling.md`.

## AWS Lambda (.NET)

Lambda is special: short-lived, no persistent collector, no continuous profiling.

- **Traces + metrics:** either the **AWS Distro for OpenTelemetry (ADOT) Lambda layer** (a collector extension inside the execution environment that buffers and exports), or instrument in code: add `OpenTelemetry.Instrumentation.AWSLambda` (`AddAWSLambdaConfigurations()`) and `OpenTelemetry.Instrumentation.AWS` (`AddAWSInstrumentation()`), then wrap the handler with `AWSLambdaWrapper.Trace()` / `TraceAsync()` (it creates and exports the per-invocation span, so you do not lose data when the environment freezes). Set `DisableAwsXRayContextExtraction = true` if you are not using X-Ray. Point the OTLP exporter at the gateways.
- Point the ADOT collector config (or the in-code OTLP exporter) at the gateways. Confirm the current ADOT layer ARN for `us-east-2` from AWS docs before deploying.
- **Logs:** already flow. Lambda stdout/CloudWatch logs are shipped to Loki by the existing `lambda-promtail` / Firehose pipeline (Alloy derives `service_name` from the log group). Your job: make sure log lines include `trace_id`/`span_id` so they correlate (structured logging, see `logs.md`).
- **Profiling: not applicable.** Continuous Pyroscope profiling does not fit an ephemeral, frozen-between-invokes runtime. Do not add the Pyroscope SDK to Lambdas. For a hot Lambda, profile it locally or in a container with `dotnet-trace` (`dotnet-diag` skill).
- Set resource attrs via `OTEL_RESOURCE_ATTRIBUTES` Lambda env (or `AWS_LAMBDA_*` enrichment from the AWS resource detector).

## EKS (Docker)

App exports OTLP to the **node-local Grafana Alloy DaemonSet** (receivers on `:4317`/`:4318`). Resolve the node IP via the Downward API:

```yaml
env:
  # Downward-API vars first: k8s only substitutes $(VAR) for vars declared earlier in the list.
  - name: NODE_IP
    valueFrom: { fieldRef: { fieldPath: status.hostIP } }
  - name: POD_NAME
    valueFrom: { fieldRef: { fieldPath: metadata.name } }
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://$(NODE_IP):4318"
  - name: OTEL_EXPORTER_OTLP_PROTOCOL
    value: "http/protobuf"
  - name: OTEL_SERVICE_NAME
    value: "myservice"
  - name: OTEL_RESOURCE_ATTRIBUTES
    value: "service.namespace=lending,deployment.environment=Prod,service.instance.id=$(POD_NAME)"
  - name: PYROSCOPE_SERVER_ADDRESS
    value: "https://pyroscope.observability-internal.attainfinance.com"
  - name: PYROSCOPE_APPLICATION_NAME
    value: "myservice"
```

Per-signal routing on EKS:
- **Traces:** OTLP to node Alloy, which forwards to Tempo. Works today.
- **Metrics:** Alloy's OTLP receiver currently forwards only traces. So either export metrics OTLP **direct to mimir `/otlp`** over the cluster network, or expose a Prometheus `/metrics` endpoint and add a `ServiceMonitor` (Alloy already scrapes ServiceMonitors to Mimir). Prefer the ServiceMonitor path if the cluster already scrapes your namespace.
- **Logs:** write structured JSON to **stdout**; the Alloy DaemonSet tails pod logs into Loki and the pipeline sets `service_name`/`deployment_environment`. (OTLP-direct to loki `/otlp` also works.) Either way include `trace_id` in the log line.
- **Profiles:** Pyroscope SDK pushes direct to the pyroscope endpoint (Attain currently scrapes pprof only for Go; .NET pushes). See `profiling.md`.

> Note: if you want app-OTLP metrics/logs to flow through Alloy instead of going direct, that requires extending the Alloy `otelcol` pipeline (metrics to Mimir, logs to Loki). Flag it to SRE; until then use the direct/ServiceMonitor/stdout paths above.

## ECS (Docker)

Run an **OTel Collector sidecar** container in the task definition (matches the existing "ECS OTel Sidecars" pattern). The app sends to `localhost`, the sidecar fans out to the gateways.

- App container env: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`, plus service/resource vars.
- Sidecar: `otelcol-contrib` (or ADOT collector) with otlp receivers and otlphttp exporters to mimir `/otlp`, loki `/otlp`, tempo. Use `dependsOn`/`links` so the app waits for the sidecar.
- **Logs:** typically `awslogs` driver to CloudWatch, then to Loki via the existing pipeline; or route logs through the sidecar to loki `/otlp`. Include `trace_id` in log lines either way.
- **Profiles:** Pyroscope SDK push direct to the pyroscope endpoint.

## Direct export (no collector, e.g. local verify or bare EC2)

Set per-signal endpoints so each signal hits the right gateway:

```bash
# Per-signal endpoints are used as-is (no /v1/<signal> auto-append), so give the full path:
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://tempo.observability-internal.attainfinance.com/v1/traces
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://mimir.observability-internal.attainfinance.com/otlp/v1/metrics
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://loki.observability-internal.attainfinance.com/otlp/v1/logs
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

Contrast: the **base** `OTEL_EXPORTER_OTLP_ENDPOINT` (used with a local collector / node Alloy) gets `/v1/traces`, `/v1/metrics`, `/v1/logs` appended automatically, which is why `http://localhost:4318` works for all signals. Use this direct form for local verification on VPN (`verify.md`) with `deployment.environment=local`.
