# Delivery verification, ownership, and rollback

Use this after selecting a central workflow. The [shared CLI operating guide](../../references/cli-operating.md) owns the common preflight, evidence directory, confirmation, wait, and mutation rules.

## Evidence before and after

Capture only what proves the change. Do not collect broad account dumps.

| Before | After |
|---|---|
| Source commit and build run | Same source commit linked to the immutable digest |
| Caller, account, and Region | Caller and target still match |
| Exact service, fleet tags and count, bucket prefix, or infrastructure project | Same bounded target set |
| Current active revision and health | Requested revision and health |
| Proposed write or dry-run output | Waiter or bounded poll result |
| Exact rollback revision or artifact | Application revision or behavior check |

Redact account IDs, role ARNs, hostnames, bucket names, URLs, and sensitive output before sharing evidence. Keep raw evidence only in the approved restricted location.

## Identity boundary

### GitHub Actions

Use OIDC and one least-privilege role per delivery purpose. Keep `id-token: write` on the one job that assumes the role. Restrict the role trust policy to the approved organization, repository, ref, and environment where the release model supports it.

Do not pass access keys through GitHub secrets. Do not let a build role deploy, or a deploy role change unrelated infrastructure.

Inspect how each workflow resolves its deployment role. A workflow may construct an ARN from separate inputs or require an exact role ARN. Input names and trust boundaries are not interchangeable.

### AWS-managed host

Use the attached machine role or its configured profile. If injected credentials are absent on an AppStream or EC2 host, that is not a reason to add static keys. Verify the machine caller and Region through the shared CLI guide before the first write.

## ECR build proof

Use the approved image-build workflow against an existing immutable repository and a unique source-derived tag. Retain the source commit, image tag, authoritative digest and digest-pinned deployment reference. Map these to the workflow's actual output names.

The digest is the release identity. The deployment reference must include it. Never promote a mutable tag by itself.

