# Prompt Caching on Amazon Bedrock

Prompt caching stores frequently used input content so subsequent requests can reuse it, reducing latency by up to 85% and costs by up to 90%. Cache reads do not count toward Bedrock token quotas.

## Table of Contents
- [Two Approaches](#two-approaches)
- [Setup Workflow](#setup-workflow)
- [Key Concepts](#key-concepts)
- [Minimum Token Thresholds](#minimum-token-thresholds)
- [Why Isn't My Cache Working?](#why-isnt-my-cache-working)
- [Debug Workflow](#debug-workflow)
- [Break-Even Analysis](#break-even-analysis)
- [Preventing Cache Fragmentation](#preventing-cache-fragmentation)

## Two Approaches

**Simplified** (Claude models only): A single `cachePoint` marker; Bedrock checks ~20 preceding blocks automatically. First request shows `cacheWriteInputTokens > 0`; subsequent identical requests show `cacheReadInputTokens > 0`.

**Explicit** (all supported models): Place multiple `cachePoint` markers at specific positions. Supports mixed TTL (1h + 5min) for different content sections.

## Setup Workflow

### 1. Choose Strategy

Ask the developer which approach fits. Simplified is recommended for Claude-only workloads. Explicit is required for Nova models or mixed-TTL scenarios.

### 2. Fetch Implementation Guidance

Before giving implementation advice, fetch the latest from the aws-samples repo:
- Use context7 MCP to query `amazon-bedrock-samples` for prompt caching docs
- Fallback: fetch `https://raw.githubusercontent.com/aws-samples/amazon-bedrock-samples/main/introduction-to-bedrock/prompt-caching/README.md`
- Key directories: `converse_api/` (recommended), `invoke_model_api/` (provider-specific)

### 3. Configure TTL

| TTL | Supported Models | Use Case |
|-----|-----------------|----------|
| 5 min (default) | All supported models | Dynamic content, short conversations |
| 1 hour | Claude Sonnet 4.6, Opus 4.6, Sonnet 4.5, Opus 4.5, Haiku 4.5 | System prompts, reference docs |

When mixing TTLs, longer durations MUST precede shorter ones.

### 4. Validate

Use the same SDK request twice inside the selected TTL. Keep the cacheable prefix byte-for-byte identical. Capture only the response `usage` object: the first request must show `cacheWriteInputTokens > 0`, and the second must show `cacheReadInputTokens > 0`. If either value is zero, use the checks below. Do not log prompt or response content as validation evidence.

## Key Concepts

The `cachePoint` is a standalone content block placed **after** the content to cache: `{"cachePoint": {"type": "default"}}`. For 1-hour TTL, add `"ttl": "1h"`.

Cache metrics in the Converse API `usage` object:
- `cacheWriteInputTokens > 0`: Cache populated (first request or expired)
- `cacheReadInputTokens > 0`: Cache hit (subsequent requests within TTL)
- Both zero: Below threshold or unsupported model

For InvokeModel (Anthropic format): `cache_creation_input_tokens` and `cache_read_input_tokens`.

**Good candidates:** System prompts, few-shot examples, reference docs, tool definitions, long code files.
**Poor candidates:** Per-request user messages, dynamic context, content below the token threshold.

## Minimum Token Thresholds

Content before a cache point must meet the model's minimum. Below threshold = silently ignored.

> **Note:** This table goes stale as new models launch. Before relying on it, fetch the latest supported models from the [Amazon Bedrock model cards](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html) and confirm the per-model threshold on that model's card.

| Model | Minimum Tokens |
|-------|---------------|
| Claude Sonnet 4.6 | 2,048 |
| Claude Opus 4.6 / Opus 4.5 / Haiku 4.5 | 4,096 |
| Claude Sonnet 4.5 / Opus 4.1 / Opus 4 / Sonnet 4 / 3.7 Sonnet / 3.5 Sonnet v2 | 1,024 |
| Claude 3.5 Haiku | 2,048 |
| Amazon Nova Pro | 1,024 |
| Amazon Nova Lite / Micro | 1,536 |

## Why Isn't My Cache Working?

Caching fails silently. Checklist:

1. **Model not supported?** Silently ignored for unsupported models.
2. **Below minimum threshold?** Cache point ignored if content is too short.
3. **Content not identical?** Cache keys use exact byte-for-byte prefix match. Invalidators: timestamps in system prompts, whitespace differences, reordered JSON keys, session tokens before the cache point.
4. **TTL expired?** Default is 5 minutes. After expiry, next request is a cache write.
5. **Cache point misplaced?** Must be a separate content block placed **after** the content to cache.

## Debug Workflow

Run six bounded checks when cache issues are reported: (1) current model support, (2) model token threshold, (3) cache write/read cycle, (4) one controlled prefix-sensitivity change, (5) TTL behavior, and (6) model-specific break-even analysis. Record usage counters and timing only; keep prompt and response content out of evidence files.

**If tests fail:** Focus on the matching section above. Prefix sensitivity failures indicate cache fragmentation (see below). Break-even failures mean caching is not cost-effective at the developer's request volume.

**After diagnosis:** Recommend simplified vs explicit caching for their model, 5-min vs 1-hour TTL for their request pattern, and whether caching is cost-effective.

## Break-Even Analysis

Cache write and read prices vary by model and can vary by TTL. Do not apply one 25% write premium, 90% read discount, or two-request break-even rule to every model.

For one cached token and `n` identical requests inside the TTL window:

```text
without_cache = n * standard_input_rate
with_cache    = cache_write_rate + ((n - 1) * cache_read_rate)
```

Add uncached input and output charges to both sides. Fetch the current rates for the exact model, Region or routing type, service tier, and TTL. Caching is cost-effective only when `with_cache < without_cache` for the measured hit rate. For single-use content, do not enable caching.

## Preventing Cache Fragmentation

Cache fragmentation = "static" content varies between requests. Fixes:

- Move timestamps and session IDs AFTER the cache point
- Separate static content from dynamic user context
- Use sorted JSON keys, consistent whitespace, fixed-format strings
