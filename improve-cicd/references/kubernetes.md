# Kubernetes

Build the image once, deploy it by digest, roll out progressively, and roll back by itself. Checked 2026-11-25 (build-push-action v7, Helm 4.3, Argo CD and Argo Rollouts stable docs).

## Build the image fast

```yaml
- uses: docker/setup-buildx-action@v4
- id: build
  uses: docker/build-push-action@v7
  with:
    push: true
    tags: ghcr.io/acme/app:${{ github.sha }}
    cache-from: type=registry,ref=ghcr.io/acme/app:buildcache
    cache-to: type=registry,ref=ghcr.io/acme/app:buildcache,mode=max
```

- **`mode=max`** caches the intermediate stages too. Use a separate cache image, never the release tag ([registry cache](https://docs.docker.com/build/cache/backends/registry/)). `type=gha` also works; scope it per image ([gha cache](https://docs.docker.com/build/cache/backends/gha/)).
- **Copy the dependency manifests and install before you copy the source**, so a code change does not rebuild the dependency layer ([optimize](https://docs.docker.com/build/cache/optimize)).
- **Build arm64 on arm64 runners**, not under QEMU emulation, when you need both platforms ([multi-platform](https://docs.docker.com/build/building/multi-platform/)).
- **Hosted builders keep the cache on disk.** Blacksmith's builder (`useblacksmith/setup-docker-builder@v2`) keeps layers on NVMe and removes cache upload and download ([Blacksmith](https://docs.blacksmith.sh/blacksmith-caching/docker-builds)); Depot runs native multi-platform builders with a persistent cache, and reports 2.1× faster than cached Docker on its Moby benchmark ([Depot](https://depot.dev/benchmark/moby)). Both are vendor numbers: measure on your Dockerfile.
- **Keep the image small.** Vannevar Labs cut an ML deploy from 3 hours to 6 minutes, mostly by splitting a 25 GB image into per-model images of 2 to 12 GB ([AWS blog](https://aws.amazon.com/blogs/containers/how-vannevar-labs-cut-ml-inference-costs-by-45-using-ray-on-amazon-eks/)).

## Sign what you ship

```yaml
permissions: { contents: read, id-token: write, attestations: write, packages: write }
- uses: actions/attest@v4
  with:
    subject-name: ghcr.io/acme/app
    subject-digest: ${{ steps.build.outputs.digest }}
    push-to-registry: true
```

Attest the digest, not a tag. `actions/attest-build-provenance@v4` is a wrapper around `actions/attest`; use `actions/attest` in new workflows ([attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)). Signing does nothing until the cluster checks it, so add an admission policy that verifies the signature.

## Deploy: GitOps with Argo CD (default)

- **CI commits the tested digest to the config repo.** Argo CD Image Updater can do it too, but CI already knows which digest passed the tests ([Image Updater](https://github.com/argoproj-labs/argocd-image-updater/blob/master/docs/configuration/images.md)).
- **Turn on automated sync with `selfHeal: true`.** `prune` is opt-in; turn it on once the app's resources are all in Git ([auto sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)).
- **Add a GitHub webhook to Argo CD.** Without it, Argo CD polls every 120 s plus up to 60 s of jitter, so a deploy can wait 3 minutes before it starts ([webhook](https://argo-cd.readthedocs.io/en/stable/operator-manual/webhook/), [auto sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)).
- **Sync waves** apply lower numbers first and check health between waves ([sync waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)). Use a negative wave for a migration Job.
- **Never also `helm upgrade` an app Argo CD manages.** Two deployers fight.

## Roll out progressively: Argo Rollouts

```yaml
strategy:
  canary:
    steps:
      - setWeight: 10
      - pause: { duration: 2m }
      - analysis: { templates: [{ templateName: error-rate }] }
      - setWeight: 50
      - pause: { duration: 5m }
```

```yaml
kind: AnalysisTemplate
metadata: { name: error-rate }
spec:
  metrics:
    - name: error-rate
      interval: 30s
      failureLimit: 3
      successCondition: result < 0.01
      provider:
        datadog:
          apiVersion: v2
          interval: 5m
          queries:
            a: sum:requests.errors{service:app,version:canary}.as_count()
            b: sum:requests{service:app,version:canary}.as_count()
          formula: a / b
```

- A failed analysis aborts the canary and sends traffic back to the stable version ([canary](https://argo-rollouts.readthedocs.io/en/stable/features/canary/)). Without a traffic router, the weight is only a replica ratio.
- The Datadog provider runs metric queries, and v2 formulas need Argo Rollouts 1.7 or later ([Datadog analysis](https://argo-rollouts.readthedocs.io/en/stable/analysis/datadog/)). To gate on a monitor's state, use the separate Datadog metric plugin ([plugin](https://github.com/argoproj-labs/rollouts-plugin-metric-datadog/blob/main/docs/configuration.md)). Prometheus works the same way ([Prometheus](https://argo-rollouts.readthedocs.io/en/stable/analysis/prometheus/)).
- Flagger does the same job ([Flagger](https://docs.flagger.app/main/usage/how-it-works)). Use one controller per workload.
- **Prove the abort with a drill:** deploy a version that returns errors to the canary on purpose, in staging, and confirm it rolls back inside the budget. Do it once per service, not as a committed test.

## Deploy without GitOps: Helm

```bash
# Helm 4
helm upgrade --install app ./chart --set-string image.digest="$DIGEST" \
  --rollback-on-failure --wait --wait-for-jobs --timeout 10m
```

- **Helm 4 renamed `--atomic` to `--rollback-on-failure`.** Helm 3 uses `--atomic`, which also implies `--wait` ([Helm 4](https://helm.sh/docs/helm/helm_upgrade/), [Helm 3](https://helm.sh/docs/v3/helm/helm_upgrade/)).
- **In Helm 4, an upgrade without `--wait` waits only for hooks** (the default is `hookOnly`). A green job then proves nothing about the pods. Always pass `--wait`.
- `--timeout` defaults to 5 minutes.

## The gate inside the cluster

- **Readiness probes keep a pod out of the Service until it is ready.** Without one, a rollout counts a starting pod as healthy.
- `kubectl rollout status deployment/app --timeout=10m` waits for the new pods. It does not check error rates, and a missed progress deadline does not roll back by itself ([rollout status](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_status/)). That is why the analysis step exists.
