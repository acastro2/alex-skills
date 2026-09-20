#!/usr/bin/env python3
"""Render an Architecture Weekly page body from content JSON into CanvasContent1.

WHY THIS EXISTS
---------------
The page body used to be written freehand by the model each week from prose in
SKILL.md, so every issue drifted a little. This script owns ALL the markup. The run
supplies content only, never HTML. Same input, same page, every week.

    recap-content.json  ->  render_page.py  ->  canvas.json  ->  stage_news_recap.py

WHO CONSUMES THE OUTPUT
-----------------------
`stage_news_recap.py --kind recap --id <page_id> --canvas canvas.json`. That script
does the SharePoint plumbing; this one only builds the body.

SHAREPOINT RULES THE MARKUP OBEYS (verified against live page canvases, 2026-09-18)
-----------------------------------------------------------------------------------
1. Inline `style` attributes survive in the stored canvas AND on a published page.
   108 of them read back byte-identical on 2026-09-09-AAB-Recap.aspx.
2. `h1`/`h2`/`h3`, `p`, `ul`/`li`, `strong`, `em`, `span`, `a`, `table` and styled
   `div` containers all survive. A div carrying background, padding, border-radius and
   a 6px left border read back whole.
3. `class=`, `<style>` blocks and custom elements are NOT emitted. The page is a
   Text web part edited by a human in the SharePoint rich text editor, so the markup
   must be plain and editable.
4. NO `font-family`. The site renders Segoe UI from its theme and the page inherits
   it, so the page stays consistent with every other page on the site. Hierarchy comes
   from size, weight, colour and letter-spacing.
5. No fixed pixel page width and no page background. The SharePoint page section owns
   the width; the design's 600px email card and grey page background are email-only
   artefacts and are dropped.

The palette is the one Alex approved from the Claude Design mock on 2026-09-18. It is
deliberately NOT the Attain brand palette; he asked for the mock's colours.

    navy band      #12395C      teal header rule  #0E8FA8
    shipped band   #1A4E7A      shipped surface     #E6F0F7
    exec + light   #E6F0F7      card border top     #1A4E7A
    section title  #12395C      micro-label         #1A4E7A
    body text      #23303B      rationale text      #3C4A55
    muted text     #55636E      links               #0E6E96
    borders        #D4DDE4      shipped divider     #CFE0EE
    on navy: date #C7DCEB, eyebrow #7FD4E8, shipped eyebrow #A9CCE4, footer #9FBFD6
    callouts: green bg #E7F3ED / edge #1C6B4A / lead #155A3D
              amber bg #FBF1DF / edge #A2620A / text #3A2F1C / divider #EBDCBE
    exec divider #C3D6E4      on-band text #FFFFFF

Every colour the page emits is a named constant below. A bare hex in a builder is
drift: name it, and add it to this list too.

USAGE
-----
    python3 render_page.py recap-content.json canvas.json
    python3 render_page.py --check-only canvas.json     # validate a rendered canvas
    python3 render_page.py --text canvas.json           # plain text, for voice_check.py

`references/example-content.json` is a complete, valid input. It is the worked example
and the smoke test: render it after any change to this script.

The script refuses rather than warning, on markup AND on content shape. A failure here
means the template was edited or the content is incomplete, and neither must happen
quietly. Content is checked all the way down, not just at the top level, so a missing
`rationale` on one decision is a named error and not a traceback.

CONTENT SCHEMA (every key below is required; only `decisions[].lead`,
`exec_summary.points[].lead` and `actions[].due` may be omitted or empty)
---------------------------------------------------------------------------
{
  "title":     "Architecture Weekly — September 16, 2026",
  "subtitle":  "Forum held Wednesday 16 September. Delivery covering 12 to 18 September 2026.",
  "exec_summary": {                       # REQUIRED; the ELT reader's gate
    "headline": "One sentence, plain words, no acronyms.",
    "points":   [{"lead": "Bold lead-in.", "text": "What it means."}],   # 3 or 4
    "footer":   "The line that says whether leadership must act."
  },
  "objective": "Text.",
  "outcome":   {"tag": "Achieved", "text": "Text."},   # tag: Achieved | Partially achieved | Not achieved
  "tldr":      "Text.",
  "decisions": [{"lead": "Bold first sentence.", "text": "Rest.", "rationale": "Text.", "owner": "Name (role)"}],
  "actions":   [{"action": "Text.", "owner": "Name", "due": "Next sprint"}],   # due may be ""
  "topics":    [{"title": "Short name.", "summary": "Two sentences max.", "tag": "Decided"}],
                                                       # tag: Decided | Needs follow-up | Parked
  "open_questions": ["Text."],
  "artifacts":      ["Document name. Screen-shared; file name not stated."],
  "speakers":       "Alexandre Castro, Chris Goodrich, ...",
  "speakers_source": "Teams meeting transcript, 3:00pm to 4:01pm Central.",
  "shipped": {"window": "12 to 18 September 2026",
              "items": [{"sentence": "Outcome-first sentence.",
                         "evidence": [{"label": "Network and transit access", "url": "https://..."}]}]}
}
"""
import json
import re
import sys
from html import unescape

