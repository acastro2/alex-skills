# Exposure Investigation and Containment

Use this for a public endpoint that returns sensitive configuration, a suspect ALB route, or a WAF evidence question. The first goal is to stop further disclosure without destroying evidence or taking the whole application offline.

Complete the shared [CLI preflight](../../references/cli-operating.md) first. Keep investigation read-only until the exact host, path, listener, owner, and evidence needs are known.

## Read-only investigation

### Probe routing without downloading the body

Use an HTTP `HEAD` request. Do not use `curl --output /dev/null` with a normal `GET`: curl still downloads the body before it discards it.

```bash
curl --head --silent --show-error \
  --output /dev/null \
  --write-out 'HEAD HTTP %{http_code} type=%{content_type}\n' \
  'https://replace-with-approved-test-url'
```

Record the UTC time, status, content type, and exact variant tested. This proves only the `HEAD` route and response. It does not prove that `GET` returns the same result. If the application does not support `HEAD`, use existing edge or application logs. Do not fall back to a secret-bearing `GET` without the incident owner's explicit evidence plan.

### Map the edge path

Start from the exact listener ARN and preserve its rules:

```bash
AWS_PROFILE="$PROFILE" aws elbv2 describe-rules \
  --region "$REGION" \
  --listener-arn "$LISTENER_ARN" \
  --output json \
  --no-cli-pager \
  > "$EVIDENCE_DIR/listener-rules-before.json"

jq -e '.' "$EVIDENCE_DIR/listener-rules-before.json" >/dev/null
```

Confirm which rule matches the host and path, its priority, action, and target. Do not assume source code, a Terraform file, and the live listener match.

For a known regional WAF web ACL, inspect logging and attached resources:

```bash
AWS_PROFILE="$PROFILE" aws wafv2 get-logging-configuration \
  --region "$REGION" \
  --resource-arn "$WEB_ACL_ARN" \
  --output json \
  --no-cli-pager

AWS_PROFILE="$PROFILE" aws wafv2 list-resources-for-web-acl \
  --region "$REGION" \
  --web-acl-arn "$WEB_ACL_ARN" \
  --output json \
  --no-cli-pager
```

Use `REGIONAL` resources in their Region. CloudFront WAF work uses the `CLOUDFRONT` scope and `us-east-1`. Do not mix them.

### Preserve evidence and state limits

Use one explicit UTC window from the earliest supportable exposure time through containment. Review the available sources:

- WAF logs for host, URI variants, source address, timestamp, user agent, request ID, action, and count.
- ALB access logs, if they were enabled before the incident.
- Application and web-server logs for every active instance or task.
- Deployment history and active artifact identifiers.
- Identity, database, vendor, GuardDuty, and CloudTrail evidence tied to exposed credentials.

A WAF log miss does not prove no access. Record the destination, window, filter, fields, pagination or query limits, retention, and failed sources. If ALB access logging was off, say so as an evidence gap.

Do not reboot, redeploy, rotate, or clean the workload until the incident owner decides whether local or volatile evidence must be preserved.

## Approved containment mutation

A higher-priority fixed response on the exact ALB host and path can stop disclosure while leaving the rest of the application available. The networking module owns that change. Follow [ALB listener emergency response](../../networking/references/listener-emergency.md) for the reviewed payload, confirmation gate, verification, and exact-ARN rollback.

The security incident owner must first supply the evidence window, affected route variants, safe comparison route, and evidence-preservation decision. If Firewall Manager, Terraform, or another controller owns the edge, coordinate the durable fix there so the temporary rule is not reverted or duplicated.

Do not improvise a WAF, listener-default, security-group, DNS, or application deployment change from this investigation. Each option has a different blast radius and owner. Use the narrow ALB rule only when that exact method is approved.

## Close with evidence, not confidence

Containment is not remediation. Keep the edge block until the deployed artifact is proven fixed on every target, all exposed credentials have an owner and rotation or revocation result, the available evidence has been reviewed for a defined window, and remaining gaps are written plainly.

Do not claim "no impact," "no access," or "not reportable" from a failed credential test or missing logs. Route legal, privacy, contractual, and notification decisions to the responsible teams.

Current command references: [WAF logging configuration](https://docs.aws.amazon.com/cli/latest/reference/wafv2/get-logging-configuration.html) and [WAF resources](https://docs.aws.amazon.com/cli/latest/reference/wafv2/list-resources-for-web-acl.html).
