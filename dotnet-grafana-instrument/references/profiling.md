# Continuous profiling (to Pyroscope)

This is net-new for .NET at Attain: today only Go services are profiled (Alloy scrapes their pprof endpoints). .NET does not expose pprof for scraping, so .NET apps **push** profiles using the Pyroscope .NET profiler. This is the biggest value-add of the skill: continuous CPU/alloc/lock profiling correlated to traces.

**Platform limits (verified):** the profiler ships as Linux native libraries, so it is **Linux on amd64/arm64 only**, .NET 8/9/10. It applies to EC2 Linux and Linux containers (EKS/ECS). It does **not** run on Windows/IIS (no Windows profiler build) and **not** on Lambda (ephemeral, frozen between invokes). For Windows/.NET Framework apps that need profiling, use on-demand `dotnet-trace` (the `dotnet-diag` skill), not this.

> [!IMPORTANT]
> The Pyroscope profiler and the OpenTelemetry **zero-code auto-instrumentation agent** both register a CLR profiler via the single `CORECLR_PROFILER` slot. You cannot run both in one process. So: use the **manual OTel SDK** (`setup.md`) together with Pyroscope (full traces + profiles + span profiles), OR use the zero-code agent (`dotnet-framework-iis.md`) with **no** Pyroscope. Pick one per app.

## How the .NET profiler works

The Pyroscope .NET profiler is a native CLR profiler (`CORECLR_PROFILER`) that the runtime loads at startup. It samples continuously and pushes to the Pyroscope server. You enable it with environment variables; the `Pyroscope` NuGet package adds dynamic labels and the OTel span-profile bridge.

## 1. Packages

```bash
dotnet add package Pyroscope                 # dynamic labels + API
dotnet add package Pyroscope.OpenTelemetry   # span profiles: links profiles to spans
```

The actual continuous profiler is two native Linux files, `Pyroscope.Profiler.Native.so` and `Pyroscope.Linux.ApiWrapper.x64.so`, from the `grafana/pyroscope-dotnet` releases (glibc or musl, x86_64 or aarch64; match your base image). In a Dockerfile, copy them from the published image:

```dockerfile
COPY --from=pyroscope/pyroscope-dotnet:<version>-glibc /Pyroscope.Profiler.Native.so /dotnet/Pyroscope.Profiler.Native.so
COPY --from=pyroscope/pyroscope-dotnet:<version>-glibc /Pyroscope.Linux.ApiWrapper.x64.so /dotnet/Pyroscope.Linux.ApiWrapper.x64.so
```

On EC2 Linux, download the tarball and place the `.so` files where the env vars below point.

## 2. Environment (enables + targets the profiler)

```bash
# Load the CLR profiler
CORECLR_ENABLE_PROFILING=1
CORECLR_PROFILER={BD1A650D-AC5D-4896-B64F-D6FA25D6B26A}
CORECLR_PROFILER_PATH=/dotnet/Pyroscope.Profiler.Native.so   # path to the shipped profiler
LD_PRELOAD=/dotnet/Pyroscope.Linux.ApiWrapper.x64.so          # enables dynamic labels API
LD_LIBRARY_PATH=/dotnet                                       # dir holding the profiler .so files

# .NET 8+ gotcha: DOTNET_EnableDiagnostics=0 silently disables the profiler.
# If diagnostics are locked down, instead set:
#   DOTNET_EnableDiagnostics=1
#   DOTNET_EnableDiagnostics_IPC=0
#   DOTNET_EnableDiagnostics_Debugger=0
#   DOTNET_EnableDiagnostics_Profiler=1

# Pyroscope target + identity
PYROSCOPE_SERVER_ADDRESS=https://pyroscope.observability-internal.attainfinance.com
PYROSCOPE_APPLICATION_NAME=myservice                          # matches service.name
PYROSCOPE_PROFILING_ENABLED=1

# Profile types (enable what you want; CPU + alloc are the core two)
PYROSCOPE_PROFILING_CPU_ENABLED=true
PYROSCOPE_PROFILING_ALLOCATION_ENABLED=true
PYROSCOPE_PROFILING_LOCK_ENABLED=true
PYROSCOPE_PROFILING_EXCEPTION_ENABLED=true
# wall-clock is also available: PYROSCOPE_PROFILING_WALLTIME_ENABLED=true
```

Add a label for environment so profiles filter like the other signals:

```bash
PYROSCOPE_LABELS=deployment_environment=Prod,service_namespace=lending
```

The exact `CORECLR_PROFILER` GUID and profiler file names come from the Pyroscope .NET distribution you deploy: verify against the current Grafana Pyroscope `.NET` docs before shipping, do not assume.

## 3. Span profiles (trace to profile correlation)

Tempo is already configured with tracesToProfiles to Pyroscope (CPU). To make a span carry its profiling data, register the Pyroscope span processor so each span (auto or manual `ActivitySource.StartActivity()`) is tagged with the profile context:

```csharp
builder.Services.AddOpenTelemetry()
    .WithTracing(b => b
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter()
        .AddProcessor(new Pyroscope.OpenTelemetry.PyroscopeSpanProcessor()));
```

With this, spans created automatically (HTTP handlers) and manually (`ActivitySource.StartActivity()`) carry profiling data, so in Grafana you can open a slow span in Tempo and jump to the flame graph of exactly what it was doing on-CPU.

> [!IMPORTANT]
> Span profiles work **only with manual OpenTelemetry instrumentation** (the SDK in `setup.md`), not with the OTel zero-code agent, because the agent and the Pyroscope profiler are separate CLR profilers and cannot coexist. **Span profiles support CPU only** at present; the other profile types still flow as continuous (non-span) profiles. Spans shorter than the sampling interval may not capture a profile.

## 4. Container note (EKS/ECS)

- Base the image on a runtime that includes the Pyroscope profiler, or add it in the Dockerfile and point `CORECLR_PROFILER_PATH` / `LD_PRELOAD` at it.
- The profiler needs to run as the app process; no extra sidecar required (unlike Go pprof scraping). Profiles push straight to the pyroscope endpoint over VPN.
- Modest overhead (single-digit % CPU typical for CPU+alloc). Start with CPU+alloc, add lock/exception if investigating.

## 5. Why bother

CPU and allocation profiles tied to traces turn "this endpoint is slow sometimes" into "this exact method allocates a 2MB array on the hot path during the slow spans." It closes the loop: metric spike to exemplar trace to the span's flame graph.

## Verify

`list_pyroscope_profile_types` for the Pyroscope datasource, then query profiles filtered to `service_name="myservice"`. Confirm a `process_cpu` profile exists and, from a Tempo span, that the "profiles for this span" link resolves. See `verify.md`.
