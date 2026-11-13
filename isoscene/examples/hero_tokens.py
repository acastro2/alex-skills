# Copied from the pitch deck's scene_animated.py. sigilant_hero.py imports token() and the timing
# from it; its main() is for the deck and is not used here.
"""Animated version of the isometric Solution scene.

Reads scene.svg (written by scene.py) and writes scene-animated.svg beside it: the same
picture, with tokens moving through it in a continuous loop.

    python scene_animated.py

What the tokens do, which is what the platform does:

  * every token leaves the agents, runs along the ground path and climbs onto the Decide tile;
  * most are allowed there: they turn green, pick up a tick, cross Credential and Record and
    run on to the business systems;
  * some are refused there: they turn red, pick up a cross and go no further;
  * some are held for a person: they turn amber, wait on the Approve tile, and are then
    either approved (tick, on via Record to the systems) or rejected (cross, no further).

The animation is SMIL inside the SVG, so the file is self-contained: it plays in a browser,
in an <img> tag and in anything else that renders animated SVG. PowerPoint does not animate
SVG; a slide needs a video or GIF captured from this file.

Geometry comes from scene.py: the same projection, the same world coordinates.
"""
import math
import pathlib

HERE = pathlib.Path(__file__).parent
C30 = math.cos(math.pi / 6)


def P(x, y, z=0.0):
    """World to scene coordinates, as in scene.py."""
    return ((x - y) * C30, (x + y) * 0.5 - z)


# ---- where things are (world coordinates from scene.py) ----
TILE_TOP = 0.55 + 0.22                    # platform top plus a tile's thickness
AGENTS = P(-4.8, 0.0)                     # the path's start, under the agents' cubes
EDGE_IN = P(-2.75, 0.0)                   # where the ground path passes under the platform
DECIDE = P(-1.1, 1.1, TILE_TOP)           # tile centres
APPROVE = P(-1.1, -1.1, TILE_TOP)
CREDENTIAL = P(1.1, 1.1, TILE_TOP)
RECORD = P(1.1, -1.1, TILE_TOP)
EDGE_OUT = P(0.0, -2.75)                  # where the ground path comes out again
SYSTEMS = P(0.0, -4.8)                    # the path's end, under the systems' blocks

# ---- timing, in seconds ----
CYCLE = 16.0                              # the loop: every token repeats after this long
SPACING = 2.0                             # one token sets off every this long
ORDER = ["allow", "deny", "allow", "hold_ok", "allow", "allow", "deny", "hold_no"]
assert len(ORDER) * SPACING == CYCLE

T_EDGE = 2.0                              # reaches the platform
T_DECIDE = 2.7                            # is on the Decide tile
T_VERDICT = 3.4                           # the decision is made
T_PERSON = 6.3                            # a held token's person decides

BLUE, GREEN, RED, AMBER, WHITE = "#1499FE", "#22C55E", "#EF4444", "#F59E0B", "#FFFFFF"


# ---- SMIL helpers ----
def _times(frames):
    return ";".join(f"{t / CYCLE:.5f}" for t, _ in frames)


def _whole(frames):
    """Pads keyframes so that they span the whole cycle."""
    frames = list(frames)
    if frames[0][0] > 0:
        frames.insert(0, (0.0, frames[0][1]))
    if frames[-1][0] < CYCLE:
        frames.append((CYCLE, frames[-1][1]))
    return frames


def _loop(offset):
    # A negative begin starts each token part-way through its loop, so the flow is already
    # running in the first frame.
    return f'dur="{CYCLE:g}s" begin="-{offset:g}s" repeatCount="indefinite"'


def move(frames, offset):
    frames = _whole(frames)
    values = ";".join(f"{x:.4f} {y:.4f}" for _, (x, y) in frames)
    return (f'<animateTransform attributeName="transform" type="translate" calcMode="linear" '
            f'values="{values}" keyTimes="{_times(frames)}" {_loop(offset)}/>')


def scale(frames, offset):
    frames = _whole(frames)
    values = ";".join(f"{v:g}" for _, v in frames)
    return (f'<animateTransform attributeName="transform" type="scale" calcMode="linear" '
            f'values="{values}" keyTimes="{_times(frames)}" {_loop(offset)}/>')


def fade(frames, offset):
    frames = _whole(frames)
    values = ";".join(f"{v:g}" for _, v in frames)
    return (f'<animate attributeName="opacity" calcMode="linear" values="{values}" '
            f'keyTimes="{_times(frames)}" {_loop(offset)}/>')


def step(attribute, frames, offset):
    """A value that changes at once: each holds until the next begins."""
    values = ";".join(v for _, v in frames)
    return (f'<animate attributeName="{attribute}" calcMode="discrete" values="{values}" '
            f'keyTimes="{_times(frames)}" {_loop(offset)}/>')


def shown(start, end, fade_out=0.02):
    """Opacity keyframes: invisible, then visible from start to end."""
    frames = []
    if start > 0:
        frames += [(0.0, 0), (max(start - 0.02, 0.0), 0)]
    frames += [(start, 1), (end, 1), (end + fade_out, 0)]
    return frames


# ---- what a token is drawn as ----
MARKS = {
    "tick": '<path d="M-.095 .005 -.03 .07 .1 -.075"/>',
    "cross": '<path d="M-.07 -.07 .07 .07M.07 -.07 -.07 .07"/>',
    "wait": '<path d="M-.045 -.07V.07M.045 -.07V.07"/>',
}


