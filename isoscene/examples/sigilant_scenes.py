"""The six sigilant.io scenes in the polished style.  python examples/sigilant_scenes.py OUTDIR"""
import os, sys
import _path  # noqa: F401  (lets the examples run from a checkout)
from isoscene import *

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
AH = 0.78   # agent height
SH = 1.1    # system height


def save(name, s):
    open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8").write(s.render())


def agent(s, x, y, logo, col=ICE, z=0, **k):
    return s.box(x, y, z, 1.05, 1.05, AH, col, logo=logo, lw=0.66, r=0.14, **k)


def system(s, x, y, logo, h=SH, lw=0.82):
    return s.box(x, y, 0, 1.2, 1.2, h, ICE, logo=logo, lw=lw, r=0.15)


# (a) Shared key: three agents, one gold key, one system. In the logs they are one.
s = Scene()
s.ring(0.0, 0.0, 2.3, op=0.10)
s.ring(0.0, 0.0, 3.9, color="5B7CFA", op=0.35, dash="0.12 0.12")
agents = [(-4.3, -1.2), (-4.3, 0.7), (-2.9, -0.25)]
for (x, y) in agents:
    s.path([(x + 1.05, y + 0.5, 0), (0.0, 0.0, 0)])
s.path([(0.0, 0.0, 0), (3.3, 0.0, 0)])
for (x, y), lg in zip(agents, ("claude", "openai", "copilot")):
    agent(s, x, y, lg)
s.box(-0.65, -0.65, 0, 1.3, 1.3, 0.32, GOLD2, glyph=KEY, lw=0.85, r=0.1, glow=0.55)
system(s, 3.2, -0.6, "sap")
save("shared-key", s)

# (b) The register: agents on a navy slab, each beside an owner tag; the person one agent acts for, linked.
s = Scene()
s.ring(0.2, 0.0, 4.6, color="5B7CFA", op=0.30, dash="0.12 0.12")
s.box(-3.3, -1.8, 0, 6.8, 3.4, 0.4, NAVY2, order=(0, 0), r=0.16, glow=0.22)
for (x, y), lg in zip([(-2.9, -0.7), (-0.8, -0.7), (1.3, -0.7)], ["claude", "openai", "copilot"]):
    agent(s, x, y, lg, z=0.4, order=(0, 10 + x), glow=0.18)
    s.box(x - 0.05, y + 1.3, 0.4, 1.15, 0.8, 0.14, TAG2, glyph=upright(OWNER), lw=0.62, r=0.06,
          order=(0, 9 + x), glow=0.25)
s.path([(-0.3, -3.4, 0), (-0.3, -1.8, 0)])
s.path([(-0.3, -1.8, 0.42), (-0.3, -0.7, 0.42)], order=(0, 5))
s.box(-0.85, -4.55, 0, 1.1, 1.1, 0.7, ICE, glyph=PERSON_T, lw=0.78, r=0.14)
save("register", s)

# (c) Security said no: the agent's path ends at a closed boom gate; the system beyond is locked.
s = Scene()
s.ring(-0.5, 0.5, 3.4, color="5B7CFA", op=0.30, dash="0.12 0.12")
s.path([(-3.3, 0.5, 0), (-0.9, 0.5, 0)])
s.path([(-0.3, 0.5, 0), (2.4, 0.5, 0)], color="8A929C", dash="0.16 0.16", flow=False, halo=False)
agent(s, -4.4, 0.0, "copilot")
for py in (-0.9, 1.7):                                        # gate posts
    s.box(-0.7, py, 0, 0.3, 0.3, 1.1, STRIPE2, order=(-0.55 + py + 0.15, 0), r=0.05, glow=0.15)
for k in range(6):                                            # the boom, red and white
    y0 = -0.75 + k * 0.48
    s.box(-0.62, y0, 0.85, 0.14, 0.48, 0.14, RED2 if k % 2 == 0 else STRIPE2, order=(-0.55 + y0 + 0.24, 1),
          r=0.02, glow=0.35 if k % 2 == 0 else 0, ground=False)
system(s, 2.4, -0.1, "sap")
# The lock hangs as a red sign on the side facing the gate, so the system's name on top stays visible.
s.box(2.7, 1.1, 0.22, 0.62, 0.05, 0.62, RED2, order=(4, 2), r=0.07, glow=0.6, ground=False)
s.side_glyph(2.79, 1.15, 0.79, 0.44, LOCK_T, order=(4, 3))
save("blocked", s)

# (d) Kill switch: one agent switched off, and everything it started; the red tile is the switch.
s = Scene()
s.ring(0.0, 0.0, 3.4, op=0.10)
s.ring(0.0, 0.0, 5.6, color="5B7CFA", op=0.30, dash="0.12 0.12")
s.path([(-5.15, -1.1, 0), (-2.2, -1.1, 0)])
s.path([(1.1, -2.2, 0), (1.1, -4.4, 0)])
s.path([(-5.15, 1.1, 0), (-2.2, 1.1, 0)], color="8A929C", dash="0.14 0.2", flow=False, halo=False)
for (sx, sy) in [(-8.6, 1.0), (-7.6, 2.6)]:                   # what the switched-off agent started
    s.path([(sx + 0.3, sy + 0.3, 0.02), (-5.7, 1.1, 0.02)], color="6E7887", dash="0.1 0.14", flow=False,
           halo=False, order=-85)
    s.box(sx, sy, 0, 0.6, 0.6, 0.45, GREY2, r=0.08, glow=0)
