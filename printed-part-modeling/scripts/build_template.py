#!/usr/bin/env python3
"""Parametric build script skeleton for a printed part.

Copy this, replace the parameters and the profile, keep the shape:

    parameters -> derived stations -> assertions -> geometry -> checks -> export

The assertions sit next to the parameters on purpose. They are the design rules
you reasoned about once, and they are what stops a later "just make it thicker"
from quietly breaking a fit three features away.

Verify the EXPORTED mesh afterwards with mesh-measure. Checking parameters only
proves your arithmetic agrees with itself.
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon

ENGINE = "manifold"

# ---------------------------------------------------------------- parameters
# One named constant per real dimension. Comment where each number came from --
# "measured", "from the doorway", "chosen" -- so a later reader knows what is
# negotiable and what is fixed by the physical world.
LENGTH      = 125.0   # measured
T_FLOOR     = 2.0     # chosen: clearance vs stiffness, see fit-and-strength.md
T_BASE      = 5.0     # chosen: enough to fully countersink the head
H_RIB       = 30.0    # measured off the part being remixed
RIB         = 10.0    # must fit the gap in the mating assembly
CHANNEL     = 37.5    # mating part + float
FILLET_RUN  = 2.0     # root fillet: wide and low keeps headroom while adding material
FILLET_RISE = 0.4
CH_TOP      = 0.5     # lead-in chamfer on rib tops
SHANK_R     = 2.30    # #8 clearance (4.17 mm major + 0.4)
HEAD_R      = 4.00
SEAT_R      = 3.50    # partial recess: narrower than the head on purpose

MATING_T, MATING_GAP, FLOOR_GAP = 35.0, 15.0, 5.0   # the physical referee

# ------------------------------------------------------------ derived stations
x0 = 0.0
x1 = x0 + CHANNEL
x2 = x1 + RIB
x3 = x2 + CHANNEL
W  = x3
RIB_X = (x1 + x2) / 2.0

# ------------------------------------------------------------------ assertions
# Each of these is a rule that was true when the part was designed and must stay
# true. Put the measured numbers in the message so a failure explains itself.
assert abs((CHANNEL + RIB + CHANNEL) - (MATING_T + MATING_GAP + MATING_T)) < 1e-9, (
    f"fit chain does not close: {CHANNEL+RIB+CHANNEL} vs "
    f"{MATING_T+MATING_GAP+MATING_T} mm")
assert T_FLOOR + FILLET_RISE <= FLOOR_GAP - 2.0, (
    f"only {FLOOR_GAP-(T_FLOOR+FILLET_RISE):.2f} mm under the mating part")
assert (RIB / 2 - SEAT_R) >= 1.5, f"recess leaves {RIB/2-SEAT_R:.2f} mm walls in a {RIB} mm rib"
assert (RIB / 2 - CH_TOP) - SEAT_R >= 0.99, "no flat ring left for the head to bear on"
assert HEAD_R <= RIB / 2, "head overhangs the rib and would foul the mating part"


# --------------------------------------------------------------------- helpers
def dedupe(pts, tol=1e-9):
    out = [p for i, p in enumerate(pts)
           if i == 0 or abs(p[0]-pts[i-1][0]) > tol or abs(p[1]-pts[i-1][1]) > tol]
    while len(out) > 1 and abs(out[0][0]-out[-1][0]) < tol and abs(out[0][1]-out[-1][1]) < tol:
        out.pop()
    return out


def frustum(r0, r1, z0, z1, n=96):
    """Watertight capped frustum on Z. Convex, so hulls of it sweep exactly."""
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    lo = np.column_stack([r0*np.cos(a), r0*np.sin(a), np.full(n, z0)])
    hi = np.column_stack([r1*np.cos(a), r1*np.sin(a), np.full(n, z1)])
    v = np.vstack([lo, hi, [[0, 0, z0]], [[0, 0, z1]]])
    c_lo, c_hi = 2*n, 2*n+1
    f = []
    for i in range(n):
        j = (i+1) % n
        f += [[i, j, n+j], [i, n+j, n+i], [c_lo, j, i], [c_hi, n+i, n+j]]
    m = trimesh.Trimesh(vertices=v, faces=np.array(f), process=True)
    m.fix_normals()
    return m


def extrude_xz_along_y(poly, y0, y1):
    """(X, Z) profile extruded along Y. Proper rotation -- a bare axis swap mirrors."""
    m = trimesh.creation.extrude_polygon(poly, height=(y1 - y0))
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
    m.apply_translation([0, y1, 0])
    return m


# ------------------------------------------------------- 1. cross-section
zc = T_FLOOR + FILLET_RISE
zt = H_RIB - CH_TOP
profile = dedupe([
    (x0, 0.0), (x3, 0.0),                                # face that sits on the bed
    (x3, zt), (x3 - CH_TOP, H_RIB),                      # far rib: outer face, top chamfer
    (x2 + CH_TOP, H_RIB), (x2, zt),                      #          inner face
    (x2, zc), (x2 - FILLET_RUN, T_FLOOR),                # root fillet into channel 2
    (x1 + FILLET_RUN, T_FLOOR), (x1, zc),                # channel 1 side
    (x1, zt), (x1 - CH_TOP, H_RIB),
    (x0 + CH_TOP, H_RIB), (x0, zt),
    (x0, 0.0),
])
poly = Polygon(profile)
assert poly.is_valid and poly.exterior.is_simple, "profile self-intersects"
part = extrude_xz_along_y(poly, -LENGTH/2, LENGTH/2)

# --------------------------------------------- 2. features (one screw per rib)
bore = frustum(SHANK_R, SHANK_R, -2.0, H_RIB + 0.05)     # overshoot: avoid coplanar faces
seat = frustum(SHANK_R, SEAT_R, H_RIB - 1.4, H_RIB + 0.05)
tool = trimesh.boolean.union([bore, seat], engine=ENGINE)
tool.apply_translation([RIB_X, 0.0, 0.0])
part = trimesh.boolean.difference([part, tool], engine=ENGINE)

# ------------------------------------------------------------------ 3. checks
part.process(validate=True)
part.fix_normals()
assert part.is_watertight, "not watertight"
assert part.is_winding_consistent, "inconsistent winding"
assert len(trimesh.graph.split(part, only_watertight=False)) == 1, "more than one body"

part.export("part.stl")
print(f"size   : {np.round(part.extents, 2).tolist()} mm")
print(f"volume : {part.volume/1000:.2f} cm^3  (~{part.volume/1000*1.24:.0f} g in PLA)")
print("\nNow verify the exported mesh with mesh-measure -- these asserts only")
print("checked the parameters, not the geometry that landed in the file.")
