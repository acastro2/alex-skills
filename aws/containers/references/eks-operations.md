# EKS: access, nodes and add-ons

Use this for AWS-side EKS diagnosis. Keep the existing cluster and deployment path. Do not move a workload to ECS because the operator asked a generic container question.

Complete the [shared preflight](../../references/cli-operating.md). AWS IAM identity, Kubernetes authorization and endpoint reachability are separate checks.

```bash
set -euo pipefail
PROFILE="<confirmed-profile>"
REGION="<confirmed-region>"
aws eks list-clusters --profile "$PROFILE" --region "$REGION" \
  --output json --no-cli-pager
```

For one discovered cluster:

```bash
set -euo pipefail
PROFILE="<confirmed-profile>"
REGION="<confirmed-region>"
CLUSTER="<discovered-cluster-name>"
aws eks describe-cluster --name "$CLUSTER" --profile "$PROFILE" --region "$REGION" \
  --query 'cluster.{Name:name,Status:status,Version:version,Platform:platformVersion,Auth:accessConfig,Network:resourcesVpcConfig,Compute:computeConfig,Health:health.issues}' \
  --output json --no-cli-pager
aws eks list-nodegroups --cluster-name "$CLUSTER" --profile "$PROFILE" --region "$REGION" \
  --output json --no-cli-pager
aws eks list-addons --cluster-name "$CLUSTER" --profile "$PROFILE" --region "$REGION" \
  --output json --no-cli-pager
```

Managed node groups are not all compute. Check the discovered cluster's compute mode, Fargate profiles, self-managed nodes and provisioners in its IaC/Kubernetes configuration. Managed add-ons are not all Helm releases or controllers. Empty lists do not mean an empty cluster.

## Access failure

| Symptom | Next evidence |
|---|---|
| STS fails | Existing SSO/profile flow, not a cluster change |
| `DescribeCluster` denied | Exact IAM action/resource and caller |
| Kubernetes API timeout | Endpoint access mode, DNS and approved VPC/connected-network path |
| Kubernetes unauthorized/forbidden | Cluster auth mode, exact principal, access entries/policies or legacy `aws-auth`, then namespace/RBAC |
| Nodes or workload unhealthy | Exact nodes/pods/events and affected namespace after context is proven |

A private cluster API endpoint requires VPC or connected-network access. It is not a normal PrivateLink endpoint in the VPC endpoint list. Do not open public access to work around a local connection failure.

`update-kubeconfig` is a local state change: it merges/replaces entries and changes `current-context`. Get approval before altering the user's default file. Prefer an agreed separate file and explicit context. Its `--dry-run` prints configuration without writing; keep that output local. `--role-arn` controls Kubernetes authentication, while `--assume-role-arn` is for retrieving cluster information across accounts.

Prove the exact context and namespace before any Kubernetes action. Do not fetch secrets, full workload environment values or broad logs for access diagnosis. Do not change auth mode, add admin access, restart nodes or import an add-on into IaC without owner approval and recovery planning.

## Node/add-on or version change

Inspect `describe-nodegroup` / `describe-addon` for the selected returned names. Compare health, versions, launch template/configuration, IAM and recent updates. Check control-plane, node, add-on and client compatibility in current docs before selecting versions.

Find the current owning module/release controller. Review the plan, disruption budgets, capacity, drain behavior and application checks. Cluster version upgrades are not reversible downgrades; require an explicit recovery plan instead of promising a version rollback. A completed AWS update does not prove pods, DNS, storage drivers or application paths work.

## Sources

Checked through Exa and Context7 on 2026-09-04:
- [Cluster endpoint](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [Access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Describe cluster](https://docs.aws.amazon.com/cli/latest/reference/eks/describe-cluster.html)
- [Kubeconfig effects and role options](https://docs.aws.amazon.com/cli/latest/reference/eks/update-kubeconfig.html)