agent(s, -6.2, -1.6, "claude")
agent(s, -6.2, 0.6, "openai", col=GREY2, glow=0)
s.box(-2.2, -2.2, 0, 4.4, 4.4, 0.45, NAVY2, order=(0, 0), r=0.16, glow=0.22)
for (x, y), col, g in [((-2.0, -2.0), BLUE2, None), ((0.2, -2.0), BLUE2, None), ((0.2, 0.2), BLUE2, None),
                       ((-2.0, 0.2), RED2, upright(POWER_T))]:
    s.box(x, y, 0.45, 1.8, 1.8, 0.2, col, glyph=g, lw=1.0, order=(0, 10 + x + y), r=0.1,
          glow=0.5 if g else 0.18, ground=False)
system(s, 0.5, -5.6, "workday", lw=1.04)
save("kill-switch", s)

# (e) The audit chain: linked blocks, each sealed, anchored to a vault.
s = Scene()
s.ring(-1.0, 0.5, 3.6, color="5B7CFA", op=0.30, dash="0.12 0.12")
xs = [-4.4, -2.9, -1.4, 0.1]
for i, x in enumerate(xs):
    if i:
        s.path([(x - 0.5, 0.5, 0.35), (x, 0.5, 0.35)], order=(x + 0.25, 0), halo=False)
    s.box(x, 0.0, 0, 1.0, 1.0, 0.7, ICE, glyph=upright(SEAL), lw=0.62, order=(x + 0.5, 0), r=0.13, glow=0.22)
s.path([(1.1, 0.5, 0.35), (2.4, 0.5, 0.35)], order=(1.75, 0), dash="0.1 0.2", halo=False)
s.box(2.4, -0.3, 0, 1.6, 1.6, 1.1, NAVY2, glyph=upright(VAULT), lw=0.9, order=(10, 0), r=0.16, glow=0.45)
save("audit-chain", s)

# (f) Discovery: a governed runner scans the estate; what it finds is claimed by an owner or still unknown.
s = Scene()
s.ring(0.1, 0.1, 5.4, color="5B7CFA", op=0.30, dash="0.12 0.12")
s.box(-4.0, -2.5, 0, 8.2, 5.2, 0.3, NAVY2, order=(0, 0), r=0.16, glow=0.22)
Z = 0.3
def on(x, y, a, b, h, col, **k):
    k.setdefault("ground", False)
    k.setdefault("glow", 0.2)
    return s.box(x, y, Z, a, b, h, col, order=(0, 10 + x + a / 2 + y + b / 2), **k)
RX, RY = 2.9, 1.6
targets = [(-3.0, -1.7), (-1.0, -0.4), (-3.2, 0.9), (0.6, -2.0), (-1.2, 1.6), (1.2, -0.3)]
for tx, ty in targets:
    s.path([(RX + 0.5, RY + 0.5, Z + 0.02), (tx + 0.5, ty + 0.5, Z + 0.02)], order=(0, 5), dash="0.12 0.12",
           halo=False, pulse=0.16)                                # pulses run out from the scanner to each find
s.ripple(RX + 0.5, RY + 0.5, Z + 0.01, 3.6, order=(0, 6), within=(-4.0, -2.5, 4.2, 2.7))
for (x, y) in [(-3.0, -1.7), (0.6, -2.0)]:                    # repositories: stacked plates with a code mark
    for k in range(3):
        s.box(x, y, Z + k * 0.15, 1.1, 1.1, 0.11, ICE, order=(0, 10 + x + y + 1.1 + k * 0.01), r=0.08,
              glow=0.2 if k == 0 else 0, ground=k == 0, **({"glyph": CODE, "lw": 0.6} if k == 2 else {}))
on(1.2, -0.3, 0.9, 0.9, 1.25, DARK2, r=0.1, glow=0.3)          # an MCP server: a dark tower with blue lights
for k in range(3):
    s.box(1.25, 0.6, Z + 0.25 + k * 0.33, 0.8, 0.02, 0.07, BLUE2, order=(0, 10.5 + 1.2 - 0.3 + 0.9), r=0.01,
          glow=0.6, ground=False)
on(-1.2, 1.6, 0.9, 0.9, 0.16, GOLD2, glyph=KEY, lw=0.7, r=0.08, glow=0.55)   # a model key, lying in the open
for (x, y), lg in [((-1.0, -0.4), "claude"), ((-3.2, 0.9), "openai")]:          # claimed agents, with owner tags
    on(x, y, 0.9, 0.9, 0.68, ICE, logo=lg, lw=0.58, r=0.12)
    s.box(x - 0.02, y + 1.0, Z, 0.94, 0.6, 0.1, TAG2, glyph=OWNER, lw=0.46, order=(0, 9.9 + x + y + 1.4), r=0.05,
          glow=0.25, ground=False)
for (x, y) in [(-1.6, -2.35), (2.2, -1.9)]:                   # agents nobody has claimed yet
    on(x, y, 0.8, 0.8, 0.55, GREY2, glyph=QMARK, lw=0.55, r=0.1, glow=0)
s.box(RX, RY, Z, 1.0, 1.0, 0.6, NAVY2, order=(0, 30), r=0.12, glow=0.3, ground=False)
s.box(RX + 0.1, RY + 0.1, Z + 0.6, 0.8, 0.8, 0.14, BLUE2, glyph=SCAN, lw=0.6, order=(0, 31), r=0.08, glow=0.6,
      ground=False)
save("discovery", s)

print("scenes:", sorted(os.listdir(OUT)))
