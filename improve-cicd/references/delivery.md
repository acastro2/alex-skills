# Delivery

What every deploy target shares: how to measure, environments, credentials, concurrency, build once, verification and rollback, flags, migrations, and the evidence. Checked 2026-11-25.

## Measure

DORA defines five metrics ([DORA metrics](https://dora.dev/guides/dora-metrics/)):

| Metric | Definition |
| --- | --- |
| Change lead time | Commit to running in production. Merge to production is a narrower part of it, and it is the part CD controls |
| Deployment frequency | Production deployments per period |
| Change failure rate | Share of production deployments that need immediate fixing, usually a rollback or a hotfix. A failure caught before production does not count |
| Failed deployment recovery time | Time to recover from such a failure |
| Deployment rework rate | Share of deployments that were unplanned, caused by a production incident |

The 2024 report's bands are clusters from a survey, not targets ([DORA 2024](https://dora.dev/research/2024/dora-report/2024-dora-accelerate-state-of-devops-report.pdf)):

| Band | Lead time | Frequency | Change failure rate | Recovery | Share of respondents |
| --- | --- | --- | --- | --- | --- |
| Elite | under 1 day | on demand | 5% | under 1 hour | 19% |
| High | 1 day to 1 week | daily to weekly | 20% | under 1 day | 22% |
| Medium | 1 week to 1 month | weekly to monthly | 10% | under 1 day | 35% |
| Low | 1 to 6 months | monthly to every 6 months | 40% | 1 week to 1 month | 25% |

### From GitHub data

`scripts/cd_audit.py` computes these from the GitHub API:

- **A deployment succeeded** when one of its statuses is `success`. Its time is the earliest `success` status, not the deployment's `created_at` ([statuses](https://docs.github.com/en/rest/deployments/statuses)).
- **Lead time** for a merged PR is the first successful production deployment whose commit contains the PR's merge commit, minus `merged_at`. PRs not yet deployed are counted, never dropped.
- **Change failure** is a successful deploy followed by a rollback (an earlier commit deployed again) or a revert. A deploy that failed before it reached `success` never reached production, so it is not a change failure.
- **GitHub deletes deployment statuses after 90 days.** Keep the audit's JSON output if you need a longer history.
- **A completed workflow run is not a deployment.** Only a job with `environment:` creates deployment records. If the repo has none, adding them is the first fix.

### In Datadog

If the service runs in Datadog, send deploys there too, so the monitors can compare versions:

- **Tag every deploy:** `DD_ENV`, `DD_SERVICE`, and `DD_VERSION` set to the commit SHA ([unified service tagging](https://docs.datadoghq.com/getting_started/tagging/unified_service_tagging.md)). Deployment tracking then compares errors and latency by version ([deployment tracking](https://docs.datadoghq.com/tracing/services/deployment_tracking.md)).
- **DORA metrics** take deployments from APM version tracking, or from `datadog-ci dora deployment --service S --env E --started-at T --git-repository-url U --git-commit-sha SHA` ([setup](https://docs.datadoghq.com/delivery_performance/dora_metrics/setup.md)). Datadog counts a change failure when an earlier SHA is deployed again, or a revert or hotfix follows ([change failure detection](https://docs.datadoghq.com/delivery_performance/dora_metrics/change_failure_detection.md)).

## Environments

- **Every deploy job names its environment:** `environment: production`. That creates the deployment record, holds the environment's secrets until its rules pass, and lets the AWS role trust only that environment ([deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)).
- **Restrict which branches and tags may deploy** to production: "Selected branches and tags". `*` does not match `/`.
- **Required reviewers** (up to 6, one approval passes, turn on "prevent self-review") and **wait timers** (up to 30 days, not billed) exist. Use them only where a rule requires a human. See [manual approvals](#manual-approvals).
- **Custom deployment protection rules** let a GitHub App gate a deploy, for example on a monitor's state.

## Credentials: OIDC to AWS

```yaml
permissions:
  contents: read
  id-token: write
steps:
  - uses: aws-actions/configure-aws-credentials@v6
    with:
      role-to-assume: arn:aws:iam::<ACCOUNT_ID>:role/gha-prod
      aws-region: us-east-1
```

The role's trust policy checks `token.actions.githubusercontent.com:aud` equals `sts.amazonaws.com`, and `sub` equals the exact repo and environment, never a wildcard ([GitHub OIDC in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws), [AWS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html)).

**Check the subject format before you write the trust policy.** Repos created after July 15, 2026 use an immutable subject with numeric IDs: `repo:octo-org@123456/octo-repo@456789:environment:production`. Older repos keep the old `repo:ORG/REPO:...` format unless they opt in, and a rename or transfer after that date switches the repo to the new format, which breaks a trust policy written for the old one ([GitHub OIDC](https://docs.github.com/en/actions/reference/security/oidc)).

Use separate roles for plan (read) and deploy (write), each trusting only its own environment.

## One deploy at a time

```yaml
jobs:
  deploy:
    environment: production
    concurrency:
      group: deploy-production
      cancel-in-progress: false
```

The default queue keeps one running and one pending deploy, and a newer pending deploy **replaces** the older pending one. That is what you want when every deploy carries all earlier merges. `queue: max` keeps up to 100 pending, with no guaranteed order, and cannot be combined with `cancel-in-progress: true` ([concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)).

## Build once, promote the digest

```yaml
jobs:
  build:
    outputs:
      digest: ${{ steps.build.outputs.digest }}
    steps:
      - id: build
        uses: docker/build-push-action@v7
        with: { push: true, tags: "ghcr.io/acme/app:${{ github.sha }}" }
  staging:
    needs: build
    environment: staging
    # deploy ghcr.io/acme/app@${{ needs.build.outputs.digest }}
  production:
    needs: [build, staging]
    environment: production
    # deploy the same digest
```

A tag can move; a digest cannot. ECS, Kubernetes, and Lambda all accept `image@sha256:...` ([build-push-action](https://github.com/docker/build-push-action)).

**Events from `GITHUB_TOKEN` do not start other workflows.** A release or push made with it does not trigger the next workflow, so keep build and promotion in one workflow, or call the next one with `workflow_dispatch` ([trigger a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)).

## Verify, then mark success

- **Smoke-test the real endpoints after each deploy, and block on failure.** For Datadog Synthetics: `DataDog/synthetics-ci-github-action` with the tests set to `blocking`; a `non_blocking` test cannot gate a rollback ([GitHub Actions](https://docs.datadoghq.com/continuous_testing/cicd_integrations/github_actions.md), [configuration](https://docs.datadoghq.com/continuous_testing/cicd_integrations/configuration.md)).
- **Gate promotion on monitors:** `DataDog/deployment-gate-github-action` waits for monitors and Watchdog to judge the new version. A monitor rule can wait 0 to 7,200 s; Watchdog needs at least 900 s after the deploy starts ([deployment gates](https://docs.datadoghq.com/deployment_gates/setup/preconfigured.md)). So a Watchdog gate alone puts at least 15 minutes in the lead time: use it only where that bake earns its time.
- **Bake 5 minutes by default.** Then measure how long the signal takes to fire on a known-bad version, add two evaluation periods, and use that. There is no universal number, so write the measured one in the PR.
- **Only then set the deployment status to `success`.** Set `failure` when verification fails, and record a rollback as a new deployment.

## Feature flags

A flag separates deploy from release. Ship the code dark, turn it on for a few users, and turn it off in seconds if it misbehaves, with no deploy. OpenFeature gives one API over many flag providers; the flag change itself happens in the provider ([OpenFeature](https://openfeature.dev/docs/tutorials/getting-started/python/)). Every flag has an owner and a removal date.

## Database migrations

- **Expand, then contract, each step in its own deploy:** add the new column or table; backfill and write to both; switch reads; stop writing the old; drop it last.
- **Never drop a column that any running version, canary, or custom environment still reads.** GitHub's August 2025 incidents came from dropping a column the ORM still referenced: 32 minutes and about 4% of web and API traffic hit on August 5, and 46 minutes on August 27 ([GitHub availability report](https://github.blog/news-insights/company-news/github-availability-report-august-2025/)).
- **Set a short lock timeout and retry.** A migration that waits on a lock blocks every query behind it. One team sets a 2-second PostgreSQL lock timeout with up to 100 retries, and reports no outages from migrations ([Defacto](https://www.getdefacto.com/article/database-schema-migrations)).

## Manual approvals

- In DORA's 2019 data, teams with external change approval were 2.6× as likely to be low performers, and there was no evidence the approval lowered change failure rates ([DORA 2019](https://dora.dev/research/2019/dora-report/2019-dora-accelerate-state-of-devops-report.pdf)).
- A required company approval stays. Measure its wait in the audit, and bring Alex the number with this evidence. Automate what feeds the approval (the plan, the diff, the risk) so the approver decides in seconds.

## Evidence for the shape

All of these are associations or single-company results, not controlled trials:

- **Canary with automatic abort:** iFood saw 37% fewer deployment incidents after moving 881 services to it ([iFood](https://tech.ifood.com.br/en/back-end-engineering/canary-2-0-how-ifood-turned-production-deploy-into-a-safe-and-automated-process/)). OfferUp went from about 1 hour per deploy and a manual 1-hour rollback to about 5 minutes each, with Flagger and Datadog checks ([AWS blog](https://aws.amazon.com/blogs/devops/journey-to-adopt-cloud-native-devops-platform-series-1-offerup-modernized-devops-platform-with-amazon-eks-and-flagger-to-accelerate-time-to-market/)).
- **Build once, deploy only what changed:** BetterHealthcare cut a deploy from about 10 minutes to about 3, and a promotion to about 2, with Nx affected-only builds and one image promoted through Argo CD ([BetterHealthcare](https://dev.to/betterhealthcare/monorepo-and-trunk-based-development-using-nx-github-actions-and-argo-cd-261e)).
- **Removing a manual release gate:** one fintech cut median lead time from 20.2 to 6.2 hours and doubled releases per week ([Aalto thesis](https://aaltodoc.aalto.fi/handle/123456789/141309)).
- **Risk-based gating instead of a blanket freeze:** during Meta's 2023 winter freeze, a risk model gated 16% of changes; 42% more changes landed than the winter before, and severe outages fell 52% ([ACM](https://dl.acm.org/doi/full/10.1145/3722216)).
- **Trunk-based development:** elite performers that met reliability targets were 2.3× as likely to use it ([DORA 2021](https://dora.dev/research/2021/dora-report/2021-dora-accelerate-state-of-devops-report.pdf)).
- **AI adoption:** in DORA 2024, more AI adoption went with slightly lower throughput (−1.5%) and lower stability (−7.2%) per 25% more adoption; DORA 2025 found more throughput and still more instability. More AI-written changes make the safety rules here more important, not less.
