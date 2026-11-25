# OpenTofu on AWS

Plan on the PR, apply the saved plan after merge, fast and without hiding drift. Checked 2026-11-25 (OpenTofu 1.11, setup-opentofu v2.0.2). The code rules for OpenTofu, such as module pins and lock files, are in `coding`'s [Terraform and OpenTofu standards](../../coding/references/terraform-opentofu.md). In a work repo, the platform team's reusable workflow owns plan and apply: improve it there.

## The flow

```mermaid
flowchart LR
  PR[PR: plan, post summary] --> M[Merge queue: full checks]
  M --> P[Push to main: new plan, saved]
  P --> A[Apply that exact plan file]
  A --> S[Second plan: must be empty]
```

| Step | Command | Notes |
| --- | --- | --- |
| Setup | `opentofu/setup-opentofu@v2.0.2` with `tofu_version` pinned and `tofu_wrapper: false` | The wrapper changes exit codes; turn it off so `-detailed-exitcode` works ([setup-opentofu](https://github.com/opentofu/setup-opentofu/blob/main/README.md)) |
| PR | `tofu init -input=false -lockfile=readonly` then `tofu plan -input=false -no-color -out=tfplan` | The PR plan is advice: main can move before merge |
| After merge | a new `tofu plan -out=tfplan` on the merged commit, then `tofu apply -input=false tfplan` | Apply the file you reviewed, never a fresh `apply` that re-plans ([apply](https://developer.hashicorp.com/terraform/cli/commands/apply)) |
| Proof | `tofu plan -detailed-exitcode` after the apply | Exit 0 means no changes. Some blocks show a diff on every plan until fixed; `coding`'s Terraform reference lists the known ones |

## Keep it honest

- **A saved plan goes stale.** If another apply changed the state, applying the old plan fails: plan again, never force it. Drift made outside OpenTofu does not always trip that check, so the apply job runs its own fresh plan ([CLI runs](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/run/cli)).
- **A plan file can hold secrets in clear text.** Keep it as a short-lived, private artifact (`retention-days: 1`), and post only a redacted summary to the PR. `tf-summarize` makes a short summary; it is for reading, not for applying ([tf-summarize](https://github.com/dineshba/tf-summarize/blob/main/README.md)).
- **Never `-refresh=false` in a production plan or a drift check.** It is faster because it does not look at real resources, so it misses drift.
- **`-target` and `-exclude` are for recovery, not for speed.** Both hide changes ([plan](https://opentofu.org/docs/v1.11/cli/commands/plan/)).
- **Never `-lock=false` in CI.**
- **Ephemeral values (OpenTofu 1.11) are not stored in the plan file.** Pass them again to `tofu apply tfplan`.
- **Fork PRs get no AWS role.** Run them with `pull_request`, never `pull_request_target` with a checkout of the fork's code ([pull_request_target](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)).

## Make it fast

- **Split big roots.** A plan's time grows with the number of resources it refreshes. Separate network, data, and app into their own roots and states, so a change plans only what it touches ([best practices](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/best-practices)). This is the real speed-up; `-target` is not.
- **Cache providers, not `.terraform`:**

  ```yaml
  - run: mkdir -p ~/.terraform.d/plugin-cache
  - uses: actions/cache@v4
    with:
      path: ~/.terraform.d/plugin-cache
      key: providers-${{ runner.os }}-${{ runner.arch }}-tofu-1.11-${{ hashFiles('**/.terraform.lock.hcl') }}
  - run: tofu init -input=false -lockfile=readonly
    env:
      TF_PLUGIN_CACHE_DIR: ~/.terraform.d/plugin-cache
  ```

  `.terraform` holds backend settings and can hold credentials; never cache it, the state, or a plan ([config file](https://opentofu.org/docs/v1.11/cli/config/config-file/)).
- **Plan the roots a PR touches in parallel**, one job per root, with a matrix built from the changed paths. List the inputs that plan every root: shared modules, provider versions, CI config.
- **`-parallelism`** defaults to 10. Raise it only if the audit shows plan time is resource reads and AWS does not throttle.

## State and locks

```hcl
terraform {
  backend "s3" {
    bucket       = "example-state"
    key          = "prod/network.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}
```

The S3 lock file (`<key>.tflock`) needs no DynamoDB table. OpenTofu 1.11 supports both and does not deprecate DynamoDB; set both while you migrate ([OpenTofu S3 backend](https://opentofu.org/docs/v1.11/language/settings/backends/s3/)). Turn on bucket versioning. One state key per root and environment, and one deploy job at a time per state:

```yaml
concurrency: { group: infra-prod-network, cancel-in-progress: false }
```

## Drift

```yaml
on:
  schedule: [{ cron: "17 3 * * *" }]
  workflow_dispatch: {}
# tofu plan -detailed-exitcode -input=false -no-color
# exit 0: no drift; 2: drift, alert; 1: error, fail
```

Alert on drift; never apply it automatically. Scheduled runs use the default branch and can start late.

## Orchestrators

Atlantis (v0.50.0), Digger (now OpenTaco), and Terrateam (now Stategraph) run plan on PR and apply on merge with locks and drift checks. Check each one's current name and setup before you choose it; all three changed in 2026 ([Atlantis](https://github.com/runatlantis/atlantis/releases/tag/v0.50.0), [Digger](https://github.com/diggerhq/digger/blob/develop/README.md), [Terrateam](https://github.com/terrateamio/terrateam/blob/main/README.md)). In a work repo, the platform workflow is the orchestrator.
