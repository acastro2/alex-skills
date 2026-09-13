# Fit and strength

Numbers for deciding a dimension, and quick estimates for defending it. The point
of the estimates is not precision — it is turning "that feels thin" into "that is
50 MPa against a 55 MPa yield, so it has no margin", which is a statement the
user can actually make a decision about.

## Clearances

| Situation | Gap |
|---|---|
| Press fit, assembled with force | 0.0 to −0.1 mm interference |
| Snug fit, assembled by hand, no play wanted | 0.1–0.2 mm |
| Parts that must slide or rotate | 0.3–0.5 mm |
| Captive nut / bolt head pocket | 0.2–0.4 mm on the flats |
| Guide that only stops something swinging | 1–2.5 mm of float |
| Clearance over a moving object's path | as much as you can spare |

Printers are not identical: a first article can come out 0.1–0.3 mm tight on
internal features from elephant's foot and over-extrusion. Where a fit is
critical, say which dimension to check on the first print and which parameter to
change.

## Wall thickness

- **1 mm minimum** around any hole. Below that it splits when the fastener is
  tightened, and it will not survive a countersink breaking out sideways.
- **1.2–2 mm** for a wall doing structural work — that is 3–5 perimeters at a
  0.4 mm nozzle, so it prints solid with no infill.
- A thin sheet spanning a gap is an excellent **tie** and a poor **beam**. If it
  only has to hold two features in relative position, thin is fine. If it has to
  transmit a moment, thickness matters — cubically (see below).

## Fasteners

| Screw | Major dia | Clearance hole | Flat head dia | Countersink depth |
|---|---|---|---|---|
| #6 | 3.5 mm | 3.9 mm | 6.9 mm | 1.7 mm |
| #8 | 4.2 mm | 4.6 mm | 8.0 mm | 1.9 mm |
| #10 | 4.8 mm | 5.2 mm | 9.4 mm | 2.3 mm |
| M3 | 3.0 mm | 3.4 mm | 6.0 mm | 1.5 mm |
| M4 | 4.0 mm | 4.5 mm | 8.0 mm | 2.0 mm |
| M5 | 5.0 mm | 5.5 mm | 10.0 mm | 2.5 mm |

Clearance hole ≈ major diameter + 0.4 mm. Countersink depth ≈
`(head_dia − shank_dia) / 2` for an 82–90° head.

**Head styles matter more than people expect.**

- *Flat (countersunk)* seats on a cone and sits flush. The standard choice where
  anything passes over it.
- *Bugle* — drywall and construction screws — has a shallower **curved**
  underside. It will seat in an 82° countersink but bears on the rim and stands
  ~0.5 mm proud. Fine where nothing passes over; do not promise flush.
- *Pan / button* sits entirely proud. Perfectly good where there is headroom, and
  it saves you spending wall thickness on a recess.

**Do not bury a head that does not need burying.** A recess costs wall thickness
you may not have. Before adding one, check whether anything actually passes over
that surface — if not, let the head sit proud and keep the material.

**The recess must fit the feature, not just the head.** A 10 mm rib cannot take
an 8.6 mm counterbore: that leaves 0.7 mm walls, which split. Two ways out:

- *Full counterbore*, needing `head_dia + 2×1.5 mm` of feature width. Head fully
  buried, bearing on the pocket floor.
- *Partial conical recess* narrower than the head. The head sinks until its taper
  meets the rim and stands slightly proud — most of the benefit, no widening.
  A 7.0 mm recess in a 10 mm rib takes an 8 mm head to ~0.8 mm proud instead of
  2.2 mm, while keeping 1.5 mm walls.

Also check what is left **at the top surface**: chamfers eat into it. A rib with
a 9 mm flat top between chamfers and a 7 mm recess leaves only a 1 mm ring for
the head to bear on. Assert that ring, not just the wall.

## Load paths

Before sizing anything, trace how force gets from where it is applied to where it
is reacted. Most sizing mistakes are a misread load path rather than bad
arithmetic.

Ask: where does the force enter, what is the nearest anchor, and what has to
carry it in between? Anchors are screws, and *large stiff features* — a tall rib
is a deep beam and carries far more than its thickness suggests.

**Removing a nearby anchor lengthens the path.** Taking screws off a flange means
a load applied there must now travel through whatever spans to the next anchor,
often a thin floor. That change alone took one floor from 15 MPa to 52 MPa with
no dimension altered.

## Plate bending

For a plate carrying a moment from a feature to an anchor, work per unit length
along the feature:

```
w   = F / L                       load per mm of feature length      (N/mm)
m   = w * arm                     moment per mm at the critical section (N·mm/mm)
Z   = t**2 / 6                    section modulus per mm             (mm³/mm)
σ   = m / Z
```

Note `Z` goes as **t²**. Thickening a floor 1.6 → 2.0 mm cuts stress ~36 %; going
to 2.4 mm halves it. This is why small thickness changes buy so much, and why
thin floors fail suddenly rather than gradually.

For a tipping load applied at height `h` on a feature standing `arm` away from
the anchor line, the uplift couple is `R = F * h / arm`, and the moment in the
plate at distance `d` from the bearing edge is `R * d`.

Sanity check with two arrangements before believing a result. Removing a flange
once shortened the arm *and* the moment arm by the same amount — 33.1 → 32.3 MPa,
essentially no change — which is not what intuition predicts.

## Ribs are deep beams

A rib standing `h` tall and `t` thick, running length `L`, bending in its tall
direction:

```
Z = t * h**2 / 6
```

A 10 mm × 30 mm rib gives `Z = 1500 mm³` — enormous. This is why a *single*
fastener partway along a ribbed part is often fine: the rib carries load along
its length to that anchor at well under 1 MPa. Check it before adding fasteners
that buy nothing.

Whereas the same rib resisting a sideways push bends about its *thin* axis,
`I = h·t³/12`, which is small — but it is bonded to the plate along its whole
length, so it transfers into the plate rather than spanning.

## Material numbers

| Material | Tensile yield | Notes |
|---|---|---|
| PLA | 50–60 MPa | Stiff, creeps under sustained load, softens ~55 °C |
| PLA+ / Tough PLA | 45–55 MPa | Much better layer adhesion and impact |
| PETG | 45–55 MPa | Tougher, more flexible, good outdoors |
| ABS/ASA | 40–45 MPa | Heat and UV resistant, warps |
| Nylon | 40–80 MPa | Tough and wear resistant, absorbs moisture |

These are along the layers. **Across layers assume 40–70 % of it**, which is
exactly why orientation is a structural decision.

Treat a computed stress within ~30 % of yield as having no margin, and say so.
Sustained load needs more headroom than occasional load, because PLA in
particular creeps.

## Presenting a trade-off

When a change trades one property for another, give both numbers and a
recommendation, then let the user choose. "Floor at 1.6 mm gives 3.4 mm of
clearance at ~50 MPa against a 55 MPa yield; at 2.0 mm it is 3.0 mm clearance at
32 MPa" is a decision they can make. "That might be a bit thin" is not.

If they pick the aggressive option after hearing the number, build it — and note
in the handover which single parameter to change if it ever fails.
