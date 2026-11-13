"""plane(): put any SVG content flat on any world plane. Run: python3 -I tests/test_plane.py"""
import math, os, re, sys
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from isoscene import Scene, ICE, P, C30  # noqa: E402


def matrix_of(markup):
    m = re.search(r'matrix\(([^)]*)\)', markup)
    assert m, "plane() output must use a matrix() transform"
    return [float(v) for v in re.split(r"[ ,]+", m.group(1).strip())]


def apply(mx, p, q):
    a, b, c, d, e, f = mx
    return (a * p + c * q + e, b * p + d * q + f)


def close(u, v, tol=1e-3):
    return abs(u[0] - v[0]) < tol and abs(u[1] - v[1]) < tol


def test_maps_local_points_to_projected_world_points():
    s = Scene()
    o, u, v = (1.0, 2.0, 0.5), (0.0, 1.5, 0.0), (0.0, 0.0, -0.8)   # a left face, v pointing down
    s.plane(o, u, v, '<rect width="1" height="1"/>', order=5)
    order, markup = s.shapes[-1]
    assert order == 5
    mx = matrix_of(markup)
    for p, q in [(0, 0), (1, 0), (0, 1), (1, 1), (0.3, 0.7)]:
        world = tuple(o[i] + p * u[i] + q * v[i] for i in range(3))
        assert close(apply(mx, p, q), P(*world)), (p, q)


def test_top_face_matrix_is_the_standard_one():
    s = Scene()
    s.plane((0, 0, 1), (1, 0, 0), (0, 1, 0), "<g/>", order=1)
    a, b, c, d, e, f = matrix_of(s.shapes[-1][1])
    assert close((a, b), (C30, 0.5)) and close((c, d), (-C30, 0.5))
    assert close((e, f), P(0, 0, 1))


def test_documented_side_faces_read_left_to_right():
    # the SKILL.md recipes: text along u must run rightward on screen (not mirrored)
    for o, u, v in [((0, 2, 1), (2, 0, 0), (0, 0, -1)),      # left face
                    ((2, 2, 1), (0, -2, 0), (0, 0, -1))]:    # right face
        s = Scene()
        s.plane(o, u, v, "<g/>", order=1)
        a, b, c, d, _, _ = matrix_of(s.shapes[-1][1])
        assert a > 0, ("mirrored", u)
        assert a * d - b * c > 0, ("flipped", u)


def test_corners_join_the_fit():
    s = Scene()
    n = len(s.pts)
    s.plane((0, 0, 0), (2, 0, 0), (0, 0, 3), "<g/>", order=1, w=1, h=1)
    pts = s.pts[n:]
    for want in [P(0, 0, 0), P(2, 0, 0), P(0, 0, 3), P(2, 0, 3)]:
        assert any(close(p, want) for p in pts), want


def test_w_h_scale_the_local_box():
    # w,h = size of the content's local box; u,v span that whole box
    s = Scene()
    o, u, v = (0, 0, 0), (1, 0, 0), (0, 1, 0)
    s.plane(o, u, v, "<g/>", order=1, w=100, h=50)
    mx = matrix_of(s.shapes[-1][1])
    assert close(apply(mx, 100, 0), P(1, 0, 0))
    assert close(apply(mx, 0, 50), P(0, 1, 0))


def test_render_is_well_formed():
    s = Scene()
    top = s.box(0, 0, 0, 2, 2, 0.3, ICE)
    s.plane((0.2, 0.2, top[2] + 0.01), (1.6, 0, 0), (0, 1.6, 0),
            '<text x="5" y="30" font-size="20">Kernel &amp; Runtime</text>', order=(0, 20), w=100, h=100)
    minidom.parseString(s.render(bg=False))


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("PASS", name)
            except Exception as ex:  # noqa: BLE001
                fails += 1; print("FAIL", name, type(ex).__name__, ex)
    sys.exit(1 if fails else 0)
