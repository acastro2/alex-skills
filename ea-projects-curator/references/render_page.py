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

USAGE
-----
    python3 render_page.py recap-content.json canvas.json
    python3 render_page.py --check-only canvas.json     # validate a hand-made canvas

The script refuses to emit forbidden constructs rather than warning. A failure here
means the template was edited, which is exactly what must not happen quietly.

CONTENT SCHEMA (all keys required unless marked optional)
---------------------------------------------------------
{
  "title":     "Architecture Weekly — September 16, 2026",
  "subtitle":  "Forum held Wednesday 16 September. Delivery covering 12 to 18 September 2026.",
  "exec_summary": {                       # optional block, but see SKILL.md gate
    "headline": "One sentence, plain words, no acronyms.",
    "points":   [{"lead": "Bold lead-in.", "text": "What it means."}],
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

GREEN_BG, GREEN_EDGE, GREEN_LEAD = "#E7F3ED", "#1C6B4A", "#155A3D"
AMBER_BG, AMBER_EDGE, AMBER_TEXT, AMBER_DIV = "#FBF1DF", "#A2620A", "#3A2F1C", "#EBDCBE"

TOPIC_TAG_COLOR = {"Decided": GREEN_LEAD, "Needs follow-up": AMBER_EDGE, "Parked": MUTED}
OUTCOME_GREEN = {"Achieved"}

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


def callout(bg, edge, inner, divider=None):
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
             f'color:#FFFFFF;font-weight:400;">{esc(c["title"])}</h1>'
             f'<div style="font-size:14px;line-height:20px;color:{DATE_ON_NAVY};">'
             f'{esc(c["subtitle"])}</div>')
    return band(NAVY, inner, "26px 26px 24px 26px") + rule(height="4px", width="100%")


def exec_summary(c):
    e = c.get("exec_summary")
    if not e:
        return ""
    parts = [micro_label("Executive summary", top="0"),
             f'<h2 style="margin:0 0 16px 0;font-size:19px;line-height:27px;'
             f'color:{NAVY};font-weight:400;">{esc(e["headline"])}</h2>']
    for pt in e["points"]:
        lead = f'<strong style="color:{NAVY};">{esc(pt["lead"])}</strong> ' if pt.get("lead") else ""
        parts.append(p(lead + esc(pt["text"])))
    if e.get("footer"):
        parts.append(f'<p style="margin:14px 0 0 0;padding-top:14px;font-size:14px;'
                     f'line-height:20px;color:{MUTED};border-top:1px solid #C3D6E4;">'
                     f'{esc(e["footer"])}</p>')
    return band(LIGHT, "".join(parts), "26px 26px 24px 26px")


def outcome_block(c):
    o = c["outcome"]
    tag = o["tag"]
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
          f'color:#FFFFFF;text-align:left;font-size:14px;font-weight:400;')
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
    head = (f'<h2 style="margin:0 0 4px 0;font-size:21px;line-height:28px;color:#FFFFFF;'
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
    body = [header(c)]
    if e := exec_summary(c):
        body.append(e)
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


def validate(html):
    for bad in FORBIDDEN:
        if bad in html:
            die(f"forbidden construct in output: {bad!r}. The markup is owned by this "
                f"script; edit the builders, not the output.")
    if "{{" in html:
        die("unsubstituted token in output")
    # Em dashes are banned in everything Alex writes, except the house-format <h1> title
    # separator. The renderer leaked one through the Action items empty-cell placeholder on
    # 2026-09-18, which is why this is a hard check and not a note in a review checklist.
    if "\u2014" in re.sub(r"<h1.*?</h1>", "", html, flags=re.S):
        die("em dash outside the <h1> title. Alex bans them; use a comma, a colon, or a full stop.")


def main():
    args = sys.argv[1:]
    if not args:
        die(__doc__.split("USAGE")[1].split("The script")[0].strip())
    if args[0] == "--check-only":
        canvas = json.load(open(args[1]))
        validate(canvas[0]["innerHTML"])
        print(f"OK: {args[1]} has no forbidden constructs")
        return
    if len(args) != 2:
        die("usage: render_page.py <content.json> <canvas.json>")
    content = json.load(open(args[0]))
    for key in ("title", "subtitle", "objective", "outcome", "tldr", "decisions",
                "actions", "topics", "open_questions", "artifacts", "speakers",
                "speakers_source", "shipped"):
        if key not in content:
            die(f"content JSON is missing required key: {key!r}")
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
