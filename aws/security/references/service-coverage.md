# Security service coverage discovery

Use this to locate the active control, its owner and the coverage gap. Do not enable services or organization-wide features during inventory. Complete the [shared preflight](../../references/cli-operating.md) and distinguish workload, management and delegated-administrator accounts.

## Start with metadata

```bash
set -euo pipefail
PROFILE="<confirmed-profile>"
REGION="<confirmed-region>"
aws configservice describe-configuration-recorders --profile "$PROFILE" --region "$REGION" \
  --query 'ConfigurationRecorders[].{Name:name,Role:roleARN,Group:recordingGroup,Mode:recordingMode}' \
  --output json --no-cli-pager
aws configservice describe-configuration-recorder-status --profile "$PROFILE" --region "$REGION" \
  --query 'ConfigurationRecordersStatus[].{Name:name,Recording:recording,Status:lastStatus,Error:lastErrorCode}' \
  --output json --no-cli-pager
aws securityhub describe-hub --profile "$PROFILE" --region "$REGION" \
  --query '{Arn:HubArn,Since:SubscribedAt,AutoEnable:AutoEnableControls}' \
  --output json --no-cli-pager
```

A Config recorder definition does not prove it is recording. Compare status and resource-type inclusions/exclusions, then validate the affected resource's recent configuration evidence. A Security Hub CSPM hub does not prove every standard/control or account is covered. Find the administrator, enabled standards and effective configuration before querying findings.

An access error must remain visible. Do not turn it into an empty list or assume the service is disabled.

## Pick only the relevant control

| Service | First metadata path | What it does not prove |
|---|---|---|
| GuardDuty | [Detector and coverage guide](guardduty.md) | One detector does not prove all protection plans/workloads are covered |
| Firewall Manager | Inspect `list-policies` in the administrator scope, then the relevant policy/compliance state | A local manual rule may be controlled or replaced centrally |
| Shield | Inspect subscription and relevant protections with the authorized owner | Subscription alone does not prove a particular resource is protected |
| Macie | Inspect `get-macie-session` in the chosen Region, then the approved bucket/job coverage | Enabled service does not mean every bucket was classified |
| Detective | Inspect `list-graphs` and the relevant membership in the owner scope | A graph alone is not incident evidence or complete account coverage |
| WAF | [Exposure response](exposure-response.md) | A Web ACL's existence does not prove attachment or rule behavior |

Resolve current CLI/API details before executing a follow-up operation. Record accounts, Regions, resource types, denied scopes and timestamps. Billing helps find likely owners but does not establish effective protection.

Enabling a plan, changing organization auto-enrollment, modifying recorder coverage or suppressing findings needs a separate approved change with cost, exclusions, rollback and post-change evidence. Do not remediate controls that belong to another controller through manual CLI writes.

## Sources

- [Configuration recorders](https://docs.aws.amazon.com/cli/latest/reference/configservice/describe-configuration-recorders.html), checked through Exa on 2026-09-04
- [Security Hub CSPM metadata](https://docs.aws.amazon.com/cli/latest/reference/securityhub/describe-hub.html), checked through Exa on 2026-09-04
