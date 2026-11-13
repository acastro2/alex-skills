"""Polished isometric scenes: gradient faces, rounded silhouettes, edge highlights, coloured glow,
glass boxes and an optional backdrop. Same projection and logos as iso.py, which is left as it was."""
import math
from .iso import P, C30, LOGOS, KEY, upright, OWNER, SEAL, VAULT, POWER_T, LOCK_T, QMARK, CODE, SCAN, PERSON_T

# Face colours: (top light, top dark, left light, left dark, right light, right dark, glow)
ICE = ("FFFFFF", "E6EDF8", "E6EDF7", "B6C6DF", "AFC0DB", "8299BE", "5AA9FF")
GOLD2 = ("FFE7A8", "F5C766", "F8D488", "D9A445", "C99232", "9C6C1C", "F5C766")
BLUE2 = ("8FD0FF", "3FA9FF", "4DB0FF", "1286E0", "0F74C9", "0A4F96", "3FA9FF")
NAVY2 = ("2B3E63", "1C2C47", "22355A", "14213D", "15223D", "0B1424", "5B7CFA")
RED2 = ("FF8A8E", "F0565B", "F06A6E", "D23F44", "B8363A", "8A2427", "FF6B70")
GREY2 = ("9AA3AE", "7D8794", "6E7887", "525C6B", "4A5361", "323944", "8A929C")
DARK2 = ("3A4660", "2A3448", "2A3448", "1C2537", "1A2233", "10161F", "3FA9FF")
STRIPE2 = ("FFFFFF", "EEF2F8", "E6EDF7", "C9D5E8", "B9C7DD", "9AABC6", "FFFFFF")
TAG2 = ("FFFFFF", "EAF1FB", "4DB0FF", "1286E0", "1286E0", "0B5CC9", "3FA9FF")