# --- palette -----------------------------------------------------------------
NAVY = "#12395C"
SHIPPED_BAND = "#1A4E7A"
TEAL = "#0E8FA8"
LIGHT = "#E6F0F7"
BODY = "#23303B"
RATIONALE = "#3C4A55"
MUTED = "#55636E"
LABEL = "#1A4E7A"
LINK = "#0E6E96"
BORDER = "#D4DDE4"
SHIPPED_DIVIDER = "#CFE0EE"
EYEBROW_ON_NAVY = "#7FD4E8"
DATE_ON_NAVY = "#C7DCEB"
SHIPPED_EYEBROW = "#A9CCE4"
FOOTER_ON_NAVY = "#9FBFD6"
EXEC_DIVIDER = "#C3D6E4"
ON_BAND = "#FFFFFF"       # text on the navy and shipped bands

GREEN_BG, GREEN_EDGE, GREEN_LEAD = "#E7F3ED", "#1C6B4A", "#155A3D"
AMBER_BG, AMBER_EDGE, AMBER_TEXT, AMBER_DIV = "#FBF1DF", "#A2620A", "#3A2F1C", "#EBDCBE"

TOPIC_TAG_COLOR = {"Decided": GREEN_LEAD, "Needs follow-up": AMBER_EDGE, "Parked": MUTED}
OUTCOME_TAGS = ("Achieved", "Partially achieved", "Not achieved")
OUTCOME_GREEN = {"Achieved"}

# SKILL.md, Executive Summary gate. Enforced, not suggested: a band that quietly comes
# out at two points is the drift this script exists to stop, and it is the line Alex
# reads most closely.
EXEC_POINTS_MIN, EXEC_POINTS_MAX = 3, 4

# --- validation ---------------------------------------------------------------
FORBIDDEN = [
    "class=", "<style", "</style", "mso-", "@media", "sc-raw", "sc-camel", "<x-dc",
    'role="presentation"', "font-family", "position:", "<script", "<!--",
    "data-sp-", "display:flex", "display:grid",
]


def die(msg):
    print(f"RENDER FAILED: {msg}", file=sys.stderr)
    raise SystemExit(1)


def esc(s):
    """Escape for HTML text nodes. Content is prose; it must never become markup."""
    if not isinstance(s, str):
        die(f"expected a string, got {type(s).__name__}: {s!r}")
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def esc_attr(s):
    return esc(s).replace('"', "&quot;")


def safe_url(u):
    if not isinstance(u, str):
        die(f"evidence url must be a string, got {u!r}")
    if u.startswith("https://") or u.startswith("/sites/"):
        return esc_attr(u)
    die(f"evidence url must be https:// or /sites/... — got {u!r}")


def link(url, label):
    return (f'<a href="{safe_url(url)}" style="color:{LINK};text-decoration:underline;">'
            f"{esc(label)}</a>")


# --- content validation -------------------------------------------------------
# Every key is named where it lives, so a failure says "decisions[2].rationale" and not
# KeyError. The top-level-only check this replaces let a missing nested key reach the
# builders and come out as a traceback, which reads like the script is broken.
def need(obj, key, where, kind=str, allow_empty=False):
    if not isinstance(obj, dict):
        die(f"{where} must be an object, got {type(obj).__name__}")
    if key not in obj:
        die(f"{where} is missing required key {key!r}")
    value = obj[key]
    if not isinstance(value, kind):
        die(f"{where}.{key} must be {kind.__name__}, got {type(value).__name__}")
    if not allow_empty and not value:
        die(f"{where}.{key} is empty; fill it or the page ships with a hole in it")
    return value


