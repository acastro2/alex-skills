"""Small isometric scenes in the hero's style: the primitives of deck-build/isometric/scene.py as a library."""
import math, re
from .logos import get as _logos
LOGOS = _logos()
C30 = math.cos(math.pi / 6)


def P(x, y, z=0.0):
    return ((x - y) * C30, (x + y) * 0.5 - z)


WHITE = ("FFFFFF", "DCE4EF", "C3D0E2", "AEBCD0")
NAVY = ("1C2C47", "14213D", "0E1726", "none")
TILE = ("3FA9FF", "1286E0", "0B5CC9", "none")
LIT = ("FFFFFF", "1286E0", "0B5CC9", "1499FE")
GREY = ("8A929C", "5B6678", "3E4653", "2A2F38")
GOLD = ("F0CF7A", "D9B36C", "B38F3C", "none")
RED = ("FF6B70", "E5484D", "B2363A", "none")


class Scene:
    def __init__(s):
        s.shapes = []
        s.pts = []  # projected points of everything drawn, for the fit

    def poly(s, pts, fill, stroke="none", sw=0, extra=""):
        pr = [P(*p) for p in pts]
        s.pts += pr
        d = " ".join(f"{a:.4f},{b:.4f}" for a, b in pr)
        st = "none" if stroke == "none" else "#" + stroke
        return f'<polygon points="{d}" fill="#{fill}" stroke="{st}" stroke-width="{sw}" stroke-linejoin="round" {extra}/>'

    def box(s, x0, y0, z0, a, b, h, col, order=None, logo=None, lw=0.7, glyph=None):
        top, left, right, edge = col
        x1, y1, z1 = x0 + a, y0 + b, z0 + h
        svg = (s.poly([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], left, edge, 0.012)
               + s.poly([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], right, edge, 0.012)
               + s.poly([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], top, edge, 0.012))
        if logo or glyph:
            X, Y = P(x0, y0, z1)
            m = (a - lw) / 2
            vb, inner = LOGOS[logo] if logo else glyph
            svg += (f'<g transform="matrix({C30:.5f},0.5,{-C30:.5f},0.5,{X:.4f},{Y:.4f})">'
                    f'<svg x="{m:.4f}" y="{(b - lw) / 2:.4f}" width="{lw}" height="{lw}" viewBox="{vb}" '
                    f'preserveAspectRatio="xMidYMid meet" overflow="visible">{inner}</svg></g>')
        s.shapes.append((order if order is not None else (x0 + a / 2 + y0 + b / 2, z0), svg))
        return (x0 + a / 2, y0 + b / 2, z1)

    def shadow(s, x0, y0, a, b, order=-100):
        s.shapes.append((order, s.poly([(x0, y0, 0), (x0 + a, y0, 0), (x0 + a, y0 + b, 0), (x0, y0 + b, 0)],
                                        "000000", extra='opacity="0.28" filter="url(#blur)"')))

    def strip(s, pts, w, color, op, order, dash=None, cap="round"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        pr = [P(*p) for p in pts]
        s.pts += pr
        pt = " ".join(f"{a:.4f},{b:.4f}" for a, b in pr)
        s.shapes.append((order, f'<polyline points="{pt}" fill="none" stroke="#{color}" stroke-width="{w}" '
                                f'stroke-linecap="{cap}" stroke-linejoin="round" opacity="{op}"{d}/>'))

    def path(s, pts, order=-90, color=("5AA9FF", "1499FE"), dash=None):
        s.strip(pts, 0.34, color[0], 0.18, order)
        s.strip(pts, 0.07, color[1], 0.9, order + 1, dash)

    def dot(s, x, y, z, r, fill, ring, order):
        sx, sy = P(x, y, z)
        s.pts += [(sx - r, sy - r), (sx + r, sy + r)]
        s.shapes.append((order, f'<circle cx="{sx:.4f}" cy="{sy:.4f}" r="{r}" fill="#{fill}" stroke="#{ring}" stroke-width="0.05"/>'))

    def flat(s, x, y, z, order, svg_inner, size=1.0):
        """A 2D glyph standing upright at a world point, for things with no isometric form."""
        sx, sy = P(x, y, z)
        s.pts += [(sx - size / 2, sy - size / 2), (sx + size / 2, sy + size / 2)]
        s.shapes.append((order, f'<g transform="translate({sx:.4f},{sy:.4f}) scale({size / 24:.5f}) translate(-12,-12)">{svg_inner}</g>'))

    def person(s, x, y, z, order, color="1499FE"):
        s.flat(x, y, z, order,
               f'<circle cx="12" cy="7" r="4.2" fill="#FFFFFF" stroke="#{color}" stroke-width="1.6"/>'
               f'<path d="M4 22c0-4.4 3.6-7.5 8-7.5s8 3.1 8 7.5" fill="#FFFFFF" stroke="#{color}" stroke-width="1.6" stroke-linejoin="round"/>', 1.3)

    def render(s, w=1200, h=760, pad=0.3):
        s.shapes.sort(key=lambda t: t[0] if isinstance(t[0], tuple) else (t[0], -1))
        body = "\n".join(v for _, v in s.shapes)
        xs = [p[0] for p in s.pts]
        ys = [p[1] for p in s.pts]
        minx, maxx, miny, maxy = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
        scale = min(w / (maxx - minx), h / (maxy - miny))
        ox = (w - (maxx - minx) * scale) / 2 - minx * scale
        oy = (h - (maxy - miny) * scale) / 2 - miny * scale
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                f'<defs><filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="0.18"/></filter></defs>'
                f'<g transform="translate({ox:.2f},{oy:.2f}) scale({scale:.4f})">\n{body}\n</g></svg>')