def _rounded(pts, r):
    """A closed path through pts with each corner rounded by r (in scene units)."""
    n = len(pts)
    d = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        def toward(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            k = min(r, L / 2.2) / L
            return (a[0] + dx * k, a[1] + dy * k)
        a, b = toward(p1, p0), toward(p1, p2)
        d.append(("M" if i == 0 else "L") + f"{a[0]:.4f},{a[1]:.4f} Q{p1[0]:.4f},{p1[1]:.4f} {b[0]:.4f},{b[1]:.4f}")
    return " ".join(d) + " Z"


def _pts(pts):
    return " ".join(f"{a:.4f},{b:.4f}" for a, b in pts)


class Scene:
    def __init__(s):
        s.shapes, s.pts, s.defs, s.n = [], [], [], 0
        s.backdrop = []  # drawn in scene units, behind everything, not part of the fit

    def uid(s, k):
        s.n += 1
        return f"{k}{s.n}"

    def grad(s, a, b, c0, c1, o0=1, o1=1):
        g = s.uid("g")
        s.defs.append(f'<linearGradient id="{g}" gradientUnits="userSpaceOnUse" x1="{a[0]:.4f}" y1="{a[1]:.4f}" x2="{b[0]:.4f}" y2="{b[1]:.4f}">'
                      f'<stop offset="0" stop-color="#{c0}" stop-opacity="{o0}"/><stop offset="1" stop-color="#{c1}" stop-opacity="{o1}"/></linearGradient>')
        return f"url(#{g})"

    def box(s, x0, y0, z0, a, b, h, col, order=None, logo=None, lw=0.7, glyph=None, r=0.09,
            glass=False, inner=None, glow=0.32, ground=True):
        tl, td, ll, ld, rl, rd, gc = col
        x1, y1, z1 = x0 + a, y0 + b, z0 + h
        T = [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)]
        Lf = [P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)]
        Rf = [P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)]
        sil = [P(x0, y0, z1), P(x1, y0, z1), P(x1, y0, z0), P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1)]
        s.pts += sil
        out = ""
        cid = s.uid("c")
        s.defs.append(f'<clipPath id="{cid}"><path d="{_rounded(sil, r)}"/></clipPath>')
        # Coloured glow beneath, and a soft contact shadow on the ground.
        if ground:
            g0 = [P(x0 - .08, y0 - .08, z0), P(x1 + .08, y0 - .08, z0), P(x1 + .08, y1 + .08, z0), P(x0 - .08, y1 + .08, z0)]
            out += f'<polygon points="{_pts(g0)}" fill="#000" opacity=".45" filter="url(#soft)"/>'
        if glow:
            out += f'<path d="{_rounded(sil, r)}" fill="#{gc}" opacity="{glow}" filter="url(#glow)"/>'
        op = 0.62 if glass else 1
        body = ""
        if glass and inner:
            # Something inside the glass, blurred as if seen through frosted glass.
            body += inner
        body += (f'<polygon points="{_pts(Lf)}" fill="{s.grad(P(x0, y1, z1), P(x1, y1, z0), ll, ld)}" opacity="{op}"/>'
                 f'<polygon points="{_pts(Rf)}" fill="{s.grad(P(x1, y1, z1), P(x1, y0, z0), rl, rd)}" opacity="{op}"/>'
                 f'<polygon points="{_pts(T)}" fill="{s.grad(T[0], T[2], tl, td)}" opacity="{op}"/>')
        # Edge highlights: brightest at the front-top corner, fading away from it.
        c = T[2]
        hl = 0.35 if col in (NAVY2, DARK2) else 0.95   # a softer edge on dark blocks
        for e in (T[3], T[1], P(x1, y1, z0)):
            k = 0.82
            end = (c[0] + (e[0] - c[0]) * k, c[1] + (e[1] - c[1]) * k)
            body += (f'<line x1="{c[0]:.4f}" y1="{c[1]:.4f}" x2="{end[0]:.4f}" y2="{end[1]:.4f}" '
                     f'stroke="{s.grad(c, end, "FFFFFF", "FFFFFF", hl, 0)}" stroke-width="0.035" stroke-linecap="round"/>')
        out += f'<g clip-path="url(#{cid})">{body}</g>'
        if logo or glyph:
            X, Y = P(x0, y0, z1)
            m = (a - lw) / 2
            vb, inn = LOGOS[logo] if logo else glyph
            out += (f'<g transform="matrix({C30:.5f},0.5,{-C30:.5f},0.5,{X:.4f},{Y:.4f})">'
                    f'<svg x="{m:.4f}" y="{(b - lw) / 2:.4f}" width="{lw}" height="{lw}" viewBox="{vb}" '
                    f'preserveAspectRatio="xMidYMid meet" overflow="visible">{inn}</svg></g>')
        s.shapes.append((order if order is not None else (x0 + a / 2 + y0 + b / 2, z0), out))
        return (x0 + a / 2, y0 + b / 2, z1)

    def side_glyph(s, x0, y, z1, w, glyph, order):
        """A glyph drawn upright on a block's left face (the plane y = const), its top-left at (x0, y, z1)."""
        X, Y = P(x0, y, z1)
        vb, inn = glyph
        s.shapes.append((order, f'<g transform="matrix({C30:.5f},0.5,0,1,{X:.4f},{Y:.4f})">'
                                f'<svg width="{w}" height="{w}" viewBox="{vb}" overflow="visible">{inn}</svg></g>'))

    def plane(s, o, u, v, inner, order, w=1, h=1):
        """SVG `inner` flat on the world plane from origin o along u and v; local (w,0) is o+u, (0,h) is o+v."""
        def proj(d):
            return ((d[0] - d[1]) * C30, (d[0] + d[1]) * 0.5 - d[2])
        pu, pv, po = proj(u), proj(v), P(*o)
        s.shapes.append((order, f'<g transform="matrix({pu[0] / w:.5f},{pu[1] / w:.5f},{pv[0] / h:.5f},{pv[1] / h:.5f},'
                                f'{po[0]:.4f},{po[1]:.4f})">{inner}</g>'))
        for k in (0, 1, 2, 3):
            du = u if k & 1 else (0, 0, 0)
            dv = v if k & 2 else (0, 0, 0)
            s.pts.append(P(o[0] + du[0] + dv[0], o[1] + du[1] + dv[1], o[2] + du[2] + dv[2]))

    def path(s, pts, order=-90, color="5AA9FF", flow=True, dash=None, halo=True, pulse=0.05):
        pr = [P(*p) for p in pts]
        s.pts += pr
        d = _pts(pr)
        out = (f'<polyline points="{d}" fill="none" stroke="#{color}" stroke-width="0.32" stroke-linecap="round" '
               f'stroke-linejoin="round" opacity=".22" filter="url(#glow)"/>' if halo else "") + (
               f'<polyline points="{d}" fill="none" stroke="#{color}" stroke-width="0.055" stroke-linecap="round" '
               f'stroke-linejoin="round" opacity=".95"{f" stroke-dasharray=\"{dash}\"" if dash else ""}/>')
        if flow:
            # Small bright pulses travelling along the line.
            out += (f'<polyline points="{d}" fill="none" stroke="#FFFFFF" stroke-width="{0.06 + pulse * 0.3:.3f}" stroke-linecap="round" '
                    f'stroke-dasharray="{pulse} 1.2" opacity=".9"><animate attributeName="stroke-dashoffset" '
                    f'from="1.25" to="0" dur="1.6s" repeatCount="indefinite"/></polyline>')
        s.shapes.append((order, out))

    def ripple(s, cx, cy, z, R, order, color="5AA9FF", n=3, dur=3.0, within=None):
        """Rings that spread from a point on a surface and fade, n of them staggered: a scan going out."""
        X, Y = P(cx, cy, z)
        rx, ry = R * math.sqrt(2) * C30, R * math.sqrt(2) * 0.5
        out = ""
        for i in range(n):
            b = f'begin="{-dur * i / n:.2f}s" dur="{dur}s" repeatCount="indefinite"'
            out += (f'<ellipse cx="{X:.4f}" cy="{Y:.4f}" rx="0" ry="0" fill="none" stroke="#{color}" stroke-width="0.04">'
                    f'<animate attributeName="rx" from="0" to="{rx:.4f}" {b}/><animate attributeName="ry" from="0" to="{ry:.4f}" {b}/>'
                    f'<animate attributeName="opacity" values=".8;0" {b}/></ellipse>')
        if within:   # keep the rings on a surface: within = (x0, y0, x1, y1) at height z
            x0, y0, x1, y1 = within
            cid = s.uid("c")
            s.defs.append(f'<clipPath id="{cid}"><polygon points="{_pts([P(x0, y0, z), P(x1, y0, z), P(x1, y1, z), P(x0, y1, z)])}"/></clipPath>')
            out = f'<g clip-path="url(#{cid})">{out}</g>'
        s.shapes.append((order, out))

    def ring(s, cx, cy, R, color="FFFFFF", op=0.12, w=0.025, dash=None):
        """A circle on the ground, seen in projection: a backdrop line, not part of the fit."""
        X, Y = P(cx, cy, 0)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        s.backdrop.append(f'<ellipse cx="{X:.4f}" cy="{Y:.4f}" rx="{R * math.sqrt(2) * C30:.4f}" ry="{R * math.sqrt(2) * 0.5:.4f}" '
                          f'fill="none" stroke="#{color}" stroke-width="{w}" opacity="{op}"{da}/>')

    def render(s, w=1200, h=760, pad=0.35, bg=True):
        s.shapes.sort(key=lambda t: t[0] if isinstance(t[0], tuple) else (t[0], -1))
        xs = [p[0] for p in s.pts]
        ys = [p[1] for p in s.pts]
        minx, maxx, miny, maxy = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
        sc = min(w / (maxx - minx), h / (maxy - miny))
        ox = (w - (maxx - minx) * sc) / 2 - minx * sc
        oy = (h - (maxy - miny) * sc) / 2 - miny * sc
        back = ""
        if bg:
            back = (f'<rect width="{w}" height="{h}" fill="url(#bgr)"/>'
                    f'<rect width="{w}" height="{h}" fill="url(#dots)" mask="url(#edges)"/>')
        defs = ("".join(s.defs)
                + '<filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="0.22"/></filter>'
                + '<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="0.12"/></filter>'
                + '<filter id="frost" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="0.07"/></filter>'
                + '<radialGradient id="bgr" cx="50%" cy="55%" r="75%"><stop offset="0" stop-color="#1F3358"/>'
                  '<stop offset=".55" stop-color="#162139"/><stop offset="1" stop-color="#11161F"/></radialGradient>'
                + '<pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="7" cy="7" r="1.6" fill="#7F95C8" opacity=".35"/></pattern>'
                + '<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#fff"/><stop offset=".14" stop-color="#000"/>'
                  '<stop offset=".86" stop-color="#000"/><stop offset="1" stop-color="#fff"/></linearGradient>'
                + f'<mask id="edges"><rect width="{w}" height="{h}" fill="url(#fade)"/></mask>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs>{defs}</defs>{back}'
                f'<g transform="translate({ox:.2f},{oy:.2f}) scale({sc:.4f})">\n' + "".join(s.backdrop) + "\n"
                + "\n".join(v for _, v in s.shapes) + "\n</g></svg>")
