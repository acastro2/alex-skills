---
name: lucid-diagrammer
description: Author and edit Lucid diagrams via the Lucid MCP server. Use when the user wants to create a flowchart, org chart, mind map, sequence diagram, swimlane/BPMN, ERD, AWS/GCP/Azure architecture diagram, network topology, UML class diagram, wireframe, or any other Lucid document; or wants to edit, restyle, share, or export an existing Lucid doc. Encodes the Lucid Standard Import spec gotchas (containers, swimlanes, endpoints, assistedLayout) and applies Attain Finance brand defaults when the user is in an Attain context.
---

# Lucid Diagrammer

## When to use this skill

Use this skill whenever the user asks to:

- Create a new Lucid document (flowchart, ERD, mind map, org chart, sequence diagram, BPMN, UML class diagram, swimlane process, cloud architecture, wireframe, etc.)
- Edit shapes, lines, colors, or text in an existing Lucid document
- Generate a Lucid diagram from a CSV, PlantUML markup, or structured prompt
- Share, export (PNG), or fetch images from a Lucid document
- Pair Lucid with another MCP (e.g., "share this Lucid doc via Slack")

Do NOT use this skill for:

- Generic mermaid/PlantUML rendering with no Lucid involvement
- Image generation that doesn't end up in a Lucid doc

## Tool decision tree

Pick the most specialized tool — it does layout work for you. Fall back to the general spec only when necessary.

| User intent | Tool | Why |
| --- | --- | --- |
| Org chart from people/managers | `lucid_create_org_chart` | Auto-layout, handles hierarchy |
| Hierarchical topic tree | `lucid_create_mind_map` | Auto-radial layout |
| Sequence diagram (interactions over time) | `lucid_create_sequence_diagram` | Takes PlantUML, auto-styled in Lucid blue |
| Anything else (flowchart, ERD, BPMN, architecture, wireframe, swimlane) | `lucid_create_diagram_from_specification` | Full control via Standard Import JSON |
| Edit existing doc | `lucid_fetch` first → then `lucid_add_block` / `lucid_add_line` / `lucid_edit_item` / `lucid_delete_items` | Need item IDs before editing |
| Export as image | `lucid_export_document_as_PNG` | |
| Pull image attached to a shape | `lucid_fetch_item_image` | |
| Share with people/links | `lucid_share_document_with_collaborators` / `lucid_create_document_share_link` | |
| Find existing docs | `lucid_search` | |

**Always preview the result.** After creating or editing, return the document edit URL so the user can verify.

## Required pre-flight for Standard Import

