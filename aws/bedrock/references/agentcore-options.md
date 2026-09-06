# AgentCore: fit and discovery

Use this when a Bedrock application needs managed agent hosting or tool integration. Do not recommend migration just because the service exists. Identify the current agent, framework, tools, session model and owner first.

## Discover the actual starting point

Complete the [shared preflight](../../references/cli-operating.md), then inspect one account and Region. Verify the installed CLI exposes this command before upgrading dependencies.

```bash
set -euo pipefail
PROFILE="<confirmed-profile>"
REGION="<confirmed-region>"
aws bedrock-agentcore-control list-agent-runtimes \
  --profile "$PROFILE" --region "$REGION" \
  --query 'agentRuntimes[].{Id:agentRuntimeId,Name:agentRuntimeName,Status:status}' \
  --output json --no-cli-pager
```

This lists runtimes, not every possible agent resource. An empty list does not prove there are no classic Bedrock Agents, gateways, knowledge bases or externally hosted agents. Inspect the application's code/IaC and the corresponding current control-plane APIs. Do not dump prompts, memory, credentials or tool payloads.

## Fit check

| Need | Evaluate | First constraint |
|---|---|---|
| Host an existing agent loop | Runtime | Framework/protocol support, networking, identity, packaging and session behavior |
| Expose existing tools | Gateway | Tool authorization, private access and downstream permissions |
| Preserve conversation context | Memory | Tenant/user isolation, retention and deletion requirements |
| Use a managed orchestration loop | Current managed-agent options | Model/tool support and behavior parity with the existing application |

Fetch the current service guide through Exa and exact SDK/CLI docs through Context7 before writing configuration. Do not carry forward old protocol paths, image architectures, model identifiers or API contracts without checking them.

## Before any migration

Require an owner-approved inventory of prompts, tool schemas, action groups, knowledge sources, identities, permissions and session/memory behavior. Decide how clients switch and how the old endpoint stays available for rollback.

Prove parity with approved non-sensitive test cases: tool selection, tool side effects, permission denials, content controls, multi-turn behavior, latency and cost. Deployment success is not parity. Never delete the old agent automatically after a successful deploy.

Any container path needs an approved immutable image digest, supported architecture, secret-safe local tests with cleanup, runtime proof and a known-good rollback artifact. Reuse [release controls](../../delivery/references/release-controls.md), rather than copying a generic push script.

Payments/x402 and provider-specific wallets are outside normal skill scope. An explicit request needs a separate requirements and security review before setup.

## Sources

Checked through Exa on 2026-09-04:
- [List agent runtimes](https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore-control/list-agent-runtimes.html)
- [AgentCore developer guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)
