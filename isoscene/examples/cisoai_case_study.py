"""The isometric picture at the top of cisoai.au/case-study.  python examples/cisoai_case_study.py OUT.svg

What CISO AI does, left to right: news feeds, YouTube, X and Hacker News / Y Combinator feed a platform where Claude writes each
brief; the briefs go out as pages on the site, the weekly email, the API and video briefs on YouTube, and a person writes
the analysis that opens the email. Glyphs are Lucide 0.468 (ISC licence)."""
import sys
import _path  # noqa: F401  (lets the examples run from a checkout)
from isoscene import *


RSS = lucide('<path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/>', "E8701A")
PAGE = lucide('<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
              '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>')
MAIL = lucide('<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>')
CODE = lucide('<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>')
VIDEO = lucide('<path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3Z"/><path d="m6.2 5.3 3.1 3.9"/>'
               '<path d="m12.4 3.4 3.1 4"/><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>')
PERSON = lucide('<path d="M11.5 15H7a4 4 0 0 0-4 4v2"/><path d="M21.378 16.626a1 1 0 0 0-3.004-3.004l-4.01 4.012'
                'a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z"/><circle cx="10" cy="7" r="4"/>')

s = Scene()
s.ring(0.0, -1.5, 3.2, op=0.08)
s.ring(0.0, -1.5, 5.6, color="00C8FF", op=0.28, dash="0.12 0.12")

# Sources in, along the ground to the platform: news feeds, YouTube, agency posts on X, and the
# startups launching on Hacker News and in Y Combinator's newest batches.
sources = [((-7.0, -1.7), dict(glyph=RSS, lw=0.62)), ((-7.0, 0.0), dict(logo="youtube", lw=0.66)),
           ((-5.4, -1.15), dict(logo="x", lw=0.5)), ((-5.4, 0.55), dict(logo="ycombinator", lw=0.6))]
for (x, y), _ in sources:
    s.path([(x + 1.0, y + 0.5, 0), (-1.8, 0.0, 0)])
for (x, y), mark in sources:
    s.box(x, y, 0, 1.0, 1.0, 0.72, ICE, r=0.13, **mark)

# The platform, with Claude at its centre.
s.box(-1.8, -1.8, 0, 3.6, 3.6, 0.45, NAVY2, order=(0, 0), r=0.16, glow=0.25)
s.box(-0.85, -0.85, 0.45, 1.7, 1.7, 0.42, ICE, logo="claude", lw=1.0, order=(0, 10), r=0.14,
      glow=0.5, ground=False)

# Out: the platform to the four things readers get: pages, the email, the API and video briefs.
outs = [(-2.3, -6.2, PAGE), (-0.55, -6.2, MAIL), (1.2, -6.2, CODE), (2.95, -6.2, VIDEO)]
s.path([(0.0, -1.8, 0), (0.0, -4.4, 0)])
for (x, y, _) in outs:
    s.path([(0.0, -4.4, 0), (x + 0.55, -4.4, 0), (x + 0.55, y + 1.1, 0)], order=-89)
for (x, y, g) in outs:
    s.box(x, y, 0, 1.1, 1.1, 0.62, ICE, glyph=g, lw=0.66, r=0.13)

# A person writes the analysis that opens the email.
s.path([(0.0, -7.6, 0), (0.0, -6.2, 0)], color="00C8FF", order=-88)
s.box(-0.55, -8.7, 0, 1.1, 1.1, 0.62, TAG2, glyph=PERSON, lw=0.66, r=0.13, glow=0.35)

open(sys.argv[1], "w", encoding="utf-8").write(s.render())
print("wrote", sys.argv[1])
