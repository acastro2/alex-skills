# AWS Budgets

> **Pricing note:** All prices shown are approximate as of early 2026 and may change. Always verify current pricing before reporting to users.

## Budget Types

| Type | Use Case |
|------|----------|
| COST | Track spend against dollar amount (default) |
| USAGE | Track usage quantity (e.g., EC2 hours) |
| RI_UTILIZATION | Alert when RI utilization drops below threshold |
| SAVINGS_PLANS_UTILIZATION | Alert when SP utilization drops |

Use `FORECASTED` notification type to catch runaway costs before they hit threshold.

## Create Budget with Alerts

Budget creation changes account state and can notify real recipients. Prove the caller, list existing budgets, validate the payload files, and get confirmation before creation.

```bash
jq -n '{
  BudgetName: "Monthly-Total",
  BudgetLimit: {Amount: "1000", Unit: "USD"},
  TimeUnit: "MONTHLY",
  BudgetType: "COST"
}' > budget.json

jq -n \
  --arg email "$BUDGET_EMAIL" \
  --arg topic "$BUDGET_SNS_TOPIC_ARN" \
  '[
    {Notification: {NotificationType: "ACTUAL", ComparisonOperator: "GREATER_THAN", Threshold: 80, ThresholdType: "PERCENTAGE"}, Subscribers: [{SubscriptionType: "EMAIL", Address: $email}]},
    {Notification: {NotificationType: "FORECASTED", ComparisonOperator: "GREATER_THAN", Threshold: 100, ThresholdType: "PERCENTAGE"}, Subscribers: [{SubscriptionType: "SNS", Address: $topic}]}
  ]' > notifications.json

jq -e '.' budget.json notifications.json >/dev/null

AWS_PROFILE="$PROFILE" aws budgets create-budget \
  --region us-east-1 \
  --account-id "$ACCOUNT_ID" \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json \
  --no-cli-pager
```

Each threshold is a separate entry in `NotificationsWithSubscribers`. Do not put multiple thresholds in one notification object.

## Tag-Based Budget

Use `CostFilters` with `TagKeyValue` key and `tag-key$tag-value` format:
```json
"CostFilters": {"TagKeyValue": ["user:Environment$production"]}
```

## Budget Actions

Budget Actions are optional responses to a threshold, not automatic hard spending limits. Each action needs an IAM execution role and an explicit approval model:

- `MANUAL`: AWS waits for an authorized approval before execution.
- `AUTOMATIC`: AWS runs the approved action when the threshold is met.

Supported definitions include attaching an IAM policy, attaching an Organizations SCP, or targeting EC2 or RDS resources. SCP attachment must be created from the Organizations management account. Budget evaluation is periodic, so an action cannot prevent all spend beyond a threshold.

Before creating an action, show the threshold, approval model, execution role, exact targets, blast radius, recovery path, and notification recipients. Get confirmation. Prefer notification-only budgets unless the user has approved tested enforcement behavior.

## Gotchas

- **Budgets API requires `us-east-1` region** for global billing data
- Monitoring-only budgets (no actions) are free — unlimited
- First 2 action-enabled budgets are free; additional action-enabled budgets cost $0.10/day each
- Budget Reports cost $0.01 per report delivered
- Budget alerts evaluate once per day — up to 24-hour delay, not real-time
- `FORECASTED` alerts use ML-based forecasting — useful for catching runaway costs early
- Budget Actions are powerful but dangerous — test in non-prod first
- RI/SP utilization budgets default to 100% — set to 80% for practical alerting
