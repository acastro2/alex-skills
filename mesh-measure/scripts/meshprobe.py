#!/usr/bin/env python3
"""Measure a real mesh by ray-casting its triangles.

The point of this module is that it answers questions about the geometry that
actually exists in a file, rather than about the parameters someone believes
generated it. Those two things drift apart, and the drift is where bugs live.

Every query casts a ray along one axis and reports where it entered and left the
solid. `nan` means the ray missed entirely -- which for a through-hole is the
correct, informative answer, not an error.

Library:
    p = Probe("part.stl")
    p.top(x, y)                 # highest Z of solid on a vertical ray, nan if none
    p.bottom(x, y)              # lowest Z
    p.through(x, y)             # True if the ray hits nothing (a through-hole)
    p.profile("x", 10, 50, y=0) # heights across a line
    p.flat_run("x", 10, 50, 1.6)# longest stretch sitting at a given height
    p.span("x", 10, 50, y=0)    # extent + centre of the hole crossing that line
    p.heightmap()               # ASCII top view

CLI:
    python meshprobe.py part.stl                       # bbox + ASCII height map
    python meshprobe.py part.stl --profile x --at 0    # cross-section heights
    python meshprobe.py part.stl --span x --at 0 --range 43.5 53.5
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

AXES = {"x": 0, "y": 1, "z": 2}


class Probe:
    """Ray-cast queries against a triangle mesh.

    `up` names the axis rays travel along (default "z", i.e. looking down at a
    part sitting on a bed). The two remaining axes become the query plane.
    """

    def __init__(self, source, up: str = "z"):
        if isinstance(source, str):
            import trimesh

            mesh = trimesh.load(source, force="mesh")
        else:
            mesh = source
        self.mesh = mesh
        self.tri = np.asarray(mesh.vertices)[np.asarray(mesh.faces)]
        self.set_up(up)

    def set_up(self, up: str) -> "Probe":
        self.up = AXES[up]
        self.pa, self.pb = [i for i in (0, 1, 2) if i != self.up]
        return self

    # -- core ---------------------------------------------------------------
    def _hits(self, a: float, b: float) -> np.ndarray:
        """Values along the ray axis where the ray at (a, b) crosses the surface."""
        A, B, C = self.tri[:, 0], self.tri[:, 1], self.tri[:, 2]
        pa, pb, up = self.pa, self.pb, self.up
        det = (B[:, pb] - C[:, pb]) * (A[:, pa] - C[:, pa]) + \
              (C[:, pa] - B[:, pa]) * (A[:, pb] - C[:, pb])
        det = np.where(np.abs(det) < 1e-12, 1e-12, det)
        w0 = ((B[:, pb] - C[:, pb]) * (a - C[:, pa]) +
              (C[:, pa] - B[:, pa]) * (b - C[:, pb])) / det
        w1 = ((C[:, pb] - A[:, pb]) * (a - C[:, pa]) +
              (A[:, pa] - C[:, pa]) * (b - C[:, pb])) / det
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not inside.any():
            return np.empty(0)
        return (w0[inside] * A[inside, up] + w1[inside] * B[inside, up]
                + w2[inside] * C[inside, up])

    def top(self, a: float, b: float) -> float:
        h = self._hits(a, b)
        return float("nan") if h.size == 0 else float(h.max())

    def bottom(self, a: float, b: float) -> float:
        h = self._hits(a, b)
        return float("nan") if h.size == 0 else float(h.min())

    def through(self, a: float, b: float) -> bool:
        """No material on this ray at all. For a bore, this is the pass condition."""
        return self._hits(a, b).size == 0

    # -- derived ------------------------------------------------------------
    def bbox(self):
        return np.asarray(self.mesh.bounds)

    def _line(self, axis: str, lo: float, hi: float, at: float, n: int):
        """Sample `n` points along `axis` from lo..hi, with the other plane axis at `at`."""
        ax = AXES[axis]
        if ax == self.up:
            raise ValueError(f"axis {axis!r} is the ray axis; pick one of the plane axes")
        us = np.linspace(lo, hi, n)
        first = ax == self.pa
        return us, [(u, at) if first else (at, u) for u in us]

    def profile(self, axis: str, lo: float, hi: float, at: float = 0.0, n: int = 400):
        """Surface height along a line. Returns (positions, heights) with nan gaps."""
        us, pts = self._line(axis, lo, hi, at, n)
        return us, np.array([self.top(a, b) for a, b in pts])

    def flat_run(self, axis: str, lo: float, hi: float, height: float,
                 at: float = 0.0, tol: float = 0.01, n: int = 600):
        """Longest contiguous stretch sitting at `height`. Returns (start, end, length).

        Useful for "is this surface actually flat, and over how much of its width?"
        -- a question that ramps, haunches and fillets quietly change.
        """
        us, zs = self.profile(axis, lo, hi, at, n)
        best = cur = None
        out = (0.0, 0.0, 0.0)
        for u, z in zip(us, zs):
            if not np.isnan(z) and abs(z - height) <= tol:
                cur = u if cur is None else cur
                best = u
            else:
                if cur is not None and best - cur > out[2]:
                    out = (cur, best, best - cur)
                cur = None
        if cur is not None and best - cur > out[2]:
            out = (cur, best, best - cur)
        return out

    def span(self, axis: str, lo: float, hi: float, at: float = 0.0, n: int = 900):
        """Extent of the through-hole crossing this line: (start, end, width, centre).

        Measures a bore where it actually is, so you can compare it against where
        you meant it to be. Returns None if the line crosses no hole.
        """
        us, pts = self._line(axis, lo, hi, at, n)
        hit = [u for u, (a, b) in zip(us, pts) if self.through(a, b)]
        if not hit:
            return None
        s, e = min(hit), max(hit)
        return s, e, e - s, (s + e) / 2.0

    def heightmap(self, nx: int = 56, ny: int = 28, chars: str = " .:-=+*#%@") -> str:
        """ASCII top view. Fast way to see whether the shape is the shape you meant."""
        b = self.bbox()
        us = np.linspace(b[0][self.pa], b[1][self.pa], nx)
        vs = np.linspace(b[0][self.pb], b[1][self.pb], ny)
        zlo, zhi = b[0][self.up], b[1][self.up]
        rng = (zhi - zlo) or 1.0
        rows = []
        for v in reversed(vs):
            row = ""
            for u in us:
                z = self.top(u, v)
                row += " " if np.isnan(z) else chars[
                    min(len(chars) - 1, max(0, int((z - zlo) / rng * (len(chars) - 0.01))))]
            rows.append(row)
        return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mesh")
    ap.add_argument("--up", default="z", choices=list(AXES))
    ap.add_argument("--profile", metavar="AXIS", choices=list(AXES))
    ap.add_argument("--span", metavar="AXIS", choices=list(AXES))
    ap.add_argument("--at", type=float, default=0.0, help="other plane axis value")
    ap.add_argument("--range", nargs=2, type=float, metavar=("LO", "HI"))
    ap.add_argument("--steps", type=int, default=40)
    a = ap.parse_args(argv)

    p = Probe(a.mesh, up=a.up)
    b = p.bbox()
    print(f"file    : {a.mesh}")
    print(f"bounds  : {np.round(b[0], 3).tolist()} .. {np.round(b[1], 3).tolist()}")
    print(f"size    : {np.round(b[1] - b[0], 3).tolist()} mm")
    print(f"watertight: {p.mesh.is_watertight}   volume: {p.mesh.volume / 1000:.2f} cm^3")

    if a.profile:
        ax = AXES[a.profile]
        lo, hi = a.range if a.range else (b[0][ax], b[1][ax])
        us, zs = p.profile(a.profile, lo, hi, a.at, a.steps)
        print(f"\nprofile along {a.profile} at {a.at}:")
        for u, z in zip(us, zs):
            bar = "" if np.isnan(z) else "#" * int(round(z * 4))
            print(f"  {a.profile}={u:8.2f}  {'(hole)' if np.isnan(z) else f'{z:7.3f}'}  {bar}")
    elif a.span:
        ax = AXES[a.span]
        lo, hi = a.range if a.range else (b[0][ax], b[1][ax])
        r = p.span(a.span, lo, hi, a.at)
        print(f"\nhole along {a.span} at {a.at}: "
              + ("none found" if r is None else
                 f"{r[0]:.3f}..{r[1]:.3f}  width {r[2]:.3f}  centre {r[3]:.3f}"))
    else:
        print("\ntop view:")
        print(p.heightmap())
    return 0


if __name__ == "__main__":
    sys.exit(main())
