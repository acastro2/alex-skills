# Bedrock Cost Attribution and Tracking

Track, allocate, and manage Bedrock inference costs across teams, products, and models. Bedrock charges per input/output token with model-specific rates.

## Table of Contents
- [Cost Attribution Approaches](#cost-attribution-approaches)
- [Application Inference Profiles](#application-inference-profiles)
- [IAM Principal-Based Attribution](#iam-principal-based-attribution)
- [CloudWatch Usage Monitoring](#cloudwatch-usage-monitoring)
- [Budget Alerts](#budget-alerts)

## Cost Attribution Approaches

| Approach | Best For | Setup Effort |
|----------|----------|-------------|
| Application inference profiles + cost allocation tags | Per-product or per-team billed dollars on `bedrock-runtime` | Medium — create profiles, tag, activate in Billing |
| IAM principal attribution | Aggregated per-user or per-role billed dollars | Medium — identity capture is automatic, but billing export and optional tags need setup |
| Projects or Workspaces | Per-workload billed dollars on supported `bedrock-mantle` APIs | Medium — create and tag the resource, then activate tags |
| Request metadata + model invocation logging | Per-request token and estimated-cost analysis on `bedrock-runtime` | High — stamp metadata, enable protected logs, maintain rate logic |

For most teams, **application inference profiles with cost allocation tags** is the recommended approach. It provides clean cost breakdowns in Cost Explorer without custom analytics.

## Application Inference Profiles

### Setup Workflow

#### 1. Create an Application Inference Profile

```bash
AWS_PROFILE="$PROFILE" aws bedrock create-inference-profile \
  --inference-profile-name "$TEAM_OR_PRODUCT_NAME" \
  --model-source "copyFrom=$MODEL_SOURCE_ARN" \
  --region "$REGION" \
  --output json \
  --no-cli-pager
```

Note the returned `inferenceProfileArn`.

#### 2. Tag the Profile

```bash
AWS_PROFILE="$PROFILE" aws bedrock tag-resource \
  --resource-arn "$INFERENCE_PROFILE_ARN" \
  --tags key=CostCenter,value="$COST_CENTER" key=Project,value="$PROJECT" \
  --region "$REGION" \
  --no-cli-pager
```

#### 3. Activate Cost Allocation Tags

In the AWS Billing console (or via API), activate the tags as cost allocation tags. Tags take ~24 hours to appear in Cost Explorer after activation.

#### 4. Use the Profile for Inference

Replace the base model ID with the inference profile ARN in application code:

```python
response = bedrock_runtime.converse(
    modelId="<INFERENCE_PROFILE_ARN>",
    messages=[...],
    inferenceConfig={"maxTokens": 1024}
)
```

#### 5. Verify in Cost Explorer

After 24–48 hours, filter Cost Explorer by the tag keys. Bedrock costs appear under `Amazon Bedrock` service, grouped by tag values.

## IAM Principal-Based Attribution

Amazon Bedrock automatically captures the IAM user or role for inference requests on `bedrock-runtime` and `bedrock-mantle`. Billing visibility still needs explicit setup:

1. Create a **new CUR 2.0 Data Export** with the option to include the caller identity ARN. An existing export does not gain this column automatically or retroactively.
2. To add team, department, or cost-center dimensions, tag the IAM principals or pass session tags, then activate those keys as cost allocation tags in Billing.
3. Allow up to 24 hours for activated tags and cost data to appear. Tags are not retroactive.

The finest native billing grain is aggregated by usage type and identity or tag, not one row per inference request. A shared gateway role attributes every call to the gateway unless it assumes per-user or per-tenant sessions. Session tags are fixed for the STS session. Use a per-user role session for billed-dollar attribution, and use request metadata in protected invocation logs for per-prompt detail.

Do not put PII, secrets, credentials, or regulated values in principal, session, or request-metadata tags.

## CloudWatch Usage Monitoring

Key metrics for cost monitoring (namespace `AWS/Bedrock`, dimension `ModelId`):

| Metric | Cost Signal |
|--------|------------|
| `InputTokenCount` | Input token spend (charged per token) |
| `OutputTokenCount` | Output token spend (higher per-token rate) |
| `Invocations` | Request volume |
| `CacheReadInputTokens` | Tokens served from cache (billed at a reduced rate; see pricing page) |
| `CacheWriteInputTokens` | Cache write tokens (may be billed above the standard input rate; see pricing page) |

Exact cache read and write rates are model-dependent — consult the [Amazon Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/) for the specific model, endpoint, service tier, and routing type.

CUR and Cost Explorer provide invoice-aligned aggregated dollars. They do not contain a per-request identifier. For per-prompt analysis, use model invocation logs, which contain token counts and optional `requestMetadata`, then calculate an estimate with the current model rate. Reconcile that estimate to CUR at the model, usage-type, and time grain; do not claim a request-ID join or exact per-prompt billed cost.

### Cost Explorer Analysis

Use Cost Explorer for aggregated billed spend. Supply an inclusive start date and exclusive end date:

```bash
AWS_PROFILE="$PROFILE" aws ce get-cost-and-usage \
  --region us-east-1 \
  --time-period Start="$START_DATE",End="$END_DATE" \
  --granularity DAILY \
  --metrics UnblendedCost UsageQuantity \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Bedrock"]}}' \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json \
  --no-cli-pager
```

Account for input, output, cache-read, and cache-write usage types. Apply the correct rate for the endpoint, service tier, and routing type. Do not sum token quantities across usage types as if they had one price.

## Budget Alerts

Set up AWS Budgets to alert when Bedrock spend approaches a threshold. Budget creation changes account state and can notify real recipients. Prove the caller, use `us-east-1`, inspect existing budgets, show the exact Bedrock cost filter and recipients, and get confirmation first.

Read [AWS Budgets](../../billing/references/budgets.md) for the scoped, file-based creation pattern. Add `"CostFilters":{"Service":["Amazon Bedrock"]}` to its budget JSON. This can alert at 80% of the monthly budget; confirm the threshold and notification targets with the user.
