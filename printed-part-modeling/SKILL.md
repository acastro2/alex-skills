---
name: printed-part-modeling
description: Design, adapt, or repair 3D-printable parts as parametric code. Use for new physical parts, remixes of STL/3MF/OBJ/STEP models, or fitting a part to real measurements, even when printing is not named. Verify the exported mesh. For measurement-only tasks use mesh-measure; general printer, filament, or slicer advice alone does not trigger this skill.
---

# Modelling printed parts

A part that has to fit a real object is not an art problem, it is a constraint
problem with a physical referee. The workflow below is built around that: pull
real numbers out of whatever exists, express the fit as arithmetic, and let a
measurement of the finished mesh — not your own parameters — decide whether you
got it right.

Work in **millimetres** throughout, since that is what every slicer and mesh
format assumes.

## The loop

1. **Measure what already exists** — the part being remixed, and the object it
   must fit.
2. **Write the fit down as a constraint chain**, and check it closes.
3. **Build it parametrically**, one named variable per real dimension.
4. **Encode the design rules as assertions** in the build script.
5. **Verify by measuring the exported mesh.**
6. **Render it and look at it.**
7. **Iterate by changing parameters,** never by editing the mesh.

Steps 4 and 5 are what make later changes cheap. Skipping them feels faster on
the first version and is much slower by the third.

## 1. Measure first

Never model against a description. Product listings round, CAD screenshots
dimension the sketch rather than the solid, and "40 mm" in a listing has an even
chance of being the gap rather than the rib. Use `../mesh-measure/SKILL.md` to
get real numbers off the actual mesh, and read any slicer project metadata — the
designer's notes and chosen print orientation are usually load-bearing.

From the user, get the measurements the part must satisfy and **the tolerance
that matters**. "It's about 5 mm" and "it's exactly 5 mm" lead to different
parts. Ask for the numbers that change the design, then design to them.

## 2. Make the fit a constraint chain

Write the mating dimensions as an equation and confirm it closes before modelling
anything. For a guide holding two 35 mm panels with a 15 mm gap between them:

```
lane + rib + lane  ==  35 + 15 + 35  ==  85 mm
```

Pick the interior split from that total (`37.5 + 10 + 37.5`), so each panel gets
2.5 mm of float and the rib sits centred in the gap. Put the equation in the
script as an assertion — then a later "make the rib thicker" automatically shows
you what it costs the lanes, instead of silently breaking the fit.

Separate the two kinds of dimension, because people conflate them and it changes
the whole design:

- **Clearance** — how much room the mating part needs to pass. Governs anything
  underneath or alongside the moving object.
- **Engagement** — how much of your feature actually does the retaining job.

They are often independent. A guide rib beside a door is not limited by the
door's floor gap at all; only material *under* the door is. Getting this
backwards leads to solving the wrong problem, so state explicitly which surfaces
the mating part passes over.

## 3. Build parametrically

Never edit mesh vertices directly. Write a script where every real dimension is a
named constant, so a change request is a one-line edit and a rebuild.

`scripts/build_template.py` is a working skeleton: parameters, derived stations,
assertions, a 2D profile extruded along an axis, boolean features, and export to
both STL and 3MF. Copy it and replace the geometry.

The general shape that handles most parts: **draw the cross-section as a 2D
polygon and extrude it**, then boolean features in. Ribbed, channelled, extruded
and bracket-like parts are nearly all one profile plus a few cuts. Reach for
lofts and sweeps only when a profile genuinely cannot express the shape.

See `references/toolchain.md` for the trimesh/manifold/shapely mechanics that are
easy to get subtly wrong — axis permutations that mirror your part, exact swept
slots, curve sampling, and writing a 3MF without extra dependencies.

## 4. Assert the design rules

Every rule you reason about once should become an assertion, in the build script,
next to the parameters. They cost one line and they catch the regression three
changes later when you have forgotten the rule existed.

