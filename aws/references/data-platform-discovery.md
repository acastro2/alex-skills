# Data platform discovery

Use this to find the owner and resource behind SageMaker or Airflow charges. Billing can describe older use or a vendor subscription. It does not prove an active endpoint, notebook or MWAA environment.

Complete the [shared preflight](cli-operating.md). Start in approved billed account/Region scopes, then inspect only metadata.

```bash
set -euo pipefail
PROFILE="<confirmed-profile>"
REGION="<confirmed-region>"
aws sagemaker list-domains --profile "$PROFILE" --region "$REGION" \
  --query 'Domains[].{Id:DomainId,Name:DomainName,Status:Status}' --output json --no-cli-pager
aws sagemaker list-endpoints --profile "$PROFILE" --region "$REGION" \
  --query 'Endpoints[].{Name:EndpointName,Status:EndpointStatus,Modified:LastModifiedTime}' \
  --output json --no-cli-pager
aws mwaa list-environments --profile "$PROFILE" --region "$REGION" \
  --output json --no-cli-pager
```

These lists are not a complete SageMaker inventory. Use the actual usage types and owning repo to choose the next resource family: Studio apps/spaces, notebook instances, training, processing, batch transform or inference. Stopped endpoints do not account for storage or every other billable resource.

For one discovered endpoint, inspect its configuration and variant capacity/health with projected `describe-endpoint` / `describe-endpoint-config` output. Do not invoke it, download a model, open a notebook, read datasets or print environment values during cost discovery.

For MWAA, inspect the chosen environment's state, network, execution role and logging configuration with projected `get-environment` output. Do not create CLI/web login tokens or run DAGs as an inventory step. A vendor-managed Airflow deployment may live outside MWAA; find its owning platform instead of treating an empty MWAA list as proof of no Airflow.

## Changes and proof

Discovery ends with a report, not a change. If the owner then asks for a stop, resize, delete or schedule change, every answer must carry this gate, in this order:

1. **Owner** named and in agreement. No owner, no change.
2. **Dependencies** checked: who calls the endpoint, which pipelines read the notebook output, which jobs run on the schedule. Low utilization can still be a monthly batch.
3. **Impact and retention**: what stops working, what data must be kept, and for how long.
4. **Approved diff and recovery**: the exact before state saved (`describe-endpoint-config`, `describe-notebook-instance`), the exact command, and how to restore it.
5. **Proof after the fact**: a successful API response is not a saving. Confirm the workload still completes and confirm the drop on the next bill after the billing lag.

Write these five out even when the current task is discovery only, so the reader knows what the next step costs.

For deep service configuration, fetch current official docs through Exa and exact APIs through Context7. Keep local depth small until a real task needs more.

## Sources

Checked through Exa and Context7 on 2026-09-04:
- [SageMaker domains](https://docs.aws.amazon.com/cli/latest/reference/sagemaker/list-domains.html)
- [SageMaker endpoints](https://docs.aws.amazon.com/cli/latest/reference/sagemaker/list-endpoints.html)
- [MWAA environments](https://docs.aws.amazon.com/cli/latest/reference/mwaa/list-environments.html)
