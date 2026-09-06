# Metadata discovery

Use this to identify the resource without opening its data. Complete the [shared preflight](../../references/cli-operating.md); `PROFILE` and `REGION` below must already be confirmed. Run only the service reads needed for the question.

## RDS and Aurora

Start with instances and clusters together. Join `Cluster` to `Id`; an Aurora cluster can have different classes across its members.

```bash
AWS_PROFILE="$PROFILE" aws rds describe-db-instances --region "$REGION" \
  --query 'DBInstances[].{Id:DBInstanceIdentifier,Engine:Engine,Version:EngineVersion,Class:DBInstanceClass,Cluster:DBClusterIdentifier,Status:DBInstanceStatus,License:LicenseModel}' \
  --output json --no-cli-pager
AWS_PROFILE="$PROFILE" aws rds describe-db-clusters --region "$REGION" \
  --query 'DBClusters[].{Id:DBClusterIdentifier,Engine:Engine,Version:EngineVersion,Mode:EngineMode,Capacity:ServerlessV2ScalingConfiguration,Members:DBClusterMembers[].{Id:DBInstanceIdentifier,Writer:IsClusterWriter},Status:Status}' \
  --output json --no-cli-pager
```

After selecting an exact instance, capture network and pending-change metadata. Set `DB_ID` from discovery, not an endpoint alias.

```bash
AWS_PROFILE="$PROFILE" aws rds describe-db-instances --region "$REGION" \
  --db-instance-identifier "$DB_ID" \
  --query 'DBInstances[].{Id:DBInstanceIdentifier,Endpoint:Endpoint,Vpc:DBSubnetGroup.VpcId,SubnetGroup:DBSubnetGroup.DBSubnetGroupName,SGs:VpcSecurityGroups,Public:PubliclyAccessible,MultiAZ:MultiAZ,Parameters:DBParameterGroups,Options:OptionGroupMemberships,Domains:DomainMemberships,IAMAuth:IAMDatabaseAuthenticationEnabled,Pending:PendingModifiedValues.{Class:DBInstanceClass,Version:EngineVersion,Storage:AllocatedStorage,Port:Port}}' \
  --output json --no-cli-pager
```

For Aurora, select `CLUSTER_ID` from discovery. Cluster endpoints are not individual member endpoints; check the application's intended writer/read path.

```bash
AWS_PROFILE="$PROFILE" aws rds describe-db-clusters --region "$REGION" \
  --db-cluster-identifier "$CLUSTER_ID" \
  --query 'DBClusters[].{Id:DBClusterIdentifier,Writer:Endpoint,Reader:ReaderEndpoint,Port:Port,SubnetGroup:DBSubnetGroup,SGs:VpcSecurityGroups,Parameters:DBClusterParameterGroup,IAMAuth:IAMDatabaseAuthenticationEnabled,Pending:PendingModifiedValues.{Version:EngineVersion,BackupRetention:BackupRetentionPeriod,IAMAuth:IAMDatabaseAuthenticationEnabled}}' \
  --output json --no-cli-pager
```

## DocumentDB

Use its own service API after classification. Set `CLUSTER_ID` to the selected DocumentDB cluster. The instance filter keeps membership scoped.

```bash
AWS_PROFILE="$PROFILE" aws docdb describe-db-clusters --region "$REGION" \
  --db-cluster-identifier "$CLUSTER_ID" \
  --query 'DBClusters[].{Id:DBClusterIdentifier,Engine:Engine,Version:EngineVersion,Status:Status,Endpoint:Endpoint,Reader:ReaderEndpoint,Port:Port,Members:DBClusterMembers,SGs:VpcSecurityGroups,SubnetGroup:DBSubnetGroup,Parameters:DBClusterParameterGroup}' \
  --output json --no-cli-pager
AWS_PROFILE="$PROFILE" aws docdb describe-db-instances --region "$REGION" \
  --filters "Name=db-cluster-id,Values=$CLUSTER_ID" \
  --query 'DBInstances[].{Id:DBInstanceIdentifier,Class:DBInstanceClass,Status:DBInstanceStatus,Endpoint:Endpoint,Vpc:DBSubnetGroup.VpcId}' \
  --output json --no-cli-pager
```

## Redis OSS and Valkey

Read both node-based views. Replication groups describe topology and controls; cache clusters identify member engines and versions.

```bash
AWS_PROFILE="$PROFILE" aws elasticache describe-replication-groups --region "$REGION" \
  --query 'ReplicationGroups[].{Id:ReplicationGroupId,Status:Status,Members:MemberClusters,ClusterMode:ClusterEnabled,ConfigurationEndpoint:ConfigurationEndpoint,Failover:AutomaticFailover,MultiAZ:MultiAZ,TLS:TransitEncryptionEnabled,Encrypted:AtRestEncryptionEnabled,AuthTokenEnabled:AuthTokenEnabled,UserGroups:UserGroupIds}' \
  --output json --no-cli-pager
AWS_PROFILE="$PROFILE" aws elasticache describe-cache-clusters --region "$REGION" \
  --query 'CacheClusters[].{Id:CacheClusterId,Group:ReplicationGroupId,Engine:Engine,Version:EngineVersion,Type:CacheNodeType,Status:CacheClusterStatus,SubnetGroup:CacheSubnetGroupName,SGs:SecurityGroups,Parameters:CacheParameterGroup}' \
  --output json --no-cli-pager
```

Then set `CACHE_GROUP_ID` to one selected replication group. Keep node-group endpoints with their shard IDs; do not flatten them into one assumed write endpoint.

```bash
AWS_PROFILE="$PROFILE" aws elasticache describe-replication-groups --region "$REGION" \
  --replication-group-id "$CACHE_GROUP_ID" \
  --query 'ReplicationGroups[].{Id:ReplicationGroupId,ConfigurationEndpoint:ConfigurationEndpoint,NodeGroups:NodeGroups[].{Shard:NodeGroupId,Status:Status,Primary:PrimaryEndpoint,Reader:ReaderEndpoint,Members:NodeGroupMembers[].{Id:CacheClusterId,Role:CurrentRole,ReadEndpoint:ReadEndpoint}},Retention:SnapshotRetentionLimit,SnapshotWindow:SnapshotWindow,Pending:PendingModifiedValues}' \
  --output json --no-cli-pager
```

For a selected member, `describe-cache-clusters --cache-cluster-id "$CACHE_ID" --show-cache-node-info` supplies node endpoint metadata. Resolve its subnet group to a VPC with `describe-cache-subnet-groups --cache-subnet-group-name "$SUBNET_GROUP"`. Apply a narrow output query before running either command.

Check client topology support, TLS, auth method, and intended read/write role before testing. Do not run `KEYS`, `MONITOR`, broad `SCAN`, or flush commands as diagnostics. Cache contents can contain customer data.

If the request explicitly concerns ElastiCache Serverless, use its separate `describe-serverless-caches` API. This is a related option, **not confirmed adoption**. An empty node-based inventory does not prove all cache types are absent.

## Interpret the result

- Empty results mean no match in the checked scope, not company-wide absence. Failed access is not an empty inventory.
- Keep endpoints and resource identifiers inside approved evidence. Never paste internal metadata into public documentation searches.
- Record edition/version, owner, IaC location, dependency path, status, and pending changes. Do not retrieve secret values to fill this record.
- For the next step, use [connection and recovery checks](connection-recovery.md).
