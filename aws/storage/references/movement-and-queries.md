# Discover movement without moving data

Payer charges establish past spend, not active jobs. Use the [shared CLI guide](../../references/cli-operating.md), then discover only the requested account and Region. Metadata may reveal partner names, paths, and database identifiers; keep output narrow and local.

These examples are first slices, not complete inventories. Preserve `NextToken` and resume with `--starting-token` before claiming coverage. DMS `describe-replication-configs` instead uses service `Marker` and `--marker`; repeat until that marker is absent.

```bash
aws transfer list-servers --profile "$PROFILE" --region "$REGION" \
  --max-items 25 --output json --no-cli-pager \
  --query '{Servers:Servers[].{Id:ServerId,State:State,Endpoint:EndpointType,Identity:IdentityProviderType,Domain:Domain},NextToken:NextToken}'
aws datasync list-tasks --profile "$PROFILE" --region "$REGION" \
  --max-items 25 --output json --no-cli-pager \
  --query '{Tasks:Tasks[].{Arn:TaskArn,Status:Status},NextToken:NextToken}'
aws dms describe-replication-tasks --without-settings --profile "$PROFILE" --region "$REGION" \
  --max-items 25 --output json --no-cli-pager \
  --query '{Tasks:ReplicationTasks[].{Arn:ReplicationTaskArn,Status:Status,Mode:MigrationType,Source:SourceEndpointArn,Target:TargetEndpointArn,Stats:ReplicationTaskStats},NextToken:NextToken}'
aws dms describe-replication-configs --profile "$PROFILE" --region "$REGION" \
  --max-records 25 --output json --no-cli-pager \
  --query '{Configs:ReplicationConfigs[].{Arn:ReplicationConfigArn,Type:ReplicationType,Source:SourceEndpointArn,Target:TargetEndpointArn},Marker:Marker}'
```

## Follow only the selected resource

| Service | Next metadata checks | What not to infer or execute |
|---|---|---|
| Transfer Family | `describe-server` for protocol, identity provider, endpoint details, logging; `list-connectors`/`describe-connector` if outbound connectors are in scope | No servers does not exclude connectors. Online does not prove authentication, backend S3/EFS access, or delivery. Do not start servers, test partner login, invoke workflows, or send files. |
| DataSync | `describe-task` for source/destination ARNs, schedule, options; `list-task-executions` then `describe-task-execution` for the selected existing run; inspect only the matching location type | Check overwrite/delete options and verification results before judging an existing run. Do not start/cancel executions, change schedules, or activate agents. |
| DMS | `describe-endpoints` with a narrow projection, existing task statistics, replication instance metadata; `describe-replications` for serverless runtime state | Configured serverless replication is not a running replication. No start/resume/reload, connection tests, endpoint changes, or source SQL. Task status alone does not prove target correctness or acceptable CDC lag. |

Use service-side ID filters where supported. Apply projections before display; never print whole DMS endpoint settings, table mappings, Transfer identity-provider settings, or task payloads. CLI projections reduce output, not what the service returns to the local process.

For a failed existing run, record the run/task ARN, source and target types, UTC window, state, counters, and sanitized error. Correlate existing logs/metrics through [observability](../../observability/instructions.md). Check the job role and KMS via [security](../../security/instructions.md), and private routes/DNS/endpoints via [networking](../../networking/instructions.md). Do not rerun a transfer to obtain better evidence.

## S3 query adjacency: Athena and Glue

These are related capabilities, not evidence of deployment. Reach for them only when the user needs to query an approved S3 dataset, not to inventory storage.

- Inspect an existing Athena workgroup with `get-work-group`: enforced result location, encryption, and scan limits. Inspect the relevant Glue table metadata with `get-table`: S3 location, format, columns, and partitions. Metadata can itself be sensitive; project only what the question needs.
- Agree on the dataset owner, allowed columns/partitions, result bucket/prefix, KMS keys, IAM/Lake Formation access, scan budget, and retention before planning SQL.
- `start-query-execution` reads data and can write result objects. A Glue crawler or job can read data and change catalog/output state. None is a discovery command. Do not execute them here.
- SQL `LIMIT` is not a scan-cost limit. Prefer known partitions and the workgroup's enforced scan control; do not read sample customer rows just to infer a schema.

Return discovered configuration, existing execution evidence, and unknowns separately. Transfer success, DMS task state, or a query result is not backup or restore proof.
