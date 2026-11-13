---
name: isoscene
description: Draw polished isometric scenes (gradient blocks, glow, brand logos, Lucide glyphs, animated flow lines) as self-contained SVG for websites, case studies and decks, in the style of sigilant.io and cisoai.au. Use when asked for an isometric diagram, hero image, scene or illustration of a system, or to change one of the existing scenes. Not for validated architecture, sequence, data-flow or state diagrams where accuracy matters more than the look; that is archify.
---

# isoscene

A small Python library (no dependencies) that writes isometric scenes as one SVG file: blocks with
gradient faces, rounded silhouettes, edge highlights and coloured glow; logos and icons on the top
faces; glowing paths with moving pulses; scan ripples; a dark radial backdrop. It drew the six
sigilant.io scenes, the sigilant.io hero and the cisoai.au case-study picture.

The repository is this skill's folder. Examples are in `examples/`, the library in `isoscene/`.

## Workflow

1. **Sketch the story first, in words**: what flows from where to where. One idea per scene, left
   to right or back to front, 4 to 12 blocks. Labels go in the page's HTML beside the picture,
   never as text in the SVG (it won't scale, translate or read on a phone).
2. **Write a scene script** (start from the closest example), in the project that will use the
   picture (for example `tools/scenes/` or `tools/isometric/`), so it can be re-run later:
   ```python
   import sys
   sys.path.insert(0, os.path.expanduser("~/.agents/skills/isoscene"))   # import os first
   from isoscene import *

   s = Scene()
   s.ring(0, 0, 3.4, op=0.08)                                   # backdrop rings
   s.ring(0, 0, 5.6, color="5B7CFA", op=0.30, dash="0.12 0.12")
   s.path([(-4.0, 0.5, 0), (0, 0.5, 0)])                        # ground path, pulses flow along it
   s.box(-5.0, 0, 0, 1.05, 1.05, 0.78, ICE, logo="claude", lw=0.66, r=0.14)
   s.box(-1.8, -1.8, 0, 3.6, 3.6, 0.45, NAVY2, order=(0, 0), r=0.16, glow=0.25)
   open(sys.argv[1], "w", encoding="utf-8").write(s.render())
   ```
3. **Render and look**: `python -m isoscene.preview OUT.svg OUT.png --phone`, then read both PNGs.
   Check stacking (a block drawn over one in front of it), logos the right way up and legible, and
   nothing cut off at the edges. Iterate.
4. **Publish** the SVG and bump its `?v=` cache-buster wherever it is referenced. For a deck, use
   the PNG (PowerPoint does not animate SVG).

## Coordinates

- World units: `x` runs down-right, `y` runs down-left, `z` is up. `P(x, y, z)` projects to the page.
- Smaller `x + y` is further back. A block's top face reads as a square for `a == b`.
- `render()` fits everything drawn into the canvas, so absolute positions don't matter, only
  relative ones. Rings and the backdrop are not part of the fit.

## API (from isoscene import *)

`Scene()` then:

| Call | What it draws |
|---|---|
| `box(x0, y0, z0, a, b, h, col, order=None, logo=None, lw=0.7, glyph=None, r=0.09, glass=False, inner=None, glow=0.32, ground=True)` | A block `a × b × h` from corner `(x0, y0, z0)`. `col` is a palette. `logo` is a name from `LOGOS`; `glyph` is `(viewBox, inner_svg)` drawn on the top face, `lw` wide. `r` rounds the silhouette. `glow` is opacity of the coloured halo (0 = none). `ground=False` for blocks standing on another block (no floor shadow). Returns the top-centre point. |
| `path(pts, order=-90, color="5AA9FF", flow=True, dash=None, halo=True, pulse=0.05)` | A line through world points. `flow` animates white pulses along it; `halo` is the soft glow; `dash` like `"0.12 0.12"`; bigger `pulse` = longer pulses. Grey + dashed + `flow=False` reads as "blocked/inactive". |
| `ripple(cx, cy, z, R, order, color="5AA9FF", n=3, dur=3.0, within=None)` | Rings spreading from a point: a scan. `within=(x0, y0, x1, y1)` clips them to a surface. |
| `ring(cx, cy, R, color="FFFFFF", op=0.12, w=0.025, dash=None)` | A ground circle in the backdrop. |
| `side_glyph(x0, y, z1, w, glyph, order)` | A glyph upright on a block's left face (a sign on the side), so the top logo stays visible. |
| `plane(o, u, v, inner, order, w=1, h=1)` | Any SVG `inner` flat on a world plane: text, windows, key grids or icons on any face, including tilted planes. `o` is the origin, `u`, `v` world vectors; local `(w,0)` lands at `o+u`, `(0,h)` at `o+v`. Top face: `u=(a,0,0)`, `v=(0,b,0)`. Left face (`y = y0+b`): `o=(x0, y0+b, z1)`, `u=(a,0,0)`, `v=(0,0,-h)`. Right face (`x = x0+a`): `o=(x0+a, y0+b, z1)`, `u=(0,-b,0)`, `v=(0,0,-h)`; a positive `y` step there would mirror text. |
| `render(w=1200, h=760, pad=0.35, bg=True)` | The SVG string. `bg=False` for a transparent background (the hero sits on the page's own background). |

Palettes (top light/dark, left light/dark, right light/dark, glow): `ICE` (white blocks, the
default for products and logos), `NAVY2` (platforms), `BLUE2` (tiles, active), `TAG2` (white top,
blue sides: highlighted or a person), `GOLD2` (keys, secrets), `RED2` (stop, alert, kill),
`GREY2` (off, unknown, unclaimed), `DARK2` (servers), `STRIPE2` (white, for striped gates).

Logos (`LOGOS`, `logo=` name): claude, openai, copilot, sap, workday, salesforce, servicenow,
youtube, x, ycombinator. Add one by dropping its SVG in `isoscene/logos/` and a line in
`logos.py` (use the brand's official mark, Simple Icons 13.21.0 for monochrome brand marks).

Glyphs: `KEY`, `SEAL`, `VAULT`, `CODE`, `OWNER`, `PERSON_T`, `POWER_T`, `LOCK_T`, `QMARK`,
`SCAN`. `upright(glyph)` turns a glyph to read upright on a top face. For anything else use
`lucide(inner_markup, colour="0B5CC9")` with the elements copied from
`https://cdn.jsdelivr.net/npm/lucide-static@0.468.0/icons/<name>.svg` (already upright).

`flat` is the original flat-shaded style (`flat.Scene`, `flat.WHITE`, ...), kept for old scenes.

## Stacking (`order`)

Shapes are sorted by `order`. The default for a box is `(x0 + a/2 + y0 + b/2, z0)`, which is right
for blocks standing apart on the ground. Set it by hand when blocks touch or stand on others:

- Platform: `order=(0, 0)`; things on it: `order=(0, 10 + x + y)` so they all draw after it.
- Paths on the ground: the default `-90` (under every block). A path on a platform's top:
  `order=(0, 5)` with `z` = the platform's height + 0.02.
- Something leaning on a block's side: a tuple just after that block's own order.

## Style that has worked

- Keep blocks low: agents about 0.75 to 0.8 high, systems about 1.1. Tall blocks look clumsy.
- One accent per scene: the thing the scene is about glows more (`glow` 0.45 to 0.6), the rest 0.18 to 0.3.
- Put a status (lock, alert) on the side of a block with `side_glyph`, not on top, so the product logo stays readable.
- Use `plane()` for names printed on slabs and detail on faces instead of raw SVG.
- Show activity with motion: `path` pulses for flow, `ripple` for scanning, grey dashed lines for stopped.
- People are a `TAG2` block with a person glyph, not a figure.
- Check at 390 px wide: logos under about 0.55 `lw` become unreadable on a phone.
- In a page, show the SVG with `<img>` (animations still play); keep labels and legends as HTML.

## Examples

- `examples/sigilant_scenes.py OUTDIR`: six scenes (shared key, register, blocked, kill switch, audit chain, discovery).
- `examples/sigilant_hero.py OUTDIR`: a wide hero, still and animated (tokens that move, turn green/red/amber).
- `examples/cisoai_case_study.py OUT.svg`: sources → AI platform → outputs, with Lucide glyphs.

`python tests/test_examples.py` renders every example and checks the SVG is well formed.
