# Metrics (to Mimir)

## Built-in instrumentation (free metrics)

Register these in `WithMetrics` (`setup.md`):

- `AddAspNetCoreInstrumentation()` to emit `http_server_request_duration` (histogram, OTel semconv) and active-request gauges. The count series is `http_server_request_duration_count{service_name="myservice"}`.
- `AddHttpClientInstrumentation()` for outbound `http_client_request_duration`.
- `AddRuntimeInstrumentation()` (package `OpenTelemetry.Instrumentation.Runtime`) for GC, heap, thread pool, JIT, and exception counts: the .NET runtime health you want. In Mimir these land as `process_runtime_dotnet_*`. (On .NET 9+ the built-in `System.Runtime` meter also emits `dotnet_*`-named metrics; either works, just query the names you actually see.)
- Kestrel/connection metrics come from the built-in meters (`Microsoft.AspNetCore.Server.Kestrel`, `System.Net.Http`) which the ASP.NET Core/Http instrumentation enables.

That alone gives RED (rate, errors, duration) plus runtime health. Add custom metrics for business signal.

## Custom metrics

Use the shared `Meter` (`Telemetry.Meter` from the Core lib). Instrument types:

```csharp
// Counter: monotonic totals (requests, decisions, retries)
static readonly Counter<long> Decisions =
    Telemetry.Meter.CreateCounter<long>("underwriting.decisions", unit: "{decision}");

// Histogram: distributions (latency, amount buckets, batch sizes)
static readonly Histogram<double> DecisionLatency =
    Telemetry.Meter.CreateHistogram<double>("underwriting.decision.duration", unit: "ms");

// UpDownCounter: values that go up and down (queue depth, in-flight)
static readonly UpDownCounter<long> InFlight =
    Telemetry.Meter.CreateUpDownCounter<long>("underwriting.inflight");

// ObservableGauge: sampled point-in-time value (cache size, pool usage)
Telemetry.Meter.CreateObservableGauge("cache.entries", () => _cache.Count);

// record with low-cardinality tags only
Decisions.Add(1, new KeyValuePair<string, object?>("outcome", outcome),
                 new KeyValuePair<string, object?>("product", product));
DecisionLatency.Record(sw.Elapsed.TotalMilliseconds, new("outcome", outcome));
```

Naming: dotted, lowercase, OTel-style (`area.thing.unit-implied`); set `unit`. Tags are **bounded** sets (outcome, product code, status), never user id / amount / id.

## Views (histogram buckets, renaming, dropping)

Default histogram buckets are generic. Tune per histogram with a View:

```csharp
.AddView("underwriting.decision.duration", new ExplicitBucketHistogramConfiguration
{
    Boundaries = new double[] { 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000 }
})
// drop a noisy instrument:
.AddView("some.chatty.metric", MetricStreamConfiguration.Drop)
// limit tag keys kept on a metric (cardinality control):
.AddView("underwriting.decisions", new MetricStreamConfiguration { TagKeys = new[] { "outcome", "product" } })
```

## Exemplars (link a spike to a trace)

```csharp
.SetExemplarFilter(ExemplarFilterType.TraceBased)
```

Default in .NET is `AlwaysOff`. `TraceBased` attaches `trace_id`/`span_id` to measurements taken inside a sampled span, so a histogram bucket in Grafana shows an exemplar dot that jumps to the trace. Use `TraceBased` (not `AlwaysOn`) to keep cost low and only exemplar real traffic. Mimir stores exemplars; the Tempo/Mimir correlation is already configured.

## RED out of the box

Tempo's metrics-generator produces span metrics (`traces_spanmetrics_calls_total`, `_latency_*`) from your spans, so you get RED per service/route without writing metric code, as long as spans flow and have correct `ActivityKind`. Your custom metrics add business KPIs on top.

## Cardinality (Mimir will hurt otherwise)

- Never label with user id, request id, raw path, SQL text, amount, or timestamp.
- Use route templates and bucketed values.
- Prefer fewer, well-chosen tag keys; cap them with `TagKeys` views.
- High-cardinality detail belongs in span attributes (Tempo), not metric labels (Mimir).

## Export

`AddOtlpExporter()` to the per-target endpoint. On EKS, metrics either go OTLP-direct to mimir `/otlp` or via a Prometheus `/metrics` endpoint scraped by a `ServiceMonitor` (see `deployment-targets.md`). On EC2/ECS, the local collector/sidecar forwards to mimir `/otlp`.

## Verify

`query_prometheus`: `http_server_request_duration_count{service_name="myservice"}` and `process_runtime_dotnet_gc_collections_count{service_name="myservice"}`. See `verify.md`.
