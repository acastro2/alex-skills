# Toolchain: trimesh, manifold3d, shapely

The stack that covers most printed-part work without a CAD kernel:

```python
import numpy as np, trimesh
from shapely.geometry import Polygon
ENGINE = "manifold"      # manifold3d: robust, fast, handles coplanar faces well
```

Install: `pip install trimesh manifold3d shapely numpy matplotlib`.
Booleans need `manifold3d`; without it trimesh falls back to something slower and
less reliable. Always pass `engine="manifold"` explicitly so a missing dependency
fails loudly rather than silently degrading.

## Extruding a profile along an axis

`trimesh.creation.extrude_polygon` always extrudes a 2D `(u, v)` polygon along
+Z. To get a cross-section drawn in one plane extruded along a different axis,
apply a transform — and **use a proper rotation**.

Reindexing columns to permute axes is tempting and is a trap: a swap of two axes
has determinant −1, which mirrors the part and inverts every normal. A 3-cycle
has determinant +1 and is safe.

```python
def extrude_xz_along_y(poly, y0, y1):
    """Profile drawn in (X, Z), extruded along Y. Proper rotation, normals intact."""
    m = trimesh.creation.extrude_polygon(poly, height=(y1 - y0))
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation([0, y1, 0])
    return m

def extrude_yz_along_x(poly, x_lo, x_hi):
    """Profile drawn in (Y, Z), extruded along X, via a cyclic (det +1) permutation."""
    m = trimesh.creation.extrude_polygon(poly, height=(x_hi - x_lo))
    T = np.eye(4)
    T[:3, :3] = np.array([[0, 0, 1],    # X <- extrusion
                          [1, 0, 0],    # Y <- poly u
                          [0, 1, 0]])   # Z <- poly v
    assert np.isclose(np.linalg.det(T[:3, :3]), 1.0)   # -1 would mirror the part
    m.apply_transform(T)
    m.apply_translation([x_lo, 0, 0])
    return m
```

Keep that determinant assertion. A mirrored part is easy to produce and
surprisingly hard to notice until something does not fit.

## Profile polygons

Build the cross-section as an explicit ordered point list, walking the outline
and naming each feature in a comment. It stays readable and each chamfer is one
line you can change:

```python
zc = t_floor + fillet_rise
zt = h_fin - chamfer_top
profile = [
    (x0, 0.0), (x_end, 0.0),                       # the face that sits on the bed
    (x6, zt), (x6 - chamfer_top, h_fin),           # rib outer face + lead-in chamfer
    (x5 + chamfer_top, h_fin), (x5, zt),           # rib inner face
    (x5, zc), (x5 - fillet_run, t_floor),          # root fillet down into the channel
    # ...
]
poly = Polygon(dedupe(profile))
assert poly.is_valid and poly.exterior.is_simple, "profile self-intersects"
```

Guard both conditions. A self-intersecting profile produces a mesh that looks
plausible and booleans catastrophically.

Conditional features (a flange that may be zero-width) leave duplicate points
behind, which shapely dislikes. Strip them, including the wrap-around:

```python
def dedupe(pts, tol=1e-9):
    out = [p for i, p in enumerate(pts)
           if i == 0 or abs(p[0]-pts[i-1][0]) > tol or abs(p[1]-pts[i-1][1]) > tol]
    while len(out) > 1 and abs(out[0][0]-out[-1][0]) < tol and abs(out[0][1]-out[-1][1]) < tol:
        out.pop()
    return out
```

Write the feature as `if flange > 0: pts += [...]  else: pts += [(x, 0.0)]`, so
setting a parameter to zero cleanly deletes the feature.

## Sample curves by angle, not by coordinate

Sampling an arc at uniform steps of one coordinate under-samples it wherever it
runs steeply, and the chords cut straight across the true curve. On an arc that
ends tangent-vertical this removed ~1 mm from a part — invisible in the
parameters, obvious when the mesh was measured.

```python
# WRONG near a vertical tangent: uniform steps in y chord across the arc
ys = np.linspace(flat_end, flat_end + R, 120)
arc = [(y, h - (R - np.sqrt(R**2 - (y-flat_end)**2))) for y in ys]

# RIGHT: uniform angle gives uniform chord length the whole way round
th = np.linspace(0.0, np.pi/2, 120)
arc = [(flat_end + R*np.sin(t), h - R*(1 - np.cos(t))) for t in th]
```

Same rule for fillets, rounds and any swept curve.

## Watertight frustum (cylinders, cones, countersinks)

Convex, so hulls of it sweep exactly — which the slot recipe below relies on.

