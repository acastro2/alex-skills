---
name: mesh-measure
description: Measure a 3D mesh for real — pull exact dimensions, wall thicknesses, hole positions, clearances and flatness out of an STL/3MF/OBJ/PLY by ray-casting its actual triangles, instead of trusting a product listing, a CAD screenshot, or the parameters that supposedly generated it. Use this whenever someone asks how big a model is, whether a downloaded part will fit something they measured, where its screw holes are, how thick a wall or floor is, or wants a printed model checked before committing filament to it. Use it just as reliably to verify a model you generated yourself, because checking your own parameters proves nothing about the geometry that landed in the file. Also covers unpacking Bambu Studio / OrcaSlicer 3MF project files to recover settings, plate thumbnails and the designer's own notes.
---

# Measuring a mesh

A mesh file is the ground truth. Descriptions, listing text, CAD screenshots and
the script that generated the file are all secondary sources, and they disagree
with the geometry more often than people expect. When a dimension matters, cast a
ray and read it off the triangles.

This matters most in the case that feels least necessary: verifying a model you
just built. A parameter check only proves your arithmetic matches itself. It
cannot see a tessellation artefact, a boolean that removed more than you meant,
or a chamfer that ate the wall you were counting on. Those only show up when you
measure the exported file.

## The tool

`scripts/meshprobe.py` — import it, or run it directly.

```bash
python scripts/meshprobe.py part.stl                          # bbox + ASCII top view
python scripts/meshprobe.py part.stl --profile x --at 0       # heights across a line
python scripts/meshprobe.py part.stl --span x --at 0 --range 43.5 53.5   # find a hole
```

```python
from meshprobe import Probe
p = Probe("part.stl")            # up="z" by default; set up="y" for a part lying on its side

p.top(x, y)          # highest surface on a vertical ray      -> nan if the ray misses
p.bottom(x, y)       # lowest surface (0.0 means it sits flat on the bed)
p.through(x, y)      # True when the ray hits nothing at all
p.profile("x", 6, 43.5, at=0)          # (positions, heights) across a line
p.flat_run("x", 6, 43.5, 1.6)          # longest stretch actually at 1.6 -> (start, end, length)
p.span("x", 43.5, 53.5, at=0)          # the hole on that line -> (start, end, width, centre)
p.heightmap()                          # ASCII top view, good for "is this even the right shape"
```

Start with `heightmap()`. Confirming the shape is roughly what you think it is
costs one call and saves you from carefully measuring the wrong feature.

## Probe placement is the whole game

Nearly every surprising measurement is a probe in the wrong place, not a broken
model. Before believing a bad number, check it against this list.

**A ray through a hole returns `nan`, not zero.** This is correct and useful —
`through()` exists precisely so a bore can assert positively. But `nan < 0.1` is
`False` in Python, so a naive `assert p.top(x, y) < 0.1` fails on a hole that is
working perfectly. Test bores with `through()`.

**Chamfers and fillets read as "not full height."** A fin 30 mm tall with a 1 mm
top chamfer only measures 30 mm across its middle; the outer millimetre each side
ramps down. If you scan a feature edge-to-edge and filter on "below full height",
you will select the chamfers along with whatever you were hunting for. Scan the
flat interior: `lo + chamfer + eps` to `hi - chamfer - eps`.

**Recesses and counterbores pull the surface down locally.** Probing a fin's arc
profile at the exact station where a screw seat is cut reports the seat, not the
arc. Probe away from features, or exclude those stations.

**Rounded corners remove material where the plan view says there is some.** A
point 3 mm in from a corner with a 6 mm radius may be outside the part. Compute
the distance to the corner centre before trusting a `nan`.

**Scan windows leak into neighbouring features.** Skipping "the ramp at each end"
by trimming 3 mm off a scan does nothing if the ramp is 10 mm long. Derive the
trim from the actual parameter, never from a guess.

**Sampling a curve by the wrong variable distorts it.** An arc that runs
tangent-vertical at its end is badly under-sampled by uniform steps in the
horizontal axis — the chords cut straight across it. Sample by angle. This one is
a genuine model bug rather than a probe bug, and measuring is how you find it.

## Triage: is the model wrong, or is the check wrong?

When a measurement disagrees with intent, work out which one is lying **before**
changing anything. Editing a model to satisfy a broken probe is how you make a
part worse while watching the tests go green.

1. **Predict the number.** Given where the probe actually sits, what *should* the
   geometry read there? Compute it from the design equations by hand.
2. **Compare.** If the measurement matches that prediction, the model is right and
   the probe is misplaced — fix the probe. If it does not match, the model is
   genuinely wrong.
3. **Say which it was.** A run of "that was my test, not the part" is fine and
   normal. Silently rewriting probes until everything passes is not.

A worked example. A fin's arc was probed at one station and came back 8.63 mm
against an intended 7.50 mm. The prediction step showed the arc equation gives
9.62 mm at that station — so the probe was compared against the wrong reference
*and* the mesh was 1 mm below the true arc. Two faults, one number. The probe
reference was corrected, and the real bug (sampling the arc by horizontal
position instead of by angle) was fixed, dropping the error to 0.002 mm. Neither
would have been found by checking parameters.

## What to measure

For a part that has to fit something:

- **Overall size** and whether it matches the claimed envelope.
- **The mating dimension chain.** Add up the features that must equal a real
  measurement, and assert the sum, not just the pieces.
- **Every surface the mating part passes over.** Sweep the whole contact
  footprint, not one convenient point — the tallest obstruction is what matters,
  and it is usually a fillet or a fastener head rather than the flat you designed.
- **Flatness where flatness is assumed.** `flat_run` against the nominal
  thickness reports how much of a surface is genuinely flat. A "flat" floor that
  is only flat across half its width will be found here and nowhere else.
- **Hole centres,** with `span`, compared against the feature they should be
  centred in. Report the offset, signed.
- **Wall thickness left around holes** — measure from the hole edge to the
  feature edge, and treat anything under ~1 mm as a break-out risk.
- **Mesh sanity:** `is_watertight`, consistent winding, one connected body,
  positive volume. Cheap, and catches boolean failures immediately.

## Reading slicer project files

A `.3mf` is a zip. Bambu Studio and OrcaSlicer projects carry far more than
geometry, and the designer's own notes are often the fastest route to intent:

```bash
unzip -l project.3mf
unzip -p project.3mf 3D/3dmodel.model | head -50    # metadata: title, designer, description
unzip -p project.3mf Metadata/model_settings.config # per-object names, transforms
unzip -p project.3mf Metadata/project_settings.config | head -60   # slicer settings
unzip -d out project.3mf 'Metadata/*.png' 'Auxiliaries/*'          # plate + model images
```

`3D/3dmodel.model` is XML. Geometry usually lives in a referenced part under
`3D/Objects/`. The `<build><item transform="...">` matrix is the placement on the
plate, which tells you the orientation the designer intended to print in —
frequently a deliberate strength decision worth preserving.

Read the images too. A dimensioned CAD screenshot resolves ambiguity fast, though
where it conflicts with the mesh, the mesh wins.

## Related

For designing or remixing a part once you have measured it, see
`../printed-part-modeling/SKILL.md`.