def need_list(obj, key, where, min_len=1):
    items = need(obj, key, where, kind=list, allow_empty=min_len == 0)
    if len(items) < min_len:
        die(f"{where}.{key} needs at least {min_len} item(s), got {len(items)}")
    return items


def check_content(c):
    for key in ("title", "subtitle", "objective", "tldr", "speakers", "speakers_source"):
        need(c, key, "content")

    e = need(c, "exec_summary", "content", kind=dict)
    need(e, "headline", "exec_summary")
    # Never blank, and never softened into silence: SKILL.md, Executive Summary gate.
    need(e, "footer", "exec_summary")
    points = need_list(e, "points", "exec_summary", min_len=EXEC_POINTS_MIN)
    if len(points) > EXEC_POINTS_MAX:
        die(f"exec_summary.points has {len(points)}; SKILL.md sets {EXEC_POINTS_MIN} to "
            f"{EXEC_POINTS_MAX}. Merge two points, do not widen the band.")
    for i, pt in enumerate(points):
        need(pt, "text", f"exec_summary.points[{i}]")
        if "lead" in pt:
            need(pt, "lead", f"exec_summary.points[{i}]", allow_empty=True)

    o = need(c, "outcome", "content", kind=dict)
    need(o, "text", "outcome")
    tag = need(o, "tag", "outcome")
    if tag not in OUTCOME_TAGS:
        die(f"outcome.tag must be one of {list(OUTCOME_TAGS)} — got {tag!r}. A typo here "
            f"renders amber and reads to the org as 'Partially achieved'.")

    for i, d in enumerate(need_list(c, "decisions", "content")):
        where = f"decisions[{i}]"
        for key in ("text", "rationale", "owner"):
            need(d, key, where)

    for i, a in enumerate(need_list(c, "actions", "content")):
        where = f"actions[{i}]"
        need(a, "action", where)
        need(a, "owner", where)
        if "due" in a:
            need(a, "due", where, allow_empty=True)

    for i, t in enumerate(need_list(c, "topics", "content")):
        where = f"topics[{i}]"
        need(t, "title", where)
        need(t, "summary", where)
        if need(t, "tag", where) not in TOPIC_TAG_COLOR:
            die(f"{where}.tag must be one of {sorted(TOPIC_TAG_COLOR)} — got {t['tag']!r}")

    for key in ("open_questions", "artifacts"):
        for i, item in enumerate(need_list(c, key, "content")):
            if not isinstance(item, str) or not item.strip():
                die(f"{key}[{i}] must be a non-empty string, got {item!r}")

    sh = need(c, "shipped", "content", kind=dict)
    need(sh, "window", "shipped")
    for i, it in enumerate(need_list(sh, "items", "shipped")):
        where = f"shipped.items[{i}]"
        need(it, "sentence", where)
        # An item with no evidence renders as a bare "Evidence:" with nothing after it.
        # The panel's whole claim is that it is evidence-backed, so this is a hard stop.
        for j, ev in enumerate(need_list(it, "evidence", where)):
            need(ev, "label", f"{where}.evidence[{j}]")
            need(ev, "url", f"{where}.evidence[{j}]")


# --- block builders -----------------------------------------------------------
def rule(color=TEAL, width="48px", height="3px"):
    return (f'<div style="background-color:{color};height:{height};width:{width};'
            f'line-height:{height};font-size:0;margin-bottom:6px;">&nbsp;</div>')


def micro_label(text, top="26px"):
    """Literal uppercase, not text-transform. The design uses literal caps and the
    property would be one more thing the rich text editor could drop on save."""
    return (f'<h3 style="margin:{top} 0 8px 0;font-size:12px;line-height:16px;'
            f'letter-spacing:1.5px;color:{LABEL};font-weight:400;">'
            f"{esc(text.upper())}</h3>")


def section_title(text):
    """Heading only. There used to be a 48px accent rule under it, and it read as a stray
    underline that collided with the top border of the block below (Alex, 2026-09-18: "just
    remove the underline"). Do not bring it back."""
    return (f'<h2 style="margin:34px 0 14px 0;font-size:22px;line-height:28px;'
            f'color:{NAVY};font-weight:400;">{esc(text)}</h2>')


