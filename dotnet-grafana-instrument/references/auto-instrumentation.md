# Zero-code auto-instrumentation (the OTel .NET agent)

The most hands-off way to instrument: the **OpenTelemetry .NET Automatic Instrumentation agent** injects traces, metrics, and logs from the outside, configured entirely by environment variables. No SDK packages, no `Program.cs` edits. It works on **modern .NET (8/9/10) AND .NET Framework 4.6.2+**, so it is not just a legacy fallback.

## When to pick this over the manual SDK (`setup.md`)

| Situation | Path |
|---|---|
| You want **all four signals incl. continuous profiling** | Manual SDK + Pyroscope (`setup.md`, `profiling.md`). The Attain default. |
| Hosting code is **not editable** (.NET Framework / OWIN / VB, vendor binary) | Zero-code agent (this file). |
| You want the **fastest possible onboarding** and can live without continuous profiling | Zero-code agent (this file). |
| You want auto-instrumentation **and** profiling on modern Linux | Hybrid, see the bottom of this file (advanced). |

The reason this is a real choice and not a free lunch: **the agent and the Pyroscope profiler both claim the single `CORECLR_PROFILER` slot in a process and cannot coexist** (see `profiling.md`). So the plain zero-code agent gives you traces + metrics + logs but **no continuous profiling**. The manual SDK path is still the default at Attain because continuous profiling + span profiles is the headline value and you only get those on the manual path.

The agent's own CLR profiler GUID is `{918728DD-259F-4A6A-AC2B-B85E1B658318}` (Pyroscope's is `{BD1A650D-...}`): same slot, only one wins.

## What it auto-instruments

Out of the box: ASP.NET Core / ASP.NET (classic), HttpClient/WebRequest, SqlClient/ADO.NET, gRPC, EF Core, and more, with traces + metrics + logs all on by default. Same OTLP export contract as everything else, so it lands in Mimir/Loki/Tempo with no code.

## Keep your custom spans and metrics (important)

Zero-code does not mean you lose business telemetry. The agent picks up your own `ActivitySource`/`Meter` if you register their names by env var, no exporter wiring needed:

```bash
OTEL_DOTNET_AUTO_TRACES_ADDITIONAL_SOURCES=myservice        # your ActivitySource name(s), comma-sep or prefix.*
OTEL_DOTNET_AUTO_METRICS_ADDITIONAL_SOURCES=myservice       # your Meter name(s)
```

Use the same `Telemetry.ServiceName` you would in `setup.md`. Spans from a source you do **not** register are dropped, so this env var is the one thing you must not forget.

## Install per deployment target

The Attain conventions and OTLP endpoints are identical to the manual path: set `OTEL_SERVICE_NAME` (lowercase), `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` per `attain-endpoints.md` / `deployment-targets.md`.

### EC2 Linux (and any Linux host/systemd)

```bash
# Install the agent (pin a real release tag, do not assume "latest" in prod)
curl -sSfL https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation/releases/download/v1.13.0/otel-dotnet-auto-install.sh -O
sh ./otel-dotnet-auto-install.sh
chmod +x $HOME/.otel-dotnet-auto/instrument.sh

# Activate for the process/shell (sets CORECLR_*, DOTNET_STARTUP_HOOKS, OTEL_DOTNET_AUTO_HOME, ...)
. $HOME/.otel-dotnet-auto/instrument.sh

OTEL_SERVICE_NAME=myservice \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
OTEL_DOTNET_AUTO_TRACES_ADDITIONAL_SOURCES=myservice \
  dotnet MyApp.dll
```

For a systemd service, source `instrument.sh`'s exports into the unit's `Environment=`/`EnvironmentFile=` instead of an interactive shell.

### EC2 Windows / IIS (.NET Framework, OWIN, VB, classic ASP.NET)

This is the primary path for legacy apps. Use the PowerShell module and register IIS app pools: see `dotnet-framework-iis.md` (`Install-OpenTelemetryCore`, `Register-OpenTelemetryForIIS`, app-pool env vars). On .NET Framework the CLR profiler is **required** (there is no startup-hook-only mode), and there is no Pyroscope on Windows anyway, so the slot conflict is moot.

