"""The page content contract: every field, bound, and enum the weekly page accepts.

Why a separate module: the contract used to live in three places at once — a docstring, the
`need()` calls inside `render_page.py`, and two references — and it could only be tested by
rendering HTML and matching strings. Here it is data plus one pure function:

    validate(content)          # raises ContentError, or returns

No HTML, no `sys.exit`, no colours. `render_page.py` turns a `ContentError` into its own
`die()`, and a test can call `validate()` on a dict.

Every message names the exact path (`decisions[2].rationale`) so a failure reads as a content
fix, not as a traceback.
"""
from __future__ import annotations

# SKILL.md, Executive Summary gate. Enforced, not suggested: a band that quietly comes out
# at two points is the drift the render script exists to stop.
EXEC_POINTS_MIN, EXEC_POINTS_MAX = 3, 4

# A warning is the most-read block on the page, so a long one is a content fix, not a
# layout argument. Bounds follow Alex's template: "[Headline]" plus one or two sentences.
BAND_HEADLINE_MAX = 90
BAND_TEXT_MAX = 400

# A weekly page lists what moved, not the whole board.
MOVES_MAX = 8

TONES = ("info", "stop", "warn")
OUTCOME_TAGS = ("Achieved", "Partially achieved", "Not achieved")
TOPIC_TAGS = ("Decided", "Needs follow-up", "Parked")
# The board's stage values, verbatim. A stage outside these would render with no pill and
# name something the reader cannot find on the board.
STAGES = ("1. Exploring", "2. Committed", "3. Delivering", "4. Delivered", "5. Stopped")

# The forum record. A no_forum page must carry none of these.
FORUM_KEYS = (
    "objective",
    "outcome",
    "tldr",
    "decisions",
    "actions",
    "topics",
    "open_questions",
    "speakers",
    "speakers_source",
)

URL_PREFIXES = ("https://", "/sites/")

# Only the plain-string keys are listed here. The nested sections are required by the walk
# below, which checks their shape at the same time; listing them here would demand a string.
REQUIRED_WITH_FORUM = ("title", "subtitle", "objective", "tldr", "speakers", "speakers_source")
REQUIRED_NO_FORUM = ("title", "subtitle")

# Every key the renderer ever reads. The audit checks that prose naming a dotted key, such
# as `exec_summary.footnote`, uses a name from here; a key that is missing from this set
# turns correct prose into a finding, so it is one list, kept complete on purpose.
KEY_VOCABULARY = frozenset(
    {
        "action",
        "actions",
        "agenda",
        "agenda_title",
        "artifacts",
        "category",
        "chip",
        "decisions",
        "due",
        "evidence",
        "exec_summary",
        "footer",
        "from",
        "headline",
        "items",
        "label",
        "lead",
        "links",
        "next",
        "no_forum",
        "note",
        "objective",
        "open_questions",
        "outcome",
        "owner",
        "points",
        "portfolio_moves",
        "rationale",
        "sentence",
        "shipped",
        "source",
        "speakers",
        "speakers_source",
        "subtitle",
        "summary",
        "tag",
        "text",
        "title",
        "to",
        "tldr",
        "tone",
        "topics",
        "url",
        "warning",
        "window",
    }
)


# Keys that may appear at the top level of the content object. A dotted token in the prose
# is only subject to the schema check when its first segment is one of these.
TOP_LEVEL_KEYS = frozenset(
    {
        "title",
        "subtitle",
        "exec_summary",
        "warning",
        "no_forum",
        "objective",
        "tldr",
        "outcome",
        "decisions",
        "actions",
        "topics",
        "open_questions",
        "speakers",
        "speakers_source",
        "artifacts",
        "portfolio_moves",
        "shipped",
    }
)


class ContentError(ValueError):
    """The content is incomplete or out of contract. The message is the fix."""


def _need(obj, key, where, kind=str, allow_empty=False):
    if not isinstance(obj, dict):
        raise ContentError(f"{where} must be an object, got {type(obj).__name__}")
    if key not in obj:
        raise ContentError(f"{where} is missing required key {key!r}")
    value = obj[key]
    if not isinstance(value, kind):
        raise ContentError(f"{where}.{key} must be {kind.__name__}, got {type(value).__name__}")
    if not allow_empty and not value:
        raise ContentError(f"{where}.{key} is empty; fill it or the page ships with a hole in it")
    return value