If the central workflow is not used, follow the [ECR section of the shared CLI guide](../../references/cli-operating.md#ecr). A successful Docker push is not enough; read the digest back from ECR.

## ECS external deployment ownership

Choose one owner for the active task definition:

| State | Owner |
|---|---|
| Cluster, service shell, load balancer, network, IAM, autoscaling, log groups | Infrastructure code |
| Container image build and immutable digest | Build workflow |
| Rendered task definition, registration, `UpdateService`, rollout | Delivery workflow |
| Runtime digest and application behavior proof | Delivery workflow |

When this split applies, infrastructure code must ignore the externally managed task-definition value after bootstrap. Review the full plan: an infrastructure apply that resets the task definition is an ownership defect, not harmless drift.

Do not infer app deployment from an infrastructure plan or apply. The minimum proof is:

```mermaid
flowchart LR
    A[Source SHA] --> B[ECR digest]
    B --> C[Rendered image_ref]
    C --> D[ECS primary task definition]
    D --> E[Every running container imageDigest]
    E --> F[Application revision or behavior]
```

## ECS runtime proof

First let the approved ECS deployment workflow complete its rollout and health checks. Then compare every running target container with the build's ECR digest.

The command options below use the AWS CLI command reference. `describe-tasks` exposes `containers[].imageDigest` as the container image manifest digest. This operator form uses `PROFILE`, `REGION`, and `EVIDENCE_DIR` from the shared CLI guide. In an OIDC job, use the configured environment credentials and omit each `AWS_PROFILE` assignment.

```bash
set -euo pipefail

EXPECTED_DIGEST=replace-with-ecr-image-digest
CLUSTER=replace-with-cluster
SERVICE=replace-with-service
CONTAINER=replace-with-container

AWS_PROFILE="$PROFILE" aws ecs describe-services \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --output json \
  --no-cli-pager \
  > "$EVIDENCE_DIR/ecs-service-after.json"

PRIMARY_TASK_DEFINITION=$(
  jq -er '
    [.services[0].deployments[] | select(.status == "PRIMARY" and .rolloutState == "COMPLETED")]
    | select(length == 1)
    | .[0].taskDefinition
  ' "$EVIDENCE_DIR/ecs-service-after.json"
)

AWS_PROFILE="$PROFILE" aws ecs list-tasks \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --service-name "$SERVICE" \
  --desired-status RUNNING \
  --query 'taskArns' \
  --output text \
  --no-cli-pager \
| tr '\t' '\n' \
| sed '/^$/d; /^None$/d' \
> "$EVIDENCE_DIR/ecs-running-task-arns.txt"

test -s "$EVIDENCE_DIR/ecs-running-task-arns.txt"
: > "$EVIDENCE_DIR/ecs-running-tasks.jsonl"

while IFS= read -r task_arn; do
  AWS_PROFILE="$PROFILE" aws ecs describe-tasks \
    --region "$REGION" \
    --cluster "$CLUSTER" \
    --tasks "$task_arn" \
    --output json \
    --no-cli-pager \
  | jq -ce 'select(.failures == [] and (.tasks | length) == 1) | .tasks[0]' \
  >> "$EVIDENCE_DIR/ecs-running-tasks.jsonl"
done < "$EVIDENCE_DIR/ecs-running-task-arns.txt"

test "$(wc -l < "$EVIDENCE_DIR/ecs-running-tasks.jsonl" | tr -d ' ')" \
  -eq "$(wc -l < "$EVIDENCE_DIR/ecs-running-task-arns.txt" | tr -d ' ')"

jq -s -e \
  --arg task_definition "$PRIMARY_TASK_DEFINITION" \
  --arg container "$CONTAINER" \
  --arg digest "$EXPECTED_DIGEST" '
    length > 0 and all(.[];
      .lastStatus == "RUNNING"
      and .taskDefinitionArn == $task_definition
      and ([.containers[]
        | select(
            .name == $container
            and .lastStatus == "RUNNING"
            and .imageDigest == $digest
          )] | length) == 1
    )
  ' "$EVIDENCE_DIR/ecs-running-tasks.jsonl"
```

The final `jq` command is the revision gate. Fixing a shell typo in this evidence command does not authorize another deployment.

After the digest gate, run the service's existing health and behavior check. Prefer an endpoint or diagnostic field that returns the source revision. If the app does not expose one, report digest proof and behavior proof separately. Do not invent revision proof.

Official command references:

- [AWS CLI `ecs list-tasks`](https://docs.aws.amazon.com/cli/latest/reference/ecs/list-tasks.html)
- [AWS CLI `ecs describe-tasks`](https://docs.aws.amazon.com/cli/latest/reference/ecs/describe-tasks.html)

## SSM fleet delivery

Prefer the approved fleet workflow when it supports the deployment kind. Verify that it provides these controls before use:

- fixed approved document names and an explicit document version;
- exact tag target and expected target count;
- running, managed, online Windows pre-checks;
- immutable S3 staging and artifact SHA-256;
- bounded `MAX_CONCURRENCY`, `MAX_ERRORS`, command timeout, and poll interval;
- one command ID and a hard polling deadline;
- failure unless every expected invocation reaches `Success`;
- `deploy` and narrow `rollback` operations.

Start with the workflow's verified AWS preflight mode, without uploading or sending a command. Review the target count, document version, artifact identity, concurrency, failure threshold, timeout and rollback before selecting apply mode. Do not assume conventional input names have conventional effects.

Do not replace the fixed document with an inline production PowerShell payload. For diagnostics or an unsupported deployment kind, use the [Systems Manager reference](../../compute/references/systems-manager.md). Keep payloads in files, validate external values, and keep the same target, concurrency, error, timeout, and polling controls.

SSM `Success` means the command finished. It does not prove the intended service version is active. Add the narrow target check:

- IIS: deployed file digest, app-pool state, then endpoint revision or behavior.
- Windows service: installed file digest, service state, then service behavior.
- Windows file: destination file digest and the consuming application's check.

If only part of the fleet succeeds, stop. Keep the command ID and per-target results. Do not automatically rerun against the whole fleet or claim rollback completed everywhere.

## S3 delivery

### Immutable artifact

Use the approved artifact workflow for one release file. Run its verified preflight mode first and require approval for apply. Keep the exact object key and SHA-256 as deployment and rollback evidence.

Require expected ownership, approved encryption, versioning, key absence before upload, object metadata and downloaded SHA-256 checks. Use a unique immutable key, not `--delete`.

### Static content

Direction and scope decide the risk. Use a dedicated prefix. A root-bucket destination is not bounded enough for delete mode.

If the existing static-site workflow cannot show an AWS dry run or enforce production approval, use only its verified build-only path. Split controlled delivery into two dependent jobs.

The unprotected preview job must:

1. Download the exact build artifact and record its SHA-256.
2. Assume a scoped preview identity that can read destination state but cannot write it.
3. Run the shared CLI guide's [S3 sync dry run](../../references/cli-operating.md#s3-sync) against the exact source and dedicated destination prefix. Omit delete unless stale objects must be removed.
4. Publish the artifact digest, source, destination, prefix, delete mode, and proposed uploads, overwrites, and deletions for the approver.

The dependent apply job must declare the protected production environment. GitHub requests approval before this job starts, so the approver can review the completed preview. After approval, the job must:

1. Download the same build artifact and stop if its SHA-256 differs.
2. Use the same source, destination, prefix, and delete mode from fixed workflow inputs.
3. Assume the scoped deployment role and verify identity.
4. Repeat the dry run and stop if its normalized result differs from the reviewed preview. A destination change requires a new review.
5. Run the bounded sync without dry-run mode.
6. Compare representative critical files and run the site's behavior check.

Do not rebuild between preview and execution. Do not let the apply job accept mutable destination or delete inputs that were absent from the preview. If delete is enabled, the reviewed preview and production approval must both include it. For nonproduction, keep deletion disabled unless explicitly reviewed, and use the repository's normal write gate.

## Targeted applies when unrelated drift exists

A delivery repair must not carry unrelated infrastructure drift.

1. Read the full plan and name every unrelated change.
2. Stop the broad apply.
3. Use the repository's supported Atlantis project or exact resource target only when the address is already verified.
4. Save the targeted plan and require that it contains only the intended change and no surprise destroy action.
5. Gate production, apply once, and verify the AWS resource plus the application revision separately.
6. Remove stale plans or locks through the repository's normal control-plane process.
7. Run a full read-only plan afterward and leave unrelated drift visible for separate work.

Targeting is an incident or repair control, not the normal deployment model. Do not guess a resource address. Do not use a targeted apply to hide dependencies or call a partially reconciled stack healthy.

## Narrow rollback

Rollback the release selector, not the whole platform.

| Target | Narrow rollback |
|---|---|
| ECS | Re-render with the previous verified digest reference, deploy one new task-definition revision, then repeat runtime digest and app checks |
| SSM fleet | Use the verified rollback contract with the exact prior key under the approved prefix and its recorded SHA-256 |
| Immutable S3 artifact | Keep the old object unchanged; move only the consumer's release pointer through its approved process |
| Static S3 prefix | Restore the prior captured artifact to the same bounded prefix; preview deletions before execution |
| Targeted infrastructure repair | Apply only the recorded inverse of the object or value changed by the repair |

Never retag an old image as "latest." Never select a rollback artifact by timestamp or name alone. Never roll back healthy infrastructure because the application check failed unless the evidence shows infrastructure caused the failure.

After rollback, prove the rollback revision and behavior with the same checks used for deployment. "Rollback command succeeded" is not the final state.

## Validate the local contract

These controls preserve lessons from actual delivery failures without treating one organization's implementation as universal. Re-read the owning workflows, infrastructure and SSM documents at the selected ref and account before a change. Keep task-definition ownership, target bounds, preflight effects and runtime proof explicit. If the implementation does not enforce a required control, report the gap rather than assuming its name guarantees it.
