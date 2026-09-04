# GuardDuty Coverage and Remediation

Use this when GuardDuty has a finding or Runtime Monitoring shows unhealthy ECS, EC2, or EKS coverage. The delegated administrator view is the source for organization coverage. A detector in the management account can return an empty but valid result.

Complete the shared [CLI preflight](../../references/cli-operating.md) first. Use an explicit list of governed Regions. Enabled Regions and governed Regions are not always the same set.

## Read-only investigation

### 1. Discover the detector in each Region

Detector IDs are regional. Discover one inside the loop. Do not paste an ID from another Region.

```bash
REGIONS=(replace-with-governed-region-1 replace-with-governed-region-2)

for region in "${REGIONS[@]}"; do
  detector_id=$(AWS_PROFILE="$DELEGATED_ADMIN_PROFILE" aws guardduty list-detectors \
    --region "$region" \
    --query 'DetectorIds[0]' \
    --output text \
    --no-cli-pager)

  if [[ -z "$detector_id" || "$detector_id" == "None" ]]; then
    printf '%s: no detector\n' "$region" >&2
    continue
  fi

  AWS_PROFILE="$DELEGATED_ADMIN_PROFILE" aws guardduty list-coverage \
    --region "$region" \
    --detector-id "$detector_id" \
    --filter-criteria '{"FilterCriterion":[{"CriterionKey":"COVERAGE_STATUS","FilterCondition":{"Equals":["UNHEALTHY"]}}]}' \
    --query 'Resources | length(@)' \
    --output text \
    --no-cli-pager
done
```

Keep every Region failure in the result. Do not report organization coverage as complete when a profile, Region, or detector lookup failed.

After the count, query one resource type at a time to resolve targets. Proven filter keys are `RESOURCE_TYPE` and `COVERAGE_STATUS`. Proven resource values include `ECS` and `EC2`.

For ECS, project the cluster and task group:

```bash
AWS_PROFILE="$DELEGATED_ADMIN_PROFILE" aws guardduty list-coverage \
  --region "$REGION" \
  --detector-id "$DETECTOR_ID" \
  --filter-criteria '{"FilterCriterion":[{"CriterionKey":"RESOURCE_TYPE","FilterCondition":{"Equals":["ECS"]}},{"CriterionKey":"COVERAGE_STATUS","FilterCondition":{"Equals":["UNHEALTHY"]}}]}' \
  --query 'Resources[].{Account:AccountId,Cluster:ResourceDetails.EcsClusterDetails.ClusterName,Task:ResourceDetails.EcsClusterDetails.TaskDetails.Group,Issue:Issue,Updated:UpdatedAt}' \
  --output json \
  --no-cli-pager
```

For EC2, project the instance ID and reported issue:

```bash
AWS_PROFILE="$DELEGATED_ADMIN_PROFILE" aws guardduty list-coverage \
  --region "$REGION" \
  --detector-id "$DETECTOR_ID" \
  --filter-criteria '{"FilterCriterion":[{"CriterionKey":"RESOURCE_TYPE","FilterCondition":{"Equals":["EC2"]}},{"CriterionKey":"COVERAGE_STATUS","FilterCondition":{"Equals":["UNHEALTHY"]}}]}' \
  --query 'Resources[].{Account:AccountId,InstanceId:ResourceDetails.Ec2InstanceDetails.InstanceId,Issue:Issue,Updated:UpdatedAt}' \
  --output json \
  --no-cli-pager
```

### 2. Classify before remediation

| Evidence | Next check |
|---|---|
| ECS task started before managed agent coverage applied | Inspect the owning ECS service and deployment settings |
| EC2 shows SSM unmanaged or disconnected | Check instance profile, SSM registration, network path, and agent state |
| EC2 association failed | Read association execution history and its error |
| Agent outdated or missing | Prove SSM is healthy before any agent action |
| Kernel or platform is unsupported | Route to the workload owner; an OS change can require replacement or reboot |
| EKS healthy | No change. Keep the evidence. |

