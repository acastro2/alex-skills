# Hybrid connectivity: AWS-side evidence

Use this when the path includes Direct Connect or Site-to-Site VPN. This is diagnosis, not a router build guide. Complete the [shared preflight](../../references/cli-operating.md), identify the connection owner and use the affected Region.

```bash
set -euo pipefail
PROFILE="<confirmed-profile>"
REGION="<confirmed-region>"
CONNECTION_ID="<discovered-dx-connection-id>"
aws directconnect describe-connections --connection-id "$CONNECTION_ID" \
  --profile "$PROFILE" --region "$REGION" \
  --query '{Connections:connections[].{Id:connectionId,Owner:ownerAccount,State:connectionState,Region:region,Bandwidth:bandwidth},NextToken:nextToken}' \
  --output json --no-cli-pager
aws directconnect describe-virtual-interfaces --connection-id "$CONNECTION_ID" \
  --profile "$PROFILE" --region "$REGION" \
  --query '{Interfaces:virtualInterfaces[].{Id:virtualInterfaceId,Owner:ownerAccount,State:virtualInterfaceState,Type:virtualInterfaceType,Gateway:virtualGatewayId,DXGateway:directConnectGatewayId,Peers:bgpPeers[].{Id:bgpPeerId,State:bgpPeerState,Status:bgpStatus}},NextToken:nextToken}' \
  --output json --no-cli-pager
```

If no connection ID is known, run the first call without that filter in the approved owner scope. If a response returns `NextToken`, continue with the service's documented `--next-token` until absent. Do not suppress partial-result tokens.

For a known VPN:

```bash
set -euo pipefail
PROFILE="<confirmed-profile>"
REGION="<confirmed-region>"
VPN_ID="<discovered-vpn-id>"
aws ec2 describe-vpn-connections --vpn-connection-ids "$VPN_ID" \
  --profile "$PROFILE" --region "$REGION" \
  --query 'VpnConnections[].{Id:VpnConnectionId,State:State,TGW:TransitGatewayId,VGW:VpnGatewayId,CustomerGateway:CustomerGatewayId,Tunnels:VgwTelemetry[].{Status:Status,Changed:LastStatusChange,AcceptedRoutes:AcceptedRouteCount}}' \
  --output json --no-cli-pager
```

Do not dump complete Direct Connect or VPN responses. `authKey`, `customerRouterConfig`, `CustomerGatewayConfiguration` and tunnel options can expose BGP authentication or pre-shared keys. Projection limits display, not the API response in CLI memory.

## Prove the path

Compare connection, virtual interface, BGP/tunnel state and metrics in one incident window. Then follow the gateway/attachment into [TGW and exact-route checks](investigation.md#transit-gateway-route-tables-and-exact-routes). Check propagation, associations, longest-prefix selection and the return path with the network owner. An `available` connection or `UP` tunnel does not prove the required prefix is reachable.

Carrier/router-side state is separate evidence. Do not restart a tunnel, replace keys, change BGP or fail over traffic until the owner approves the exact impact and recovery plan. Verify the application path after any approved change, not just tunnel state.

## Sources

Checked through Exa on 2026-09-04:
- [Connections](https://docs.aws.amazon.com/cli/latest/reference/directconnect/describe-connections.html)
- [Virtual interfaces and sensitive fields](https://docs.aws.amazon.com/cli/latest/reference/directconnect/describe-virtual-interfaces.html)
- [VPN connections and sensitive fields](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-vpn-connections.html)
