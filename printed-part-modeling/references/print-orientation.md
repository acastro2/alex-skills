# Print orientation

Orientation is a structural decision, not a packing decision. It is usually the
single biggest lever on whether a printed part survives, and it costs nothing to
get right at design time.

## Layer bonds are the weak axis

FDM parts are strong within a layer and weaker between layers — typically 40–70 %
of in-layer strength, depending on material and temperature. So:

> Orient the part so layer lines run **across** the load path, never along the
> plane where it wants to separate.

The failure mode to design against is a feature peeling off its base along a
single layer boundary. If a rib rises from a plate and the load tries to bend the
rib off, then printing the part flat puts a layer boundary exactly at that joint,
in exactly the direction the load pulls. Standing the part on end instead means
each layer contains the *whole cross-section* — plate and rib together — so the
joint is continuous extruded plastic rather than a bond.

That is the reasoning to apply generally: **ask what a single layer contains.**
The best orientation is usually the one where each layer holds the complete
cross-section of the loaded joint.

## Reading a designer's chosen orientation

In a slicer project file, the `<build><item transform="...">` matrix records the
placement on the plate. When a downloaded model arrives rotated onto its side or
end, that is often a deliberate strength decision — check the description before
"fixing" it. Preserving it costs nothing; overriding it silently can halve the
part's strength.

## What each orientation costs

**Flat on the bed** — best adhesion, no supports for upward walls, fastest. But
any feature rising from the base has a layer boundary at its root.

**On end / on edge** — the strong choice for ribbed and bracket-like parts. Costs:
a small footprint on a tall print, so it is tippy and needs a brim; and any
feature growing sideways as the print rises becomes an overhang.

Mitigating a flat print instead of reorienting: a generous root fillet (3–4 mm)
substantially increases the bonded cross-section at the joint. Worth doing when
flat printing is required for other reasons, but it is a mitigation, not a fix.

## Self-supporting profiles

A part standing on end only prints support-free if its cross-section grows slowly
as the print rises. Check the worst rate, do not eyeball it:

```
overhang_per_layer = d(width) / d(height) * layer_height
```

Keep that under about one nozzle width (0.4 mm) per layer and it bridges cleanly.
Above it, expect droop.

This is why a rounded lead-in on a rib end is worth designing in. A tangential arc
adds material gradually, so a part that would otherwise need supports prints
clean. The steepest point of an arc is at its tangent-vertical end, so evaluate
there rather than at the middle.

A convex arched top is self-supporting in the direction it curves away. A concave
one is not.

## First layer and adhesion

Standing a part on end makes the first layer a thin slice of the cross-section —
sometimes only a few mm² per feature. **Use a brim.** Say so explicitly in a
handover, since it is easy to forget and a 125 mm tall part on a 5 mm wide footing
will detach.

If you remove a large feature (a mounting flange, say), the first layer shrinks
with it. Worth mentioning when handing over a revision, because the previous print
may have succeeded without a brim and this one may not.

## Supports

Prefer designing supports away over enabling them:

- Chamfer or fillet an overhang up to a self-supporting angle (~45°).
- Replace a horizontal hole's circular top with a teardrop or an obround.
- Split a part and print two halves in ideal orientations.

Where supports are unavoidable, keep them off cosmetic and mating surfaces —
support scarring changes a fit dimension by more than a tolerance budget usually
allows.

## Holes and slots

Vertical holes print undersize and slightly polygonal; a first article often needs
a drill or a 0.1–0.2 mm allowance.

Horizontal holes need bridging across the top. An obround with a rounded top is
self-supporting, which is one reason slots are often a better choice than round
holes on a vertically-printed wall — they also give assembly adjustment. Pick the
slot direction deliberately: it should point along the axis you actually need to
adjust, and if the fit is fully determined by geometry, a slot buys nothing and a
round hole gives more bearing area.

## Handing over

State the orientation, the reason, and the slicer settings that matter:

> Stand it on end, 125 mm tall — each layer is then the full cross-section, so
> the rib roots are continuous plastic instead of a layer bond in exactly the
> direction the load pushes. Brim on, no supports needed, ~135 g in PLA.

Giving the reason means they can make the call themselves next time, and will not
"helpfully" lay it flat to save time.