Do not translate an empty `Issue` field into a root cause. Use resource state, service events, SSM state, and association history.

For an EC2 target, use read-only checks first:

```bash
AWS_PROFILE="$WORKLOAD_PROFILE" aws ec2 describe-iam-instance-profile-associations \
  --region "$REGION" \
  --filters "Name=instance-id,Values=$INSTANCE_ID" \
  --output json \
  --no-cli-pager

AWS_PROFILE="$WORKLOAD_PROFILE" aws ssm describe-instance-information \
  --region "$REGION" \
  --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
  --output json \
  --no-cli-pager

AWS_PROFILE="$WORKLOAD_PROFILE" aws ssm list-associations \
  --region "$REGION" \
  --association-filter-list "key=InstanceId,value=$INSTANCE_ID" \
  --output json \
  --no-cli-pager
```

An instance missing from SSM is not ready for an SSM remediation command. Check the instance profile, agent, endpoint or internet path, DNS, and port 443 before changing GuardDuty.

## Approved mutation

### ECS task replacement

A forced deployment can replace tasks that predate Runtime Monitoring agent injection. It is a workload deployment, not a harmless security toggle.

Before approval:

1. Switch from the delegated administrator profile to the exact workload account profile and repeat STS verification.
2. Capture `ecs describe-services` for the cluster and service.
3. Show desired count, running count, deployment configuration, task definition, health checks, and target count.
4. Confirm the source owner. A force deployment can be operationally valid even when the service is Terraform-managed, but do not change its managed configuration.
5. State rollback. A force deployment of the same task definition has no direct undo. If the rollout exposes a workload fault, restore the captured task definition and deployment settings through the owning path.

After approval:

```bash
AWS_PROFILE="$WORKLOAD_PROFILE" aws ecs update-service \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --output json \
  --no-cli-pager
```

Poll the ECS service until it reaches steady state or the approved deadline expires. Then poll GuardDuty coverage from the delegated administrator profile until the new tasks are healthy or its approved deadline expires. A successful `update-service` response is not proof of coverage.

For deployment mechanics and service-level rollback, use [ECS service scaling and updates](../../containers/references/service-scaling-and-updates.md).

### EC2 association rerun

Only rerun the exact failed association after you read its document, parameters, targets, and latest execution error. Capture the association and execution history first.

```bash
AWS_PROFILE="$WORKLOAD_PROFILE" aws ssm describe-association-executions \
  --region "$REGION" \
  --association-id "$ASSOCIATION_ID" \
  --output json \
  --no-cli-pager
```

After confirmation, a known association can be started once:

```bash
AWS_PROFILE="$WORKLOAD_PROFILE" aws ssm start-associations-once \
  --region "$REGION" \
  --association-ids "$ASSOCIATION_ID" \
  --no-cli-pager
```

This has no generic undo. The rollback is the recovery action defined by that association's owner. Poll association execution history to a hard deadline, then recheck SSM and GuardDuty coverage.

Do not attach an instance profile, install an agent, upgrade a kernel, reboot, or change a VPC endpoint from this workflow without a separate approved plan. Those changes can be Terraform-owned or disruptive.

## Failure modes to report plainly

- `list-coverage` returns zero in the wrong administrative account.
- One detector ID reused across Regions returns wrong-scope or not-found results.
- `AccessDeniedException` after STS succeeds means the selected role lacks permission. Re-login will not fix it.
- A forced ECS deployment can stall when capacity, health checks, or deployment settings cannot support replacement.
- SSM association success does not prove the GuardDuty agent is reporting. Recheck coverage.
- Partial Region results are partial coverage, not a clean bill of health.

Current command reference: [GuardDuty `list-coverage`](https://docs.aws.amazon.com/cli/latest/reference/guardduty/list-coverage.html).
