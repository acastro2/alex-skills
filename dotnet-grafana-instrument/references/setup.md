# Base setup (modern .NET, manual SDK)

This is the **manual SDK** path: the Attain default, and the only one that gets all four signals including continuous profiling + span profiles. If you cannot edit the app or want the fastest onboarding, use the zero-code agent instead (`auto-instrumentation.md`), accepting no continuous profiling.

Self-contained base wiring for ASP.NET Core / .NET 8, 9, 10. Covers all four signals. Two hosting styles are shown because the Attain fleet uses both: minimal-hosting `Program.cs` and the older `Startup.cs` pattern (SummitAPI, Tiger.Authentication, CashMoney all use Startup.cs).

## 1. NuGet packages

```bash
# Core SDK + DI host + OTLP exporter (traces, metrics, AND logs go through OTLP)
dotnet add package OpenTelemetry.Extensions.Hosting
dotnet add package OpenTelemetry.Exporter.OpenTelemetryProtocol

# Instrumentation: install the ones your app actually uses
dotnet add package OpenTelemetry.Instrumentation.AspNetCore
dotnet add package OpenTelemetry.Instrumentation.Http
dotnet add package OpenTelemetry.Instrumentation.Runtime        # GC, thread pool, JIT, exceptions
dotnet add package OpenTelemetry.Instrumentation.SqlClient      # SQL Server (Curo/Summit/Cash use MSSQL)
dotnet add package OpenTelemetry.Instrumentation.EntityFrameworkCore  # if EF Core
# dotnet add package Npgsql.OpenTelemetry                       # if Npgsql/Postgres
# dotnet add package OpenTelemetry.Instrumentation.GrpcNetClient # if gRPC client

# Continuous profiling (see profiling.md). NOT on Lambda.
dotnet add package Pyroscope
dotnet add package Pyroscope.OpenTelemetry                      # span profiles (trace <-> profile)
```

Do **not** install the bare `OpenTelemetry` package alone: you need `OpenTelemetry.Extensions.Hosting` for DI.

## 2. Shared telemetry identity (multi-project)

Attain solutions have 20 to 30 projects. Put the `ActivitySource` and `Meter` in a Core/Abstractions library so business code in any project can emit spans and metrics without referencing the SDK. Define them once:

```csharp
// In <Service>.Core/Telemetry.cs
using System.Diagnostics;
using System.Diagnostics.Metrics;

public static class Telemetry
{
    public const string ServiceName = "myservice"; // lowercase, matches OTEL_SERVICE_NAME
    public static readonly ActivitySource Activity = new(ServiceName);
    public static readonly Meter Meter = new(ServiceName);
}
```

Business code anywhere in the solution then does `using var act = Telemetry.Activity.StartActivity("ChargeCard");` or `Telemetry.Meter.CreateCounter<long>(...)`. The host registers them via `AddSource(Telemetry.ServiceName)` / `AddMeter(Telemetry.ServiceName)`.

## 3. Complete `Program.cs` (minimal hosting, all four signals)

```csharp
using OpenTelemetry.Logs;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);

var resource = ResourceBuilder.CreateDefault()
    .AddService(
        serviceName: Telemetry.ServiceName,                 // lowercase
        serviceVersion: typeof(Program).Assembly.GetName().Version?.ToString() ?? "0.0.0")
    .AddAttributes(new Dictionary<string, object>
    {
        ["service.namespace"]       = "lending",
        ["deployment.environment"]  = builder.Configuration["DEPLOY_ENV"] ?? "local",
        ["service.instance.id"]     = Environment.MachineName,
    });

// Build the resource once (above) and apply it per signal with SetResourceBuilder.
// (Do not also use .ConfigureResource(...) here: a per-signal SetResourceBuilder overrides it,
//  so it would be dead config and would teach two different resource patterns in one file.)
builder.Services.AddOpenTelemetry()
    .WithTracing(t => t
        .SetResourceBuilder(resource)
        .AddSource(Telemetry.ServiceName)                   // custom spans
        .AddAspNetCoreInstrumentation(o =>
        {
            o.RecordException = true;
            o.Filter = ctx => !ctx.Request.Path.StartsWithSegments("/health")
                           && !ctx.Request.Path.StartsWithSegments("/metrics");
        })
        .AddHttpClientInstrumentation(o => o.RecordException = true)
        .AddSqlClientInstrumentation(o => { o.RecordException = true; o.SetDbStatementForText = true; })
        .SetSampler(new ParentBasedSampler(new TraceIdRatioBasedSampler(1.0))) // 100% local; lower in prod or sample at collector
        .AddOtlpExporter())
    .WithMetrics(m => m
        .SetResourceBuilder(resource)
        .AddMeter(Telemetry.ServiceName)                    // custom metrics
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddRuntimeInstrumentation()
        .SetExemplarFilter(ExemplarFilterType.TraceBased)   // link metrics -> traces
        .AddOtlpExporter());

// Logs: single registration on the host logging builder (gives automatic TraceId/SpanId correlation)
builder.Logging.AddOpenTelemetry(o =>
{
    o.SetResourceBuilder(resource);
    o.IncludeScopes = true;
    o.IncludeFormattedMessage = true;
    o.ParseStateValues = true;
    o.AddOtlpExporter();
});

var app = builder.Build();
// ... endpoints ...
app.Run();
```

Notes:
- `AddOtlpExporter()` reads `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_EXPORTER_OTLP_PROTOCOL` from env, so the same code works on every deployment target. Do not hardcode endpoints.
- Logs use a single `builder.Logging.AddOpenTelemetry(...)` registration (the canonical form, also what the official OTel .NET docs show). Do not also add `.WithLogging()` on the `AddOpenTelemetry()` chain, that double-registers the provider.
- `service.version` from the assembly keeps deploys traceable.

## 4. `Startup.cs` pattern (older hosting, common in the fleet)

When the project has `Startup.cs`, wire the same thing in `ConfigureServices`:

```csharp
public void ConfigureServices(IServiceCollection services)
{
    var resource = ResourceBuilder.CreateDefault()
        .AddService(Telemetry.ServiceName,
            serviceVersion: typeof(Startup).Assembly.GetName().Version?.ToString() ?? "0.0.0")
        .AddAttributes(new Dictionary<string, object>
        {
            ["service.namespace"]      = "lending",
            ["deployment.environment"] = Configuration["DEPLOY_ENV"] ?? "local",
            ["service.instance.id"]    = Environment.MachineName,
        });

    services.AddOpenTelemetry()
        .WithTracing(t => t.SetResourceBuilder(resource)
            .AddSource(Telemetry.ServiceName)
            .AddAspNetCoreInstrumentation(o => o.RecordException = true)
            .AddHttpClientInstrumentation()
            .AddSqlClientInstrumentation()
            .AddOtlpExporter())
        .WithMetrics(m => m.SetResourceBuilder(resource)
            .AddMeter(Telemetry.ServiceName)
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddRuntimeInstrumentation()
            .SetExemplarFilter(ExemplarFilterType.TraceBased)
            .AddOtlpExporter());

    services.AddLogging(lb => lb.AddOpenTelemetry(o =>
    {
        o.SetResourceBuilder(resource);
        o.IncludeScopes = true;
        o.IncludeFormattedMessage = true;
        o.AddOtlpExporter();
    }));
}
```

## Next

Go deep per signal: `traces.md`, `metrics.md`, `logs.md`, `profiling.md`. Pick the export path: `deployment-targets.md`. Then `verify.md`.
