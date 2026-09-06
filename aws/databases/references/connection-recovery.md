# Connection and recovery checks

Prove one layer at a time. Use [discovered metadata](discovery.md), not copied connection strings. The [shared CLI guide](../../references/cli-operating.md) owns scope and approval gates.

## Diagnose connectivity without secret values

| Check | Evidence and next action |
|---|---|
| Resource | Confirm engine, status, endpoint, port, member role, and recent/pending changes. A reader endpoint cannot serve the application's write path. |
| DNS | Resolve the discovered hostname from the actual application host or an approved host on the same private path. Compare it with the application's configured host, without printing its connection string. |
| Private network | Check source network, routes, return path, network ACLs, and security groups at both ends. A laptop failure does not prove the database is down. DocumentDB is VPC-only. |
| TCP | Test only the discovered host/port with a bounded timeout from that path. Success proves a socket, not TLS or login. Record timeout versus refusal. |
| TLS | Check trusted CA, hostname, certificate validity, and client settings. Do not disable certificate validation to make the test pass. |
| Secret/IAM | Inspect secret ARN, version metadata, intended runtime identity, and access policy. AWS API permission, secret/KMS permission, and database login are separate checks. Do not retrieve secret values for routine diagnosis. |
| Database auth | Use the application's established credential path for an approved login test. Check the actual engine's auth mode and user mapping. Do not assume IAM DB auth works on every engine. |
| Database rights | After login succeeds, use a narrow owner-approved read/check. Report pass/fail and timing, not rows, documents, keys, tokens, or passwords. |

For SQL Server, check whether the application uses SQL authentication or domain authentication; confirm domain metadata before changing a login. If the approved Windows host lacks `sqlcmd`, use an existing supported client or a small reviewed `.NET SqlClient` check rather than installing tools during an incident. Keep credentials out of process arguments and transcripts.

For DocumentDB, verify the driver's supported version, TLS trust, replica-set discovery, retry settings, and read preference for the actual topology. Do not copy old troubleshooting examples that disable TLS or embed passwords.

For Redis/Valkey, distinguish network/TLS errors from auth/ACL failures and wrong-role or shard-routing errors. A successful `PING` is not proof that the application can perform its required operation. Avoid cache writes unless the owner approves an isolated test key and its cleanup.

## Backups: evidence before restore

Record backup owner, source identifier, engine/version, encryption/KMS access, retention, available restore window, chosen restore point, and the required recovery point/time objectives. Backup policy settings alone do not prove that a usable recovery point exists. If AWS Backup owns protection, inspect its recovery points and restore permissions too; the default RDS snapshot listing is not a complete AWS Backup inventory.

For a selected RDS instance, compare the latest restorable time with the requested UTC recovery time. Inspect automated-backup windows when proving the lower bound; do not infer it solely from retention days.

```bash
AWS_PROFILE="$PROFILE" aws rds describe-db-instances --region "$REGION" \
  --db-instance-identifier "$DB_ID" \
  --query 'DBInstances[].{Id:DBInstanceIdentifier,Retention:BackupRetentionPeriod,Latest:LatestRestorableTime,Encrypted:StorageEncrypted,Kms:KmsKeyId,DeletionProtection:DeletionProtection}' \
  --output json --no-cli-pager
AWS_PROFILE="$PROFILE" aws rds describe-db-instance-automated-backups --region "$REGION" \
  --db-instance-identifier "$DB_ID" \
  --query 'DBInstanceAutomatedBackups[].{Id:DBInstanceIdentifier,Status:Status,Window:RestoreWindow,Retention:BackupRetentionPeriod,Encrypted:Encrypted,Kms:KmsKeyId}' \
  --output json --no-cli-pager
AWS_PROFILE="$PROFILE" aws rds describe-db-snapshots --region "$REGION" \
  --db-instance-identifier "$DB_ID" \
  --query 'DBSnapshots[].{Id:DBSnapshotIdentifier,Type:SnapshotType,Status:Status,Created:SnapshotCreateTime,Engine:Engine,Version:EngineVersion,Encrypted:Encrypted,Kms:KmsKeyId}' \
  --output json --no-cli-pager
```

Aurora and DocumentDB backups are cluster-scoped. Set `DB_SERVICE` to `rds` for Aurora or `docdb` for DocumentDB; use the selected `CLUSTER_ID`.

```bash
DB_SERVICE=rds
AWS_PROFILE="$PROFILE" aws "$DB_SERVICE" describe-db-clusters --region "$REGION" \
  --db-cluster-identifier "$CLUSTER_ID" \
  --query 'DBClusters[].{Id:DBClusterIdentifier,Retention:BackupRetentionPeriod,Earliest:EarliestRestorableTime,Latest:LatestRestorableTime,Encrypted:StorageEncrypted,Kms:KmsKeyId}' \
  --output json --no-cli-pager
AWS_PROFILE="$PROFILE" aws "$DB_SERVICE" describe-db-cluster-snapshots --region "$REGION" \
  --db-cluster-identifier "$CLUSTER_ID" \
  --query 'DBClusterSnapshots[].{Id:DBClusterSnapshotIdentifier,Type:SnapshotType,Status:Status,Created:SnapshotCreateTime,Engine:Engine,Version:EngineVersion,Encrypted:StorageEncrypted,Kms:KmsKeyId}' \
  --output json --no-cli-pager
```

For node-based Redis/Valkey, use `elasticache describe-snapshots --replication-group-id "$CACHE_GROUP_ID"`; inspect snapshot status, node snapshot times, engine/version, and KMS metadata with a narrow query. Inspect a standalone member by its cache cluster ID instead. Check whether the workload can rebuild the cache or needs a tested backup; do not assume cached state is disposable.

## Review changes and prove recovery

- Prefer a change in the owning IaC repo. Review exact targets, replacement/deletion risk, edition/version compatibility, parameters, option groups, ACU/node limits, maintenance timing, and pending reboots. Do not use an immediate CLI change to bypass review.
- Restore to a **new isolated target** first. RDS instance point-in-time restore leaves the source unchanged. Aurora/DocumentDB need their cluster restore path and usable member instances, not an RDS instance restore recipe. Cache restore creates a new cache/cluster.
- Review the target network, KMS access, parameter/option groups, and client endpoint before execution. Do not assume restore defaults preserve source settings. Preserve the source and backup until the owner accepts recovery.
- SQL Server point-in-time restore can leave cross-database transactions inconsistent; require the application's consistency checks, not only instance status.
- After the approved restore, wait/poll to a fixed deadline. Verify configuration and login, then run owner-approved integrity and application checks. Check recovery-point age and elapsed recovery time against the agreed objectives. Retain results without customer data.
- Treat endpoint cutover as a separate reviewed change. State how writes stop, how clients reconnect, and how new writes are preserved if rollback is needed. Switching DNS back after new writes is not automatically safe rollback.
- For a cache restore, prove engine/client compatibility, shard routing, required data/TTL behavior, and application health before cutover. AWS `available` alone is not acceptance.
- Finish with source/target IDs, restore point, measured recovery time, application result, owner acceptance, cleanup decision, and remaining gaps. Report untested recovery as untested; never call a snapshot list a restore test.
