# Existing App Runner services

App Runner is closed to new customers after April 30, 2026. Existing customers can continue using it, but AWS plans no new features and has announced no end-of-life date. Do not invent a forced migration deadline.

## Discover and diagnose

Read the [shared CLI guide](../../references/cli-operating.md). Use `aws apprunner list-services` in the confirmed account and Region, then inspect only the affected service. Project state, image/source reference, network configuration and operation status. Service configuration can contain application environment values; do not dump the whole response.

For a VPC connector, application-initiated outbound traffic follows the VPC path. Verify DNS, routes and NAT/endpoints for each required dependency. App Runner's managed image-pull/logging traffic is separate. A successful deploy does not prove the application's database or external API path.

## If migration is requested

Compare the existing container, runtime configuration, IAM, ingress/egress, scaling, health checks, domains, secrets and operational owner with the target. Use the organization's existing ECS or Kubernetes path when it fits. ECS Express Mode is one option, not an automatic selection.

Keep the old service until the approved target passes application, network, identity, telemetry and cost checks. Plan traffic switching and rollback explicitly. Do not delete the source after a green deploy.

## Sources

- [Availability change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)
- [VPC access](https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html)

Verify current limitations through these official sources before changing a service.
