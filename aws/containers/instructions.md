---
name: aws-containers
description: >-
  Operates containerized workloads on ECS, Fargate, EKS, and ECR. Covers task
  definitions, Fargate services, ECR repository setup and lifecycle policies, ECS
  Exec debugging, service scaling, deployment strategies, load balancer integration,
  and logging configuration. Use when deploying, debugging, or optimizing containers
  on AWS. ALSO USE for container deployment options (ECS vs ECS Express Mode), networking
  modes, health check troubleshooting, OOM errors, secrets injection, blue/green deployments,
  ECR image management, EKS access/nodes/add-ons, and existing App Runner services.
  For Kubernetes workload changes use the repo's Kubernetes tooling; for CI use delivery.
version: 1
allowed-tools: [Read]
---

# AWS Containers

## Start with the existing platform

Read the [shared CLI guide](../references/cli-operating.md). Inspect the workload's cluster, IaC and delivery owner before selecting a service. Do not recommend a new platform merely because the user says "deploy my container."

| Need | Start here |
|---|---|
| Existing Kubernetes cluster, access, nodes or add-ons | [EKS operations](references/eks-operations.md) |
| ECS tasks/services on Fargate or EC2 | Focused ECS references below |
| Image identity, pull failures or lifecycle | ECR reference below |
| Release automation and runtime digest proof | [Delivery](../delivery/instructions.md) |
| New platform choice | Establish requirements and compare against the existing deployment path first |

CDK examples below are for CDK repos. Use existing Terraform/OpenTofu modules or manifests when those own the workload.

## Overview

Provides ECS/Fargate/ECR runtime guidance and AWS-side EKS diagnosis. Existing App Runner is a limited compatibility path.

**When NOT to use this skill:**
- Kubernetes workload manifests and in-cluster changes → establish EKS access here, then use the repo's Kubernetes tooling
- AWS release automation and deployment proof → use `aws-delivery`
- Live VPC, security-group, and ALB investigation → use `aws-networking`; this skill does not design new network architecture
- Running code without containers (Lambda, Step Functions) → use the serverless skill

**Before executing any commands:**
- You MUST verify AWS CLI v2 is installed and configured before running commands
- You MUST inform the user if required tools (AWS CLI, Docker, Session Manager plugin) are missing
- You MUST respect the user's decision to abort at any point

## Gotchas

Apply these every time. Each corrects a mistake agents make without explicit instruction.

1. **Fargate CPU/memory must be valid combinations.** Arbitrary values cause `Invalid 'cpu' setting for task`:
   - 256 (0.25 vCPU): 512 MiB, 1 GB, 2 GB
   - 512 (0.5 vCPU): 1–4 GB (1 GB increments)
   - 1024 (1 vCPU): 2–8 GB (1 GB increments)
   - 2048 (2 vCPU): 4–16 GB (1 GB increments)
   - 4096 (4 vCPU): 8–30 GB (1 GB increments)
   - 8192 (8 vCPU): 16–60 GB (4 GB increments)
   - 16384 (16 vCPU): 32–120 GB (8 GB increments)

   If the user requests an invalid combination, tell them and recommend the nearest valid option. You MUST NOT silently produce an invalid task definition.

2. **Fargate requires `awsvpc` networking mode — no exceptions.** Agents frequently suggest `bridge` or `host` mode for Fargate tasks, which causes immediate registration failure. You MUST set `networkMode` to `awsvpc` for all Fargate task definitions. On EC2, `awsvpc` is recommended; `bridge` is legacy only.

3. **Execution role vs task role — never confuse them.** `executionRoleArn`: ECS agent uses it to pull images, fetch secrets, write logs. `taskRoleArn`: application code uses it to call AWS APIs. ECS Exec permissions (`ssmmessages:*`) go on the task role. ECR pull permissions go on the execution role. `ecr:GetAuthorizationToken` MUST use `Resource: "*"` (registry-level action).

4. **Secrets are injected at task launch only — no hot-reload.** Changed secrets require `aws ecs update-service --force-new-deployment`. To reference a specific JSON key in Secrets Manager: `arn:aws:secretsmanager:region:account:secret:name-hash:json-key::` — the trailing colons are required (they represent empty version-stage and version-id fields). You can also use SSM Parameter Store with `valueFrom` pointing to the parameter ARN — the execution role needs `ssm:GetParameters` permission.

