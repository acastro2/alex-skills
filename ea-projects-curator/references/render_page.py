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

SHAREPOINT RULES THE MARKUP OBEYS (measured 2026-09-18 to 2026-09-28)
--------------------------------------------------------------------
1. Inline `style` attributes survive a save, and so do `<style>`, `class=`, flex, grid,
   `border-radius`, `font-family` and inline `<svg>`. Everything here is inline anyway.
2. SharePoint silently STRIPS `gap` and `grid-template-columns` on save. Two-column rows
   are fixed-width flex children; space between items is padding.
3. SharePoint's page CSS OVERRIDES `margin` on `<div>` at render time (stored, not
   applied). Blocks are spaced with padding or `spacer()`. Margins on `p`, `h1`, `h2` and
   inline `span`s do apply.
4. Text inside a styled `<div>` does NOT inherit the div's `color` or `font-size`: set
   them on the text's own `<span>` or `<p>`.
5. Real `<table>` cells get dark gridlines forced on, so the action table is `<div>` rows.
6. No fixed page width and no page background: the SharePoint section owns the width.
7. Print (Save as PDF) needs the `PRINT_CSS` block: SharePoint fixes the body height,
   so without it one page prints. Colours print only with "Background graphics" ticked. The body opens with `<div class="aw-recap">` plus
   that block, and validate() refuses a page without it (2026-09-28).
Storage is not proof. After any change here, screenshot the read view.

The design and palette are Alex's Claude Design mock "Architecture Weekly Recap"
(2026-09-28), deliberately not the Attain brand palette. Every colour the page emits is a
named constant below; a bare hex in a builder is drift.

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