```python
# A countersink must sit entirely on the flat part of the flange: it has to clear
# the edge chamfer one side and the rib fillet the other, or the head breaks out.
flat_lo, flat_hi = rib_x + fillet, width - edge_chamfer
assert min((screw_x - csk_r) - flat_lo, flat_hi - (screw_x + csk_r)) >= 1.0, (
    f"countersink wall too thin on a {flat_hi - flat_lo:.1f} mm flat")
```

Worth asserting on almost any part: the fit chain closes; minimum wall around
every hole; nothing intrudes into the moving part's envelope; a fastener head has
somewhere to bear; the thing you call "flat" is flat. Write the failure message
with the measured numbers in it, so a failure explains itself.

## 5. Verify against the exported mesh

**Re-measure the file you just wrote.** A parameter check only proves your
arithmetic is self-consistent; it cannot see tessellation error, an over-eager
boolean, or a chamfer that ate a wall. Load the exported STL with
`../mesh-measure/SKILL.md` and check the things that actually matter: the fit
chain, the clearance under every mating surface, hole positions and their offsets
from where they should be, remaining wall thicknesses, watertightness, and a
single connected body.

Two habits make this pay off:

- **Sweep envelopes, do not spot-check.** Slide the mating part across its whole
  float range and take the worst clearance. The tallest obstruction is rarely
  where you would have poked.
- **Triage every failure before touching the model.** Most early failures are
  misplaced probes, and "fixing" the model to satisfy a bad probe makes the part
  worse. The triage procedure and the standard probe traps are in
  `../mesh-measure/SKILL.md`.

## 6. Look at it

Numbers miss things a picture catches instantly. Render an isometric view and —
more useful — a **cross-section with the mating part drawn in**, so clearances
are visible rather than asserted. `matplotlib` with the mesh section is enough;
no GUI needed. `references/toolchain.md` has the section-plotting recipe,
including the trap that silently reprojects your section into the wrong plane.

When you change something structural, render the before and after on the same
axes. It communicates the change better than any paragraph.

## 7. Iterating on feedback

Real feedback arrives as consequences, not dimensions: *the door sticks*, *this
lip is in the way*, *the screw head sticks up*. Convert it into a parameter
change, then re-run the whole verification — a change made for one reason
routinely breaks something else three features away.

Two things to hold onto while iterating:

- **Re-measure before agreeing.** When told a feature is wrong, check it. It may
  already be correct, and then the real request is something else — worth
  discovering before you "fix" a part that was fine. Report what you measured.
- **Say what a change costs.** Removing a mounting flange lengthens a load path;
  thinning a floor buys clearance and spends strength. Give the number, make the
  change they asked for, and let them decide. See
  `references/fit-and-strength.md` for the quick estimates that make this
  concrete rather than hand-wavy.

## Design rules of thumb

Detail lives in the references; the headlines:

- **Clearance:** ~0.2 mm for a snug press, 0.3–0.5 mm for parts that must slide,
  1–2 mm of float for a guide that only needs to stop something swinging.
- **Walls:** at least 1 mm of material around any hole; 1.2–2 mm for a structural
  wall; a thin sheet spanning a gap is fine as a tie and poor as a beam.
- **Fasteners:** clearance hole ≈ screw major diameter + 0.4 mm. A countersink
  needs roughly `(head_dia - shank_dia) / 2` of depth. If the head does not need
  to sit flush, do not spend wall thickness burying it.
- **Print orientation is a structural decision, not a packing decision.** Layer
  bonds are the weak axis, so orient the part to put layer lines across the load
  path. See `references/print-orientation.md`.

## References

- `references/toolchain.md` — trimesh/manifold3d/shapely recipes and the sharp edges
- `references/fit-and-strength.md` — clearances, fastener tables, load-path estimates
- `references/print-orientation.md` — layer direction, supports, first-layer adhesion
- `scripts/build_template.py` — copyable parametric build script
- `../mesh-measure/SKILL.md` — measuring real geometry and verifying your output