def badge(mark, colour, animation=""):
    """The verdict, riding above its token."""
    return (f'<g transform="translate(0 -.46)" opacity="{0 if animation else 1}">{animation[0] if animation else ""}'
            f'<g>{animation[1] if animation else ""}'
            f'<circle r=".2" fill="{colour}" stroke="{WHITE}" stroke-width=".035"/>'
            f'<g fill="none" stroke="{WHITE}" stroke-width=".055" stroke-linecap="round" '
            f'stroke-linejoin="round">{MARKS[mark]}</g></g></g>')


def appearing(start, end, offset):
    """A badge's animations: there from start to end, arriving with a small pop."""
    frames = [(0.0, 0), (max(start - 0.02, 0.0), 0), (start, 1)]
    if end is not None:
        frames += [(end, 1), (end + 0.02, 0)]
    pop = [(0.0, 0.2), (start, 0.2), (start + 0.18, 1.2), (start + 0.34, 1.0)]
    return fade(frames, offset), scale(pop, offset)


def dot(fill, stroke, animation=""):
    return (f'<circle r=".3" fill="{fill if fill != WHITE else stroke}" opacity=".16">'
            f'{animation and animation[2]}</circle>'
            f'<circle r=".15" fill="{fill}" stroke="{stroke}" stroke-width=".055">'
            f'{animation and animation[0] + animation[1]}</circle>')


def token(kind, offset):
    """One token: what goes on the ground layer, and what goes on top of the platform."""
    ground, top = [], []

    # In along the ground, from under the agents to the platform's edge.
    ground.append(f'<g opacity="0">{move([(0.0, AGENTS), (T_EDGE, EDGE_IN)], offset)}'
                  f'{fade([(0.0, 1), (T_EDGE, 1), (T_EDGE + 0.02, 0)], offset)}'
                  f'{dot(WHITE, BLUE)}</g>')

    # Over the platform. Every token climbs to Decide and waits there for its verdict.
    path = [(T_EDGE, EDGE_IN), (T_DECIDE, DECIDE), (T_VERDICT, DECIDE)]
    fills, strokes, badges = [(0.0, WHITE)], [(0.0, BLUE)], []
    leaves = None                         # when it runs on to the systems, if it does

    if kind == "allow":
        path += [(4.9, CREDENTIAL), (6.4, RECORD), (7.0, EDGE_OUT)]
        fills.append((T_VERDICT, GREEN)); strokes.append((T_VERDICT, WHITE))
        badges.append(badge("tick", GREEN, appearing(T_VERDICT, None, offset)))
        visible, leaves = shown(T_EDGE, 7.0), 7.0
    elif kind == "deny":
        path += [(4.6, (DECIDE[0], DECIDE[1] + 0.12))]
        fills.append((T_VERDICT, RED)); strokes.append((T_VERDICT, WHITE))
        badges.append(badge("cross", RED, appearing(T_VERDICT, None, offset)))
        visible = shown(T_EDGE, 4.0, fade_out=0.6)
    else:
        path += [(4.9, APPROVE), (T_PERSON, APPROVE)]
        fills.append((T_VERDICT, AMBER)); strokes.append((T_VERDICT, WHITE))
        badges.append(badge("wait", AMBER, appearing(T_VERDICT, T_PERSON, offset)))
        if kind == "hold_ok":
            path += [(7.8, RECORD), (8.4, EDGE_OUT)]
            fills.append((T_PERSON, GREEN))
            badges.append(badge("tick", GREEN, appearing(T_PERSON, None, offset)))
            visible, leaves = shown(T_EDGE, 8.4), 8.4
        else:
            path += [(7.5, (APPROVE[0], APPROVE[1] + 0.12))]
            fills.append((T_PERSON, RED))
            badges.append(badge("cross", RED, appearing(T_PERSON, None, offset)))
            visible = shown(T_EDGE, 6.9, fade_out=0.6)

    colours = (step("fill", fills, offset), step("stroke", strokes, offset), step("fill", [(t, c if c != WHITE else BLUE) for t, c in fills], offset))
    top.append(f'<g opacity="0">{move(path, offset)}{fade(visible, offset)}'
               f'{dot(WHITE, BLUE, colours)}{"".join(badges)}</g>')

    # Out along the ground, from the platform's edge to under the systems.
    if leaves is not None:
        ground.append(f'<g opacity="0">{move([(leaves, EDGE_OUT), (leaves + 2.0, SYSTEMS)], offset)}'
                      f'{fade(shown(leaves, leaves + 2.0), offset)}'
                      f'{dot(GREEN, WHITE)}{badge("tick", GREEN)}</g>')
    return ground, top


def main():
    lines = (HERE / "scene.svg").read_text(encoding="utf-8").split("\n")

    # The four still dots on the ground path make way for the moving ones.
    still = [i for i, line in enumerate(lines) if line.startswith("<circle ") and 'r="0.13"' in line]
    assert len(still) == 4, still
    first = still[0]
    lines = [line for i, line in enumerate(lines) if i not in still]

    ground, top = [], []
    for i, kind in enumerate(ORDER):
        g, t = token(kind, i * SPACING)
        ground += g
        top += t

    # The ground layer goes where the still dots were: above the path and below every cube,
    # so that a token comes out from under the agents and goes in under the systems, and is
    # hidden by the platform while it passes beneath it.
    lines.insert(first, '<g id="tokens-ground">\n' + "\n".join(ground) + "\n</g>")

    # The top layer is the last thing drawn inside the scene's group, above the tiles.
    end = max(i for i, line in enumerate(lines) if line.strip().endswith("</g></svg>"))
    lines[end] = lines[end].replace("</g></svg>", "")
    lines += ['<g id="tokens-top">', *top, "</g>", "</g></svg>"]

    out = HERE / "scene-animated.svg"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", out.name, out.stat().st_size, "bytes;", len(ORDER), "tokens,", f"{CYCLE:g}s loop")


if __name__ == "__main__":
    main()
