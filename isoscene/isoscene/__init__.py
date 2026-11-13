"""isoscene: polished isometric scenes as SVG.

    from isoscene import *
    s = Scene()
    s.box(0, 0, 0, 1, 1, 0.7, ICE, logo="claude", lw=0.66, r=0.13)
    open("scene.svg", "w", encoding="utf-8").write(s.render())

The polished style lives in iso2.py (Scene, the *2 palettes); iso.py holds the projection, the
glyphs and the original flat style, kept for scenes that still use it.
"""
from .iso2 import *  # noqa: F401,F403
from .iso2 import Scene, upright
from . import iso as flat  # noqa: F401  the original flat style: flat.Scene, flat.WHITE, ...

__version__ = "0.1.0"


def lucide(inner, colour="0B5CC9", width=2.2):
    """A Lucide icon (its inner markup, 24x24) as a top-face glyph, turned to read upright.

    Copy the <path>/<circle>/... elements from lucide-static@0.468.0/icons/<name>.svg."""
    return upright(("0 0 24 24", f'<g fill="none" stroke="#{colour}" stroke-width="{width}" '
                                 f'stroke-linecap="round" stroke-linejoin="round">{inner}</g>'))
