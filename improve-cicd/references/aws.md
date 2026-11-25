# AWS Lambda and ECS

Deploy by version or digest, shift traffic progressively, and let an alarm roll it back. Checked 2026-11-25.

## Lambda

- **Publish a version, then move an alias.** A version is immutable, and an alias cannot point at `$LATEST`. Rolling back is moving the alias to the previous version ([versions](https://docs.aws.amazon.com/lambda/latest/dg/configuration-versions.html)).
- **Shift traffic with CodeDeploy and roll back on an alarm:**

  ```yaml
  # AWS SAM
  Properties:
    AutoPublishAlias: live
    DeploymentPreference:
      Type: Canary10Percent5Minutes
      Alarms: [ErrorRateAlarm]
      Hooks: { PreTraffic: PreTrafficCheck }
  ```

  `Canary10Percent5Minutes` sends 10% for 5 minutes, then the rest; `Linear10PercentEvery1Minute` adds 10% each minute; `AllAtOnce` has no observation time ([deployment configurations](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html), [SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-property-function-deploymentpreference.html)).
- **The alarm must be set to roll back, not only named.** On the deployment group: `--auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE,DEPLOYMENT_STOP_ON_ALARM` ([create-deployment-group](https://docs.aws.amazon.com/cli/latest/reference/deploy/create-deployment-group.html)).
- **A low-traffic function may never send the canary enough calls** for the alarm to judge it. Use a pre-traffic hook that calls the new version, or a longer canary.
- **Container images take a few seconds to optimize before the function is active.** Wait with `aws lambda wait function-updated` before you shift traffic ([images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)).
- **`cdk deploy --hotswap` and `sam sync` skip CloudFormation and cause drift. Development only** ([CDK](https://docs.aws.amazon.com/cdk/v2/guide/ref-cli-cmd-deploy.html), [SAM sync](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/using-sam-cli-sync.html)).

## ECS

### Pick the strategy

| Strategy | Use when | Settings |
| --- | --- | --- |
| Rolling (default) | Most services | `minimumHealthyPercent: 100`, `maximumPercent: 200` starts new tasks before old ones stop, if capacity allows ([rolling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-ecs.html)) |
| Native CANARY or LINEAR (since October 2025) | Risky changes on a load-balanced service | `canaryConfiguration: {canaryPercent: 10.0, canaryBakeTimeInMinutes: 5}` or `linearConfiguration: {stepPercent: 10.0, stepBakeTimeInMinutes: 1}` ([announcement](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-ecs-built-in-linear-canary-deployments/)) |
| Native BLUE_GREEN (since July 2025) | A full, instant switch with the old version kept warm | `strategy=BLUE_GREEN,bakeTimeInMinutes=5`; traffic moves all at once ([update-service](https://docs.aws.amazon.com/cli/latest/reference/ecs/update-service.html)) |

The native strategies replace CodeDeploy for ECS in new services. Older services on the `CODE_DEPLOY` controller use the ECS configurations (`CodeDeployDefault.ECSCanary10Percent5Minutes`), not the Lambda ones.

### Roll back by itself

```json
"deploymentConfiguration": {
  "deploymentCircuitBreaker": { "enable": true, "rollback": true },
  "alarms": { "alarmNames": ["app-5xx"], "enable": true, "rollback": true }
}
```

The circuit breaker catches tasks that fail to start or fail health checks; the alarm catches a running version that misbehaves ([failure detection](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-failure-detection.html), [alarms](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-alarm-failure.html)). Both stop watching once the deployment completes, so the bake time is the window in which a bad version can still roll back by itself.

### Make it fast

- **Lower the target group's deregistration delay** from the 300 s default when requests are short, for example to 5 s. Not for streaming or long requests ([draining](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/load-balancer-connection-draining.html)).
- **Set the health check grace period to the real start time**, measured. Too short fails healthy tasks; too long hides a bad one ([update-service](https://docs.aws.amazon.com/cli/latest/reference/ecs/update-service.html)).
- **Keep images small.** Fargate pulls the whole image for each task. For images over about 250 MiB, test SOCI lazy loading ([Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html)).
- **Lifecycle hooks are on the critical path.** A slow validation hook is lead time.

### From GitHub Actions

```yaml
- uses: aws-actions/amazon-ecs-deploy-task-definition@v2
  with:
    task-definition: task-def.json   # image: <repo>@sha256:<digest>
    service: app
    cluster: prod
    wait-for-service-stability: true
```

Without `wait-for-service-stability`, the job is green before the deploy is ([action](https://github.com/aws-actions/amazon-ecs-deploy-task-definition/blob/master/action.yml)). Set the strategy, bake, and alarms on the service in OpenTofu, not in the workflow.

## App Runner

**App Runner takes no new customers from April 30, 2026**, and gets no new features. Existing services keep running. AWS recommends ECS Express Mode instead ([App Runner](https://aws.amazon.com/apprunner/)). Do not start anything new on it. For an existing service: turn off automatic deployment, call `aws apprunner start-deployment`, and wait on `list-operations`, because the call only starts the deploy. It has no "roll back to the previous release" call: redeploy the previous image digest ([StartDeployment](https://docs.aws.amazon.com/apprunner/latest/api/API_StartDeployment.html)).
