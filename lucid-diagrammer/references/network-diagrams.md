# Network Diagram Conventions

Reference for drawing network diagrams in Lucid. Load this when the user asks for any network topology, architecture, datacenter, or cloud-network diagram.

## Pick one layer — don't mix

A network diagram answers exactly one question. Decide which before drawing:

| Layer | Question it answers | Shapes you'll use |
| --- | --- | --- |
| **Physical** | Where are the cables? Which port goes where? | Racks, switches with port numbers, patch panels, cable runs |
| **Logical / L2** | What's in which VLAN/broadcast domain? | Switches, VLAN groupings, trunk links |
| **L3 / Routing** | How does traffic move between subnets? | Routers, subnets as containers, route arrows, OSPF/BGP areas |
| **Cloud / VPC** | What's in which VPC, subnet, and security group? | VPC container, subnet sub-containers, named cloud shapes |
| **Application flow** | Which services talk to which? | Service nodes, request arrows with protocol labels |
| **Security zones** | What's trusted vs. untrusted, what's in the DMZ? | Zone containers (DMZ, trust, untrust), firewall shapes |

Mixing L2 and L3 in one view makes both unreadable. If the user wants "everything," produce multiple pages in one Lucid doc, one per layer.

## Cloud architecture diagrams (the most common case)

Use Lucid's official cloud shape libraries via `namedShape` / `namedContainer`. **Never** recreate cloud icons with rectangles.

Load order:

1. Always start with the `common` resource — covers the ~30 most-used shapes per cloud.
2. Pull category-specific resources only when you need something not in `common`.

| Cloud | Library prefix | Resources to load |
| --- | --- | --- |
| AWS | `aws-2024` | `common`, then `networking`, `compute`, `storage`, `database`, `security-identity-compliance` as needed |
| GCP | `gcp-2021` | `common`, then `networking`, `compute`, `storage`, `databases` |
| Azure | `azure-2024` | `common`, then `networking`, `compute`, `storage`, `databases` |

Fetch via `lucid_get_mcp_resource("lucid://shape-libraries/<library>/<category>")`.

### VPC/VNet pattern (canonical)

```
Standard Import structure:

shapes: [
  {
    type: "namedContainer",
    className: "VirtualPrivateCloudVPCAWS2024",  // outer VPC
    boundingBox: { x: 0, y: 0, w: 900, h: 600 },
    assistedLayout: false,                        // nested containers
    children: [
      {
        type: "namedContainer",
        className: "PublicSubnetAWS2024",
        boundingBox: { x: 40, y: 60, w: 400, h: 480 },
        children: [
          { type: "namedShape", className: "ApplicationLoadBalancerAWS2024", ... },
          { type: "namedShape", className: "NATGatewayAWS2024", ... }
        ]
      },
      {
        type: "namedContainer",
        className: "PrivateSubnetAWS2024",
        boundingBox: { x: 460, y: 60, w: 400, h: 480 },
        children: [
          { type: "namedShape", className: "ECSAWS2024", ... },
          { type: "namedShape", className: "RDSAWS2024", ... }
        ]
      }
    ]
  }
]
```

Use `use_assisted_layout=false` at the top-level call when you have nested containers — assisted layout flattens nesting otherwise.

### Containment math reminder

Every child's `boundingBox` must fit *strictly* inside the parent. Cloud container shapes have header bars (icon + label) — leave ~40px top padding inside VPC/subnet containers so children don't clip the title bar.

## On-prem / datacenter patterns

Lucid's Cisco shape library covers most enterprise gear. Load `lucid://shape-libraries/` listing first to see the current library name (it changes between Cisco refreshes). Typical shapes: `Router`, `L3Switch`, `L2Switch`, `Firewall`, `LoadBalancer`, `WirelessAP`, `Server`, `WorkstationDesktop`.

### Tier conventions

Stack tiers vertically, top to bottom:

```
┌─────────────────────────────┐
│  Internet / WAN             │   ← top
├─────────────────────────────┤
│  Edge / Perimeter Firewall  │
├─────────────────────────────┤
│  Core                       │
├─────────────────────────────┤
│  Aggregation / Distribution │
├─────────────────────────────┤
│  Access                     │
├─────────────────────────────┤
│  Endpoints / Servers        │   ← bottom
└─────────────────────────────┘
```

### HA pairs

Draw firewall/router HA pairs side by side with a short horizontal line between them labeled with the HA protocol (`HSRP`, `VRRP`, `cluster sync`). Don't draw the pair as a single shape — it hides the failure mode.

## Line conventions

These conventions are not Lucid defaults — set them explicitly. They make network diagrams scannable at a glance.

| Link type | Style | Width | Label format |
| --- | --- | --- | --- |
| Physical / L1 link | solid | 2px | `10G`, `1G`, `100M` |
| L2 trunk | solid | 3px | `Trunk: VLAN 10,20,30` |
| Logical / VPN tunnel | dashed | 2px | `IPSec`, `WireGuard` |
| Control plane (OSPF/BGP) | dotted | 1px | `OSPF Area 0`, `iBGP` |
| Application request | solid with arrow | 2px | `HTTPS:443`, `gRPC:9000` |
| Bidirectional flow | solid, double-arrow | 2px | protocol on label |
| Decommissioned | dashed grey | 1px | strikethrough text |

