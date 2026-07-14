# Logs (to Loki)

The Attain fleet uses `Microsoft.Extensions.Logging` (`ILogger`), not Serilog, so the primary path is ILogger to OpenTelemetry to Loki. This gives automatic trace correlation for free.

## Wiring

In `setup.md` the logging provider is registered:

```csharp
builder.Logging.AddOpenTelemetry(o =>
{
    o.SetResourceBuilder(resource);   // same service.name etc. as traces/metrics
    o.IncludeScopes = true;           // emit ILogger scopes as attributes
    o.IncludeFormattedMessage = true; // include the rendered message
    o.ParseStateValues = true;        // structured: capture each {placeholder} as an attribute
    o.AddOtlpExporter();              // to the per-target endpoint
});
```

That is all that is needed for **automatic trace correlation**: every log written inside an active span carries `TraceId` and `SpanId`. Loki's derived `trace_id` field then links the log line straight to the trace in Tempo.

## Structured logging (do this, not string concat)

Use message templates with named placeholders so each value becomes a queryable attribute:

```csharp
// good: structured, placeholders become attributes
_logger.LogInformation("Decision {Outcome} for product {Product} in {ElapsedMs}ms",
    outcome, product, sw.ElapsedMilliseconds);

// bad: interpolated string, no structure, and risks PII in the body
_logger.LogInformation($"Decision {outcome} for {customerEmail}");  // never
```

Scopes add context to every log inside them:

```csharp
using (_logger.BeginScope(new Dictionary<string, object> { ["LoanProduct"] = product }))
{
    // all logs here carry LoanProduct
}
```

## Levels and noise

- `Information` for business milestones, `Warning` for recoverable issues, `Error` for failures (with the exception object: `_logger.LogError(ex, "...")` so the stack trace is captured).
- Tune `appsettings.json` `Logging:LogLevel` so framework categories (e.g. `Microsoft.AspNetCore`) are `Warning` in prod; otherwise Loki fills with request noise.
- Health-check and metrics-endpoint requests should be at `Debug` or filtered.

## PII (hard rule)

No SSN, PAN, full email, DOB, full name, account number, or tokens in log messages, attributes, or scopes. The Alloy/collector pipeline redacts SSN/CC/email patterns as a backstop, but that is defense in depth, not permission. Log identifiers that are safe to correlate (loan id is generally acceptable; raw customer PII is not, follow the data-classification guidance).

## Per-target notes

- **EC2 / ECS / Windows:** OTLP logs go to the local collector/sidecar, which forwards to loki `/otlp`.
- **EKS:** simplest is to also write structured JSON to **stdout**; the Alloy DaemonSet tails pod logs into Loki and sets `service_name`/`deployment_environment`. OTLP-direct to loki `/otlp` also works. Either way, the OTel logging provider stamps `trace_id` so correlation holds. If you rely on stdout, use a JSON console formatter so Loki can parse fields.
- **Lambda:** do not add an OTLP log exporter. Lambda stdout/CloudWatch logs already reach Loki via the `lambda-promtail`/Firehose pipeline. Just make sure lines are structured and include `trace_id` (the OTel logging provider does this when a span is active).

## Serilog (only if a service already uses it)

If a service is already on Serilog, keep it and add the OTLP sink (`Serilog.Sinks.OpenTelemetry`) configured with the same resource attributes, or bridge Serilog through `Microsoft.Extensions.Logging`. Do not introduce Serilog to a service that uses `ILogger`.

## Verify

`query_loki_logs`: `{service_name="myservice", deployment_environment="local"}` and confirm lines carry a non-empty `trace_id` (`{service_name="myservice"} | trace_id != ""`). Click a line, follow `trace_id` to Tempo. See `verify.md`.