CONTENT SCHEMA (required unless marked optional)
------------------------------------------------
{
  "title":     "Architecture Weekly, September 23, 2026",
  "subtitle":  "Forum held Wednesday, September 23. Delivery covering September 19 to 25, 2026.",
  "exec_summary": {
    "headline": "One sentence, plain words, no acronyms.",
    "points":   [{"lead": "Decided.", "text": "What it means."}],   # 3 or 4; lead optional
    "footer":   "Nothing needs leadership this week"   # status chip: green if it starts No/Nothing
  },
  "objective": "Text.",
  "outcome":   {"tag": "Achieved", "text": "Text."},   # Achieved | Partially achieved | Not achieved
  "tldr":      "Text.",
  "warning":   {"headline": "Text.", "text": "Text.", "label": "IMPORTANT",
                "tone": "warn", "links": [{"label": "Doc", "url": "https://..."}]},
                                               # optional; renders at the end of the Forum
                                               # recap, before "Decisions made". tone is
                                               # "warn" (amber) or "stop" (red). label,
                                               # links optional. headline <= 90 chars,
                                               # text <= 400.
  "decisions": [{"lead": "Bold first sentence.", "text": "Rest.", "rationale": "Text.",
                 "owner": "Name, Name", "chip": "Topic label"}],        # lead, chip optional
  "actions":   [{"action": "Text.", "owner": "Name | Unassigned (who asked)",
                 "due": "Next sprint", "source": "chat"}],             # due, source optional
  "topics":    [{"title": "Short name.", "summary": "One or two sentences.", "tag": "Decided",
                 "owner": "Name",                                       # optional
                 "points": [{"lead": "Label", "text": "Explanation."}]}],  # optional, 3-6
                                                       # tag: Decided | Needs follow-up | Parked
  "open_questions": [{"text": "Question.", "next": "Who decides / next step", "source": "chat"}],
  "artifacts":      [{"label": "Document title", "url": "https://...", "note": "Optional."}],
  "speakers":       "Alexandre Castro, Chris Goodrich, ...",
  "speakers_source": "Teams meeting transcript, 3:00pm to 4:01pm Central.",
  "shipped": {"window": "September 19 to 25, 2026",
              "items": [{"sentence": "Outcome-first sentence.", "category": "Infrastructure",
                         "evidence": [{"label": "Network change", "url": "https://..."}]}]}
}
"""
import json
import re
import sys
from html import unescape

# --- palette (design v2, Alex 2026-09-28, from the "Architecture Weekly Recap" mock) ---
NAVY = "#17375E"
ACCENT = "#2A9FD6"
GOLD = "#DFD4B8"
OLIVE = "#6B5A2E"
LIGHT = "#E8F0F7"
BODY = "#1F2A37"
MUTED = "#5F6670"
LABEL = "#2A6FB0"
LINK = "#0B5CAD"
BORDER = "#D7DEE6"
ROW_DIV = "#E6EAEF"
ZEBRA = "#FAFBFC"
EYEBROW_ON_NAVY = "#9CC6E8"
DATE_ON_NAVY = "#D5E3F0"
EXEC_DIVIDER = "#C9D8E6"
ON_BAND = "#FFFFFF"
WHITE = "#FFFFFF"

GREEN_BG, GREEN_EDGE, GREEN_LEAD = "#EAF5EE", "#2E8B57", "#1D5E36"
GREEN_BORDER = "#B9DCC6"
AMBER_BG, AMBER_EDGE, AMBER_TEXT, AMBER_DIV = "#FBEFD9", "#C9812F", "#7A4108", "#F1E2C9"
AMBER_SURFACE, AMBER_BORDER, AMBER_NUM = "#FFFAF2", "#E8CFA8", "#C9812F"
CHIP = {"green": ("#E3F1E8", "#1D5E36"), "amber": ("#FBEFD9", "#7A4108"),
        "gray": ("#EEF0F3", "#4A5563"), "blue": ("#E6EEF6", "#17375E")}
CHIP_DOT = {"green": "#2E8B57", "amber": "#C9812F"}

# Warning band (design supplied by Alex, 2026-10-05). Hazard-tape rules top and bottom,
# cream field, dark label chip. Kept as named constants because every colour this page
# emits is named; a bare hex in a builder is drift.
WARN_TAPE = "#C07735"
WARN_TAPE_LIGHT = "#F3D7AE"
WARN_FIELD = "#FAECD5"
WARN_LABEL_BG = "#6D3A15"
WARN_LABEL_FG = "#FAECD5"
WARN_TEXT = "#1B2A3A"

# Red "stop" tone of the same band (design supplied by Alex, 2026-10-05). Same geometry,
# different palette, plus a STOP chip and a BLOCKED caption. Alex has not used it yet.
STOP_TAPE = "#B8433B"
STOP_FIELD = "#FBE4E1"
STOP_HEAD = "#7A1F1A"

# tone -> (field, tape, tape_alt, headline, chip_bg, chip_fg)
WARN_TONES = {
    "warn": (WARN_FIELD, WARN_TAPE, WARN_TAPE_LIGHT, WARN_LABEL_BG, WARN_LABEL_BG, WARN_LABEL_FG),
    "stop": (STOP_FIELD, STOP_TAPE, WHITE, STOP_HEAD, STOP_TAPE, WHITE),
}

TOPIC_TAG_COLOR = {"Decided": GREEN_LEAD, "Needs follow-up": AMBER_EDGE, "Parked": MUTED}   # valid tags
OUTCOME_TAGS = ("Achieved", "Partially achieved", "Not achieved")
OUTCOME_GREEN = {"Achieved"}

# SKILL.md, Executive Summary gate. Enforced, not suggested: a band that quietly comes
# out at two points is the drift this script exists to stop, and it is the line Alex
# reads most closely.
EXEC_POINTS_MIN, EXEC_POINTS_MAX = 3, 4

# --- validation ---------------------------------------------------------------
FORBIDDEN = [
    "<script", "javascript:",   # safety
    # SharePoint strips these two on save (2026-09-28): use padding and fixed-width flex.
    "gap:", "grid-template",
]

# --- print (Save as PDF) --------------------------------------------------------
# Measured 2026-09-28 on the published 09-23 issue: SharePoint gives <body> a fixed
# viewport height with overflow:auto, so Save as PDF printed ONE page of a 5,800px issue.
# Resetting html/body under @media print lets the whole issue flow onto every page.
# SharePoint's CSS sanitizer (verified on save, same day) KEEPS html/body and class
# selectors and `page-break-*`, and STRIPS `:has()` selectors, `@page`, `break-*` and
# `print-color-adjust`. So colours print only when the reader ticks "Background
# graphics" in the print dialog; nothing in the page can force it. Only rules that
# survive a save are listed here, so the stored page matches this constant.
# `.aw-keep` blocks never split across pages; `.aw-head` never sits alone at a page end;
# `.aw-newpage` starts the shipped panel on a fresh page. The print theme classes
# (`aw-band`, `aw-inv`, `aw-olive`, `aw-avatar`, `aw-tint`, `aw-rule`) sit on every element
# that carries light-on-dark colour on screen; a new dark element needs one too.
PRINT_CSS = (
    "@media print{"
    "html,body{height:auto !important;min-height:0 !important;max-height:none !important;"
    "overflow:visible !important;position:static !important;display:block !important;}"
    ".aw-recap .aw-keep{page-break-inside:avoid;}"
    ".aw-recap h2,.aw-recap .aw-head{page-break-after:avoid;}"
    ".aw-recap .aw-newpage{page-break-before:always;}"
    # Print theme (Alex, 2026-09-28): the page must read the same with or without
    # "Background graphics". Dark bands turn white with a navy border and navy text,
    # so neither setting leaves light text on a missing (or present) navy fill.
    f".aw-recap .aw-band{{background-color:{WHITE} !important;border:2px solid {NAVY} !important;}}"
    f".aw-recap .aw-inv{{color:{NAVY} !important;}}"
    f".aw-recap .aw-olive{{color:{OLIVE} !important;}}"
    f".aw-recap .aw-avatar{{background-color:{WHITE} !important;color:{NAVY} !important;border:1px solid {NAVY} !important;}}"
    f".aw-recap .aw-tint{{border:1px solid {BORDER} !important;}}"
    f".aw-recap .aw-rule{{background-color:{WHITE} !important;border-bottom:2px solid {NAVY} !important;}}"
    # The warning label chip is light-on-dark (cream on dark brown), so it needs a print
    # theme class or it prints cream on nothing when "Background graphics" is off.
    f".aw-recap .aw-warnlabel{{background-color:{WHITE} !important;color:{WARN_LABEL_BG} !important;"
    f"border:1px solid {WARN_LABEL_BG} !important;}}"
    # The red tone's STOP chip is white-on-red inside a red ring, which prints as white on
    # white without a theme, so both the ring and the chip get one.
    f".aw-recap .aw-stopring{{background-color:{WHITE} !important;border:1px solid {STOP_TAPE} !important;}}"
    f".aw-recap .aw-stoplabel{{background-color:{WHITE} !important;color:{STOP_TAPE} !important;"
    f"border:2px solid {STOP_TAPE} !important;}}"
    "}")
STYLE_BLOCK = f"<style>{PRINT_CSS}</style>"
KEEP = ' class="aw-keep"'
HEAD = ' class="aw-head"'
# Every link this page emits opens in a new tab (Alex, 2026-10-05). `rel` is not optional
# decoration: target="_blank" without it hands the opened page a window.opener reference.
NEW_TAB = 'target="_blank" rel="noopener noreferrer"'


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


def browser_open(u):
    """Force SharePoint's browser viewer instead of a download.

    Measured 2026-10-05 against this library: a bare document URL answers with the file
    itself (`Content-Type: application/vnd.openxmlformats-officedocument...`), so the
    browser downloads it. The same URL with `?web=1` answers `text/html`, which is the
    viewer. On a locked-down laptop the download is worse than untidy, it lands somewhere
    the reader has to go and find.

    Only applied where it is needed and safe: no query string already present, and a
    document extension at the end. Sharing links (`:w:`, `:f:`), SitePages, list forms,
    folders and GitHub already open in the browser, and adding a parameter to them would
    be noise at best.
    """
    if "?" in u:
        return u
    if re.search(r"\.(?:docx?|xlsx?|pptx?|pdf|vsdx?|csv|txt|zip)$", u, re.I):
        return u + "?web=1"
    return u


def safe_url(u):
    if not isinstance(u, str):
        die(f"url must be a string, got {u!r}")
    if u.startswith("https://") or u.startswith("/sites/"):
        return esc_attr(browser_open(u))
    die(f"url must be https:// or /sites/..., got {u!r}")


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


def optional_str(obj, keys, where):
    for k in keys:
        if k in obj and not isinstance(obj[k], str):
            die(f"{where}.{k} must be a string, got {type(obj[k]).__name__}")


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

    # Optional warning band. Refuses rather than warns, like everything else here: a
    # warning is the most-read block on the page, so a long one is a content fix, not a
    # layout argument. Bounds follow Alex's own template ("[Headline]" plus one or two
    # short sentences).
    if "warning" in c:
        w = need(c, "warning", "content", kind=dict)
        need(w, "headline", "warning")
        need(w, "text", "warning")
        optional_str(w, ("label",), "warning")
        tone = w.get("tone", "warn")
        if tone not in WARN_TONES:
            die(f"warning.tone must be one of {sorted(WARN_TONES)}, got {tone!r}. "
                f"'warn' is the amber IMPORTANT band, 'stop' is the red STOP band.")
        if len(w["headline"]) > 90:
            die(f"warning.headline is {len(w['headline'])} chars; keep it under 90. It is "
                f"a headline, not a paragraph.")
        if len(w["text"]) > 400:
            die(f"warning.text is {len(w['text'])} chars; keep it under 400. One or two "
                f"short sentences, per the design.")
        # Optional sources, rendered as bordered link buttons under the text.
        for i, l in enumerate(w.get("links") or []):
            where = f"warning.links[{i}]"
            need(l, "label", where)
            safe_url(need(l, "url", where))

    o = need(c, "outcome", "content", kind=dict)
    need(o, "text", "outcome")
    tag = need(o, "tag", "outcome")
    if tag not in OUTCOME_TAGS:
        die(f"outcome.tag must be one of {list(OUTCOME_TAGS)}, got {tag!r}. A typo here "
            f"renders amber and reads to the org as 'Partially achieved'.")

    for i, d in enumerate(need_list(c, "decisions", "content")):
        where = f"decisions[{i}]"
        for key in ("text", "rationale", "owner"):
            need(d, key, where)
        optional_str(d, ("lead", "chip"), where)

    for i, a in enumerate(need_list(c, "actions", "content")):
        where = f"actions[{i}]"
        need(a, "action", where)
        need(a, "owner", where)
        optional_str(a, ("due", "source"), where)

    for i, t in enumerate(need_list(c, "topics", "content")):
        where = f"topics[{i}]"
        need(t, "title", where)
        need(t, "summary", where)
        optional_str(t, ("owner",), where)
        for j, p in enumerate(t.get("points") or []):
            if isinstance(p, dict):
                need(p, "lead", f"{where}.points[{j}]")
                need(p, "text", f"{where}.points[{j}]")
            elif not isinstance(p, str) or not p.strip():
                die(f"{where}.points[{j}] must be a non-empty string or {{lead, text}}")
        if need(t, "tag", where) not in TOPIC_TAG_COLOR:
            die(f"{where}.tag must be one of {sorted(TOPIC_TAG_COLOR)}, got {t['tag']!r}")

    for i, item in enumerate(need_list(c, "open_questions", "content")):
        if isinstance(item, dict):
            need(item, "text", f"open_questions[{i}]")
            optional_str(item, ("next", "source"), f"open_questions[{i}]")
        elif not isinstance(item, str) or not item.strip():
            die(f"open_questions[{i}] must be a string or {{text, next, source}}, got {item!r}")
    # Artifacts ALWAYS carry a link (Alex, 2026-09-28). A bare file name is a hard stop.
    for i, item in enumerate(need_list(c, "artifacts", "content")):
        where = f"artifacts[{i}]"
        if not isinstance(item, dict):
            die(f"{where} must be {{label, url, note}} with a real link, got {item!r}")
        need(item, "label", where)
        safe_url(need(item, "url", where))
        optional_str(item, ("note",), where)

    sh = need(c, "shipped", "content", kind=dict)
    need(sh, "window", "shipped")
    for i, it in enumerate(need_list(sh, "items", "shipped")):
        where = f"shipped.items[{i}]"
        need(it, "sentence", where)
        optional_str(it, ("category",), where)
        # An item with no evidence renders as a bare "Evidence:" with nothing after it.
        # The panel's whole claim is that it is evidence-backed, so this is a hard stop.
        for j, ev in enumerate(need_list(it, "evidence", where)):
            need(ev, "label", f"{where}.evidence[{j}]")
            safe_url(need(ev, "url", f"{where}.evidence[{j}]"))


# --- block builders (see SHAREPOINT RULES in the module docstring) -------------

def spacer(px):
    """Vertical space. SharePoint's page CSS overrides `margin` on <div> at render time
    (measured 2026-09-28: stored, but not applied), so spacing between blocks is a spacer."""
    return (f'<div style="height:{px}px;line-height:{px}px;font-size:0;">&nbsp;</div>')


def _initials(name):
    parts = [w for w in re.split(r"[\s-]+", name) if w and w[0].isalpha()]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper() if parts else "?"


def _owners(owner):
    """'Flor Delgado Perez, Uday Parande' -> ['Flor Delgado Perez', 'Uday Parande']."""
    return [o.strip() for o in re.split(r",| and ", owner) if o.strip()]


def avatar(name, empty=False):
    if empty:
        return (f'<span style="display:inline-block;width:24px;height:24px;line-height:21px;'
                f'border-radius:50%;background-color:{WHITE};color:{AMBER_TEXT};'
                f'border:1.5px dashed {AMBER_EDGE};font-size:11px;font-weight:600;'
                f'text-align:center;vertical-align:middle;margin-right:8px;">?</span>')
    return (f'<span class="aw-avatar" style="display:inline-block;width:26px;height:26px;line-height:26px;'
            f'border-radius:50%;background-color:{NAVY};color:{ON_BAND};font-size:11px;'
            f'font-weight:600;text-align:center;vertical-align:middle;margin-right:8px;">'
            f'{esc(_initials(name))}</span>')


def person(name):
    if name.lower().startswith("unassigned"):
        rest = name[len("unassigned"):].strip(" ()")
        note = (f'<div style="font-size:12px;line-height:16px;color:{MUTED};padding:2px 0 0 34px;">'
                f'{esc(rest)}</div>' if rest else "")
        return (f'<span style="display:inline-block;margin:2px 18px 2px 0;font-size:14px;'
                f'color:{AMBER_TEXT};">{avatar("", empty=True)}Unassigned</span>{note}')
    return (f'<span style="display:inline-block;margin:2px 18px 2px 0;font-size:14px;'
            f'color:{BODY};">{avatar(name)}{esc(name)}</span>')


def people(owner):
    return "".join(person(o) for o in _owners(owner))


def chip(text, kind="gray"):
    bg, fg = CHIP[kind]
    dot = (f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
           f'background-color:{CHIP_DOT[kind]};margin-right:6px;vertical-align:middle;"></span>'
           if kind in CHIP_DOT else "")
    return (f'<span style="display:inline-block;height:24px;line-height:24px;padding:0 10px;'
            f'border-radius:2px;background-color:{bg};color:{fg};font-size:12px;font-weight:600;'
            f'white-space:nowrap;margin-right:8px;vertical-align:middle;">{dot}{esc(text)}</span>')


TAG_CHIP = {"Decided": "green", "Needs follow-up": "amber", "Parked": "gray"}


def eyebrow(text, color=None, top=0):
    lead = spacer(top) if top else ""
    return lead + (f'<div{HEAD} style="padding-bottom:8px;font-size:11px;letter-spacing:1.5px;'
                   f'font-weight:600;color:{color or NAVY};">{esc(text.upper())}</div>')


def section_title(text, count=None, tone="blue"):
    badge = ""
    if count is not None:
        bg, fg = CHIP[tone]
        badge = (f'<span style="display:inline-block;min-width:26px;height:24px;line-height:24px;'
                 f'padding:0 8px;border-radius:2px;background-color:{bg};color:{fg};'
                 f'font-size:13px;font-weight:600;text-align:center;margin-left:12px;'
                 f'vertical-align:middle;">{count}</span>')
    return (f'<h2 style="margin:48px 0 18px 0;font-size:24px;line-height:30px;font-weight:600;'
            f'color:{NAVY};">{esc(text)}{badge}</h2>')


def p(text, size="14px", line="22px", color=BODY, margin="0 0 10px 0"):
    return f'<p style="margin:{margin};font-size:{size};line-height:{line};color:{color};">{text}</p>'


def kv_row(label, value, label_w="110px", label_color=None, caps=True):
    """Two-column row without grid (grid-template-columns is stripped on save)."""
    return (f'<div{KEEP} style="display:flex;padding-bottom:12px;">'
            f'<div style="flex:0 0 {label_w};max-width:{label_w};padding-right:20px;">'
            + (f'<span style="font-size:11px;letter-spacing:1.5px;font-weight:600;line-height:22px;'
               f'color:{label_color or LABEL};">{esc(label.upper())}</span>' if caps else
               f'<span style="font-size:14px;font-weight:600;line-height:22px;color:{label_color or NAVY};">'
               f'{esc(label)}</span>')
            + '</div>'
            f'<div style="flex:1 1 auto;min-width:0;font-size:14px;line-height:22px;color:{BODY};">'
            f'{value}</div></div>')


# --- sections -----------------------------------------------------------------
def header(c):
    return (f'<div class="aw-keep aw-band" style="background-color:{NAVY};padding:26px 24px 22px 24px;'
            f'border-bottom:4px solid {ACCENT};">'
            f'<div class="aw-inv" style="font-size:11px;letter-spacing:2px;color:{EYEBROW_ON_NAVY};font-weight:600;">'
            f'ENTERPRISE ARCHITECTURE</div>'
            f'<h1 class="aw-inv" style="margin:6px 0 0 0;font-size:26px;line-height:32px;color:{ON_BAND};'
            f'font-weight:400;">{esc(c["title"])}</h1>'
            f'<div class="aw-inv" style="font-size:13px;line-height:19px;color:{DATE_ON_NAVY};padding-top:8px;">'
            f'{esc(c["subtitle"])}</div></div>')


def warning(c):
    """Hazard-tape warning band (design supplied by Alex, 2026-10-05).

    Three deliberate departures from the markup he supplied, each forced by a measured
    SharePoint behaviour rather than a preference:

    * his headline carried `margin:14px 0 6px 0` on a <div>, and SharePoint's page CSS
      overrides margin on a <div> at render time (stored, not applied), so the space above
      is a spacer() and the space below is padding;
    * the dark IMPORTANT chip is light-on-dark, so it carries the `aw-warnlabel` print
      theme class, or it prints cream-on-nothing with "Background graphics" off;
    * the tape cells keep a solid `background-color` next to the gradient, so a stripped
      gradient degrades to a solid bar instead of a gap.

    Placement is the end of the Forum recap, before "Decisions made" (Alex, 2026-10-05,
    after rejecting both the top of the page and the slot under the Executive Summary).
    The band is the leadership gate, the recap is the forum's own record, and the warning
    closes the record before the decisions were extracted from it.

    Two tones share one geometry: `warn` (amber, IMPORTANT) and `stop` (red, STOP plus a
    BLOCKED caption). An optional `links` list adds source buttons under the text.
    """
    if "warning" not in c:
        return ""
    w = c["warning"]
    tone = w.get("tone", "warn")
    field, tape_c, tape_alt, head_c, chip_bg, chip_fg = WARN_TONES[tone]
    tape = (f'<div style="height:8px;font-size:0;line-height:0;background-color:{tape_c};'
            f'background-image:repeating-linear-gradient(-45deg,{tape_c} 0px,{tape_c} 8px,'
            f'{tape_alt} 8px,{tape_alt} 16px);">&nbsp;</div>')
    if tone == "stop":
        # Red tone: a STOP chip inside a red ring, then the caption. Two spans, not two
        # nested tables, because SharePoint forces dark gridlines onto real table cells.
        label = (f'<div style="display:flex;align-items:center;">'
                 f'<span class="aw-stopring" style="display:inline-block;padding:2px;'
                 f'background-color:{chip_bg};border-radius:4px;">'
                 f'<span class="aw-stoplabel" style="display:inline-block;padding:1px 6px;'
                 f'background-color:{chip_bg};border:2px solid {chip_fg};border-radius:3px;'
                 f'color:{chip_fg};font-size:10px;font-weight:800;letter-spacing:1.5px;">STOP</span>'
                 f'</span>'
                 f'<span style="padding-left:10px;color:{head_c};font-size:10px;font-weight:700;'
                 f'letter-spacing:2px;">{esc(w.get("label", "BLOCKED"))}</span></div>')
    else:
        label = (f'<span class="aw-warnlabel" style="display:inline-block;padding:3px 8px;'
                 f'background-color:{chip_bg};color:{chip_fg};font-size:10px;'
                 f'font-weight:700;letter-spacing:2px;">&#9888; {esc(w.get("label", "IMPORTANT"))}</span>')
    head = (f'<div style="padding:10px 0 3px 0;">'
            f'<span style="font-size:14px;font-weight:700;color:{head_c};line-height:20px;">'
            f'{esc(w["headline"])}</span></div>')
    body = (f'<div><span style="font-size:13px;color:{WARN_TEXT};line-height:20px;">'
            f'{esc(w["text"])}</span></div>')
    # Optional sources. The policy and the standard are the authority behind the claim, so
    # the band carries them rather than making a reader go and find them.
    links = ""
    if w.get("links"):
        btns = "".join(
            f'<a href="{safe_url(l["url"])}" {NEW_TAB} style="display:inline-block;font-size:12px;'
            f'font-weight:600;text-decoration:none;border:1px solid {tape_c};padding:4px 9px;'
            f'color:{head_c};margin:0 8px 4px 0;">{esc(l["label"])}</a>' for l in w["links"])
        links = f'<div style="padding-top:10px;">{btns}</div>'
    return (spacer(20) + f'<div class="aw-keep" style="background-color:{field};'
            f'border-left:1px solid {tape_c};border-right:1px solid {tape_c};">'
            f'{tape}<div style="padding:12px 18px 14px 18px;">{label}{head}{body}{links}</div>'
            f'{tape}</div>')


def exec_summary(c):
    """Mock 2026-09-28: eyebrow left, leadership status chip right (green when nothing needs
    leadership, amber when a decision is waiting), then points with a coloured dot and lead:
    decided/agreed green, shipped navy, still open amber."""
    e = c["exec_summary"]
    footer = e["footer"]
    calm = footer.lower().startswith(("no ", "nothing"))
    tone = "green" if calm else "amber"
    top = (f'<div style="display:flex;align-items:center;padding-bottom:14px;">'
           f'<div style="flex:1 1 auto;min-width:0;"><span style="font-size:11px;letter-spacing:1.5px;'
           f'font-weight:600;color:{NAVY};">EXECUTIVE SUMMARY</span></div>'
           f'<div style="flex:0 0 auto;"><span style="display:inline-block;padding:4px 12px;'
           f'background-color:{CHIP[tone][0]};color:{CHIP[tone][1]};border:1px solid {GREEN_BORDER if calm else AMBER_BORDER};'
           f'font-size:13px;font-weight:600;line-height:18px;">'
           f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
           f'background-color:{CHIP_DOT[tone]};margin-right:8px;vertical-align:middle;"></span>{esc(footer.rstrip("."))}</span></div></div>')
    head = (f'<div style="padding-bottom:16px;"><span style="font-size:18px;line-height:25px;font-weight:600;'
            f'color:{NAVY};">{esc(e["headline"])}</span></div>')
    def tone_of(lead):
        l = lead.lower()
        if "open" in l: return AMBER_TEXT, CHIP_DOT["amber"]
        if "decid" in l or "agree" in l: return GREEN_LEAD, CHIP_DOT["green"]
        return NAVY, NAVY
    pts = []
    for pt in e["points"]:
        col, dot = tone_of(pt.get("lead", ""))
        lead = f'<strong style="color:{col};">{esc(pt["lead"])}</strong> ' if pt.get("lead") else ""
        pts.append(f'<div style="display:flex;padding-bottom:12px;">'
                   f'<div style="flex:0 0 16px;max-width:16px;line-height:22px;font-size:14px;">'
                   f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background-color:{dot};vertical-align:middle;"></span></div>'
                   f'<div style="flex:1 1 auto;min-width:0;"><span style="font-size:14px;line-height:22px;color:{BODY};">'
                   f'{lead}{esc(pt["text"])}</span></div></div>')
    return f'<div class="aw-keep aw-tint" style="background-color:{LIGHT};padding:24px 24px 12px 24px;">{top}{head}{"".join(pts)}</div>'


def forum_recap(c):
    o = c["outcome"]
    green = o["tag"] in OUTCOME_GREEN
    bg, edge, lead = (GREEN_BG, GREEN_EDGE, GREEN_LEAD) if green else (AMBER_BG, AMBER_EDGE, AMBER_TEXT)
    outcome = (f'<div{KEEP} style="background-color:{bg};border-left:4px solid {edge};padding:16px 20px;'
               f'font-size:14px;line-height:22px;color:{BODY};">'
               f'<strong style="color:{lead};">{esc(o["tag"])}.</strong> {esc(o["text"])}</div>')
    return (section_title("Forum recap")
            + eyebrow("Objective") + p(esc(c["objective"]), margin="0 0 20px 0")
            + eyebrow("Outcome") + outcome
            + eyebrow("TL;DR", top=20) + p(esc(c["tldr"]), margin="0"))


def decision_cards(c):
    out = []
    for d in c["decisions"]:
        chips = chip("Decided", "green") + (chip(d["chip"], "gray") if d.get("chip") else "")
        lead = f'<strong style="color:{NAVY};">{esc(d["lead"])}</strong> ' if d.get("lead") else ""
        out.append(
            f'<div{KEEP} style="border:1px solid {BORDER};border-top:3px solid {NAVY};padding:20px 22px;">'
            f'<div style="padding-bottom:10px;">{chips}</div>'
            f'<p style="margin:0 0 14px 0;font-size:15px;line-height:23px;color:{BODY};">{lead}{esc(d["text"])}</p>'
            + kv_row("Rationale", esc(d["rationale"]), label_color=LINK)
            + kv_row("Owner", people(d["owner"]), label_color=LINK)
            + '</div>' + spacer(12))
    return section_title("Decisions made", len(c["decisions"])) + "".join(out)


def action_table(c):
    """Div rows, not <table>: SharePoint forces dark gridlines onto tables (measured 2026-09-22),
    and the mock has a navy header bar, faint row dividers and zebra rows (Alex, 2026-09-28)."""
    def row(a_html, o_html, d_html, style, cls=KEEP):
        return (f'<div{cls} style="display:flex;align-items:center;{style}">'
                f'<div style="flex:1 1 auto;min-width:0;padding-right:20px;">{a_html}</div>'
                f'<div style="flex:0 0 280px;max-width:280px;padding-right:20px;">{o_html}</div>'
                f'<div style="flex:0 0 130px;max-width:130px;">{d_html}</div></div>')
    head = row(*(f'<span class="aw-inv" style="font-size:13px;font-weight:600;color:{ON_BAND};">{h}</span>' for h in ("Action", "Owner", "Due")),
               f"background-color:{NAVY};color:{ON_BAND};font-size:13px;font-weight:600;padding:12px 20px;",
               cls=' class="aw-keep aw-head aw-rule"')
    rows = []
    for i, a in enumerate(c["actions"]):
        src = (f'<div style="padding-bottom:6px;">{chip("From meeting chat", "gray")}</div>'
               if a.get("source") == "chat" else "")
        due = (f'<span style="font-size:13px;color:{BODY};">{esc(a["due"])}</span>' if a.get("due")
               else f'<span style="font-size:13px;color:{MUTED};">No date</span>')
        owners = "".join(f'<div style="padding:2px 0;">{person(o)}</div>' for o in _owners(a["owner"]))
        unassigned = a["owner"].lower().startswith("unassigned")
        zebra = (f"background-color:{AMBER_SURFACE};" if unassigned
                 else f"background-color:{ZEBRA};" if i % 2 else "")
        rows.append(row(f"{src}<span style=\"font-size:14px;line-height:21px;color:{BODY};\">{esc(a['action'])}</span>", owners, due,
                        f"padding:14px 20px;border-top:1px solid {ROW_DIV};font-size:14px;line-height:21px;color:{BODY};{zebra}"))
    table = f'<div style="border:1px solid {BORDER};">{head}{"".join(rows)}</div>'
    note = p('"No date" means no date was stated in the session.', size="13px", color=MUTED,
             margin="10px 0 0 0")
    return section_title("Action items", len(c["actions"])) + table + note


def topic_block(t):
    """Mock 2026-09-28: header row, full-width divider, Title Case label rows. A topic
    tagged Needs follow-up gets the amber card."""
    amber = t["tag"] == "Needs follow-up"
    bg = f"background-color:{AMBER_SURFACE};" if amber else ""
    edge = AMBER_BORDER if amber else BORDER
    div = AMBER_DIV if amber else BORDER
    head = (f'<div class="aw-keep aw-head" style="display:flex;align-items:flex-start;padding:20px 22px;">'
            f'<div style="flex:1 1 auto;min-width:0;padding-right:16px;">'
            f'<span style="font-size:17px;line-height:24px;font-weight:600;color:{NAVY};">{esc(t["title"].rstrip("."))}</span>'
            f'<div style="padding-top:4px;"><span style="font-size:14px;line-height:21px;color:{MUTED};">{esc(t["summary"])}</span></div></div>'
            f'<div style="flex:0 0 auto;white-space:nowrap;padding-top:2px;">'
            + (person(t["owner"]) if t.get("owner") else "")
            + chip(t["tag"], TAG_CHIP[t["tag"]]) + '</div></div>')
    rows = ""
    for pt in t.get("points") or []:
        if isinstance(pt, dict):
            rows += kv_row(pt["lead"], esc(pt["text"]), label_w="170px", caps=False)
        else:
            rows += p(esc(pt))
    body = (f'<div style="padding:18px 22px 8px 22px;border-top:1px solid {div};">{rows}</div>'
            if rows else "")
    return (f'<div style="border:1px solid {edge};{bg}">{head}{body}</div>' + spacer(14))


def topic_list(c):
    return section_title("Topics discussed", len(c["topics"])) + "".join(topic_block(t) for t in c["topics"])


def open_questions(c):
    items = []
    for i, q in enumerate(c["open_questions"], 1):
        if isinstance(q, str):
            q = {"text": q}
        src = (f'<div style="padding-top:4px;"><span style="font-size:12px;color:{MUTED};">From the meeting chat</span></div>'
               if q.get("source") == "chat" else "")
        items.append(
            f'<div{KEEP} style="display:flex;align-items:flex-start;padding:16px 22px;{("border-top:1px solid " + AMBER_DIV + ";") if i > 1 else ""}">'
            f'<div style="flex:0 0 38px;max-width:38px;font-size:20px;line-height:24px;font-weight:600;'
            f'color:{AMBER_NUM};">{i}</div>'
            f'<div style="flex:1 1 auto;min-width:0;font-size:14px;line-height:21px;color:{BODY};padding-right:14px;">'
            f'{esc(q["text"])}{src}</div>'
            + (f'<div style="flex:0 0 auto;">{chip(q["next"], "gray")}</div>' if q.get("next") else "")
            + '</div>')
    box = (f'<div style="background-color:{AMBER_SURFACE};border:1px solid {AMBER_BORDER};">'
           f'{"".join(items)}</div>')
    return section_title("Open questions and risks", len(c["open_questions"]), tone="amber") + box


def artifact_list(items):
    """Two-column cards with an icon, per the 2026-09-28 mock. Every card is a link
    (Alex, 2026-09-28). No gap/grid: 50%-wide flex cells padded apart."""
    icon = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="' + NAVY + '" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>'
            '<path d="M14 3v6h6"></path></svg>')
    cells = []
    for k, a in enumerate(items):
        pad = "padding:0 6px 12px 0;" if k % 2 == 0 else "padding:0 0 12px 6px;"
        note = (f'<div style="font-size:12px;line-height:17px;color:{MUTED};padding-top:2px;">'
                f'{esc(a["note"])}</div>' if a.get("note") else "")
        cells.append(
            f'<div{KEEP} style="flex:0 0 50%;max-width:50%;box-sizing:border-box;{pad}">'
            f'<div style="display:flex;align-items:center;border:1px solid {BORDER};padding:14px 16px;height:100%;box-sizing:border-box;">'
            f'<div style="flex:0 0 38px;width:38px;height:38px;background-color:{CHIP["blue"][0]};'
            f'display:flex;align-items:center;justify-content:center;">{icon}</div>'
            f'<div style="flex:1 1 auto;min-width:0;padding-left:14px;">'
            f'<a href="{safe_url(a["url"])}" {NEW_TAB} style="font-size:14px;line-height:20px;font-weight:600;'
            f'color:{LINK};text-decoration:underline;">{esc(a["label"])}</a>{note}</div></div></div>')
    grid = f'<div style="display:flex;flex-wrap:wrap;">{"".join(cells)}</div>'
    return section_title("Artifacts referenced", len(items)) + grid


def speakers_line(c):
    return p(f'<strong style="color:{NAVY};">Spoke in this session:</strong> {esc(c["speakers"])}. '
             f'Source: {esc(c["speakers_source"])}', size="13px", line="19px", color=MUTED,
             margin="18px 0 0 0")


def shipped_panel(c):
    sh = c["shipped"]
    n = len(sh["items"])
    head = (f'<div class="aw-keep aw-head" style="display:flex;align-items:flex-end;">'
            f'<div style="flex:1 1 auto;min-width:0;">'
            f'<div class="aw-olive" style="font-size:11px;letter-spacing:2px;font-weight:600;color:{GOLD};">'
            f'DELIVERED BY ENTERPRISE ARCHITECTURE</div>'
            f'<div class="aw-inv" style="font-size:24px;line-height:30px;font-weight:600;color:{ON_BAND};padding-top:6px;">'
            f'What Enterprise Architecture shipped</div>'
            f'<div class="aw-inv" style="font-size:13px;color:{DATE_ON_NAVY};padding-top:6px;">{esc(sh["window"])}</div></div>'
            f'<div style="flex:0 0 auto;text-align:right;color:{ON_BAND};">'
            f'<div class="aw-olive" style="font-size:48px;line-height:48px;font-weight:600;color:{GOLD};">{n}</div>'
            f'<div class="aw-inv" style="font-size:12px;color:{DATE_ON_NAVY};">{"delivery" if n == 1 else "deliveries"}<br>this week</div>'
            f'</div></div>')
    items = []
    for it in sh["items"]:
        # Mock 2026-09-28: gold check square + small-caps category in olive, then the
        # sentence, then evidence as bordered link buttons with an arrow.
        check = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="' + NAVY + '" '
                 'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"></path></svg>')
        cat = (f'<div style="display:flex;align-items:center;">'
               f'<div style="flex:0 0 28px;width:28px;height:28px;background-color:{GOLD};display:flex;'
               f'align-items:center;justify-content:center;">{check}</div>'
               f'<span style="padding-left:10px;font-size:11px;letter-spacing:1.5px;font-weight:600;'
               f'color:{OLIVE};">{esc(it.get("category", "Delivered").upper())}</span></div>')
        arrow = ('<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="' + LINK + '" '
                 'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;">'
                 '<path d="M7 17L17 7M8 7h9v9"></path></svg>')
        ev = "".join(f'<a href="{safe_url(e["url"])}" {NEW_TAB} style="display:inline-block;font-size:12px;font-weight:600;'
                     f'text-decoration:none;border:1px solid {EXEC_DIVIDER};padding:5px 10px;color:{LINK};'
                     f'margin:0 8px 6px 0;">{esc(e["label"])} {arrow}</a>' for e in it["evidence"])
        items.append(spacer(10) + f'<div class="aw-keep aw-tint" style="background-color:{ON_BAND};padding:20px 22px;">'
                     f'<div style="padding-bottom:12px;">{cat}</div>'
                     f'<div style="padding-bottom:12px;"><span style="font-size:15px;line-height:22px;font-weight:600;color:{NAVY};">{esc(it["sentence"])}</span></div>'
                     f'<div>{ev}</div></div>')
    return spacer(48) + (f'<div class="aw-newpage aw-band" style="background-color:{NAVY};border-top:4px solid {GOLD};padding:32px 28px 28px 28px;">'
            f'{head}{"".join(items)}</div>')


def build(c):
    # One root with the print block first: the print CSS finds the page through it.
    return f'<div class="aw-recap">{STYLE_BLOCK}' + "".join([header(c), exec_summary(c), forum_recap(c), warning(c), decision_cards(c),
                    action_table(c), topic_list(c), open_questions(c),
                    artifact_list(c["artifacts"]), speakers_line(c), shipped_panel(c)]) + '</div>'


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
    """The text nodes. Used for the dash ban, which is about what Alex writes."""
    return re.sub(r"<[^>]*>", " ", without_style(html))


def without_style(html):
    """The body minus the print block. The CSS is markup this script owns, not prose, and
    its `>` combinators would otherwise leak into the text checks."""
    return html.replace(STYLE_BLOCK, "")


def to_text(html):
    """Plain text of the rendered page, for `voice_check.py`.

    recap.md requires the voice check to run on the RENDERED page and not on the content
    JSON, because the renderer's own cosmetic characters count as prose. Without this the
    instruction needed a hand-rolled tag strip every week, which is exactly the kind of
    manual step that quietly stops happening."""
    html = without_style(html)
    text = re.sub(r"<(?:br\s*/?|/(?:p|h1|h2|h3|li|div|tr|table|ul|thead|tbody))>", "\n", html)
    text = re.sub(r"<[^>]*>", " ", text)
    text = unescape(text).replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line) + "\n"


def validate(html):
    # The print block must be there, once, and unedited: without it Save as PDF prints
    # one page (2026-09-28). Any other <style> is a hand edit.
    if html.count("<style") != 1 or not html.startswith('<div class="aw-recap">' + STYLE_BLOCK):
        die("the page must open with the aw-recap root and the print block, and have no "
            "other <style>. Edit PRINT_CSS, not the output.")
    html = without_style(html)
    markup = markup_only(html)
    for bad in FORBIDDEN:
        if bad in markup:
            die(f"forbidden construct in the MARKUP: {bad!r}. The markup is owned by this "
                f"script; edit the builders, not the output.")
    # SharePoint's page CSS overrides margin on <div> at render time (2026-09-28): use
    # padding or spacer(). A margin on a div is stored but silently not applied.
    if re.search(r'<div style="[^"]*(?<![a-z-])margin', markup):
        die("margin on a <div>: SharePoint does not apply it. Use padding or spacer().")
    if "{{" in markup:
        die("unsubstituted token in output")
    # Dashes are banned everywhere, the title included (it uses a comma since 2026-09-28).
    prose = prose_only(html)
    for char, name in (("\u2014", "em dash"), ("\u2013", "en dash")):
        if char in prose:
            die(f"{name} in the page. Alex bans them; use a comma, a colon, or a full stop.")


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