5. **ALB deregistration delay defaults to 300s — reduce to 30–60s.** This is the #1 cause of slow deployments. Set it on the target group. It SHOULD exceed your longest request duration.

6. **Set `healthCheckGracePeriodSeconds` on every ECS service behind an ALB.** Without it, the ALB marks tasks unhealthy before they're ready, the circuit breaker counts failures, and the deployment rolls back. JVM/Spring Boot apps need 60–120s.

7. **Always enable deployment circuit breaker with rollback.** Without it, bad deployments stay "in progress" for 30+ minutes. In CDK: `circuitBreaker: { rollback: true }` (specifying the property implicitly enables it; `enable` defaults to `true`).

8. **Private subnet Fargate tasks need NAT or all four VPC endpoints.** Required endpoints: `ecr.dkr` (interface), `ecr.api` (interface), `s3` (gateway — ECR stores layers in S3), `logs` (interface — for CloudWatch). The S3 gateway endpoint is the most commonly missed. For ECS Exec, also add `ssmmessages`.

9. **ECR lifecycle policies evaluate within 24 hours — not immediately.** Multi-architecture images referenced by a manifest list cannot be expired until the manifest list is deleted first. Preview before applying: first `aws ecr start-lifecycle-policy-preview --repository-name $REPO`, then `aws ecr get-lifecycle-policy-preview --repository-name $REPO --output json` to see which images would be affected.

10. **ECS Exec requires task role permissions, NOT execution role.** The task role needs `ssmmessages:CreateControlChannel`, `CreateDataChannel`, `OpenControlChannel`, `OpenDataChannel`. Tasks launched before enabling `enableExecuteCommand` do NOT support ECS Exec — force a new deployment. The container image must include the binary specified in `--command` (e.g., `/bin/sh` for interactive sessions). For command logging to S3 or CloudWatch Logs, `script` and `cat` must also be installed. Fargate platform version MUST be 1.4.0+.

11. **`awslogs` log driver mode — check your account's default.** Per [ECS docs](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html), the ECS service defaults to `non-blocking` mode, which drops logs when the buffer fills. The `defaultLogDriverMode` account setting can override this per account. For guaranteed log delivery (audit/compliance), explicitly set `"mode": "blocking"` in `logConfiguration.options`. Check your effective default: `aws ecs list-account-settings --name defaultLogDriverMode --effective-settings --output json`.

12. **App Runner VPC connector routes ALL application-initiated outbound traffic through the VPC.** (App Runner is closed to new customers; AWS has not announced an end-of-life date for existing services and plans no new features.) Without a NAT gateway, external API calls and AWS service calls from your application code break. App Runner's own managed traffic (pulling images, pushing logs, retrieving secrets) is NOT routed through the VPC and is unaffected. Implement retry logic with backoff for database connections at startup.

13. **For `desiredCount=1` zero-downtime deploys: `minimumHealthyPercent=100, maximumPercent=200`.** This requires capacity for 2 tasks during deployment. You MUST NOT set `minimumHealthyPercent=0` if zero downtime is required.

14. **502 Bad Gateway from ALB — check in this order:** (a) Container not listening on the port in the target group. (b) Container crashing before responding. (c) Task security group doesn't allow inbound from ALB security group on the container port. (d) Health check path returns non-200. (e) Health check timeout exceeds response time.

15. **Fargate Linux platform version: use `LATEST` or `1.4.0`.** Version 1.3.0 was deprecated on June 15, 2026. It cannot launch new tasks or services and no longer receives fixes. Existing tasks continue only until stopped; AWS does not list a forced-update date. Migrate and test them on 1.4.0.

16. **SQS worker scaling: use a custom backlog-per-task metric.** Raw `ApproximateNumberOfMessagesVisible` with target tracking doesn't work because adding tasks doesn't reduce queue depth proportionally. Use custom metric (`ApproximateNumberOfMessagesVisible / RunningTaskCount`) with target tracking, or use step scaling. CDK `QueueProcessingFargateService` handles this automatically via `scalingSteps`. Workers MUST handle SIGTERM gracefully within `stopTimeout` (default 30s, max 120s on Fargate).

