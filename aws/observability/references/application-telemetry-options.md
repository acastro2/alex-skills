# Optional application telemetry

Use this when an application needs AWS-native service telemetry or live diagnostic capture. First inspect the current collectors, exporters, retention and owner. Do not add another backend to solve a query problem in the existing one.

## Decide before enabling

| Need | First check |
|---|---|
| Service-level latency/error visibility | Does the existing telemetry stack already collect and expose it? |
| Application Signals | Supported runtime/platform, instrumentation conflicts, service discovery permissions and expected charges |
| X-Ray/ADOT | Current trace path, propagation, sampling and sensitive attributes |
| Dynamic Instrumentation | Supported runtime, precise code location, owner approval, capture cost and data exposure |

Account-level Application Signals enablement can create a service-linked role. It is a change, not read-only discovery. Instrumentation and service discovery are separate requirements; enabling one does not prove telemetry arrives.

Use Exa for the current platform guide and Context7 for the installed SDK/add-on API. Build only the needed platform/language configuration in the owning repo. Do not copy a four-platform recipe or deploy mutable collector images.

## If the owner chooses this path

- Capture the current agent/collector/export configuration and approved retention before changing it.
- Set explicit workload/service identity without secrets or customer data in attributes.
- Prove receipt for one approved non-sensitive test, then compare volume and cost before expansion.
- Keep the previous configuration and export path available for rollback. Do not delete log groups with the deployment stack.
- For dynamic capture, get a precise scope, deadline, retention and cleanup plan first. Snapshots can expose local variables and request data. Do not dump them into chat or tickets.
- Remove temporary probes and verify removal, even if the capture fails. A create response alone proves neither activation nor a useful snapshot.

## Sources

- [Enable Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html), checked through Exa on 2026-09-04
- [Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html), starting point for current platform support
- Existing [tracing guidance](tracing.md) for an already configured trace path