def callout(bg, edge, inner):
    border = f"border-left:4px solid {edge};"
    return f'<div style="background-color:{bg};{border}padding:16px 18px;">{inner}</div>'


def band(bg, inner, pad="24px 26px"):
    return f'<div style="background-color:{bg};padding:{pad};">{inner}</div>'


def p(text, size="15px", line="23px", color=BODY, **extra):
    styles = [f"margin:{extra.pop('margin', '0 0 12px 0')}", f"font-size:{size}",
              f"line-height:{line}", f"color:{color}"]
    styles += [f"{k.replace('_', '-')}:{v}" for k, v in extra.items()]
    return f'<p style="{";".join(styles)};">{text}</p>'


# --- sections -----------------------------------------------------------------
def header(c):
    inner = (f'<div style="font-size:12px;line-height:16px;letter-spacing:2px;'
             f'color:{EYEBROW_ON_NAVY};margin-bottom:8px;">ENTERPRISE ARCHITECTURE</div>'
             f'<h1 style="margin:0 0 8px 0;font-size:27px;line-height:33px;'
             f'color:{ON_BAND};font-weight:400;">{esc(c["title"])}</h1>'
             f'<div style="font-size:14px;line-height:20px;color:{DATE_ON_NAVY};">'
             f'{esc(c["subtitle"])}</div>')
    return band(NAVY, inner, "26px 26px 24px 26px") + rule(height="4px", width="100%")


def exec_summary(c):
    # Required, not optional. This band is the one component SKILL.md calls the ELT
    # reader's gate; the script used to skip it silently when the key was absent, which
    # is the one omission nobody would notice until the page was already staged.
    e = c["exec_summary"]
    parts = [micro_label("Executive summary", top="0"),
             f'<h2 style="margin:0 0 16px 0;font-size:19px;line-height:27px;'
             f'color:{NAVY};font-weight:400;">{esc(e["headline"])}</h2>']
    for pt in e["points"]:
        lead = f'<strong style="color:{NAVY};">{esc(pt["lead"])}</strong> ' if pt.get("lead") else ""
        parts.append(p(lead + esc(pt["text"])))
    if e.get("footer"):
        parts.append(f'<p style="margin:14px 0 0 0;padding-top:14px;font-size:14px;'
                     f'line-height:20px;color:{MUTED};border-top:1px solid {EXEC_DIVIDER};">'
                     f'{esc(e["footer"])}</p>')
    return band(LIGHT, "".join(parts), "26px 26px 24px 26px")


def outcome_block(c):
    o = c["outcome"]
    tag = o["tag"]   # vocabulary checked in check_content
    bg = GREEN_BG if tag in OUTCOME_GREEN else AMBER_BG
    edge = GREEN_EDGE if tag in OUTCOME_GREEN else AMBER_EDGE
    lead = GREEN_LEAD if tag in OUTCOME_GREEN else AMBER_EDGE
    inner = f'<strong style="color:{lead};">{esc(tag)}.</strong> {esc(o["text"])}'
    return callout(bg, edge, p(inner, size="15px", line="23px"))


def decision_cards(c):
    out = []
    for d in c["decisions"]:
        lead = f'<strong>{esc(d["lead"])}</strong> ' if d.get("lead") else ""
        out.append(
            f'<div style="border:1px solid {BORDER};border-top:3px solid {SHIPPED_BAND};'
            f'padding:16px 18px;margin-top:14px;">'
            f'<p style="margin:0 0 6px 0;font-size:15px;line-height:23px;color:{NAVY};">{lead}{esc(d["text"])}</p>'
            f'<div style="font-size:11px;line-height:15px;letter-spacing:1.2px;color:{LINK};'
            f'margin-bottom:4px;">RATIONALE</div>'
            f'<p style="margin:0 0 12px 0;font-size:14px;line-height:21px;color:{RATIONALE};">'
            f'{esc(d["rationale"])}</p>'
            f'<p style="margin:0;font-size:13px;line-height:19px;color:{MUTED};">'
            f'<span style="color:{LINK};">Owner</span> &nbsp;{esc(d["owner"])}</p>'
            f"</div>")
    return "".join(out)


