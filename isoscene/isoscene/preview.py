"""Render an SVG to PNG with a local Chromium (Edge or Chrome, headless), to look at a scene.

    python -m isoscene.preview scene.svg [out.png] [--width 1200 --height 760] [--phone]

--phone renders at 390 px wide as well (out-phone.png), the width the sites are checked at.
Set ISOSCENE_BROWSER to a browser executable to use one that is not found automatically.
Animated scenes are captured at their first frame.
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def browser():
    env = os.environ.get("ISOSCENE_BROWSER")
    if env:
        return env
    for c in CANDIDATES:
        if os.path.exists(c):
            return c
    for name in ("chromium", "chromium-browser", "google-chrome", "microsoft-edge", "msedge", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    sys.exit("No Chromium browser found; set ISOSCENE_BROWSER to Edge or Chrome.")


def size_of(svg):
    head = svg.read_text(encoding="utf-8")[:400]
    w = re.search(r'width="([\d.]+)"', head)
    h = re.search(r'height="([\d.]+)"', head)
    return (int(float(w.group(1))), int(float(h.group(1)))) if w and h else (1200, 760)


def shoot(svg, png, width, height, bg="#11161F"):
    """Shoot the SVG scaled to width x height on a dark ground (the sites' background)."""
    page = (f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:{bg}}}'
            f'img{{display:block;width:{width}px;height:{height}px}}</style>'
            f'<img src="{svg.resolve().as_uri()}">')
    png = png.resolve()
    png.unlink(missing_ok=True)
    # On Windows the browser hands off to a background process and returns before the screenshot
    # is written, then holds its profile for a moment: wait for the file, and ignore a failed
    # clean-up of the temporary profile.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        html = pathlib.Path(d) / "p.html"
        html.write_text(page, encoding="utf-8")
        subprocess.run([browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", f"--user-data-dir={d}/profile",
                        f"--window-size={width},{height}", f"--screenshot={png}",
                        html.resolve().as_uri()],
                       check=True, capture_output=True, timeout=60)
        for _ in range(150):
            if png.exists() and png.stat().st_size > 0:
                time.sleep(0.3)  # let the write finish
                break
            time.sleep(0.1)
        else:
            sys.exit(f"The browser did not write {png}.")
    print("wrote", png)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("svg")
    ap.add_argument("png", nargs="?")
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--phone", action="store_true")
    a = ap.parse_args()
    svg = pathlib.Path(a.svg)
    png = pathlib.Path(a.png) if a.png else svg.with_suffix(".png")
    w0, h0 = size_of(svg)
    w = a.width or (w0 if w0 <= 1600 else 1600)
    h = a.height or round(w * h0 / w0)
    shoot(svg, png, w, h)
    if a.phone:
        shoot(svg, png.with_name(png.stem + "-phone.png"), 390, round(390 * h0 / w0))


if __name__ == "__main__":
    main()
