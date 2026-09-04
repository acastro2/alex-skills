# Credentials and Access Checks

Use this for Secrets Manager metadata, a controlled KMS encrypt/decrypt test, or an IAM role-policy inventory. This is operational diagnosis, not full policy authoring.

Complete the shared [CLI preflight](../../references/cli-operating.md) first. For IAM, record the workload Region even though IAM resources are global. The account and caller still decide the result.

## Read-only Secrets Manager checks

Read metadata first:

```bash
AWS_PROFILE="$PROFILE" aws secretsmanager describe-secret \
  --region "$REGION" \
  --secret-id "$SECRET_ID" \
  --query '{ARN:ARN,Name:Name,LastChangedDate:LastChangedDate}' \
  --output json \
  --no-cli-pager
```

Do not query `SecretString` or `SecretBinary` during diagnosis.

If the exact question is whether the caller can use `GetSecretValue`, this check keeps the value out of terminal output:

```bash
AWS_PROFILE="$PROFILE" aws secretsmanager get-secret-value \
  --region "$REGION" \
  --secret-id "$SECRET_ID" \
  --query ARN \
  --output text \
  --no-cli-pager
```

This is not metadata-only at the API boundary. The CLI process receives the secret response and projects the ARN afterward. Use it only when the permission test is required. Never add shell tracing, pipe the full response, or paste debug output.

An empty or `None` result from a name filter is not a target. Stop and resolve the exact secret ID before any access test.

## Controlled KMS smoke test

Use non-secret text. This proves the selected caller can encrypt and decrypt with the exact key in the exact Region. It does not prove another workload role can use the key.

```bash
(
set -euo pipefail
WORK_DIR=$(mktemp -d)
chmod 700 "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

printf '%s' 'kms-smoke-test' > "$WORK_DIR/plaintext"

AWS_PROFILE="$PROFILE" aws kms encrypt \
  --region "$REGION" \
  --key-id "$KEY_ID" \
  --plaintext "fileb://$WORK_DIR/plaintext" \
  --query CiphertextBlob \
  --output text \
  --no-cli-pager \
| base64 -d > "$WORK_DIR/ciphertext"

AWS_PROFILE="$PROFILE" aws kms decrypt \
  --region "$REGION" \
  --ciphertext-blob "fileb://$WORK_DIR/ciphertext" \
  --query Plaintext \
  --output text \
  --no-cli-pager \
| base64 -d > "$WORK_DIR/decrypted"

cmp -s "$WORK_DIR/plaintext" "$WORK_DIR/decrypted"
)
```

Use `fileb://` for both binary inputs. Do not put real credentials, keys, customer data, or production payloads in the smoke text. Do not print the decrypted file. The trap removes local files when the shell exits normally or on a handled failure.

## Read-only IAM role inventory

Policy names are clues, not proof of effective access. Inventory both managed-policy attachments and inline policy names:

```bash
AWS_PROFILE="$PROFILE" aws iam list-attached-role-policies \
  --role-name "$ROLE_NAME" \
  --query 'AttachedPolicies[].{Name:PolicyName,Arn:PolicyArn}' \
  --output json \
  --no-cli-pager

AWS_PROFILE="$PROFILE" aws iam list-role-policies \
  --role-name "$ROLE_NAME" \
  --query 'PolicyNames' \
  --output json \
  --no-cli-pager
```

Store full trust and policy documents in restricted evidence, not chat. To explain an allow or deny, account for all applicable layers:

- Role trust policy and the actual session principal.
- Identity policies, inline policies, and session policies.
- Permission boundaries.
- Organization SCPs or resource control policies.
- Resource policies, including the secret policy or KMS key policy.
- KMS grants and encryption context requirements.
- VPC endpoint policy or service condition keys when they apply.

`AccessDeniedException` after a successful STS call is authorization failure. Repeating SSO login will not fix it. Capture the caller, action, resource class, account, Region, and error request ID without pasting sensitive policy content.

## Approved credential or access mutation

Do not attach or detach a role policy, edit a trust policy, change a KMS key policy, schedule key deletion, or rotate a secret until you find the source owner. IAM Identity Center, workload IAM, secret rotation, and workload KMS keys are often managed through Terraform or another deployment controller.

For any approved change:

1. Capture metadata and the complete relevant attachment, version-stage, grant, or policy state.
2. Show the exact role, secret, or key target and one requested delta.
3. Explain dependent workloads and how they will receive the new access or credential.
4. Show rollback to the captured state before execution.
5. Get confirmation, apply through the owner, poll any rotation or deployment, and test with the consuming identity.
6. Revoke old access only after the new path is proven, unless the incident owner requires immediate revocation.

For a secret recovery, `AWSPREVIOUS` can expose the prior version during an approved rollback. Send it directly to the recovery process. Never print it or leave it in shell history, logs, transcripts, or a broad-permission file. A later rotation can move version stages again, so verify the stages before relying on them.

A successful administrator smoke test is not application proof. Repeat the least-sensitive check with the real workload identity or verify a workload operation that does not expose data.

## Failure modes to keep visible

- `--query ARN` protects terminal output, not the CLI process memory or debug logs.
- Secret access can fail at the secret policy, identity policy, endpoint policy, or KMS decrypt step.
- A managed policy with a promising name can still be narrowed by a boundary, SCP, session policy, resource policy, or condition.
- KMS `encrypt` success does not prove `decrypt`, cross-account use, or workload use.
- `file://` and `fileb://` are not interchangeable for KMS binary parameters.
- A key or policy changed outside its controller can drift back.
- Deleting or rotating before dependent workloads are mapped can extend an incident.

Current command references: [Secrets Manager `describe-secret`](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/describe-secret.html), [IAM `list-role-policies`](https://docs.aws.amazon.com/cli/latest/reference/iam/list-role-policies.html), and [KMS `encrypt`](https://docs.aws.amazon.com/cli/latest/reference/kms/encrypt.html).
