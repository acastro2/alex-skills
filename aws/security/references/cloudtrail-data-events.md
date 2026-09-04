# CloudTrail Data-Event Changes

Use this when a named consumer needs object-level or service data-plane evidence. Do not use it for normal control-plane investigation. Event history covers management events and does not show data events.

For management-event lookup and long-term S3 or Athena analysis, use [CloudTrail operational auditing](../../observability/references/cloudtrail.md). Complete the shared [CLI preflight](../../references/cli-operating.md) before any command.

## Read-only decision and inventory

Do not enable data events only because a security finding asks for "more logs." Before a change, write down:

- The consumer and the question it will answer.
- The exact account, Region scope, trail owner, resource type, and resource scope.
- The expected event names or read/write category.
- The destination, retention, encryption, query path, and evidence owner.
- The expected event volume and approved cost owner.
- The test event and proof that will show collection works.
- The rollback selector set.

GuardDuty has independent data sources for its protections. Do not assume GuardDuty, Security Hub, Inspector, or another service consumes CloudTrail data events. Prove the consumer.

Capture the exact trail and resolve its Home Region before touching selectors. `get-event-selectors` and `put-event-selectors` must run in that Home Region, not a generic operating Region.

```bash
AWS_PROFILE="$PROFILE" aws cloudtrail describe-trails \
  --region "$REGION" \
  --trail-name-list "$TRAIL_NAME" \
  --no-include-shadow-trails \
  --output json \
  --no-cli-pager \
  > "$EVIDENCE_DIR/trails-before.json"

HOME_REGION=$(jq -er --arg trail "$TRAIL_NAME" \
  '[.trailList[] | select(.Name == $trail or .TrailARN == $trail) | .HomeRegion]
   | if length == 1 then .[0] else error("expected exactly one trail") end' \
  "$EVIDENCE_DIR/trails-before.json")

AWS_PROFILE="$PROFILE" aws cloudtrail get-event-selectors \
  --region "$HOME_REGION" \
  --trail-name "$TRAIL_NAME" \
  --output json \
  --no-cli-pager \
  > "$EVIDENCE_DIR/selectors-before.json"

jq -e '.' "$EVIDENCE_DIR/selectors-before.json" >/dev/null
```

Record whether the trail uses basic `EventSelectors` or `AdvancedEventSelectors`. Keep the untouched CLI export and make a separate rollback array from its matching field. `put-event-selectors` replaces the trail's complete existing selector configuration; it does not merge the submitted selector with the old state. Do not prepare rollback after the write.

If Control Tower owns the organization trail, stop and confirm the supported change path. A manual selector change can be reverted by a landing-zone update. A second organization trail is not a safe shortcut: it can add cost, duplicate events, require new S3 and KMS access, and trigger security alerts.

## Build one reviewed selector set

Advanced selector fields differ by event resource type. Do not copy fields from S3 to Lambda, Bedrock, Secrets Manager, or another service. The observed failure was `InvalidEventSelectorsException` after several resource types were combined without proving each supported shape.

Use these controls:

1. Start with one resource type and one named consumer.
2. Use current AWS documentation for the supported `resources.type`, `eventSource`, `eventName`, and resource ARN operators.
3. Scope the selector to the smallest resource set that answers the question.
4. Put the complete reviewed advanced-selector array in `reviewed-selectors.json`. Because the write replaces all current selectors, preserve required management-event and data-event coverage when moving from basic to advanced selectors.
5. Validate JSON locally with `jq -e`.
6. Prepare the rollback payload from the before export and validate it separately.
7. Prepare the rollback command with `--event-selectors` for a basic before state or `--advanced-event-selectors` for an advanced before state.

Do not invent selector fields. Do not use the broad all-S3-object example from an operational note as a production default.

```bash
jq -e 'type == "array" and length > 0' \
  "$EVIDENCE_DIR/reviewed-selectors.json" >/dev/null

jq -e 'type == "array"' \
  "$EVIDENCE_DIR/rollback-selectors.json" >/dev/null
```

The rollback filename is only a local convention. Its contents and command flag must match the original selector mode.

## Approved mutation

Before confirmation, show:

- STS caller, account, operating Region, and the trail's resolved Home Region.
- Trail name and owner.
- Before selector export.
- Reviewed selector payload and exact resource scope.
- Consumer, cost owner, test event, and expected evidence.
- Rollback payload and the exact rollback command.
- Any monitoring team that can receive a CloudTrail-modified alert.

After approval, apply the complete reviewed set:

```bash
AWS_PROFILE="$PROFILE" aws cloudtrail put-event-selectors \
  --region "$HOME_REGION" \
  --trail-name "$TRAIL_NAME" \
  --advanced-event-selectors "file://$EVIDENCE_DIR/reviewed-selectors.json" \
  --output json \
  --no-cli-pager \
  > "$EVIDENCE_DIR/put-event-selectors-response.json"

jq -e '.' "$EVIDENCE_DIR/put-event-selectors-response.json" >/dev/null
```

This request changes trail configuration. Never retry it blindly after a timeout or client error. Read the selectors first because AWS might have accepted the first request.

Verify in two layers:

1. Read the configured selectors again in the trail's Home Region and compare them with the reviewed payload:
   ```bash
   AWS_PROFILE="$PROFILE" aws cloudtrail get-event-selectors \
     --region "$HOME_REGION" \
     --trail-name "$TRAIL_NAME" \
     --output json \
     --no-cli-pager \
     > "$EVIDENCE_DIR/selectors-after.json"
   jq -e '.' "$EVIDENCE_DIR/selectors-after.json" >/dev/null
   ```
2. Generate the approved bounded test event, then poll the named destination or consumer to its approved deadline.

A successful `put-event-selectors` response does not prove event delivery. Record delivery latency, query, result, and any Region or account gap.

Rollback uses the prepared before-state payload and its matching basic or advanced selector flag. Show that exact command before approval. Do not use `--advanced-event-selectors` to restore a basic before state.

After rollback, export selectors again and compare them with the untouched before export. Poll the security monitoring path if the change created an alert.

## Failure modes to keep visible

- Event history cannot validate data-event collection.
- A selector accepted by JSON parsing can still be invalid for that resource type.
- A trail can be active while the intended selector is absent or too broad.
- A selector read or write in a non-Home Region can fail or inspect the wrong trail view.
- A partial selector payload deletes coverage that is not repeated in the request.
- A security control can alert on `PutEventSelectors`, trail creation, or trail deletion. Coordinate the expected change.
- No consumer means no justified data-event spend.
- Missing records can mean wrong account, wrong Region, wrong selector, delivery delay, retention loss, or a query limit. It does not prove no access.

Current command reference: [CloudTrail `put-event-selectors`](https://docs.aws.amazon.com/cli/latest/reference/cloudtrail/put-event-selectors.html).