17. **Blue/green deployments: prefer native ECS blue/green for new services when its current feature set fits.** It supports all-at-once, canary, and linear traffic shifting, service revisions, lifecycle hooks, alarms, bake time, and rollback. The `CODE_DEPLOY` controller remains a distinct deployment path. Do not claim feature parity or migrate until the current service configuration and rollback behavior are verified.

18. **Container dependency `HEALTHY` condition requires a health check on the dependency container.** Without a configured health check, the dependent container never starts — ECS does not progress it to its next state. If `startTimeout` is set (max 120s), the dependency times out and the task fails; if not set, the dependent container blocks indefinitely. For init containers, use `SUCCESS` condition instead.

## Quick-Start: CDK Fargate Web App

Only for repos that already use CDK. The digest-pinned `ApplicationLoadBalancedFargateService` example lives in [ECS infrastructure patterns](references/ecs-infrastructure-patterns.md#quick-start-cdk-fargate-web-app). Terraform/OpenTofu repos keep their own modules; do not introduce CDK to prove a point.

## Quick-Start: ECS Exec

```bash
# 1. Enable on the service (existing tasks won't support it — force new deployment)
aws ecs update-service --cluster $CLUSTER --service $SERVICE \
  --enable-execute-command --force-new-deployment --output json

# 2. Connect (task role must have ssmmessages:* permissions)
aws ecs execute-command --cluster $CLUSTER --task $TASK_ID \
  --container $CONTAINER --interactive --command "/bin/sh"
```

If `TargetNotConnectedException`: wait 30–60s for SSM agent startup, check NAT/VPC endpoint for `ssmmessages`, verify task role (not execution role) has permissions.

## Common Workflows

The commands below show the AWS CLI form.

Read reference files only when the conversation requires deeper detail.

- Read [references/task-definition-authoring.md](references/task-definition-authoring.md) if the user needs to author a task definition, configure CPU/memory, set up networking modes, inject secrets, mount volumes, or configure container dependencies.
- Read [references/fargate-service-deployment.md](references/fargate-service-deployment.md) if the user needs to deploy a Fargate service behind an ALB, configure health checks, tune deregistration delay, set up path-based routing, or handle private subnet networking.
- Read [references/ecr-repository-management.md](references/ecr-repository-management.md) if the user needs ECR lifecycle policies, image scanning, cross-account image pulls, or is debugging image pull errors.
- Read [references/ecs-exec-debugging.md](references/ecs-exec-debugging.md) if the user needs to set up ECS Exec, debug TargetNotConnectedException, configure session logging, or validate ECS Exec prerequisites.
- Read [references/service-scaling-and-updates.md](references/service-scaling-and-updates.md) if the user needs auto-scaling, deployment strategies (rolling, blue/green), circuit breaker configuration, or Service Connect setup.
- Read [references/app-runner-guide.md](references/app-runner-guide.md) if the user has an existing App Runner service, needs to troubleshoot App Runner connectivity, or wants to migrate from App Runner to ECS Express Mode.
- Read [references/ecs-infrastructure-patterns.md](references/ecs-infrastructure-patterns.md) if the user needs CDK or CloudFormation examples for Fargate services, SQS workers, scheduled tasks, EFS volumes, ECS Exec, path-based routing, private subnets, or FireLens.
- Read [references/ecs-logging-and-firelens.md](references/ecs-logging-and-firelens.md) if the user needs awslogs configuration, FireLens/Fluent Bit setup, multiline log handling, or guaranteed log delivery.
- Read [references/ecs-troubleshooting-guide.md](references/ecs-troubleshooting-guide.md) if the user is debugging task placement failures, OOM kills (exit code 137), health check failures, image pull errors, or networking issues in private subnets.
- Read [references/fargate-spot.md](references/fargate-spot.md) if the user asks about Fargate Spot pricing, capacity provider strategies, or interruption handling.

## Related container options

ECS Express Mode is an option to evaluate for a new simple HTTP workload, not the default replacement for an existing platform. Check current networking, permissions and delivery fit before proposing it.

App Runner is closed to new customers after April 30, 2026. Existing customers can continue using it; AWS plans no new features and has announced no end-of-life date. Do not infer an urgent migration from that availability change. Use the [short compatibility guide](references/app-runner-guide.md) for an actual existing service.

## Troubleshooting

### CannotPullContainerError
**Cause**: Task cannot reach ECR. In private subnets, tasks need NAT gateway or VPC endpoints (`ecr.api`, `ecr.dkr`, `s3` gateway, `logs`).
**Fix**: Verify route table has a route to NAT gateway or create the required VPC endpoints. Verify the execution role has `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, `ecr:GetAuthorizationToken` (Resource: `"*"`). Check security group allows outbound HTTPS (443).

### Task failed ELB health checks
**Cause**: Health check path returns non-200, container not listening on the configured port, or health check grace period too short.
**Fix**: Verify the container responds on the health check path and port. Set `healthCheckGracePeriodSeconds` to at least 60s (longer for JVM apps). Ensure the security group allows traffic from the ALB security group on the container port.

### OutOfMemoryError / exit code 137
**Cause**: Container exceeded its memory hard limit (SIGKILL). On Fargate, task-level memory is the hard limit.
**Fix**: Increase task-level memory. For JVM apps, use `-XX:MaxRAMPercentage=75` instead of fixed `-Xmx` — this automatically adapts to the container's memory allocation. Check container-level `memory` (hard limit) vs `memoryReservation` (soft limit).

### AccessDeniedException on AWS API calls from container
**Cause**: Permissions are on the execution role instead of the task role, or the task role is missing.
**Fix**: Verify the task definition has `taskRoleArn` set (not just `executionRoleArn`). Add the required permissions to the task role.

### Service stuck deploying / tasks keep restarting
**Cause**: Deployment circuit breaker not enabled, or health check failing on new tasks.
**Fix**: Enable circuit breaker with rollback. Check service events: `aws ecs describe-services --cluster $CLUSTER --services $SERVICE --output json`. Check stopped task reasons: `aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK_ID --output json`.

### ECS Exec TargetNotConnectedException
**Cause**: SSM agent not running, missing task role permissions, or missing VPC endpoint.
**Fix**: Verify `enableExecuteCommand` is true on the service. Check the task role has SSM permissions. For private subnets, create the `ssmmessages` VPC endpoint. Verify with `aws ecs describe-tasks` that `ExecuteCommandAgent` status is `RUNNING`.

### Error retry classification

| Retry | Do NOT retry |
|---|---|
| ThrottlingException | InvalidParameterException |
| ServiceUnavailableException | ClientException |
| ServerException | AccessDeniedException |

## Security Considerations

- You MUST use IAM roles (execution role + task role) — never embed credentials in container images or environment variables
- You MUST use Secrets Manager or SSM Parameter Store for sensitive configuration, injected via the `secrets` field in the task definition
- You SHOULD enable ECR image scanning on push for vulnerability detection
- You SHOULD use private subnets with NAT gateway or VPC endpoints for production workloads
- You MUST enable CloudTrail for ECS API audit logging
- You SHOULD configure CloudWatch Container Insights for monitoring
- You SHOULD use `readonlyRootFilesystem: true` in container definitions where possible (note: incompatible with ECS Exec)
- You MUST scope task role permissions to specific resources — avoid `*` wildcards and `*FullAccess` policies
- You MUST confirm with the user before executing destructive operations: `--force-new-deployment` (replaces all running tasks), `delete-service`, `deregister-task-definition`. ECS does not support `--dry-run` — use the plan-validate-execute pattern: explain what will happen, get confirmation, then execute
- You SHOULD use ACM certificates with HTTPS listeners on ALBs fronting ECS services — per [ECS network security best practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-network.html): "provision certificates for the load balancer using AWS Certificate Manager (ACM)"
- You SHOULD avoid logging sensitive data (secrets, PII, tokens) in container stdout/stderr — these flow to CloudWatch Logs via the awslogs driver. If sensitive data may appear in logs, enable CloudWatch Logs encryption with a KMS key
- You SHOULD attach an AWS WAF WebACL to internet-facing ALBs for defense in depth against common web exploits
- You SHOULD include `aws:SourceArn` and `aws:SourceAccount` condition keys in ECR repository policies for cross-account access to prevent confused deputy attacks

## Additional Resources

- [Amazon ECS Developer Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)
- [Amazon ECS API Reference](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/Welcome.html)
- [Amazon ECS Best Practices Guide](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/intro.html)
- [Amazon ECR User Guide](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)
- [AWS Fargate Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [ECS Express Mode Getting Started](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html)
- [ECS Security Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-network.html)
- [App Runner Developer Guide](https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html) (existing customers)
- [App Runner Availability Change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)