In Lucid Standard Import, use `lineStyle: "dashed"` / `"dotted"` and set `stroke.width`. Always label lines — an unlabeled network arrow is a bug.

### Arrow direction

Network arrows almost always mean **request initiation direction**, not packet flow. `A → B` = "A initiates a connection to B." If you need to show return traffic explicitly, use a separate arrow or a double-arrow with a paired label.

### Endpoint anchoring

For shape-to-shape connections in network diagrams: when using `lucid_add_line` use `endpoint_auto_link=True`. For Standard Import, omit `position` on both endpoints — Lucid picks the cleanest attachment.

## Color conventions

Use colors as **semantic signals**, not decoration:

| Meaning | Color | Hex (default Lucid) | Hex (Attain Finance) |
| --- | --- | --- | --- |
| Production | green | `#27AE60` | `#2A9FD6` (Curious Blue) |
| Staging / non-prod | amber | `#F39C12` | `#A88B6A` (Twill Brown) |
| Untrusted / DMZ | red | `#C0392B` | `#C0392B` |
| Restricted / regulated | purple | `#8E44AD` | `#0B5394` (Venice Blue dark) |
| Decommissioned | grey | `#95A5A6` | `#95A5A6` |
| Trusted internal | blue | `#3498DB` | `#0B5394` (Venice Blue) |

When in an Attain Finance context, prefer the Attain column (cross-reference the attain-design-system skill in the attain-brand plugin).

## Labels — what to include

A network shape's label should answer: *what is it and how do I find it?* Minimal label template:

```
<hostname or service name>
<role or function>
<IP or CIDR>
```

Examples:

- `fw-edge-01 / Palo PA-5220 / 198.51.100.1`
- `app-prod-east-1 / ECS service / 10.0.40.0/24`
- `core-sw-pair / Nexus 9508 HA / 10.0.0.0/29`

Don't put log paths, ticket numbers, or owner emails in the label — those go in a separate text shape or off-page key.

## Subnet / CIDR notation

When showing subnets:

- Put the CIDR in the container title: `Public Subnet — 10.0.1.0/24`
- For multi-AZ, suffix the AZ: `Public Subnet A — 10.0.1.0/24 (us-east-1a)`
- Use `containerTitle` on `rectangleContainer` (basic) or the named cloud container's built-in title field.

## Security groups / NACLs / firewall rules

Don't draw security groups as containers around shapes — it gets messy with overlapping membership. Instead:

- Show the SG as a small annotation shape near the resource it protects.
- For a single key rule worth highlighting, add a labeled arrow: `sg-app → sg-db : tcp/5432`.
- For full rule sets, put a separate Lucid page with a table shape — don't try to fit it in the topology.

## Sizing & readability

| Diagram type | Max shapes per page | When to split |
| --- | --- | --- |
| Topology overview | ~30 shapes | Split by tier or region |
| Detailed L2/L3 | ~50 shapes | Split by site / VLAN |
| Application flow | ~20 services | Split by domain / bounded context |
| Cloud VPC | ~25 resources | Split by VPC or environment |

If you blow past these, make one summary page and link to per-region/per-VPC detail pages in the same Lucid doc (multi-page Standard Import).

## Anti-patterns

- **Spaghetti mesh** — every shape connected to every other shape. Group logically, use containers, or split into multiple views.
- **Mixing layers** — physical cables and application HTTPS flows in one diagram.
- **Unlabeled lines** — an arrow with no protocol/bandwidth/VLAN label is useless.
- **Recreating cloud icons** — always use `namedShape` from the official library.
- **Drawing HA as one box** — always show both halves of an HA pair.
- **Decoration colors** — don't make a router blue just because you like blue. Color = meaning.
- **Putting SG/NACL rules inside the topology** — separate page or annotation, not nested containers.
- **Missing CIDRs** — every subnet container must show its CIDR in the title.

## Workflow

1. **Ask which layer** the user wants if they say "draw our network" without specifying. Don't guess.
2. **Pick the right Lucid shape library**, load only the resources you need.
3. **Sketch tier/zone containers first** before placing shapes.
4. **Verify containment math** — child boxes fit strictly inside parent interiors.
5. **Apply line conventions** from the table above, including labels.
6. **Apply color semantically**, using the Attain palette when relevant.
7. **Return the edit URL** and offer PNG export.

## Example: "Diagram our prod AWS VPC with ALB → ECS → RDS"

1. Load `lucid://shape-libraries/aws-2024/common` (covers VPC, subnets, ALB, ECS, RDS, NAT GW).
2. Outer container: `namedContainer` `VirtualPrivateCloudVPCAWS2024`, title includes VPC CIDR.
3. Two sub-containers: `PublicSubnetAWS2024` (10.0.1.0/24) and `PrivateSubnetAWS2024` (10.0.10.0/24).
4. In public: ALB + NAT GW.
5. In private: ECS service + RDS.
6. Lines: ALB → ECS (solid, label `HTTPS:443`), ECS → RDS (solid, label `tcp/5432`), ECS → NAT GW (dashed, label `egress`).
7. Color: green/Venice Blue on production resources, grey on the NAT GW.
8. `use_assisted_layout=false` (nested containers).