### AWS Lambda (.NET)

The **ADOT (AWS Distro for OpenTelemetry) managed layer** is auto-instrumentation: attach the layer, set the handler wrapper env, point OTLP at the gateways. No code. See the Lambda section of `deployment-targets.md`. (Profiling is N/A on Lambda regardless.)

### EKS (Docker)

Two ways, depending on what is installed in the cluster:

1. **OTel Operator injection (cleanest, if available).** If the cluster runs the OpenTelemetry Operator, annotate the pod and the operator injects the agent via an init container, no image changes:
   ```yaml
   metadata:
     annotations:
       instrumentation.opentelemetry.io/inject-dotnet: "true"
       instrumentation.opentelemetry.io/otel-dotnet-auto-runtime: "linux-x64"   # or linux-musl-x64 for Alpine
   ```
   Attain currently runs the **Alloy DaemonSet, not the OTel Operator**, so confirm with SRE before relying on this. If the operator is not installed, use option 2.

2. **Bake the agent into the image (works today).** Copy the agent in and set the env in the Dockerfile:
   ```dockerfile
   FROM busybox AS otel
   # use ...-linux-musl-x64.zip for Alpine-based images
   ADD https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation/releases/download/v1.13.0/opentelemetry-dotnet-instrumentation-linux-glibc-x64.zip /otel.zip
   RUN mkdir /otel && unzip /otel.zip -d /otel

   FROM mcr.microsoft.com/dotnet/aspnet:8.0
   COPY --from=otel /otel /otel
   ENV CORECLR_ENABLE_PROFILING=1 \
       CORECLR_PROFILER='{918728DD-259F-4A6A-AC2B-B85E1B658318}' \
       CORECLR_PROFILER_PATH=/otel/linux-x64/OpenTelemetry.AutoInstrumentation.Native.so \
       DOTNET_ADDITIONAL_DEPS=/otel/AdditionalDeps \
       DOTNET_SHARED_STORE=/otel/store \
       DOTNET_STARTUP_HOOKS=/otel/net/OpenTelemetry.AutoInstrumentation.StartupHook.dll \
       OTEL_DOTNET_AUTO_HOME=/otel
   ```
   OTLP endpoint still points at the node Alloy (`http://$(NODE_IP):4318`) per `deployment-targets.md`.

### ECS (Docker)

Same image-bake as EKS option 2. The OTLP endpoint points at the collector sidecar (`http://localhost:4318`) per `deployment-targets.md`.

## Advanced: agent + Pyroscope together on modern .NET (StartupHook-only)

The docs state the startup hook is what is required "if the .NET CLR Profiler is not used." So on **modern .NET (not Framework)** you can run the agent in **StartupHook-only mode**, which leaves the CLR profiler slot free for Pyroscope:

- Set `DOTNET_STARTUP_HOOKS`, `DOTNET_ADDITIONAL_DEPS`, `DOTNET_SHARED_STORE`, `OTEL_DOTNET_AUTO_HOME` from the agent, but do **not** set the agent's `CORECLR_*` vars.
- Set Pyroscope's `CORECLR_*` vars instead (`profiling.md`).

Result: auto traces/metrics/logs from the **source-based** instrumentations (ASP.NET Core, HttpClient, SqlClient, etc., the ones that matter most) **plus** continuous profiling. The cost: you lose the agent's **bytecode-only** instrumentations, and span profiles still need the manual `PyroscopeSpanProcessor` (`profiling.md`), which means manual spans. This is more fragile than either pure path: treat it as opt-in, and verify in `verify.md` that the signals you expect actually show up before trusting it. When in doubt, prefer the manual SDK default.

## Verify

Identical to the manual path: generate traffic, then confirm `service_name="myservice"` in Mimir/Loki/Tempo via the grafana MCP (`verify.md`). Remember the agent gives no continuous profile unless you used the StartupHook-only hybrid above.
