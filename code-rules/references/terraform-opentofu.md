# Terraform and OpenTofu

Read this reference when writing, changing, or reviewing Terraform/OpenTofu code or its tooling and CI. The general standards remain in [Code Rules](../SKILL.md).

## Contents

- [Use Attain's standard AWS modules first](#use-attains-standard-aws-modules-first)
- [Use stable OpenTofu deliberately](#use-stable-opentofu-deliberately)
- [Make version constraints tell the truth](#make-version-constraints-tell-the-truth)
- [Enforce checks locally and in CI](#enforce-checks-locally-and-in-ci)

Attain-specific module, runner, and reusable-workflow choices apply only to Attain repositories. Outside Attain, keep the same safety rules but use the repo's approved equivalents.

### Use Attain's standard AWS modules first

- **Use a module from `terraform-aws-modules` when it cleanly covers the AWS requirement.** Check the Terraform Registry before writing raw `aws_*` resources. These are verified, community-maintained modules and Attain's standard, not official AWS modules.
- **Do not force a module that needs forks or workarounds.** If no module fits cleanly, write the minimum raw resources and say why the module was rejected.
- **Pin registry modules to an exact version.** OpenTofu's dependency lock file does not lock modules. Check the Registry and use the latest stable compatible release when adding or upgrading a module. This example shows the required exact-pin shape:

  ```hcl
  module "vpc" {
    source  = "terraform-aws-modules/vpc/aws"
    version = "6.6.1"
  }
  ```

**Why:** standard modules keep common AWS patterns consistent and reduce code we own. The fit check prevents a large abstraction from making a simple resource harder to understand.

### Use stable OpenTofu deliberately

- **Use the latest stable OpenTofu for new repos and planned upgrades.** Pin the exact CLI version in local tooling and CI.
- **Do not upgrade OpenTofu as unrelated cleanup.** In an existing repo, keep its current pin unless the task needs an upgrade. When upgrading, update local tooling, `required_version`, CI, and docs together.
- **For OpenTofu 1.11 or newer, use `lifecycle.enabled` for a zero-or-one resource or module.** Use `count` only for multiple identical instances. If the repo must also run with Terraform, do not use OpenTofu-only syntax.

  ```hcl
  resource "aws_s3_bucket" "logs" {
    bucket = var.bucket_name

    lifecycle {
      enabled = var.create_bucket
    }
  }
  ```

- **Use `moved` blocks when resource addresses change.** Do not make OpenTofu destroy and recreate an object just because code moved.
- **Use `terraform_data` instead of `null_resource`** when no real managed resource fits.

**Why:** exact tool pins make runs repeatable. Modern language features remove indexing tricks and state churn without turning every Terraform change into a toolchain upgrade.

### Make version constraints tell the truth

- **Every module declares its own `required_providers`.** A reusable module declares provider sources and compatibility, but it does not contain `provider` configuration blocks. The calling root module supplies provider configurations.
- **Always use `~>` (pessimistic) constraints, for `required_version` and for every provider.** Never use a bare `>=`. A bare minimum silently admits the next major release (`>= 6.0.0` accepts `7.0.0`) with no warning. `~>` caps the range before the next major, so a major upgrade becomes a deliberate, reviewed, versioned change. Write the minimum honestly, never lower it just to end in `.0`.
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

- **Do not lower a real minimum just to end the constraint in `.0`.** `~> 6.8` means `>= 6.8.0, < 7.0.0` and does allow 6.9. Use `~> 6.0` only when the code truly supports every provider release from 6.0 onward. `~> 6.8.0` is different: it allows 6.8 patch releases but blocks 6.9.
- **Handle `.terraform.lock.hcl` by working-directory role.** Commit it for every independently applied root configuration. Ignore a lock file created only to validate a reusable module because consumers do not use it. Never edit a lock file by hand. Upgrade providers deliberately with `tofu init -upgrade`, review the diff, and run a plan.

**Why:** honest lower bounds prevent consumers from selecting a provider that is too old. Upper bounds block unreviewed breaking changes, while the lock file keeps normal runs repeatable.

### Enforce checks locally and in CI

- **Whenever Terraform or OpenTofu is touched, ensure `.pre-commit-config.yaml` and CI enforcement exist.** In GitHub repos, use `.github/workflows/pre-commit.yml`; otherwise use the repo's approved equivalent. Add whichever part is missing. Merge with existing hooks and CI; never replace repo-specific checks.
- **Keep `tofu_validate` only when CI has git access to all module sources.** The hook runs `tofu init` to download providers and modules. If the repo references private GitHub modules (e.g., `github.com/Engineering-Attain-Finance/tf-aws-golden-path-mod`), the CI runner must have credentials to clone them. Without git auth, `tofu init` fails and the hook breaks. Drop `tofu_validate` from repos that reference private modules. The Atlantis plan is the real validation gate. For repos that only use public modules or local paths, keep it.
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

- **Run pre-commit on every pull request.** In Attain repos, use the reusable workflow below and match `OPENTOFU_VERSION` to the repo's exact tool pin. Outside Attain, use the repo's approved equivalent.

  ```yaml
  name: Pre-commit

  on:
    pull_request:
    workflow_dispatch:

  permissions:
    contents: read

  jobs:
    pre-commit:
      uses: Engineering-Attain-Finance/reusable-workflows/.github/workflows/pre-commit.yml@master
      with:
        GITHUB_RUNNER: attain-eks
        OPENTOFU_VERSION: "1.12.5"
  ```

  The OpenTofu value is an example. Replace it with the repo's exact pin; for a new repo, verify and use the latest stable release. The `@master` reference intentionally follows centrally managed Attain workflow updates. Use an approved commit SHA instead when a repo requires immutable CI dependencies.

- **Verify the setup before finishing.** Run:

  ```bash
  pre-commit validate-config
  pre-commit run --all-files
  ```

  When adding or deliberately upgrading hooks, run `pre-commit autoupdate` before these checks. If a hook changes files, review them and rerun `pre-commit run --all-files` until it passes.

**Why:** local hooks catch formatting, validation, and generated-doc issues early. CI makes the same checks mandatory for every pull request.