```python
def frustum(r0, r1, z0, z1, n=96):
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    lo = np.column_stack([r0*np.cos(a), r0*np.sin(a), np.full(n, z0)])
    hi = np.column_stack([r1*np.cos(a), r1*np.sin(a), np.full(n, z1)])
    v = np.vstack([lo, hi, [[0,0,z0]], [[0,0,z1]]])
    c_lo, c_hi = 2*n, 2*n+1
    f = []
    for i in range(n):
        j = (i+1) % n
        f += [[i, j, n+j], [i, n+j, n+i], [c_lo, j, i], [c_hi, n+i, n+j]]
    m = trimesh.Trimesh(vertices=v, faces=np.array(f), process=True)
    m.fix_normals()
    return m
```

A cylinder is `frustum(r, r, z0, z1)`; a countersink is `frustum(shank, head, z0, z1)`.

## Exact slots by convex hull

Sweeping a **convex** body along a segment is its Minkowski sum with that
segment, which equals the convex hull of the two end positions. So an obround
slot is exact, not approximated:

```python
def swept(mesh, d, axis=1):
    a, b = mesh.copy(), mesh.copy()
    off = np.zeros(3); off[axis] = d
    a.apply_translation(-off); b.apply_translation(off)
    return trimesh.util.concatenate([a, b]).convex_hull
```

Convexity is the condition. A shank-plus-countersink profile is **not** convex
(radius jumps outward partway up), so hulling it fattens the shank. Sweep the
cylinder and the cone separately, then union:

```python
slot = trimesh.boolean.union(
    [swept(frustum(shank_r, shank_r, -2, csk_z), dy),
     swept(frustum(shank_r, head_r, csk_z, t_plate + 0.05), dy)], engine=ENGINE)
```

Overshoot cut tools ~0.05 mm past the surface they break through. Exactly
coplanar faces are the classic source of boolean artefacts.

## Rounded rectangles with per-corner radii

`buffer(-r).buffer(r)` rounds every corner the same. When corners differ, build
the outline directly:

```python
def rounded_rect(xa, xb, ya, yb, r_a0, r_b0, r_b1, r_a1, n=32):
    def arc(cx, cy, r, d0, d1):
        if r <= 1e-9:
            return [(cx, cy)]                      # r=0 collapses to a sharp corner
        t = np.linspace(np.radians(d0), np.radians(d1), n)
        return list(zip(cx + r*np.cos(t), cy + r*np.sin(t)))
    return Polygon(arc(xa+r_a0, ya+r_a0, r_a0, 180, 270) + arc(xb-r_b0, ya+r_b0, r_b0, 270, 360)
                 + arc(xb-r_b1, yb-r_b1, r_b1, 0, 90)   + arc(xa+r_a1, yb-r_a1, r_a1, 90, 180))
```

Apply as an intersection with a tall extrusion of that outline.

## Limiting a cut to part of the model

Boolean tools are cheap to aim. If a profile cut should only affect the ribs and
not a flange, extrude the cutter only across the ribs' span rather than the whole
part — far simpler than repairing the flange afterwards:

```python
part = trimesh.boolean.difference(
    [part, extrude_yz_along_x(Polygon(cutter), -5.0, x_flange_start)], engine=ENGINE)
```

## Exporting

```python
part.process(validate=True); part.fix_normals()
part.export("part.stl")
```

Check before shipping: `is_watertight`, `is_winding_consistent`, `volume > 0`,
and `len(trimesh.graph.split(part, only_watertight=False)) == 1`.

STL is float32, so a re-import differs from the in-memory mesh by ~1e-5 %. That
is rounding, not a geometry change — do not chase it.

### Writing 3MF without lxml

trimesh's 3MF exporter needs `lxml`. A minimal core-spec 3MF is a three-entry
zip, so when the dependency is missing just write it — slicers accept this:

```python
def write_3mf(mesh, path, name="part"):
    import zipfile
    v = "".join(f'<vertex x="{a:.6g}" y="{b:.6g}" z="{c:.6g}"/>' for a,b,c in mesh.vertices)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a,b,c in mesh.faces)
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US"'
             ' xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{name}</metadata>'
             '<resources><object id="1" type="model"><mesh>'
             f'<vertices>{v}</vertices><triangles>{t}</triangles>'
             '</mesh></object></resources><build><item objectid="1"/></build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0"'
            ' Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
```

This carries geometry only — no print settings. Say so when handing it over, so
nobody expects their profile to come with it.

## Rendering sections

`mesh.section(...)` returns a 3D path. Its `.to_2D()` reprojects into its own
frame, which quietly scrambles a plot that assumes your coordinates. Take the
3D vertices and drop the normal axis yourself:

```python
s = mesh.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
loops = [s.vertices[e.points][:, [0, 2]] for e in s.entities]   # (X, Z), no reprojection
```

Then draw with `matplotlib.patches.Polygon` on `aspect="equal"` axes, and overlay
the mating part as a translucent rectangle. Use the `Agg` backend so it works
headless. For an isometric view, `Poly3DCollection` with a simple dot-product
shade is enough:

```python
sh = 0.42 + 0.58*np.clip(mesh.face_normals @ np.array([0.32, -0.58, 0.75]), 0, 1)
```
