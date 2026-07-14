---
name: dotnet-grafana-instrument
description: Instrument any .NET app (modern .NET or .NET Framework/VB, on EC2, Lambda, EKS, or ECS) with the full Attain telemetry stack and ship it to Grafana. Use whenever you add or improve observability for an Attain .NET service: metrics, logs, distributed traces, AND continuous profiling (Pyroscope), wired to Mimir/Loki/Tempo/Pyroscope with the right export path per deployment target. Triggers on instrument, observability, telemetry, OpenTelemetry, OTel, traces, metrics, profiling, Pyroscope, "send to Grafana", or "add monitoring" for a .NET app. Self-contained: everything needed is in this skill.
license: MIT
---

# Instrument .NET for Attain's Grafana

This skill takes any .NET app to **exhaustive** instrumentation across all four signals and ships them to Attain's Grafana stack: **metrics → Mimir, logs → Loki, traces → Tempo, profiles → Pyroscope**. It is self-contained: base OpenTelemetry wiring, the Attain export pipeline, continuous profiling, the per-deployment-target setup, and local verification are all here.

## When to use

- Adding observability to any Attain .NET service (web API, worker, Lambda, console).
- Going from partial (traces only) to all four signals.
- Fixing a service that does not show up correctly in Grafana.

## When not to use

- Non-.NET apps.
- Ad-hoc one-off profiling or a crash dump on a single box: use the `dotnet-diag` skills (`dotnet-trace-collect`, `dump-collect`) instead. This skill is for *continuous* instrumentation.

## The principle: instrument everything, every time

Do not ship traces only. A properly instrumented Attain service emits **all four signals** so they correlate in Grafana (click a slow trace, jump to its logs, its RED metrics, and its CPU profile). Traces are the backbone; metrics, logs, and profiles hang off the same resource identity.

## Two ways to instrument (pick one per app)

- **Manual SDK (default, `references/setup.md`).** Add the OTel packages and wire `Program.cs`/`Startup.cs`. Costs a code change but is the **only path that delivers all four signals**, because continuous profiling + span profiles require the manual setup. Use this whenever you can edit the app.
- **Zero-code agent (`references/auto-instrumentation.md`).** The OTel .NET auto-instrumentation agent injects traces/metrics/logs from env vars, no code. Works on modern .NET **and** .NET Framework. Use it when hosting code is not editable (legacy Capo/Curo) or you want the fastest onboarding. Tradeoff: the agent and the Pyroscope profiler fight over the single `CORECLR_PROFILER` slot, so the plain agent gets **no continuous profiling**. (A StartupHook-only hybrid can keep both on modern .NET, see that reference.)

Either way the conventions, endpoints, and verification are the same. Default to manual unless the app can't be touched or profiling genuinely doesn't matter.

## Workflow

1. **Detect runtime and deployment target.**
   - Runtime: modern .NET (8/9/10, has `Program.cs`/minimal hosting or `Startup.cs`) vs **.NET Framework / OWIN / VB.NET** (hosting code often not editable).
   - Target: EC2 Linux, EC2 Windows/IIS, AWS Lambda, EKS (Docker), ECS (Docker). See `references/deployment-targets.md`.
2. **Pick the export path** for that target (where OTLP goes, how profiles push). `references/deployment-targets.md`.
3. **Wire the four signals.** First pick manual vs zero-code (see "Two ways" above).
   - Manual SDK (default, modern .NET): `references/setup.md` for the base packages + complete `Program.cs` AND `Startup.cs` wiring, then go deep per signal: `traces.md`, `metrics.md`, `logs.md`, `profiling.md`.
   - Zero-code agent (any runtime, when code is not editable or for fastest onboarding): `references/auto-instrumentation.md`.
   - .NET Framework / VB / OWIN specifically (zero-code on IIS): `references/dotnet-framework-iis.md`.
4. **Set the Attain resource identity and conventions.** `references/attain-endpoints.md` (endpoints, env vars, lowercase `service.name`, `deployment.environment`, PII rules).
5. **Verify locally on VPN.** Run the app, generate traffic, confirm every signal in Grafana via the grafana MCP. `references/verify.md`.

## One-screen Attain config (modern .NET, container or EC2 Linux)

Resource identity is the contract that ties all four signals together. Set it once.

```bash
# Required env (lowercase service name)
OTEL_SERVICE_NAME=myservice
OTEL_RESOURCE_ATTRIBUTES=service.namespace=lending,service.version=1.4.2,deployment.environment=Prod
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
# Endpoint differs per target (see deployment-targets.md). EC2 Linux example (local collector):
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
# Continuous profiling (not on Lambda)
PYROSCOPE_SERVER_ADDRESS=https://pyroscope.observability-internal.attainfinance.com
PYROSCOPE_APPLICATION_NAME=myservice
```

The four gateways (VPN-internal, prefer HTTPS, HTTP:80 fallback):

| Signal | Backend | Endpoint |
|---|---|---|
| Metrics | Mimir | `https://mimir.observability-internal.attainfinance.com/otlp` |
| Logs | Loki | `https://loki.observability-internal.attainfinance.com/otlp` |
| Traces | Tempo | `https://tempo.observability-internal.attainfinance.com` |
| Profiles | Pyroscope | `https://pyroscope.observability-internal.attainfinance.com` |

## Hard rules (Attain)

- **`service.name` is lowercase** (the SDK and collector lowercase it; dashboards query lowercase). `deployment.environment` is `Prod` / `NONPROD` / `local`.
- **Never put PII in telemetry.** No SSN, PAN, full email, DOB, account numbers in span attributes, metric labels, or log bodies. This is regulated lending data (SR 11-7, ECOA/Reg B, PCI). The pipeline redacts SSN/CC/email as a backstop, do not rely on it.
- **Watch cardinality.** No unbounded values (user id, request id, raw URL with ids) as metric labels or span/log indexed labels. High cardinality breaks Mimir.
- **One resource identity across all four signals.** Same `service.name`, `service.namespace`, `deployment.environment` everywhere, or correlation breaks.

## References

- `references/setup.md`: manual SDK base, packages + complete `Program.cs` and `Startup.cs` (all four signals), multi-project ActivitySource/Meter placement.
- `references/auto-instrumentation.md`: zero-code OTel agent for any runtime/target, custom-source env vars, the CLR-slot/Pyroscope tradeoff, StartupHook-only hybrid.
- `references/attain-endpoints.md`: endpoints, env vars, conventions, PII, cardinality.
- `references/deployment-targets.md`: export path per target: EC2 Linux, EC2 Windows/IIS, Lambda, EKS, ECS.
- `references/traces.md`: auto + custom spans, attributes, propagation, sampling, exemplars, span links.
- `references/metrics.md`: built-in + custom meters, runtime metrics, views, exemplars, RED.
- `references/logs.md`: ILogger to OTel to Loki, structured logs, trace correlation.
- `references/profiling.md`: Pyroscope continuous profiling + span profiles (net-new for .NET at Attain).
- `references/dotnet-framework-iis.md`: zero-code agent for .NET Framework / OWIN / VB on IIS.
- `references/verify.md`: local-on-VPN run, generate traffic, confirm all four signals via grafana MCP.
