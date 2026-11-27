# Multi-plate builds: plan, test fast, adapt

Learned on an 11-plate, 78 h, 4 kg build (nursery diaper station, P2S, PLA). Read this when a design spans
more than one plate or more than a day of printing.

## Order plates fail-fast

Plate numbers are the print order, so choose them. Put first the plate that tests the riskiest unproven thing,
in the shortest print. A failure then costs an hour, not the 15 h plate after it.

1. **Fit coupons** (minutes): every clearance the design depends on (dovetails, press fits, snaps).
2. **Small functional parts** (latches, grips, rails, dowels): flex, nut seats, straightness.
3. **Short parts that prove a decision** (a lightning-infill step: stand on it).
4. **The smallest big box**: warp on the plate, nut traps, bolt holes.
5. Mechanism hosts (the bay a drawer runs in), then the long boxes, then cosmetic parts.

Give each plate one "check before the next plate" line in the README table. Put coupons into the same project
as plate 1, so there is one file to print from.

## Coupon loop

- Coupon: one short length of the real profile plus one slider per clearance (0.15/0.20/0.25/0.30 mm per flank),
  marked with 1-4 raised dots (at least 1 mm high). Pick the tightest that slides freely without rocking; on a
  long real part (a 246 mm rail) prefer the looser of two equal ones.
- Put the clearance on ONE side of the joint only (the female channel), so a coupon result changes one part
  and one plate, and the male parts can print before the result.
- Prove the change landed: rebuild, then compare the part's volume at old and new clearance against a hand
  estimate (2 channels x 245 mm x ~30 mm of flank x 0.05 mm = ~750 mm3; measured 767). Then rerun the
  interference check in every pose and the DFM check.
- Note how the coupon printed. A coupon printed hotter or colder than the real parts measures a different fit.

## Weight and time: measure, do not guess

- Slice the real part to answer "is X kg right?" or "what does this save?". A guess (ribs instead of infill saves
  250 g) was wrong; the slice showed the ribs cost about the same.
- Box-like parts are mostly perimeters: infill changes save little. Wall count is the big lever
  (3 instead of 4 walls: -0.6 kg / -5 h on this build).
- Lightning infill supports only the top surfaces. It fits parts loaded straight down (steps). FEA cannot prove
  infill, so test the printed part under load and keep a fallback (gyroid 12 %).
- Per-object settings in one project: structural boxes 3 walls/15 % gyroid; light parts 3 walls/12 %; grips and
  rails 5 walls/40 % (rails printed on their side get an 8 mm brim); latches and dowels solid.

## Strength checks that held up

- PLA, layers loaded across (Z): yield about 28 MPa, E about 2060 MPa. Report the target safety factor and the
  real one; never round a low one up.
- A part whose bend is stopped by a gap (a latch tooth that hits the slot roof) is judged by strain at the gap
  (about 1.5 t y / L^2), not by force safety factor.
- Refine the mesh where the peak sits before you trust it; a coarse mesh hid a wrong direction of motion.
- When a number misses the target, say so with the number, and give the physical test (luggage-scale pull)
  that settles it.

## Hand-off checklist

- All plates slice with 0 warnings; time and grams per plate in the README.
- Every plate's G-code has the real printer start (plate detection, AMS load) and the right bed type and bed
  temperature (see `bambu-studio.md`).
- One Bambu Studio instance with the current project loaded. The user presses Print.
- List what is not yet verified (full-length fits, latch feel, load tests) with the test that settles each.