Before calling `lucid_create_diagram_from_specification` you **must** have already loaded `lucid://diagram-specification` in the current session (it's enormous — only load once). Same rule for `lucid_create_sequence_diagram` → `lucid://sequence-diagram-specification`.

If you haven't loaded the relevant spec yet, call `lucid_get_mcp_resource` first. Do not guess shape type names or container property shapes — the API validates strictly and returns 400 on unknown types.

## Standard Import gotchas (memorize these)

These are the failure modes I keep hitting. Bake them into every spec.

### Containers

1. **Containment is by bounding box, strictly.** Every child shape's `boundingBox` must fit *entirely* inside the container's interior. A shape whose box clips the container edge is NOT contained — assisted layout will leave it stranded. Pad on all four sides.
2. **Swimlanes/BPMN pools have a `titleBar`.** Children must fit inside the lane's interior (which excludes `titleBar.height` and any lane headers), not the pool's outer rectangle.
3. **`assistedLayout` lives on the container shape**, not on individual lanes. Lane objects only accept `title`, `width`, `headerFill`, `laneFill`.
4. **Container titles**: `rectangleContainer`, `roundedRectangleContainer`, `circleContainer`, `pillContainer` support `containerTitle`. Brace/bracket/diamond/swimLanes do not.
5. **Containers never carry text** — use `containerTitle` or put a text shape inside.

### assistedLayout flag

- Default is `false`. Most of the time you want `true` on containers so Lucid neatens positions.
- Set `false` ONLY for:
  - Geographic/spatial layouts (positions carry meaning)
  - Floor plans, wireframes
  - Containers nested in other containers
- The top-level `use_assisted_layout` param in `lucid_create_diagram_from_specification` is separate from the per-container `assistedLayout` field. Typical patterns:
  - Plain flowchart, no containers: `use_assisted_layout=true`
  - Swimlane diagram: `use_assisted_layout=false`, swimLanes container `assistedLayout=true`
  - Geographic map: `use_assisted_layout=false`, no `assistedLayout` anywhere

### Swimlanes & BPMN pools

The `width` property is named misleadingly:

- `vertical: true` → lanes are **columns**. `width` = horizontal width. Sum of lane widths must equal `boundingBox.w`.
- `vertical: false` → lanes are **rows**. `width` = the row's **height**. Sum must equal `boundingBox.h`.

`swimLanes.lanes[]` requires `title`, `width`, `headerFill`, `laneFill` for each lane (all four). `bpmnPool.lanes[]` requires `title`, `width`, `laneFill`.

### Lines & endpoints

- **Endpoint `style` is the decoration at THAT endpoint**, not the line direction. For an arrow from A → B: `endpoint1.style: "none"`, `endpoint2.style: "arrow"`.
- **Position rule**: specify `position` on BOTH endpoints or NEITHER. Omitting both makes a "smart line" that auto-picks attachment points — usually what you want for shape-to-shape connections. Specifying one but not the other will fail.
- When using `lucid_add_line` (live edit tool, not Standard Import), strongly prefer `endpoint_auto_link=True` for shape endpoints. It picks the optimal side and re-routes on move/resize. Only set explicit `position_x`/`position_y` if the user asks for a specific anchor — never default to `0.5, 0.5` because the line will overlap shape text.
- `lineEndpoint.position` is a **number** 0–1 (NOT an object).

### Shape special properties

- `text` shapes don't accept `style`.
- `hotspot` doesn't accept `text`.
- `lucidCard` doesn't accept `text` — use `title`/`description`/`status`/etc.
- `umlClass` doesn't accept `text` — use `title`/`properties`/`methods`.
- `image` requires `image: {type, url}` AND `stroke`.
- `stickyNote` requires a `style` property.
- `sparkFrame` uses `title` instead of `text`.
- `braceNote` puts `rightFacing` and `braceWidth` at the **top level**, not nested under `shape`.
- `predefinedProcess` puts `sideWidth` at the top level.
- `polyStar` nests `{numPoints, innerRadius}` under `shape`.
- `or` and `summingJunction` reject `text`.

### Text rules

- No emojis. They render as black boxes.
- All colors are hex with `#` prefix.
- Numbers are numeric, booleans are booleans — no string-wrapping.
- **Standard Import strips newlines.** A `text` field of `"Line 1\nLine 2"` in the JSON spec collapses to `"Line 1 Line 2"` on a single line and overflows the box. For multi-line labels, either (a) keep the label one short line, (b) split into multiple stacked text shapes, or (c) create with one-liner text and post-edit each shape via `lucid_edit_item` (whose `text` parameter DOES preserve newlines, different code path).

### Z-index

Shapes draw in array order. Later shapes render in front. If a shape should sit behind others, put it earlier in the array.

### Size cap

`document.json` is capped at 2MB. For large diagrams, strip whitespace from the JSON string before passing it in.

## Visual quality — verify before declaring done

Pixel-perfect positions are hard to get right blind. **Always export a PNG and look at it** before claiming a diagram is done.

```
lucid_export_document_as_PNG(document_id=..., page=1)
```

Common visual bugs to look for (each has a root cause and a fix pattern):

| Symptom | Root cause | Fix pattern |
| --- | --- | --- |
| Line labels overlap each other along one edge | Multiple lines converge on the same anchor point (e.g. top-center of a container) | Anchor each line to a distinct `position_x` on the target (0.1, 0.3, 0.7, 0.9), not the default center |
| Line label sits inside a container's title bar | Endpoint `position_y=0` puts the line on the container header | Anchor to `position_y` of the title bar height as fraction of container height (e.g. `0.15` for a 40px title on a 220px container), or terminate on a child shape instead |
| Named-shape captions collide horizontally | AWS/GCP shapes are ~80px wide but their captions are 100-150px — gap < 60px causes overlap | Space named cloud shapes at least 150px apart horizontally |
| Container title overlaps inner shapes | Container height too tight; named-container header eats ~40-50px from top | Add ≥ 50px top padding inside named containers before placing children |
| Text appears as run-on instead of multi-line | Standard Import strips `\n` (see Text rules above) | Single-line text OR create then `lucid_edit_item` with newlines |
| Edit batch returns 400 on child + parent move | Race condition: parallel edits processed child before parent — child placed outside parent's old bounds | Edit parent FIRST in a separate call, then children. Never parallel-edit parent + child positions. |

### Iteration limit — when to rebuild instead of edit

If 2 PNG export rounds haven't fixed the layout, **stop tweaking and rebuild from scratch** with proper spacing baked in. Iterative `lucid_edit_item` calls trying to nudge pixels are diminishing returns — Lucid does auto-adjustments on shape boundaries that fight your edits. A clean Standard Import rebuild with corrected spacing is faster than a 4th edit pass.

## Named shape libraries (cloud architecture diagrams)

For AWS / GCP / Azure architecture diagrams, **always** use `namedShape` / `namedContainer` with the official `className` — never recreate cloud icons with basic shapes.

1. Start with `lucid://shape-libraries/aws-2024/common` (or `gcp-2021/common`, `azure-2024/common`) — gives you the ~30 most-used shapes.
2. If you need something not in `common`, read the relevant category resource, e.g. `lucid://shape-libraries/aws-2024/compute`.
3. Each resource lists `id` (the `className`), `label`, and `defaultFillColor`.
4. Containers like `VirtualPrivateCloudVPCAWS2024` have `isContainer: true` — place service shapes inside their bounding box to visually nest.

## Sequence diagrams (PlantUML)

`lucid_create_sequence_diagram` takes PlantUML markup. Lucid auto-styles in blue — don't add color directives unless the user explicitly wants overrides.

**Don't use these** (parse errors):

- `skinparam ...`
- `activate X #color`
- `destroy`, `newpage`, preprocessor `!` directives
- `collections`, `queue` participants
- Lost-message `->x`
- Dividers `== ==`, `...`, `return`, `ref over`
- `else` outside `alt` blocks

**Participant trick**: don't write `participant "Alice" as Alice` — when display and alias match, just write `participant Alice`.

**Arrow colors** must replace exactly one dash: `A -[#FF0000]> B` ✓, `A --[#FF0000]-> B` ✗.

## Brand defaults (Attain Finance context)

When the user is working in an Attain Finance context (read the attain-design-system skill in the attain-brand plugin for the full system), apply these defaults instead of Lucid's:

- **Primary fill**: Venice Blue `#0B5394` (or check DESIGN.md for the exact token)
- **Secondary fill**: Curious Blue `#2A9FD6`
- **Accent**: Twill Brown for highlighted nodes
- **Stroke**: dark blue or neutral grey, `width: 2`
- **Text color**: white on dark fills, near-black on light fills
- **Font**: leave to canvas default (Lucid will pick its own; Avant Garde is a presentation-only font)

When the user is NOT in an Attain context, use Lucid defaults — don't impose styling unless asked.

## Workflow

1. **Clarify scope** if ambiguous: diagram type, audience, whether to add to an existing doc or create new.
2. **Pick the right tool** from the decision tree above.
3. **Load required spec resources** if using Standard Import or sequence diagrams (only once per session).
4. **For architecture diagrams**: load the relevant `shape-libraries` resource(s) first.
5. **For network/topology diagrams**: load `references/network-diagrams.md` for layer conventions, line/color semantics, cloud + on-prem patterns, and sizing rules.
6. **Build the spec / call the tool.** Validate containment math (bounding boxes) before calling.
7. **Return the edit URL** to the user. Offer to export as PNG if useful.
8. **For edits**: always `lucid_fetch` first to get item IDs. Never guess IDs.

## Examples

### "Create a flowchart of our deployment pipeline"

→ `lucid_create_diagram_from_specification` with `use_assisted_layout=true`, no containers, use `terminator` shapes for start/end, `process` for steps, `decision` for gates.

### "Make an org chart from this CSV"

→ `lucid_create_org_chart`. Parse the CSV into `[{id, name, managerId, role}]` nodes.

### "Diagram the auth flow between User, Web App, API, DB"

→ `lucid_create_sequence_diagram` with PlantUML. Use `actor User`, `participant "Web App" as app`, `database DB`.

### "Show our AWS architecture: ALB → ECS → RDS in a VPC"

→ Load `lucid://shape-libraries/aws-2024/common`. Use `namedContainer` for the VPC, `namedShape` for ALB/ECS/RDS inside it. `use_assisted_layout=false` because VPC is a nested container.

### "In my IT Escalation doc, make all decision blocks red with bold white text"

→ `lucid_fetch` the doc → filter for items where type is `decision` → `lucid_edit_item` each one with `fill_color="#C0392B"`, `text_color="#FFFFFF"`, `bold=true`.

## Anti-patterns

- Don't call `lucid_create_diagram_from_specification` without first loading `lucid://diagram-specification`.
- Don't recreate AWS/GCP/Azure shapes with rectangles — use named shapes.
- Don't set explicit `position_x: 0.5, position_y: 0.5` on line endpoints — it overlaps shape text. Use `auto_link=true` or omit position.
- Don't put `assistedLayout` on individual lane objects — it goes on the container.
- Don't put text in containers — use `containerTitle` or a child text shape.
- Don't include emoji in any text field.
- Don't guess shape `type` names — they're validated and 400 on miss.
- **Don't declare a diagram done without a PNG export check.** What looks right in JSON often isn't.
- **Don't parallel-edit a container and its children's positions.** Move the parent first, wait, then move the children.
- **Don't pack named cloud shapes closer than 150px horizontally.** Their captions are wider than the icons.
- **Don't try to fix layout problems with more than 2 rounds of `lucid_edit_item`.** Rebuild instead — auto-arrange fights edits.
