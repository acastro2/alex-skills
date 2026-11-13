"""Brand marks, cleaned for embedding: name -> (viewBox, inner markup)."""
import base64, re
from pathlib import Path

D = Path(__file__).parent / "logos"

def _svg(name, fixes=(), fill=None):
    s = (D / f"{name}.svg").read_text(encoding="utf-8")
    s = re.sub(r"<\?xml.*?\?>", "", s)
    s = re.sub(r"<style>.*?</style>", "", s, flags=re.S)
    s = re.sub(r"<title>.*?</title>", "", s, flags=re.S)
    for a, b in fixes:
        s = s.replace(a, b)
    head = re.search(r"<svg[^>]*>", s).group(0)
    vb = re.search(r'viewBox="([^"]+)"', head)
    if vb:
        vb = vb.group(1)
    else:
        w = re.search(r'width="([\d.]+)"', head).group(1); h = re.search(r'height="([\d.]+)"', head).group(1)
        vb = f"0 0 {w} {h}"
    inner = s[s.index(head) + len(head): s.rindex("</svg>")]
    p = f"lg{name}"
    inner = re.sub(r'id="([^"]+)"', lambda m: f'id="{p}{m.group(1)}"', inner)
    inner = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{p}{m.group(1)})', inner)
    inner = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{p}{m.group(1)}"', inner)
    if fill:
        inner = f'<g fill="{fill}">{inner}</g>'
    return vb, inner

def get():
    png = base64.b64encode((D / "sn_crop.png").read_bytes()).decode()
    return {
        "claude": _svg("claude", fill="#D97757"),
        "openai": _svg("openai", [("var(--primary-fill)", "none"), ("var(--secondary-fill)", "#000000")]),
        "copilot": _svg("copilot"),
        "sap": _svg("sap", fill="#0FAAFF"),
        "workday": _svg("workday"),
        "salesforce": _svg("salesforce"),
        # Simple Icons 13.21.0 (CC0), for the case study's sources.
        "youtube": _svg("youtube", fill="#FF0000"),
        "x": _svg("x", fill="#000000"),
        "ycombinator": _svg("ycombinator", fill="#F0652F"),
        "servicenow": ("0 0 667 166", f'<image width="667" height="166" href="data:image/png;base64,{png}"/>'),
    }