def action_table(c):
    th = (f'background-color:{NAVY};border:1px solid {NAVY};padding:9px 11px;'
          f'color:{ON_BAND};text-align:left;font-size:14px;font-weight:400;')
    td = (f'border:1px solid {BORDER};padding:9px 11px;vertical-align:top;'
          f'color:{BODY};font-size:14px;line-height:20px;')
    # An empty Due cell, never a dash. House rule: do not repeat "Not stated" down a column; the
    # footnote under the table carries it. A dash would also be an em dash, which is banned.
    rows = "".join(
        f"<tr><td style=\"{td}\">{esc(a['action'])}</td>"
        f"<td style=\"{td}\">{esc(a['owner'])}</td>"
        f"<td style=\"{td}\">{esc(a.get('due') or '')}</td></tr>"
        for a in c["actions"])
    return (f'<table style="width:100%;border-collapse:collapse;margin-top:10px;">'
            f'<thead><tr><th style="{th}">Action</th><th style="{th}">Owner</th>'
            f'<th style="{th}">Due</th></tr></thead><tbody>{rows}</tbody></table>')


def topic_list(c):
    items = []
    for t in c["topics"]:
        color = TOPIC_TAG_COLOR.get(t["tag"])
        if not color:
            die(f"topic tag must be one of {sorted(TOPIC_TAG_COLOR)} — got {t['tag']!r}")
        items.append(
            f'<li style="margin-bottom:12px;font-size:15px;line-height:23px;color:{BODY};">'
            f'<strong>{esc(t["title"])}</strong> {esc(t["summary"])} '
            f'<span style="color:{color};">[{esc(t["tag"])}]</span></li>')
    return f'<ul style="margin:14px 0 0 0;padding-left:22px;">{"".join(items)}</ul>'


def bullet_list(items, amber=False):
    if amber:
        rows = []
        for i, q in enumerate(items):
            border = f"border-top:1px solid {AMBER_DIV};" if i else ""
            rows.append(f'<p style="margin:0;padding:8px 0;font-size:15px;line-height:22px;'
                        f'color:{AMBER_TEXT};{border}">{esc(q)}</p>')
        return callout(AMBER_BG, AMBER_EDGE, "".join(rows))
    lis = "".join(f'<li style="margin-bottom:8px;font-size:15px;line-height:23px;color:{BODY};">'
                  f"{esc(x)}</li>" for x in items)
    return f'<ul style="margin:14px 0 0 0;padding-left:22px;">{lis}</ul>'


def speakers_line(c):
    return (f'<p style="margin:26px 0 0 0;padding-top:14px;border-top:1px solid {BORDER};'
            f'font-size:13px;line-height:20px;color:{MUTED};font-style:italic;">'
            f'Spoke in this session: {esc(c["speakers"])}. '
            f'Source: {esc(c["speakers_source"])}</p>')


def shipped_panel(c):
    s = c["shipped"]
    head = (f'<h2 style="margin:0 0 4px 0;font-size:21px;line-height:28px;color:{ON_BAND};'
            f'font-weight:400;">What Enterprise Architecture shipped</h2>'
            f'<div style="font-size:13px;line-height:19px;color:{SHIPPED_EYEBROW};">'
            f'{esc(s["window"])}</div>')
    items = []
    for it in s["items"]:
        ev = " &middot; ".join(link(e["url"], e["label"]) for e in it["evidence"])
        items.append(
            f'<p style="margin:0;padding:14px 0 4px 0;font-size:15px;line-height:22px;'
            f'color:{NAVY};border-top:1px solid {SHIPPED_DIVIDER};"><strong>{esc(it["sentence"])}</strong></p>'
            f'<p style="margin:0;padding:0 0 12px 0;font-size:13px;line-height:19px;'
            f'color:{MUTED};">Evidence: {ev}</p>')
    inner = (f'<div style="background-color:{LIGHT};padding:18px;">{"".join(items)}</div>')
    return (f'<div style="background-color:{SHIPPED_BAND};padding:26px 26px 30px 26px;'
            f'margin-top:34px;">{head}<div style="height:14px;font-size:0;line-height:0;">&nbsp;</div>'
            f"{inner}</div>")


