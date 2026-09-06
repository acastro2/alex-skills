---
name: amazon-bedrock
description: >-
  Operate Bedrock applications: model/API discovery, access and residency checks,
  invocation failures, prompt caching, quotas, billed attribution and controlled
  model changes. Use focused references for Knowledge Bases, Guardrails and Agents
  when the application needs them. AgentCore is a related option, not a default
  migration. For SageMaker inventory use the root data-platform discovery reference.
version: 5
disable-model-invocation: true
---

# Amazon Bedrock

Start with the application that exists: its account, Region, API endpoint, model or inference profile, caller and observed failure. Do not turn an invocation problem into a new agent platform.

Read the [shared CLI guide](../references/cli-operating.md) before commands. Use existing SSO and deployment paths. Current AWS documentation and live discovery take priority over cached model IDs or version advice in a reference.

## Choose the task

| Task | Read |
|---|---|
| Select an available model/profile and confirm geography | [model selection](references/model-selection-guide.md) |
| Choose API or diagnose invocation errors | [model invocation](references/model-invocation.md) |
| Python or TypeScript Converse integration | [Python](references/sdk-converse-api-python.md), [TypeScript](references/sdk-converse-api-typescript.md) |
| Throttling, quota or max-token diagnosis | [quota health](references/quota-health.md) |
| Cache hits and economics | [prompt caching](references/prompt-caching.md) |
| Billed cost versus per-request estimates | [cost tracking](references/cost-tracking.md) |
| Controlled model upgrade | [model migration](references/model-migration.md) |
| Model-specific prompt behavior | [prompt guidance](references/prompt-engineering-by-model.md) |
| Existing or requested RAG | [KB setup](references/knowledge-bases-setup.md), [retrieval](references/knowledge-bases-retrieval.md) |
| Existing or requested content controls | [guardrails](references/guardrails.md) |
| Existing classic agent/action group | [agents](references/agents-and-action-groups.md) |
| Evaluate agent hosting or migrate an actual agent | [AgentCore discovery](references/agentcore-options.md) |

Knowledge Bases, Guardrails and Agents are related capabilities. Bedrock model billing alone does not prove the organization adopted them.

## Discover before invoking

Replace placeholders with confirmed values. These calls discover metadata; they do not send a prompt.

```bash
set -euo pipefail
PROFILE="<confirmed-profile>"
REGION="<confirmed-region>"
aws bedrock list-foundation-models --profile "$PROFILE" --region "$REGION" \
  --query 'modelSummaries[].{Id:modelId,Name:modelName}' --output json --no-cli-pager
aws bedrock list-inference-profiles --profile "$PROFILE" --region "$REGION" \
  --query 'inferenceProfileSummaries[].{Id:inferenceProfileId,Name:inferenceProfileName,Type:type}' \
  --output json --no-cli-pager
```

For one candidate, inspect `get-inference-profile` and its destination model ARNs. Do not construct an ARN or select a global profile to bypass a failure. Confirm geography, content storage, IAM/SCP permissions and workload approval. A model in a catalog is not proof that this caller can invoke it.

## Failure checks that matter

- **Access denied:** distinguish credentials, model entitlement, IAM/SCP, Region and inference-profile permissions. Do not grant wildcard access as a diagnostic shortcut.
- **Throttling:** identify the endpoint and model, set an explicit output limit, then inspect metrics and current quotas. A missing metric is unknown, not zero.
- **Cache miss:** check the model's supported cache shape and minimum tokens, identical prefix, TTL and returned cache counters. Do not print production prompts to compare them.
- **Unexpected bill:** separate aggregated CUR/Cost Explorer charges from estimated request cost. Caller attribution and cost allocation tags require configuration; they are not a universal per-request ledger.
- **Model change:** compare approved test cases, latency, cost, tool behavior and content controls before routing traffic. Keep a known-good configuration for rollback.

Runtime and Mantle quotas differ. Cache-read tokens do not belong in the runtime quota-consumption formula; output burndown and cache pricing are model-specific. Use the focused references and current model documentation, not a universal multiplier.

## Protect application content

Invocation is a data-processing action and can incur charges. Use only an approved non-sensitive test prompt unless the owner has approved a production evidence plan. Never enable invocation logging as a routine discovery step. Logs and request metadata can contain original prompts, outputs, secrets and personal data despite response masking.

For CloudTrail, distinguish runtime management events from Mantle data events. Use the [reviewed selector workflow](../security/references/cloudtrail-data-events.md) for changes; do not replace existing coverage with a partial payload.

For SDK/config changes, use the existing repo and dependency pins. Resolve current docs through Context7 and AWS guidance through Exa when the API or model behavior is uncertain.

## Official references

- [Bedrock endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html)
- [Supported models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html)
- [Cross-Region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)
- [Quotas](https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html)
