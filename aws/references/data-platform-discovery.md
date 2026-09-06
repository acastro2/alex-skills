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

Before a stop, resize, delete or schedule change, require the owner, dependencies, impact, retention requirements, approved diff and recovery plan. A resource with low utilization can still support scheduled or infrequent work. Confirm cost after the billing lag and verify the workload still completes; do not call an API response a realized saving.

For deep service configuration, fetch current official docs through Exa and exact APIs through Context7. Keep local depth small until a real task needs more.

## Sources

Checked through Exa and Context7 on 2026-09-04:
- [SageMaker domains](https://docs.aws.amazon.com/cli/latest/reference/sagemaker/list-domains.html)
- [SageMaker endpoints](https://docs.aws.amazon.com/cli/latest/reference/sagemaker/list-endpoints.html)
- [MWAA environments](https://docs.aws.amazon.com/cli/latest/reference/mwaa/list-environments.html)
