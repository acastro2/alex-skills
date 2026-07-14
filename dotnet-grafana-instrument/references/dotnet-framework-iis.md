# .NET Framework, OWIN, and VB.NET on IIS (zero-code)

Legacy apps (Capo.*, Curo VB.NET, older WebForms/MVC on .NET Framework) often cannot be wired in code: no minimal-hosting `Program.cs`, OWIN `Startup` only, or VB you do not want to touch. Use the **OpenTelemetry .NET Automatic Instrumentation agent**: a zero-code CLR profiler that instruments traces, metrics, and logs from the outside, configured entirely by environment variables.

This file is the **Windows/IIS specialization** of the zero-code agent. The general agent mechanics (custom-source env vars, Linux/EKS/ECS/Lambda installs, the CLR-slot/Pyroscope tradeoff) live in `auto-instrumentation.md`; this file covers the IIS-specific install and app-pool wiring.

This pairs with the host collector setup already documented in the repo: `observability/OTEL-ONBOARD-APP.md` and `OTEL-WINDOWS-RUNBOOK.md`. Do not re-create the collector; this file is the app side.

## 1. Install the agent (Windows / IIS)

Use the official PowerShell module (`OpenTelemetry.DotNet.Auto.psm1`) from the opentelemetry-dotnet-instrumentation releases. PowerShell 5.1 (default on Windows):

```powershell
# download + import the module from the release, then:
Install-OpenTelemetryCore
Register-OpenTelemetryForIIS    # hooks the IIS worker processes; performs an IIS restart
```

Default install path: `C:\Program Files\OpenTelemetry .NET AutoInstrumentation`. `Register-OpenTelemetryForIIS` sets the CLR profiler env for IIS app pools so `w3wp.exe` loads the agent.

## 2. Configure via environment (per app pool or machine)

The agent reads `OTEL_*` env vars. Set per app pool (so each app gets its own service name) via `applicationHost.config` `environmentVariables` (see the SSM/app-pool method in `OTEL-ONBOARD-APP.md`):

```
OTEL_SERVICE_NAME            = myservice            # lowercase
OTEL_RESOURCE_ATTRIBUTES     = service.namespace=lending,deployment.environment=Prod
OTEL_EXPORTER_OTLP_ENDPOINT  = http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL  = http/protobuf
```

For .NET Framework you can also place `OTEL_*` settings in the app's `App.config`/`Web.config` `appSettings`, or in the Windows Registry for Windows Services. App-pool env vars are the standard at Attain.

The agent auto-instruments ASP.NET (classic), HttpClient/WebRequest, ADO.NET/SqlClient, and more, all signals enabled by default. No code changes, no NuGet packages.

## 3. HTTPS vs HTTP on hardened hosts

Some Windows hosts have SCHANNEL hardened so TLS 1.3 to the NLB fails. The local collector usually negotiates fine (Go TLS stack), but if exporting direct, fall back to `http://...:80` per `OTEL-ONBOARD-APP.md`. App to local collector is plain `http://localhost:4318`, so this only matters for the collector-to-gateway hop.

## 4. Custom spans/metrics in .NET Framework code (optional)

If you *can* touch the code and want business spans on top of the zero-code traces, you can still use `System.Diagnostics.ActivitySource` and `System.Diagnostics.Metrics.Meter` (available on .NET Framework via the `System.Diagnostics.DiagnosticSource` NuGet package). Name the source/meter after the service; the agent picks them up. This is the same `Telemetry` pattern as `setup.md`.

## 5. Continuous profiling: not available here

No continuous Pyroscope profiling for IIS / .NET Framework / Windows, for two reasons:
1. The Pyroscope .NET profiler ships as **Linux-only** native libraries (amd64/arm64). There is no Windows build.
2. Even on Linux, the Pyroscope profiler and this zero-code agent both claim the single `CORECLR_PROFILER` slot, so they cannot run together.

So a Windows/Framework app gets metrics, logs, and traces (via this agent), which is the priority. For a one-off CPU/memory investigation, use on-demand `dotnet-trace` / `dotnet-dump` (the `dotnet-diag` skill). If continuous profiling is a hard requirement, the app has to move to .NET on Linux and use the manual SDK path (`profiling.md`).

## 6. VB.NET

Same as .NET Framework: VB compiles to the same CLR, so the zero-code agent instruments it identically. No VB-specific work; set the env vars and register the agent.

## Verify

Same as everything else: generate traffic, then check Mimir/Loki/Tempo for `service_name="myservice"`. Traces appear once the agent is registered and the pool recycled. See `verify.md`.
