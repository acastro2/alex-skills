# CloudTrail Operational Auditing

Using CloudTrail for operational debugging: who changed what, when. Not for security threat detection.

## Contents
- [Event types](#event-types)
- [Event history](#event-history)
- [Common operational queries](#common-operational-queries)
- [Organization audit baseline](#organization-audit-baseline)
- [Querying CloudTrail logs](#querying-cloudtrail-logs)
- [CloudTrail → CloudWatch integration](#cloudtrail-cloudwatch-integration)

---

## Event types

| Type | Description | Default logging | Cost |
|------|-------------|:-:|------|
| **Management events** | Control plane (CreateBucket, RunInstances, IAM changes) | Yes | First copy included |
| **Data events** | Data plane (S3 GetObject, Lambda Invoke, DynamoDB GetItem) | No | Additional cost |
| **Network activity events** | VPC endpoint activity | No | Additional cost |
| **Insights events** | Unusual API call rate or error rate | No | Additional cost |

---

## Event history

- **90 days** of management events retained by default, no trail required
- Searchable in the console by one lookup attribute plus a time range
- Single account, single Region only
- Cannot view data events, Insights events, or network activity events
- Useful for a narrow known management event; not a complete incident or compliance evidence source

### Common lookups
```bash
# Who deleted an S3 bucket?
AWS_PROFILE="$PROFILE" aws cloudtrail lookup-events \
  --region "$REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteBucket \
  --start-time 2026-04-20T00:00:00Z \
  --output json \
  --no-cli-pager

# Who modified a security group?
AWS_PROFILE="$PROFILE" aws cloudtrail lookup-events \
  --region "$REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress \
  --output json \
  --no-cli-pager

# Who stopped an EC2 instance?
AWS_PROFILE="$PROFILE" aws cloudtrail lookup-events \
  --region "$REGION" \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=i-1234567890abcdef0 \
  --output json \
  --no-cli-pager
```

---

## Common operational queries

### "Who deleted my resource?"
1. Identify whether the delete operation is logged as a management or data event.
2. For a known management event in the last 90 days, query Event History in the exact account and Region.
3. For organization-wide, cross-Region, older, or data-event evidence, query the approved centralized trail or event data store instead.
4. Inspect `userIdentity`, `sourceIPAddress`, request parameters, and the event time. A missing Event History result does not prove that no delete occurred.

### "Who changed this configuration?"
1. Search for `Update*`, `Modify*`, `Put*` events on the resource
2. Compare `requestParameters` across events to see what changed

### "What happened during the incident?"
1. Use the centralized organization trail or event data store across every affected account and Region; do not rely on Event History alone.
2. Filter by the incident time range and relevant event sources, names, resources, and principals.
3. Look for `errorCode` fields such as `AccessDenied` and `ThrottlingException`.
4. Correlate with CloudWatch metrics, logs, deployments, and configuration history for the same window.

### "Who accessed my data?" (requires data events)

Event History cannot answer this. Query an existing trail or event data store that records the required resource type. If coverage is missing, use the reviewed [CloudTrail data-event change procedure](../../security/references/cloudtrail-data-events.md). It resolves the trail Home Region, captures the complete selector state, controls cost and scope, and prevents `put-event-selectors` from replacing unrelated coverage.

---

## Organization audit baseline

For production and incident evidence, maintain one approved centralized baseline rather than creating trails during an incident:

- Use an organization trail or organization event data store that covers every account and Region in scope, including global service events where required.
- Deliver trail logs to a protected central log-archive account. Encrypt them, restrict read and delete access, and set retention and lifecycle from audit and incident requirements.
- Enable log file integrity validation for trails and verify delivery in every account and Region.
- Monitor and alert on changes that can blind audit collection, including `StopLogging`, `DeleteTrail`, `UpdateTrail`, and `PutEventSelectors`. Protect these controls with organization guardrails and separate security administration.
- Test that named management and approved data events arrive and remain queryable. A configured trail alone is not proof of usable evidence.

Changing this baseline is a security architecture change. Capture current state, expected coverage and cost, rollback, and owner approval first. If Control Tower or another landing-zone system owns it, use that system's supported change path.

---

## Querying CloudTrail logs

### Recommended: Trail → S3 → Athena

For new setups, deliver CloudTrail logs to S3 and query with Amazon Athena:

```sql
SELECT eventTime, userIdentity.arn, sourceIPAddress, eventName
FROM cloudtrail_logs
WHERE eventName = 'DeleteBucket'
  AND eventTime > '2026-04-20'
ORDER BY eventTime DESC
LIMIT 100;
```

This is the long-term supported approach — works with standard SQL, scales to any volume, and integrates with existing S3-based analytics.

---

## CloudTrail → CloudWatch integration

### Alert on specific API calls
```
CloudTrail → Trail → CloudWatch Logs → Metric Filter → CloudWatch Alarm → SNS
```

1. Configure trail to deliver events to a CloudWatch Logs log group
2. Create metric filter for the event pattern (e.g., `{ $.eventName = "DeleteBucket" }`)
3. Create alarm on the metric filter
4. Configure SNS notification

### Event selectors
- **Basic**: simple include/exclude for management and data events
- **Advanced**: fine-grained filtering by event source, resource type, resource ARN
- Exclude high-volume management event sources on trails: AWS KMS, RDS Data API
- Max **250 data resources** across all basic event selectors per trail (does not apply to advanced event selectors)
