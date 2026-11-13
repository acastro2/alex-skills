"""The sigilant.io hero in the polished style (iso2), still and animated.
    python examples/sigilant_hero.py OUTDIR   ->  OUTDIR/scene.svg (still) and OUTDIR/scene-animated.svg
The moving tokens come from hero_tokens.py, which shares the layout's world coordinates."""
import os, sys
import _path  # noqa: F401  (lets the examples run from a checkout)
from isoscene import *
import hero_tokens as T

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
W, H = 3549, 1410          # the hero's canvas (11.83 x 4.7 in at 300 ppi, as in scene.py)


def build(animated):
    s = Scene()
    s.ring(0.0, 0.0, 3.4, op=0.08)
    s.ring(0.0, 0.0, 5.2, color="5B7CFA", op=0.28, dash="0.12 0.12")
    # The ground path: agents -> gateway along +x, gateway -> systems along -y.
    s.path([(-4.8, 0.0, 0), (0.0, 0.0, 0), (0.0, -4.8, 0)], flow=False)
    if animated:
        ground, top = [], []
        for i, kind in enumerate(T.ORDER):
            g, t = T.token(kind, i * T.SPACING)
            ground += g
            top += t
        # Above the path and below every block: tokens come out from under the agents, pass
        # beneath the platform and go in under the systems.
        s.shapes.append((-80, '<g id="tokens-ground">' + "\n".join(ground) + "</g>"))
        s.shapes.append(((999, 999), '<g id="tokens-top">' + "\n".join(top) + "</g>"))
    else:
        for t in (-3.8, -3.0):
            for (x, y) in ((t, 0), (0, t)):
                X, Y = P(x, y, 0)
                s.shapes.append((-80, f'<circle cx="{X:.4f}" cy="{Y:.4f}" r="0.13" fill="#FFFFFF" stroke="#1499FE" stroke-width="0.05"/>'))
    # Agents.
    for (x, y), lg in zip([(-6.8, -0.9), (-6.8, 0.4), (-5.6, -0.25)], ["claude", "openai", "copilot"]):
        s.box(x, y, 0, 1.0, 1.0, 0.75, ICE, logo=lg, lw=0.66, r=0.13)
    # The gateway: a navy platform with four tiles; Approve is the white one.
    TZ = 0.55
    s.box(-2.2, -2.2, 0, 4.4, 4.4, TZ, NAVY2, order=(0, 0), r=0.16, glow=0.25)
    s.path([(-2.2, 1.0, TZ), (1.0, 1.0, TZ), (1.0, -2.2, TZ)], order=(0, 0.6), flow=False, halo=False)
    for k, (x, y) in {"decide": (-2.0, 0.2), "approve": (-2.0, -2.0), "credential": (0.2, 0.2), "record": (0.2, -2.0)}.items():
        s.box(x, y, TZ, 1.8, 1.8, 0.22, TAG2 if k == "approve" else BLUE2, order=(0, 10 + x + y), r=0.1,
              glow=0.3, ground=False)
    # Business systems: four blocks of different heights.
    for (x, y, h), lg in zip([(-1.0, -7.1, 1.12), (0.4, -7.1, 0.88), (-1.0, -5.7, 0.7), (0.4, -5.7, 0.98)],
                             ["sap", "workday", "servicenow", "salesforce"]):
        s.box(x, y, 0, 1.1, 1.1, h, ICE, logo=lg, lw=1.0 if lg in ("workday", "servicenow") else 0.78, r=0.13)
    return s.render(w=W, h=H, pad=0.25, bg=False)


open(os.path.join(OUT, "scene.svg"), "w", encoding="utf-8").write(build(False))
open(os.path.join(OUT, "scene-animated.svg"), "w", encoding="utf-8").write(build(True))
print("hero: scene.svg, scene-animated.svg")