def build(c):
    body = [header(c), exec_summary(c)]
    body.append(section_title("Forum recap"))
    body.append(micro_label("Objective") + p(esc(c["objective"])))
    body.append(micro_label("Outcome") + outcome_block(c))
    body.append(micro_label("TL;DR") + p(esc(c["tldr"])))
    body.append(section_title("Decisions made") + decision_cards(c))
    body.append(section_title("Action items") + action_table(c)
                + p("An empty Due cell means no date was stated in the session.",
                    size="13px", color=MUTED, margin="10px 0 0 0"))
    body.append(section_title("Topics discussed") + topic_list(c))
    body.append(section_title("Open questions and risks")
                + bullet_list(c["open_questions"], amber=True))
    body.append(section_title("Artifacts referenced") + bullet_list(c["artifacts"]))
    body.append(speakers_line(c))
    body.append(shipped_panel(c))
    return "".join(body)


def markup_only(html):
    """Everything inside a tag, and nothing outside one.

    Every text node is run through esc() first, so `<` and `>` reach the body only as
    tag delimiters. That makes this split exact: what comes back is the markup this
    script generated, with all author-supplied prose removed.

    It has to be exact, because the forbidden-construct scan used to run over the whole
    body and so fired on ordinary sentences. "What is our position: buy or build?" in an
    open question hit `position:` and failed the render with a message about markup.
    """
    return "".join(re.findall(r"<[^>]*>", html))


def prose_only(html):
    """The text nodes, minus the <h1> title. Used for the dash ban, which is about what
    Alex writes and not about what the builders emit."""
    return re.sub(r"<[^>]*>", " ", re.sub(r"<h1.*?</h1>", "", html, flags=re.S))


def to_text(html):
    """Plain text of the rendered page, for `voice_check.py`.

    recap.md requires the voice check to run on the RENDERED page and not on the content
    JSON, because the renderer's own cosmetic characters count as prose. Without this the
    instruction needed a hand-rolled tag strip every week, which is exactly the kind of
    manual step that quietly stops happening."""
    text = re.sub(r"<(?:br\s*/?|/(?:p|h1|h2|h3|li|div|tr|table|ul|thead|tbody))>", "\n", html)
    text = re.sub(r"<[^>]*>", " ", text)
    text = unescape(text).replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line) + "\n"


def validate(html):
    markup = markup_only(html)
    for bad in FORBIDDEN:
        if bad in markup:
            die(f"forbidden construct in the MARKUP: {bad!r}. The markup is owned by this "
                f"script; edit the builders, not the output.")
    if "{{" in markup:
        die("unsubstituted token in output")
    # Dashes are banned in everything Alex writes, except the house-format <h1> title
    # separator. The renderer leaked an em dash through the Action items empty-cell
    # placeholder on 2026-09-18, which is why this is a hard check and not a checklist note.
    prose = prose_only(html)
    for char, name in (("\u2014", "em dash"), ("\u2013", "en dash")):
        if char in prose:
            die(f"{name} outside the <h1> title. Alex bans them; use a comma, a colon, "
                f"or a full stop.")


def read_canvas(path):
    try:
        canvas = json.load(open(path))
    except (OSError, ValueError) as err:
        die(f"cannot read canvas {path!r}: {err}")
    try:
        return canvas[0]["innerHTML"]
    except (KeyError, IndexError, TypeError):
        die(f"{path!r} is not a CanvasContent1 array with an innerHTML body")


def main():
    args = sys.argv[1:]
    if not args:
        die(__doc__.split("USAGE")[1].split("`references/example")[0].strip())
    if args[0] in ("--check-only", "--text"):
        if len(args) != 2:
            die(f"usage: render_page.py {args[0]} <canvas.json>")
        body = read_canvas(args[1])
        if args[0] == "--text":
            sys.stdout.write(to_text(body))
            return
        validate(body)
        print(f"OK: {args[1]} has no forbidden constructs")
        return
    if len(args) != 2:
        die("usage: render_page.py <content.json> <canvas.json>")
    try:
        content = json.load(open(args[0]))
    except (OSError, ValueError) as err:
        die(f"cannot read content {args[0]!r}: {err}")
    check_content(content)
    body = build(content)
    validate(body)
    canvas = [{"controlType": 4, "id": "00000000-0000-0000-0000-0000000000aa",
               "position": {"controlIndex": 1, "sectionIndex": 1, "zoneIndex": 1,
                            "sectionFactor": 12, "layoutIndex": 1},
               "emphasis": {}, "innerHTML": body}]
    json.dump(canvas, open(args[1], "w"), ensure_ascii=False)
    print(f"wrote {args[1]}: {len(body)} chars of body HTML")


if __name__ == "__main__":
    main()
