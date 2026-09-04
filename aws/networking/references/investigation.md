# Network Investigation

Read the shared [AWS CLI operating guide](../../references/cli-operating.md) first.
Use its preflight, evidence, pagination, and failure rules. The commands below add only
network-specific steps.

## Cross-account ownership

Start with the shared guide's
[Sweep accounts and Regions without hiding failures](../../references/cli-operating.md#sweep-accounts-and-regions-without-hiding-failures)
workflow. It owns profile discovery, caller proof, and the coverage record. Do not copy its
preflight here. Never build the profile list from a resource name or an assumed account
naming rule.

After that proof, put only approved profiles in `PROFILES`. This network-specific sweep
discovers TGWs without guessing ownership. It preserves each service failure, leaves AWS
CLI auto-pagination on, and keeps each result small.

```bash
set -u
set -o pipefail
REGION=replace-with-region
EVIDENCE_DIR=replace-with-private-evidence-directory
PROFILES=(replace-with-profile-a replace-with-profile-b)
mkdir -p "$EVIDENCE_DIR"

for profile in "${PROFILES[@]}"; do
  if result=$(aws ec2 describe-transit-gateways \
      --profile "$profile" \
      --region "$REGION" \
      --query 'TransitGateways[].{Id:TransitGatewayId,Owner:OwnerId,State:State,AssociationDefault:Options.AssociationDefaultRouteTableId,PropagationDefault:Options.PropagationDefaultRouteTableId}' \
      --output json \
      --no-cli-pager 2>&1); then
    jq -cn \
      --arg profile "$profile" \
      --arg region "$REGION" \
      --argjson resources "$result" \
      '{Profile:$profile,Region:$region,Status:"ok",TransitGateways:$resources}'
  else
    jq -cn \
      --arg profile "$profile" \
      --arg region "$REGION" \
      --arg error "$result" \
      '{Profile:$profile,Region:$region,Status:"failed",Operation:"ec2:DescribeTransitGateways",Error:$error}'
  fi
done | tee "$EVIDENCE_DIR/tgw-ownership.ndjson"
```

An empty successful list is different from a failed profile. If more Regions are in scope,
run the full approved profile list in each Region and keep a separate evidence file.

## Transit Gateway route tables and exact routes

Use the owner profile and exact TGW ID found above. Do not select a route table from a tag
alone.

```bash
set -euo pipefail
PROFILE=replace-with-confirmed-owner-profile
REGION=replace-with-region
TGW_ID=replace-with-transit-gateway-id
TARGET_PREFIX=replace-with-exact-prefix
EVIDENCE_DIR=replace-with-private-evidence-directory
mkdir -p "$EVIDENCE_DIR"

aws ec2 describe-transit-gateway-route-tables \
  --profile "$PROFILE" \
  --region "$REGION" \
  --filters "Name=transit-gateway-id,Values=$TGW_ID" \
  --query 'TransitGatewayRouteTables[].{RouteTableId:TransitGatewayRouteTableId,TransitGatewayId:TransitGatewayId,State:State,DefaultAssociation:DefaultAssociationRouteTable,DefaultPropagation:DefaultPropagationRouteTable}' \
  --output json \
  --no-cli-pager \
  > "$EVIDENCE_DIR/tgw-route-tables.json"

jq -e 'length > 0' "$EVIDENCE_DIR/tgw-route-tables.json" >/dev/null

jq -r '.[].RouteTableId' "$EVIDENCE_DIR/tgw-route-tables.json" \
| while IFS= read -r route_table_id; do
    aws ec2 search-transit-gateway-routes \
      --profile "$PROFILE" \
      --region "$REGION" \
      --transit-gateway-route-table-id "$route_table_id" \
      --filters "Name=route-search.exact-match,Values=$TARGET_PREFIX" \
      --query 'Routes[].{Destination:DestinationCidrBlock,PrefixList:PrefixListId,Type:Type,State:State,Attachments:TransitGatewayAttachments[].{AttachmentId:TransitGatewayAttachmentId,ResourceId:ResourceId,ResourceType:ResourceType}}' \
      --output json \
      --no-cli-pager \
      > "$EVIDENCE_DIR/tgw-exact-route-$route_table_id.json"
  done
```

Check every route table file, including empty arrays. A route can be static or propagated,
active or blackhole, and tied to one or more attachments. Keep those fields together.
Do not turn `route-search.exact-match` into an effective-path claim. Use a separate,
approved longest-prefix investigation when the question is where an address will flow.

## Route 53 and Resolver

### Hosted-zone ownership

Hosted zones are account-scoped and global. `--region` makes CLI context explicit; it does
not make the hosted zone Regional. Include the trailing dot in the exact zone name.

```bash
set -u
set -o pipefail
REGION=replace-with-cli-region
EVIDENCE_DIR=replace-with-private-evidence-directory
PROFILES=(replace-with-profile-a replace-with-profile-b)
ZONE_NAME=replace-with-exact-zone-name-ending-in-dot
mkdir -p "$EVIDENCE_DIR"

for profile in "${PROFILES[@]}"; do
  if result=$(aws route53 list-hosted-zones-by-name \
      --profile "$profile" \
      --region "$REGION" \
      --dns-name "$ZONE_NAME" \
      --query "HostedZones[?Name=='$ZONE_NAME'].{Id:Id,Name:Name,Private:Config.PrivateZone,RecordCount:ResourceRecordSetCount}" \
      --output json \
      --no-cli-pager 2>&1); then
    jq -cn \
      --arg profile "$profile" \
      --argjson zones "$result" \
      '{Profile:$profile,Status:"ok",HostedZones:$zones}'
  else
    jq -cn \
      --arg profile "$profile" \
      --arg error "$result" \
      '{Profile:$profile,Status:"failed",Operation:"route53:ListHostedZonesByName",Error:$error}'
  fi
done | tee "$EVIDENCE_DIR/hosted-zone-ownership.ndjson"
```

Do not stop at the first same-name zone. Public and private zones can share a name. Select
the exact hosted-zone ID and confirm its `Private` value before reading records.

```bash
PROFILE=replace-with-confirmed-owner-profile
REGION=replace-with-cli-region
HOSTED_ZONE_ID=replace-with-hosted-zone-id
RECORD_NAME=replace-with-exact-record-name-ending-in-dot

aws route53 list-resource-record-sets \
  --profile "$PROFILE" \
  --region "$REGION" \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --query "ResourceRecordSets[?Name=='$RECORD_NAME'].{Name:Name,Type:Type,TTL:TTL,Values:ResourceRecords[].Value,Alias:AliasTarget.{Target:DNSName,ZoneId:HostedZoneId,EvaluateHealth:EvaluateTargetHealth},Routing:{SetIdentifier:SetIdentifier,Weight:Weight,Region:Region,Failover:Failover,MultiValue:MultiValueAnswer}}" \
  --output json \
  --no-cli-pager
```

### Resolver discovery

Resolver endpoints, rules, and rule associations are Regional. Repeat these commands for
every approved profile and Region. Keep misses and failures separate.

```bash
PROFILE=replace-with-profile
REGION=replace-with-region
RULE_DOMAIN=replace-with-exact-forwarded-domain-ending-in-dot

aws route53resolver list-resolver-endpoints \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'ResolverEndpoints[].{Id:Id,Name:Name,Direction:Direction,Status:Status,HostVpcId:HostVPCId,SecurityGroups:SecurityGroupIds,IpAddressCount:IpAddressCount,Protocols:Protocols}' \
  --output json \
  --no-cli-pager

aws route53resolver list-resolver-rules \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query "ResolverRules[?DomainName=='$RULE_DOMAIN'].{Id:Id,Name:Name,DomainName:DomainName,Status:Status,RuleType:RuleType,ResolverEndpointId:ResolverEndpointId,OwnerId:OwnerId,ShareStatus:ShareStatus}" \
  --output json \
  --no-cli-pager
```

Trace each returned endpoint security group through the
[security-group topology](#security-group-topology) workflow. After selecting the returned
rule ID, find every VPC association in that account and
Region. Do not assume a shared rule is associated with the VPC that needs it.

```bash
RULE_ID=replace-with-resolver-rule-id

aws route53resolver list-resolver-rule-associations \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query "ResolverRuleAssociations[?ResolverRuleId=='$RULE_ID'].{Id:Id,Name:Name,RuleId:ResolverRuleId,VpcId:VPCId,Status:Status,StatusMessage:StatusMessage}" \
  --output json \
  --no-cli-pager
```

## VPC endpoint and S3 bucket-policy alignment

Do not assume the endpoint and bucket have the same owner. Confirm separate profiles and
Regions before reading either policy.

```bash
set -euo pipefail
ENDPOINT_PROFILE=replace-with-confirmed-endpoint-profile
ENDPOINT_REGION=replace-with-endpoint-region
VPC_ENDPOINT_ID=replace-with-vpc-endpoint-id
BUCKET_PROFILE=replace-with-confirmed-bucket-profile
BUCKET_REGION=replace-with-bucket-region
BUCKET_NAME=replace-with-bucket-name
EVIDENCE_DIR=replace-with-private-evidence-directory
mkdir -p "$EVIDENCE_DIR"

aws ec2 describe-vpc-endpoints \
  --profile "$ENDPOINT_PROFILE" \
  --region "$ENDPOINT_REGION" \
  --vpc-endpoint-ids "$VPC_ENDPOINT_ID" \
  --query 'VpcEndpoints[0].{Id:VpcEndpointId,Owner:OwnerId,Type:VpcEndpointType,VpcId:VpcId,Service:ServiceName,ServiceRegion:ServiceRegion,State:State,RouteTableIds:RouteTableIds,SubnetIds:SubnetIds,SecurityGroups:Groups[].GroupId,NetworkInterfaces:NetworkInterfaceIds,PrivateDnsEnabled:PrivateDnsEnabled,PolicyDocument:PolicyDocument}' \
  --output json \
  --no-cli-pager \
| jq -e 'if (.PolicyDocument | type) == "string" then .PolicyDocument |= fromjson else . end' \
  > "$EVIDENCE_DIR/vpc-endpoint-before.json"

aws s3api get-bucket-policy \
  --profile "$BUCKET_PROFILE" \
  --region "$BUCKET_REGION" \
  --bucket "$BUCKET_NAME" \
  --query Policy \
  --output text \
  --no-cli-pager \
| jq -e '{Version:.Version,Statement:[.Statement[] | {Sid:.Sid,Effect:.Effect,Principal:.Principal,Action:.Action,Resource:.Resource,Condition:.Condition}]}' \
  > "$EVIDENCE_DIR/bucket-policy-before.json"
```

Compare these exact facts:

1. Endpoint state, type, service, VPC, and route tables or subnets.
2. Endpoint-policy effects, principals, actions, and resources for the requested S3 call.
3. Bucket-policy allows and explicit denies for the same principal, action, and resource.
4. Any bucket-policy `aws:SourceVpce` or `aws:SourceVpc` condition against the endpoint's
   returned ID and VPC ID.

This local check finds literal endpoint-ID references. It does not evaluate IAM policy and
does not prove access by itself.

```bash
jq --arg endpoint_id "$VPC_ENDPOINT_ID" \
  '[paths(scalars) as $path | select(getpath($path) == $endpoint_id) | $path]' \
  "$EVIDENCE_DIR/bucket-policy-before.json"
```

A missing bucket policy is not the same as a wrong account. Preserve the AWS error.

A bucket-policy deny that uses `aws:SourceVpce` can lock out every request that does not use the exact endpoint, including AWS console requests. Before an approved policy mutation:

1. Verify the endpoint ID, owner, VPC, state, service, and tested caller path from live output.
2. Save and validate the complete before policy and a CLI-compatible rollback file.
3. Keep a tested recovery session that reaches S3 through the named endpoint. Do not depend on the console for rollback.
4. Show the exact policy diff and rollback command, then get confirmation.
5. Change only one policy, verify the intended call and one denied out-of-path call, and roll back from the tested recovery path if either result differs.

If an approved owner changes either policy, rerun the same exact commands into `*-after.json` and use a local `diff -u` for evidence. Do not change the endpoint policy and bucket policy together or widen both until the request works.

## Security-group topology

Start from one exact security-group ID, account, and Region. Save the complete projected
rules and every attached ENI. Both commands retain automatic pagination.

```bash
set -euo pipefail
PROFILE=replace-with-confirmed-profile
REGION=replace-with-region
SECURITY_GROUP_ID=replace-with-security-group-id
EVIDENCE_DIR=replace-with-private-evidence-directory
mkdir -p "$EVIDENCE_DIR"

aws ec2 describe-security-groups \
  --profile "$PROFILE" \
  --region "$REGION" \
  --group-ids "$SECURITY_GROUP_ID" \
  --query 'SecurityGroups[0].{GroupId:GroupId,Name:GroupName,Owner:OwnerId,VpcId:VpcId,Ingress:IpPermissions[].{Protocol:IpProtocol,FromPort:FromPort,ToPort:ToPort,IPv4:IpRanges[].{Prefix:CidrIp,Description:Description},IPv6:Ipv6Ranges[].{Prefix:CidrIpv6,Description:Description},PrefixLists:PrefixListIds[].{Id:PrefixListId,Description:Description},ReferencedGroups:UserIdGroupPairs[].{Owner:UserId,GroupId:GroupId,VpcId:VpcId,PeeringId:VpcPeeringConnectionId,PeeringStatus:PeeringStatus,Description:Description}},Egress:IpPermissionsEgress[].{Protocol:IpProtocol,FromPort:FromPort,ToPort:ToPort,IPv4:IpRanges[].{Prefix:CidrIp,Description:Description},IPv6:Ipv6Ranges[].{Prefix:CidrIpv6,Description:Description},PrefixLists:PrefixListIds[].{Id:PrefixListId,Description:Description},ReferencedGroups:UserIdGroupPairs[].{Owner:UserId,GroupId:GroupId,VpcId:VpcId,PeeringId:VpcPeeringConnectionId,PeeringStatus:PeeringStatus,Description:Description}}}' \
  --output json \
  --no-cli-pager \
  > "$EVIDENCE_DIR/security-group-before.json"

aws ec2 describe-network-interfaces \
  --profile "$PROFILE" \
  --region "$REGION" \
  --filters "Name=group-id,Values=$SECURITY_GROUP_ID" \
  --query 'NetworkInterfaces[].{Id:NetworkInterfaceId,Type:InterfaceType,Status:Status,VpcId:VpcId,SubnetId:SubnetId,Description:Description,PrivateIp:PrivateIpAddress,RequesterManaged:RequesterManaged,Attachment:{InstanceId:Attachment.InstanceId,DeviceIndex:Attachment.DeviceIndex,Status:Attachment.Status},Groups:Groups[].GroupId}' \
  --output json \
  --no-cli-pager \
  > "$EVIDENCE_DIR/security-group-enis-before.json"
```

List referenced groups with their returned owner fields before following them:

```bash
jq -r \
  '(.Ingress[]?, .Egress[]?) | .ReferencedGroups[]? | [.Owner,.GroupId,.VpcId,.PeeringId,.PeeringStatus] | @tsv' \
  "$EVIDENCE_DIR/security-group-before.json" \
| sort -u
```

For each peer, confirm its owner profile and Region, then run the same exact
`describe-security-groups --group-ids` shape against that peer ID. Do not silently try
random profiles. An account boundary or stale reference is part of the finding.

If an approved owner changes the group, capture the same group and ENI projections after
the change. Compare ingress, egress, referenced-group owners, and attachments. A rule diff
without the ENI topology is incomplete.

## Evidence basis and current references

These workflows reflect repeated Attain operations: multi-profile TGW, Route 53, and
Resolver discovery; exact TGW route searches; and security-group and S3 policy inspection.
The shared guide requires profile failures to stay visible instead of being redirected
away.

Current command shape and pagination were checked against the official AWS CLI references:

- [AWS CLI pagination](https://docs.aws.amazon.com/cli/latest/userguide/pagination.html)
- [Describe Transit Gateways](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-transit-gateways.html)
- [Describe TGW route tables](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-transit-gateway-route-tables.html)
- [Search TGW routes](https://docs.aws.amazon.com/cli/latest/reference/ec2/search-transit-gateway-routes.html)
- [List hosted zones by name](https://docs.aws.amazon.com/cli/latest/reference/route53/list-hosted-zones-by-name.html)
- [List record sets](https://docs.aws.amazon.com/cli/latest/reference/route53/list-resource-record-sets.html)
- [List Resolver endpoints](https://docs.aws.amazon.com/cli/latest/reference/route53resolver/list-resolver-endpoints.html)
- [List Resolver rules](https://docs.aws.amazon.com/cli/latest/reference/route53resolver/list-resolver-rules.html)
- [List Resolver rule associations](https://docs.aws.amazon.com/cli/latest/reference/route53resolver/list-resolver-rule-associations.html)
- [Describe VPC endpoints](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-vpc-endpoints.html)
- [Get an S3 bucket policy](https://docs.aws.amazon.com/cli/latest/reference/s3api/get-bucket-policy.html)
- [Describe security groups](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-security-groups.html)
- [Describe network interfaces](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-network-interfaces.html)