def _need_list(obj, key, where, min_len=1):
    items = _need(obj, key, where, kind=list, allow_empty=min_len == 0)
    if len(items) < min_len:
        raise ContentError(f"{where}.{key} needs at least {min_len} item(s), got {len(items)}")
    return items


def _optional_str(obj, keys, where):
    for key in keys:
        if key in obj and not isinstance(obj[key], str):
            raise ContentError(f"{where}.{key} must be a string, got {type(obj[key]).__name__}")


def _url(value, where):
    """A URL here is either an absolute https link or a site-relative SharePoint path.

    Rendering adds `?web=1` for documents and escapes the attribute; that is the renderer's
    job. This function only decides whether the value is a link at all.
    """
    if not isinstance(value, str):
        raise ContentError(f"{where} must be a URL string, got {type(value).__name__}")
    if value.startswith(URL_PREFIXES):
        return value
    raise ContentError(f"{where} must be https:// or /sites/..., got {value!r}")


def _band(band, where):
    """The amber/red warning and the blue no-forum notice share one shape, so one check."""
    _need(band, "headline", where)
    _need(band, "text", where)
    _optional_str(band, ("label",), where)
    tone = band.get("tone", "warn")
    if tone not in TONES:
        raise ContentError(
            f"{where}.tone must be one of {sorted(TONES)}, got {tone!r}. 'warn' is the amber "
            f"IMPORTANT band, 'stop' the red STOP band, 'info' the blue notice."
        )
    if len(band["headline"]) > BAND_HEADLINE_MAX:
        raise ContentError(
            f"{where}.headline is {len(band['headline'])} chars; keep it under "
            f"{BAND_HEADLINE_MAX}. It is a headline, not a paragraph."
        )
    if len(band["text"]) > BAND_TEXT_MAX:
        raise ContentError(
            f"{where}.text is {len(band['text'])} chars; keep it under {BAND_TEXT_MAX}. One or "
            f"two short sentences, per the design."
        )
    for index, link in enumerate(band.get("links") or []):
        _need(link, "label", f"{where}.links[{index}]")
        _url(_need(link, "url", f"{where}.links[{index}]"), f"{where}.links[{index}].url")


def _forum(c):
    outcome = _need(c, "outcome", "content", kind=dict)
    _need(outcome, "text", "outcome")
    tag = _need(outcome, "tag", "outcome")
    if tag not in OUTCOME_TAGS:
        raise ContentError(
            f"outcome.tag must be one of {list(OUTCOME_TAGS)}, got {tag!r}. A typo here renders "
            f"amber and reads to the org as 'Partially achieved'."
        )

    for index, decision in enumerate(_need_list(c, "decisions", "content")):
        where = f"decisions[{index}]"
        for key in ("text", "rationale", "owner"):
            _need(decision, key, where)
        _optional_str(decision, ("lead", "chip"), where)

    for index, action in enumerate(_need_list(c, "actions", "content")):
        where = f"actions[{index}]"
        _need(action, "action", where)
        _need(action, "owner", where)
        _optional_str(action, ("due", "source"), where)

    for index, topic in enumerate(_need_list(c, "topics", "content")):
        where = f"topics[{index}]"
        _need(topic, "title", where)
        _need(topic, "summary", where)
        _optional_str(topic, ("owner",), where)
        for point_index, point in enumerate(topic.get("points") or []):
            if isinstance(point, dict):
                _need(point, "lead", f"{where}.points[{point_index}]")
                _need(point, "text", f"{where}.points[{point_index}]")
            elif not isinstance(point, str) or not point.strip():
                raise ContentError(
                    f"{where}.points[{point_index}] must be a non-empty string or {{lead, text}}"
                )
        if _need(topic, "tag", where) not in TOPIC_TAGS:
            raise ContentError(
                f"{where}.tag must be one of {sorted(TOPIC_TAGS)}, got {topic['tag']!r}"
            )

    for index, question in enumerate(_need_list(c, "open_questions", "content")):
        where = f"open_questions[{index}]"
        if isinstance(question, dict):
            _need(question, "text", where)
            _optional_str(question, ("next", "source"), where)
        elif not isinstance(question, str) or not question.strip():
            raise ContentError(
                f"{where} must be a string or {{text, next, source}}, got {question!r}"
            )


