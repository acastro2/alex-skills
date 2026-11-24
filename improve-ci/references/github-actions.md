# GitHub Actions

Runners, caches, merge queue, hooks, and budgets. Checked 2026-11-24. Prices and speeds marked "vendor" come from the vendor's own docs: measure them on your repo before you quote them as fact.

## Runners: waiting under 5 seconds

**Default: Blacksmith.** Switch a job by changing one label, after the GitHub app is installed (needs Alex: an account).

```yaml
runs-on: blacksmith-2vcpu-ubuntu-2604
```

| Runner | Linux 2-vCPU price | Warm start and cache | Source |
| --- | --- | --- | --- |
| GitHub-hosted (baseline) | USD 0.006/min, each job rounded up to a whole minute | none | [GitHub pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing) |
| Blacksmith (default) | USD 0.004/min, 3,000 free min/month | boots in under 3 s (vendor); sticky disk restores a 6 GB cache in about 3 s (vendor), USD 0.50/GB-month | [pricing](https://www.blacksmith.sh/pricing), [sticky disks](https://docs.blacksmith.sh/blacksmith-caching/dependencies-sticky-disks) |
| Depot | USD 20/month with 2,000 min, then USD 0.006/min, billed by the second | standby instances; cache up to 10× faster (vendor) | [docs](https://depot.dev/docs/github-actions/overview) |
| Namespace | USD 0.002–0.003/min (2 vCPU, 4 GB) | persistent NVMe cache volumes | [pricing](https://namespace.so/pricing) |
| RunsOn | EUR 300/year licence plus your own AWS bill | warm pools: hot under 6 s, stopped under 15 s (vendor) | [warm pools](https://runs-on.com/docs/performance/warm-pools/) |
| WarpBuild | USD 0.004/min, plus USD 0.04 per snapshot restore | snapshots keep the toolchain, expire after 15 days | [pricing](https://www.warpbuild.com/pricing) |

A fast runner does not remove GitHub's own dispatch delay. Measure waiting after the switch.

## Cancel stale runs

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Keep the group per ref, so merge queue refs and other branches never cancel each other. A cancelled run is not a pass ([concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency)).

## Merge queue: the full suite before main

```yaml
on:
  pull_request:
  merge_group:
    types: [checks_requested]
```

Turn on the merge queue in the branch ruleset, and make the full-suite job a required check. The same job must run on `merge_group`, or the queue never passes ([merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)). On `merge_group`, skip test selection and run everything.

## Setup under 15 seconds

- **Blobless clone:** `actions/checkout` with `filter: blob:none`. Later file reads fetch blobs on demand, so set `fetch-depth` on its own: `0` only when the job needs history, such as test selection against the base ([checkout](https://github.com/actions/checkout/blob/master/README.md)).
- **Seed caches from main.** A PR can read caches from its base branch, but a PR's own caches are visible only to re-runs of that PR. So save the caches in a `push` to main, and let PRs only restore them ([cache scope](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)). Never put a secret in a cache a PR can read.
- **Cache the installed dependencies, not only the download cache.** Key on the lockfile, and keep `restore-keys` as a fallback. Log `cache-hit` on every run so the audit can count the hit rate.
- **Bake the toolchain into the image.** GitHub larger runners take a custom image built from a job with `snapshot:`; image storage is billed ([custom images](https://docs.github.com/en/actions/how-tos/manage-runners/larger-runners/use-custom-images)). On Blacksmith, use a sticky disk for the toolchain and dependency cache.
- **Parallel jobs must not write the same cache key.** Let one job save, and the others use `actions/cache/restore`.

## Fail a slow green job

`timeout-minutes` kills a hang. It does not fail a job that finished slowly. Add the budget check after the command:

```yaml
- name: Tests (budget 30 s)
  timeout-minutes: 5
  run: |
    start=$SECONDS
    ./ci/test.sh
    if (( SECONDS - start > 30 )); then echo "tests took $((SECONDS - start)) s, budget 30 s" >&2; exit 1; fi
```

## Local hooks: hk

hk keeps its config in `hk.pkl`. Top-level `steps` run on pre-commit; declare `pre-push` under `hooks`. CI runs `hk check --all`, which changes no files ([hk configuration](https://hk.jdx.dev/configuration.html)).

```bash
mise use hk
hk init
hk install
hk check --all
```

Pin the Pkl package to the release you install (v2.14.0 on 2026-11-24). In hk's own benchmark (about 60 staged files, 8 CPUs, warm cache), the median commit hook took 1.37 s against 1.81 s for lefthook and 2.97 s for pre-commit ([hk benchmarks](https://hk.jdx.dev/benchmarks.html)). Before you replace an existing `pre-commit` setup, run both and list any hook hk does not have.

## Timing API

```bash
gh api "repos/OWNER/REPO/actions/runs?status=completed&per_page=100"
gh api "repos/OWNER/REPO/actions/runs/RUN_ID/jobs?per_page=100&filter=latest"
```

Jobs report `created_at`, `started_at`, and `completed_at`; steps report `started_at` and `completed_at` ([runs](https://docs.github.com/en/rest/actions/workflow-runs?apiVersion=2026-03-10), [jobs](https://docs.github.com/en/rest/actions/workflow-jobs?apiVersion=2026-03-10)). `scripts/ci_audit.py` uses these.