KEY = ("0 0 24 24", '<circle cx="8" cy="12" r="4.2" fill="none" stroke="#5A4718" stroke-width="2"/>'
                    '<path d="M12 12h9M18 12v3.2M15 12v2.4" fill="none" stroke="#5A4718" stroke-width="2" stroke-linecap="round"/>')
LOCK = '<rect x="5" y="10.5" width="14" height="10" rx="2" fill="#FFFFFF" stroke="#E5484D" stroke-width="1.8"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" fill="none" stroke="#E5484D" stroke-width="1.8"/>'
SEAL = ("0 0 24 24", '<path d="M12 2.5 19 5.5v5.3c0 4.6-3 8.3-7 9.7-4-1.4-7-5.1-7-9.7V5.5z" fill="#FFFFFF" stroke="#1499FE" stroke-width="1.7" stroke-linejoin="round"/>'
                     '<path d="m8.8 12 2.2 2.2 4.3-4.4" fill="none" stroke="#1499FE" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')
VAULT = ("0 0 24 24", '<rect x="4" y="10" width="16" height="10" rx="2" fill="none" stroke="#5AA9FF" stroke-width="1.8"/><path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="#5AA9FF" stroke-width="1.8"/>')
POWER = '<path d="M12 4v8" fill="none" stroke="#FFFFFF" stroke-width="2.6" stroke-linecap="round"/><path d="M7.5 7.5a6.4 6.4 0 1 0 9 0" fill="none" stroke="#FFFFFF" stroke-width="2.6" stroke-linecap="round"/>'
CROSS = '<path d="M6 6l12 12M18 6 6 18" fill="none" stroke="#E5484D" stroke-width="3" stroke-linecap="round"/>'
LENS = '<circle cx="10" cy="10" r="6.5" fill="rgba(90,169,255,0.18)" stroke="#5AA9FF" stroke-width="2.2"/><path d="m15 15 6 6" stroke="#5AA9FF" stroke-width="2.8" stroke-linecap="round"/>'

# Marks drawn onto a tile's top face (projected with it), in the navy of the platform.
OWNER = ("0 0 24 24", '<circle cx="12" cy="8" r="4" fill="none" stroke="#14213D" stroke-width="2"/>'
                      '<path d="M4.5 21c0-4.1 3.4-7 7.5-7s7.5 2.9 7.5 7" fill="none" stroke="#14213D" stroke-width="2" stroke-linecap="round"/>')
POWER_T = ("0 0 24 24", '<path d="M12 4v8" fill="none" stroke="#FFFFFF" stroke-width="2.8" stroke-linecap="round"/>'
                        '<path d="M7.5 7.5a6.4 6.4 0 1 0 9 0" fill="none" stroke="#FFFFFF" stroke-width="2.8" stroke-linecap="round"/>')

LOCK_T = ("0 0 24 24", '<rect x="5" y="10.5" width="14" height="10" rx="2" fill="#FFFFFF"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" fill="none" stroke="#FFFFFF" stroke-width="2.2"/>')
QMARK = ("0 0 24 24", '<text x="12" y="19" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" font-size="19" fill="#FFFFFF">?</text>')
CODE = ("0 0 24 24", '<path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4.5l-4 15" fill="none" stroke="#1499FE" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
SCAN = ("0 0 24 24", '<circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="#FFFFFF" stroke-width="2.4"/><path d="m15.5 15.5 5 5" stroke="#FFFFFF" stroke-width="2.8" stroke-linecap="round"/>')
STRIPE = ("FFFFFF", "DCE4EF", "C3D0E2", "none")
DARK = ("2A3448", "1C2537", "141B29", "none")

def upright(glyph):
    vb, inner = glyph
    return (vb, f'<g transform="rotate(-45 12 12)">{inner}</g>')

PERSON_T = upright(("0 0 24 24", '<circle cx="12" cy="8" r="4" fill="none" stroke="#1499FE" stroke-width="2.2"/>'
                                 '<path d="M4.5 21c0-4.1 3.4-7 7.5-7s7.5 2.9 7.5 7" fill="none" stroke="#1499FE" stroke-width="2.2" stroke-linecap="round"/>'))
