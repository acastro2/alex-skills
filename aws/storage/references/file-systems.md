# File systems: control-plane health is not client access

Use the [shared CLI guide](../../references/cli-operating.md) for scope. Keep `PROFILE` and `REGION` explicit. Do not mount a share, browse directories, or read files to discover infrastructure.

## FSx for NetApp ONTAP

Discover ONTAP file systems in the agreed account and Region; do not hardcode inventory counts. Keep the continuation token when bounding discovery, and resume before claiming complete coverage.

```bash
aws fsx describe-file-systems --profile "$PROFILE" --region "$REGION" \
  --max-items 25 --output json --no-cli-pager \
  --query '{Systems:FileSystems[?FileSystemType==`ONTAP`].{Id:FileSystemId,State:Lifecycle,Vpc:VpcId,Subnets:SubnetIds,CapacityGiB:StorageCapacity,Key:KmsKeyId,Deployment:OntapConfiguration.DeploymentType,Throughput:OntapConfiguration.ThroughputCapacity},NextToken:NextToken}'
```

Set `FSX_ID` from that result. Inspect its storage virtual machines (SVMs) and volumes, not just the parent file system:

```bash
aws fsx describe-storage-virtual-machines --filters "Name=file-system-id,Values=$FSX_ID" \
  --profile "$PROFILE" --region "$REGION" --max-items 25 --output json --no-cli-pager \
  --query '{SVMs:StorageVirtualMachines[].{Id:StorageVirtualMachineId,State:Lifecycle,Endpoints:Endpoints,RootSecurity:RootVolumeSecurityStyle},NextToken:NextToken}'
aws fsx describe-volumes --filters "Name=file-system-id,Values=$FSX_ID" \
  --profile "$PROFILE" --region "$REGION" --max-items 25 --output json --no-cli-pager \
  --query '{Volumes:Volumes[].{Id:VolumeId,State:Lifecycle,Svm:OntapConfiguration.StorageVirtualMachineId,Junction:OntapConfiguration.JunctionPath,SizeMiB:OntapConfiguration.SizeInMegabytes,Security:OntapConfiguration.SecurityStyle,Tiering:OntapConfiguration.TieringPolicy},NextToken:NextToken}'
```

- Follow file system → SVM → volume → client protocol. Use SVM data endpoints for the client's NFS/SMB/iSCSI path, not the management endpoint.
- `AVAILABLE` does not prove the client route, DNS resolution, export policy, SMB share, directory authentication, or POSIX/NTFS access. Separate these layers before proposing a fix.
- For private access, compare discovered subnets, routes, security groups, and endpoint addresses with the actual client path. Multi-AZ ONTAP routing needs special attention. [Networking](../../networking/instructions.md) owns route and security-group changes.
- Provisioned capacity is not free space. Compare file-system and volume capacity, throughput, latency, and IOPS for the same incident window through [observability](../../observability/instructions.md). Consider snapshots and tiering before calling growth a leak.
- AWS metadata does not expose every ONTAP export/share setting. If needed, ask the storage owner for a scoped read-only ONTAP configuration check. Do not improvise admin credentials or run volume, snapshot, or SnapMirror changes.
- Inspect existing FSx backup metadata for the exact volume when recovery is the question. A snapshot policy, backup schedule, or replication relationship is not restore proof; use the [recovery guidance](../instructions.md#a-backup-is-not-restore-proof).

## EFS

Use a known `EFS_ID`. If unknown, discover with `describe-file-systems`, a bounded result, and preserved continuation token first.

```bash
aws efs describe-file-systems --file-system-id "$EFS_ID" \
  --profile "$PROFILE" --region "$REGION" --output json --no-cli-pager \
  --query 'FileSystems[].{Id:FileSystemId,State:LifeCycleState,Encrypted:Encrypted,Key:KmsKeyId,Size:SizeInBytes,Performance:PerformanceMode,Throughput:ThroughputMode}'
aws efs describe-mount-targets --file-system-id "$EFS_ID" \
  --profile "$PROFILE" --region "$REGION" --output json --no-cli-pager \
  --query 'MountTargets[].{Id:MountTargetId,State:LifeCycleState,Vpc:VpcId,Subnet:SubnetId,Az:AvailabilityZoneName,Ip:IpAddress,Eni:NetworkInterfaceId}'
aws efs describe-access-points --file-system-id "$EFS_ID" \
  --profile "$PROFILE" --region "$REGION" --output json --no-cli-pager \
  --query 'AccessPoints[].{Id:AccessPointId,State:LifeCycleState,User:PosixUser,Root:RootDirectory}'
```

- A mount timeout points first to target state, DNS, route, and NFS TCP 2049 security-group paths. Inspect target groups with `describe-mount-target-security-groups`; send changes to networking.
- A mount/access denial needs the file-system policy, client IAM role and mount options, access-point root, and UID/GID/permissions checked together. Do not fix it with broad permissions or `chmod`.
- Metadata can include sensitive directory paths. Keep those local unless needed. Even a successful mount would not prove application access; ask for existing client evidence before any new test.
- Use `describe-lifecycle-configuration` for tiering and `describe-backup-policy` for policy state. Policy enabled does not prove a successful backup. Check actual recovery points separately.
- `SizeInBytes` is metered size, not real-time client free space. Correlate throughput mode, throughput use, and I/O pressure before resizing or changing modes. For key state and access, use [security](../../security/instructions.md).

## Official sources checked

- Exa: [FSx DescribeFileSystems](https://docs.aws.amazon.com/cli/latest/reference/fsx/describe-file-systems.html).
- Context7 CLI: [FSx DescribeStorageVirtualMachines](https://docs.aws.amazon.com/cli/latest/reference/fsx/describe-storage-virtual-machines.html) and [DescribeVolumes](https://docs.aws.amazon.com/cli/latest/reference/fsx/describe-volumes.html), library `/websites/aws_amazon_cli`.
- Exa: [EFS mount troubleshooting](https://docs.aws.amazon.com/efs/latest/ug/troubleshooting-efs-mounting.html).
