# Terraform and OpenTofu

Read this reference when writing, changing, or reviewing Terraform/OpenTofu code or its tooling and CI. The general standards remain in [Code Rules](../SKILL.md).

## Contents

- [Use the SRE module library first, community modules second](#use-the-sre-module-library-first-community-modules-second)
- [Use stable OpenTofu deliberately](#use-stable-opentofu-deliberately)
- [Make version constraints tell the truth](#make-version-constraints-tell-the-truth)
- [Enforce checks locally and in CI](#enforce-checks-locally-and-in-ci)
- [Match the sibling root before review](#match-the-sibling-root-before-review)

Company-specific module, runner, and reusable-workflow choices apply only to work repositories. Outside them, keep the same safety rules but use the repo's approved equivalents.

### Use the SRE module library first, community modules second

- **First, use the company's SRE module library when it has a module for the job.** Find the library in an existing SRE-reviewed root: it is the `git::` module source next to the root's defaults module. SRE reviews new roots against that library, and its modules already carry the company naming, tagging, and guardrails.
- **Pin a library module to an exact release tag (`?ref=<tag>`), and look the tag up.** Git sources have no version ranges, so the `~>` rule below applies to registry modules only. Get the newest tag with `git ls-remote --tags <library-url> '<module-path>/*'`; never copy a tag from memory or from another root.
- **Second, use a module from `terraform-aws-modules` when the library has nothing that fits.** Check the Terraform Registry before writing raw `aws_*` resources. These are verified, community-maintained modules, not official AWS modules.
- **Do not force a module that needs forks or workarounds.** If no module fits cleanly, write the minimum raw resources and say why each module was rejected.
- **In a root that CI applies, pin a registry module to an exact version.** OpenTofu's lock file locks providers, not modules, so a `~>` range lets a new module release change the next plan with no code change. Look up the newest release on the Registry and pin it: `version = "8.13.0"`. Bump it on purpose, in its own commit, and read the plan.
- **In a reusable module, use a `~>` range on registry modules.** Consumers resolve it, so set the honest minimum and block the next major: `version = "~> 6.3"` (`>= 6.3.0, < 7.0.0`).
- **A community module in an SRE root is a deviation: record its exit.** Put it in the root README's deviation table with the reason the library module does not fit and the library ask (ticket) that would remove it.

**Why:** the SRE library is what reviewers check against, so using it first avoids rework at review. Community modules beat raw resources because they keep common AWS patterns consistent and reduce code we own. The fit check prevents a large abstraction from making a simple resource harder to understand.

### Use stable OpenTofu deliberately

- **Use the latest stable OpenTofu for new repos and planned upgrades.** Pin the exact CLI version in local tooling and CI.
- **Do not upgrade OpenTofu as unrelated cleanup.** In an existing repo, keep its current pin unless the task needs an upgrade. When upgrading, update local tooling, `required_version`, CI, and docs together.
- **For OpenTofu 1.11 or newer, use `lifecycle.enabled` for a zero-or-one resource or module.** Use `count` only for multiple identical instances. If the repo must also run with Terraform, do not use OpenTofu-only syntax. This holds even when a platform team's guide says `count`: put it in the README deviation table, ask the platform team to bless it on their standard page (it pins the root to OpenTofu >= 1.11), and set `required_version` to at least `~> 1.11`.

  ```hcl
  resource "aws_s3_bucket" "logs" {
    bucket = var.bucket_name

    lifecycle {
      enabled = var.create_bucket
    }
  }
  ```

- **Never put `depends_on` on a module call to order it after a resource.** It defers every data source inside the module while the dependency has pending changes; a deferred lookup (for example `aws_subnet` → `vpc_id`) turns a ForceNew argument unknown and replaces live resources. Order through a value the module consumes instead, and keep that value stable: `join("", [real_value, substr(dep.id, 0, 0)])`. Check the module for its own internal `depends_on` too: any changing input that feeds it has the same effect.
- **A just-created IAM service-linked role or role is not usable at once.** Put a `time_sleep` (hashicorp/time) between the role and its first consumer; `depends_on` orders the API calls but does not wait for IAM propagation.
- **A module output that echoes an input carries no dependency.** If a resource takes a name from such an output (`repository_name = var.name`), add the dependency explicitly, or it can run before the module creates the object.
- **Prove a root with a real sandbox apply, then a second plan.** A plan cannot catch ordering or propagation failures; the follow-up plan must show no replacement of what the apply created.
- **Use `moved` blocks when resource addresses change.** Do not make OpenTofu destroy and recreate an object just because code moved.
- **Use `terraform_data` instead of `null_resource`** when no real managed resource fits.

**Why:** exact tool pins make runs repeatable. Modern language features remove indexing tricks and state churn without turning every Terraform change into a toolchain upgrade.

### Make version constraints tell the truth

- **Every module declares its own `required_providers`.** A reusable module declares provider sources and compatibility, but it does not contain `provider` configuration blocks. The calling root module supplies provider configurations.
- **Always use `~>` (pessimistic) constraints, for `required_version`, every provider, and every registry module.** Never use a bare `>=`. A bare minimum silently admits the next major release (`>= 6.0.0` accepts `7.0.0`) with no warning. `~>` caps the range before the next major, so a major upgrade becomes a deliberate, reviewed, versioned change. Write the minimum honestly, never lower it just to end in `.0`.
- **A reusable module sets a real minimum and lets later minors in, but still blocks the next major.** `~> 1.6` is `>= 1.6.0, < 2.0.0`; `~> 6.0` is `>= 6.0.0, < 7.0.0`. The minimum must be the oldest version that supports every feature the module uses.

  ```hcl
  terraform {
    required_version = "~> 1.6"

    required_providers {
      aws = {
        source  = "hashicorp/aws"
        version = "~> 6.0"
      }
    }
  }
  ```

- **Root modules pin OpenTofu to a supported minor and cap providers before their next major.** Same rule: `~>` everywhere, never a bare `>=`.

  ```hcl
  terraform {
    required_version = "~> 1.12.0"

    required_providers {
      aws = {
        source  = "hashicorp/aws"
        version = "~> 6.8"
      }
    }
  }
  ```

- **When another team owns the CI OpenTofu version, use a minor-level range.** A shared reusable workflow picks the CLI version, so `~> 1.12.0` breaks your root the day that team moves CI to 1.13. Use `~> 1.<minimum>` with the honest minimum instead, for example `~> 1.11` for a root that uses `lifecycle.enabled`.
- **Do not lower a real minimum just to end the constraint in `.0`.** `~> 6.8` means `>= 6.8.0, < 7.0.0` and does allow 6.9. Use `~> 6.0` only when the code truly supports every provider release from 6.0 onward. `~> 6.8.0` is different: it allows 6.8 patch releases but blocks 6.9.
- **Handle `.terraform.lock.hcl` by working-directory role.** Commit it for every independently applied root configuration. Ignore a lock file created only to validate a reusable module because consumers do not use it. Never edit a lock file by hand. Upgrade providers deliberately with `tofu init -upgrade`, review the diff, and run a plan.

**Why:** honest lower bounds prevent consumers from selecting a provider that is too old. Upper bounds block unreviewed breaking changes, while the lock file keeps normal runs repeatable.

### Enforce checks locally and in CI

- **Whenever Terraform or OpenTofu is touched, ensure `.pre-commit-config.yaml` and CI enforcement exist.** In GitHub repos, use `.github/workflows/pre-commit.yml`; otherwise use the repo's approved equivalent. Add whichever part is missing. Merge with existing hooks and CI; never replace repo-specific checks.
- **Keep `tofu_validate` only when CI has git access to all module sources.** The hook runs `tofu init` to download providers and modules. If the repo references private GitHub modules (e.g., `github.com/example-org/tf-aws-private-mod`), the CI runner must have credentials to clone them. Without git auth, `tofu init` fails and the hook breaks. Drop `tofu_validate` from repos that reference private modules. The plan that the CI pipeline posts on the pull request is the real validation gate. For repos that only use public modules or local paths, keep it.
- **Use the right terraform-docs scope.** The CLI arguments below work without a settings file. If the repo stores settings, name the file `.terraform-docs.yml`; `.terraform-docs.yaml` is not auto-discovered. The base config handles one module at the repo root.

  ```yaml
  repos:
    - repo: https://github.com/terraform-docs/terraform-docs
      rev: v0.24.0
      hooks:
        - id: terraform-docs-go
          args: ["markdown", "table", "--output-file", "README.md", "."]

    - repo: https://github.com/tofuutils/pre-commit-opentofu
      rev: v2.4.2
      hooks:
        - id: tofu_fmt
        - id: tofu_validate

    - repo: https://github.com/pre-commit/pre-commit-hooks
      rev: v6.0.0
      hooks:
        - id: trailing-whitespace
          exclude: '\.lock\.hcl$'
        - id: end-of-file-fixer
          exclude: '\.lock\.hcl$'
        - id: check-merge-conflict
        - id: no-commit-to-branch
  ```

  For child modules under `modules/`, replace the terraform-docs `args` line with:

  ```yaml
  args: ["markdown", "table", "--output-file", "README.md", "--recursive", "--recursive-path", "modules", "."]
  ```

  Recursive mode reads a child module's own `.terraform-docs.yml` when present. If modules live elsewhere, add an explicit terraform-docs hook entry for each module path instead of assuming auto-discovery.

- **Run pre-commit on every pull request.** If the company publishes a reusable pre-commit workflow, call it. If not, add this plain workflow, and set `tofu_version` to the version the CI pipeline runs:

  ```yaml
  name: Pre-commit

  on:
    pull_request:
    workflow_dispatch:

  permissions:
    contents: read

  jobs:
    pre-commit:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v7
        - uses: actions/setup-python@v7
          with:
            python-version: "3.13"
        - uses: opentofu/setup-opentofu@v2
          with:
            tofu_version: "1.12.0"
            tofu_wrapper: false
        - uses: pre-commit/action@v3.0.1
  ```

  The OpenTofu value is an example. Change `runs-on` when the repo must use the company's self-hosted runners. Use approved commit SHAs instead of tags when a repo requires immutable CI dependencies.

- **Verify the setup before finishing.** Run:

  ```bash
  pre-commit validate-config
  pre-commit run --all-files
  ```

  When adding or deliberately upgrading hooks, run `pre-commit autoupdate` before these checks. If a hook changes files, review them and rerun `pre-commit run --all-files` until it passes.

**Why:** local hooks catch formatting, validation, and generated-doc issues early. CI makes the same checks mandatory for every pull request.

### Match the sibling root before review

SRE reviewers check a new root against the closest existing root of the same team (for Builder Tools: builder-hub `.sre/tf/*` on `develop`). Diff your root against it before you open the PR. Each rule below is a finding from a real review (bt-cortex #22, 2026-11-11).

- **Copy conventions from the sibling, not from memory.** Tag keys and their casing (`Application`, `Ticket`), log retention (30 days), and caller inputs (`require-apply-reviewers`) come from the sibling's current files. Policy changes land there first, so read `develop`, not an old copy.
- **Compose resource names only through the defaults module, including in CI.** If a workflow needs a resource name, publish it in the root's SSM contract and read it with `aws ssm get-parameter`. A `case "$ENV"` that rebuilds `DV-USE2-...` is name composition outside `module.q`.
- **Every override of a module default carries a reason in a comment.** Never turn off a module's logging (`log_publishing_options = []`) to save effort. If the default fails (Auto-Tune on t3), say that in the comment and when to remove the override.
- **A generated secret needs `keepers` and a rotation note.** `random_password` with `keepers` tied to the resource it protects, so a plan never rotates it by accident; the README says how to rotate.
- **Document every out-of-band secret:** owner, scope, expiry, and the ticket that replaces it (for example a PAT replaced by a GitHub App).
- **Guard list indexing on contract values.** `slice(list, 0, 2)` on an SSM list fails with an index error on a short list. Clamp it with `min()` so the module's own validation reports the real problem, or add a `precondition` with a clear message.
- **When the code works around the platform, write the runtime decision down.** Wiping `/tmp` every run or living under a 900 s cap is a sign; add an ADR line in the README with the intent and the trigger to move.
- **Take external identifiers from the live system, not from old code.** Org names, account IDs and repository lists come from the running environment (or the API) when one exists. `ChamberlainGroupFirmware` and `ChamberlainGroup-myQ-Firmware` are different orgs.
- **Keep the PR body current.** Remove "before merge" items and CI notes as soon as they are done; reviewers read stale notes as open work.
