# Bedrock Quota Health Check

Monitor and manage Bedrock model quotas to prevent throttling. Quotas are model-, endpoint-, and Region-specific. On `bedrock-runtime`, models can have token and request quotas with model-specific output burndown. On `bedrock-mantle`, input TPM and output TPM are separate and there is no RPM quota.

## Table of Contents
- [How Quota Reservation Works](#how-quota-reservation-works)
- [Audit Workflow](#audit-workflow)
- [CloudWatch Metrics](#cloudwatch-metrics)
- [When You're Being Throttled](#when-youre-being-throttled)
- [Quota Increase Requests](#quota-increase-requests)

## How Quota Reservation Works

Bedrock reserves TPM quota at request start based on: `Total input tokens + maxTokens` (i.e., `InputTokenCount + CacheWriteInputTokens + maxTokens`). If `maxTokens` is unset, it defaults to the model's maximum (up to 64K–128K), reserving far more quota than needed.

**Example (Claude Sonnet, 2M TPM quota):**
- `maxTokens=1000`, 500 input tokens: reserves 1,500 → ~1,333 concurrent requests
- `maxTokens` unset (defaults to 64K): reserves ~64,500 → ~31 concurrent requests

This is the most common cause of unexpected `ThrottlingException`. Always set `maxTokens` explicitly.

Cache read tokens (`CacheReadInputTokens`) are NOT counted toward `bedrock-runtime` TPM quota — they do not contribute to reservation or settlement. Prompt caching can therefore increase usable TPM capacity. At settlement, consumption is `InputTokenCount + CacheWriteInputTokens + (OutputTokenCount × model-specific burndown rate)`. Verify the exact model's current rate; do not use a family-wide default.

These formulas describe `bedrock-runtime`. For `bedrock-mantle`, inspect its separate input-TPM and output-TPM quotas instead.

## Audit Workflow

### 1. Check Current Quotas

```bash
AWS_PROFILE="$PROFILE" aws service-quotas list-service-quotas \
  --service-code bedrock \
  --region "$REGION" \
  --query "Quotas[?contains(QuotaName, 'tokens per minute')].{Name:QuotaName, Value:Value}" \
  --output table \
  --no-cli-pager
```

### 2. Check Recent Usage vs Limits

Discover the exact current metric dimensions before querying; do not assume a `ModelId` dimension shape:

```bash
AWS_PROFILE="$PROFILE" aws cloudwatch list-metrics \
  --region "$REGION" \
  --namespace AWS/Bedrock \
  --metric-name InvocationThrottles \
  --recently-active PT3H \
  --output json \
  --no-cli-pager
```

Build a bounded `get-metric-data` request from the returned namespace, metric name, and dimensions. Compare peak request and token usage with the exact endpoint/model quotas over the same period. Report missing metrics as unknown, not zero.

### 3. Assess maxTokens Impact

Review application code for Bedrock calls without explicit `maxTokens`. Each unset call wastes quota proportional to the model's max output tokens.

## CloudWatch Metrics

Key metrics in the `AWS/Bedrock` namespace (dimension: `ModelId`):

| Metric | What It Tells You |
|--------|------------------|
| `Invocations` | RPM usage — compare against RPM quota |
| `InvocationThrottles` | Throttled requests — any value > 0 needs attention |
| `InputTokenCount` | Input token consumption per request |
| `OutputTokenCount` | Actual output tokens — use to right-size `maxTokens` |
| `InvocationLatency` | Latency distribution — spikes may correlate with throttling |

**Sample CloudWatch Logs Insights query** (requires model invocation logging enabled):

```
fields @timestamp, @message
| filter modelId like /claude/
| stats count() as requests, sum(inputTokenCount) as totalInput, sum(outputTokenCount) as totalOutput by bin(1m)
| sort @timestamp desc
```

## When You're Being Throttled

Decision table for resolving `ThrottlingException`:

| Situation | Action |
|-----------|--------|
| `maxTokens` not explicitly set | Set it to expected output length — biggest single impact |
| Traffic is bursty | Inspect live inference profiles. Use one only after its complete destination set, residency, and IAM/SCP access are approved; do not default to a geographic or global prefix |
| Steady-state traffic exceeds quota | Request a quota increase (see below) |
| Latency-sensitive workload | Use `priority` service tier for preferential processing |
| Non-time-critical workload | Use `flex` service tier (may queue during peak, lower cost) |
| Consistent high-volume | Request quota increase + use cross-region inference for headroom |

## Quota Increase Requests

A quota increase request is an account mutation. Prove the caller and Region, read the current quota, show the exact requested value, and get approval before submission:

```bash
AWS_PROFILE="$PROFILE" aws service-quotas request-service-quota-increase \
  --service-code bedrock \
  --quota-code "$QUOTA_CODE" \
  --desired-value "$DESIRED_VALUE" \
  --region "$REGION" \
  --output json \
  --no-cli-pager
```

To find the quota code for a specific model:

```bash
AWS_PROFILE="$PROFILE" aws service-quotas list-service-quotas \
  --service-code bedrock \
  --region "$REGION" \
  --query "Quotas[?contains(QuotaName, '$MODEL_NAME')].{Code:QuotaCode, Name:QuotaName, Value:Value}" \
  --output json \
  --no-cli-pager
```

AWS reviews quota increases. Do not promise a completion time. For urgent production needs, open an AWS Support case.