def _moves_artifacts_shipped(c, no_forum):
    if "portfolio_moves" in c:
        moves = _need(c, "portfolio_moves", "content", kind=list, allow_empty=True)
        if len(moves) > MOVES_MAX:
            raise ContentError(
                f"portfolio_moves has {len(moves)}; the page carries at most {MOVES_MAX}. "
                f"List the moves that matter this week."
            )
        for index, move in enumerate(moves):
            where = f"portfolio_moves[{index}]"
            _need(move, "title", where)
            for key, stage in (("from", _need(move, "from", where)), ("to", _need(move, "to", where))):
                if stage not in STAGES:
                    raise ContentError(
                        f"{where}.{key} must be one of {list(STAGES)}, got {stage!r}"
                    )
            if move["from"] == move["to"]:
                raise ContentError(
                    f"{where}.from and {where}.to are both {move['from']!r}; a move changes stage"
                )
            if "url" in move:
                _url(_need(move, "url", where), f"{where}.url")

    # An artifact always carries a link: a bare file name is a hard stop. A no_forum page may
    # still link artifacts, but needs none.
    artifacts = _need_list(c, "artifacts", "content") if not no_forum else c.get("artifacts", [])
    for index, artifact in enumerate(artifacts):
        where = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            raise ContentError(
                f"{where} must be {{label, url, note}} with a real link, got {artifact!r}"
            )
        _need(artifact, "label", where)
        _url(_need(artifact, "url", where), f"{where}.url")
        _optional_str(artifact, ("note",), where)

    shipped = _need(c, "shipped", "content", kind=dict)
    _need(shipped, "window", "shipped")
    for index, item in enumerate(_need_list(shipped, "items", "shipped")):
        where = f"shipped.items[{index}]"
        _need(item, "sentence", where)
        _optional_str(item, ("category",), where)
        # An item with no evidence renders as a bare "Evidence:" with nothing after it. The
        # panel's whole claim is that it is evidence-backed, so this is a hard stop.
        for evidence_index, evidence in enumerate(_need_list(item, "evidence", where)):
            where_evidence = f"{where}.evidence[{evidence_index}]"
            _need(evidence, "label", where_evidence)
            _url(_need(evidence, "url", where_evidence), f"{where_evidence}.url")


def validate(content) -> None:
    """Check one week's content. Raises ContentError with the first problem found."""
    if not isinstance(content, dict):
        raise ContentError(f"content must be an object, got {type(content).__name__}")

    # A week with no forum (Alex, 2026-10-12): the page carries one line in the forum's slot
    # and no forum sections. Never fill decisions or topics a forum did not produce.
    no_forum = "no_forum" in content
    if no_forum:
        notice = _need(content, "no_forum", "content", kind=dict)
        _band(notice, "no_forum")
        for index, agenda_item in enumerate(notice.get("agenda") or []):
            where = f"no_forum.agenda[{index}]"
            _need(agenda_item, "title", where)
            _url(_need(agenda_item, "url", where), f"{where}.url")
            _optional_str(agenda_item, ("note",), where)
        _optional_str(notice, ("agenda_title",), "no_forum")
        for key in FORUM_KEYS:
            if key in content:
                raise ContentError(
                    f"{key} is set on a no_forum page; a week with no forum has no forum record"
                )

    for key in REQUIRED_NO_FORUM if no_forum else REQUIRED_WITH_FORUM:
        _need(content, key, "content")

    summary = _need(content, "exec_summary", "content", kind=dict)
    _need(summary, "headline", "exec_summary")
    # Never blank, and never softened into silence: SKILL.md, Executive Summary gate.
    _need(summary, "footer", "exec_summary")
    points = _need_list(summary, "points", "exec_summary", min_len=EXEC_POINTS_MIN)
    if len(points) > EXEC_POINTS_MAX:
        raise ContentError(
            f"exec_summary.points has {len(points)}; SKILL.md sets {EXEC_POINTS_MIN} to "
            f"{EXEC_POINTS_MAX}. Merge two points, do not widen the band."
        )
    for index, point in enumerate(points):
        _need(point, "text", f"exec_summary.points[{index}]")
        if "lead" in point:
            _need(point, "lead", f"exec_summary.points[{index}]", allow_empty=True)

    if "warning" in content:
        _band(_need(content, "warning", "content", kind=dict), "warning")

    if not no_forum:
        _forum(content)
    _moves_artifacts_shipped(content, no_forum)
