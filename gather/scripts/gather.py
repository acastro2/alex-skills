#!/usr/bin/env python3
"""gather: fetch-only intake. Writes raw, verbatim tool results to a local store.

Contracts: references/spec.md (next to SKILL.md). The `claude` and `gh` subprocesses are injected, so the
core (`run`) is testable without a network.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

M365 = "mcp__claude_ai_Microsoft_365__"
ATL = "mcp__claude_ai_Atlassian__"
HINT_KEYS = ("moreResults", "nextOffset", "nextCursor")
FIRST_RUN_DAYS = 7
# Teams and mail search can index a message after it was sent (Alex chose 15 min, 2026-11-13)
CURSOR_OVERLAP = timedelta(minutes=15)
# One chain per day keeps a busy week from hitting the page cap in its first days
CHUNK = timedelta(days=1)
# Upcoming deadlines: the calendar reaches this far past the run start
CALENDAR_AHEAD = timedelta(days=14)
RETENTION = "30d"
# Alex's personal GitHub account: never gather from it (Alex, 2026-11-13)
PERSONAL_GH = "acastro2"
CLAUDE_TIMEOUT_S = 300
# Above Claude Code's default cap a result becomes an error text with no data in the stream.
MCP_OUTPUT_TOKENS = "200000"
PREVIEW_MARK = "<persisted-output>"
CAP_ERROR = re.compile(r"Error: result \([\d,]+ characters\) exceeds maximum allowed tokens")
DEFAULT_ROOT = Path.home() / ".gather"
_SPACE = re.compile(r"\s*")
# a JSON body with only these keys is an error reply, not data
ERROR_KEYS = {"error", "message", "code", "status", "statusCode"}

# window sources, the calls each one makes. `me` fills the "ME" marker.
# (tool, fixed args, max page size)
WINDOW = {
    "teams_chats": [("chat_message_search", {"query": "*", "recipient": "ME"}, 25)],
    "teams_mine": [("chat_message_search", {"query": "*", "sender": "ME"}, 25)],
    "mail": [
        ("outlook_email_search", {"recipient": "ME"}, 25),
        ("outlook_email_search", {"sender": "ME"}, 25),
    ],
    "calendar": [("outlook_calendar_search", {"query": "*"}, 25)],
    # author takes the display name: live, author=<mail> matched nothing (2026-11-13)
    "sharepoint": [("sharepoint_search", {"query": "*", "author": "ME_NAME"}, 50)],
}

# Sources the first slice cannot fetch correctly. Each reason is the proof gap.
NOT_FETCHED = {
    "teams_channels": "channel hit shape and reply activity fields not verified live",
}

SOURCES = ["teams_chats", "teams_mine", "teams_channels", "mail", "calendar", "sharepoint", "jira", "github", "github_activity"]
ACTIVITY_PAGES = 3
# snapshot sources whose mark moves even after a cap: see fetch_one
STREAM = ("github_activity",)
# one busy day touched more than 50 items live (2026-11-13); a cap that binds daily never clears
ACTIVITY_TIMELINES = 200

# Snapshot: every open item assigned to Alex. bard filters by changelog date, so no Jira
# time-zone watermark is needed here.
JIRA_JQL = "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"
JIRA_FIELDS = ["summary", "status", "issuetype", "duedate", "updated"]

GH_FIELDS = "number,title,url,repository,author,state,isDraft,updatedAt,createdAt"
GH_LIMIT = 100
# getJiraIssue calls per `claude -p` round: one run per issue cost a process start each
JIRA_BATCH = 10


class GuardError(Exception):
    def __init__(self, tool):
        super().__init__(f"tool not allowed: {tool}")
        self.tool = tool


class PersonalAccount(Exception):
    pass


class SpillError(Exception):
    pass


class ToolError(Exception):
    """`reason` is fixed text that is safe for the ledger. `detail` may hold private text, so it
    goes to the log only."""

    def __init__(self, reason, detail=""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


# --- stream-json -----------------------------------------------------------------------

def _result_text(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


def _full_text(full):
    if isinstance(full, dict):
        full = full.get("content")
    return _result_text(full) if full is not None else ""


def parse_stream(text, allowed):
    """tool_use / tool_result pairs, matched by id, in call order."""
    uses, results = {}, {}
    for line in text.splitlines():
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        content = (msg.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        # A spilled result: the block holds a preview, the line's tool_use_result the full text.
        full = msg.get("tool_use_result")
        n_results = sum(1 for b in content if isinstance(b, dict) and b.get("type") == "tool_result")
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                if block["name"] not in allowed:
                    raise GuardError(block["name"])
                uses[block["id"]] = block
            elif block.get("type") == "tool_result":
                if full is not None and n_results == 1 and _result_text(block.get("content")).startswith(PREVIEW_MARK):
                    block = {**block, "content": _full_text(full)}
                results[block["tool_use_id"]] = block
    calls = []
    for tid, use in uses.items():
        res = results.get(tid)
        calls.append({
            "tool": use["name"],
            "args": use.get("input", {}),
            "content": _result_text(res.get("content")) if res else "no tool_result in the stream",
            "is_error": bool(res.get("is_error")) if res else True,
        })
    return calls


def resolve_spill(content):
    """Never store a preview or a size error as if it were the result. The spill file the
    preview names is deleted when the run ends, so it is not a source."""
    if content.startswith(PREVIEW_MARK):
        raise SpillError("only a preview came back; the full text was not in the stream")
    if CAP_ERROR.match(content):
        raise SpillError(f"result over MAX_MCP_OUTPUT_TOKENS={MCP_OUTPUT_TOKENS}")
    return content


def json_values(text):
    """Every JSON value at the start of `text`, back to back. Stops at the first thing that is not
    JSON: mail search ends its JSON with a plain-text note (seen live)."""
    dec, i, out = json.JSONDecoder(), 0, []
    while True:
        i = _SPACE.match(text, i).end()
        if i >= len(text):
            return out
        try:
            value, i = dec.raw_decode(text, i)
        except ValueError:
            return out
        out.append(value)


def _error_body(value):
    return isinstance(value, dict) and bool(value) and set(value) <= ERROR_KEYS


def _valid_result(tool, text):
    """Non-error text is data only when it starts with JSON or is the connector's empty text. Auth pages
    and other prose come back with is_error unset, and a bare error body can come back as JSON; none
    of these may be stored as a result."""
    if text == f"({tool} completed with no output)":
        return True
    values = json_values(text)
    return bool(values) and not all(_error_body(v) for v in values)


def run_round(runner, calls, tolerate_errors=False):
    """One `claude -p` round. The model sometimes changes an argument (seen live: an invented
    `uri` key on get_me). A drifted round is thrown away and tried up to 3 times in all, and
    each try can take up to CLAUDE_TIMEOUT_S. With `tolerate_errors`, a call whose result is an
    error comes back with is_error set and the caller decides; otherwise it raises."""
    allowed = sorted({c["tool"] for c in calls})
    for attempt in (1, 2, 3):
        got = parse_stream(runner(calls, allowed), set(allowed))
        if len(got) == len(calls) and all(
                g["tool"] == c["tool"] and g["args"] == c["args"] for g, c in zip(got, calls)):
            break
        if attempt == 3:
            raise ToolError("call mismatch", f"asked for {len(calls)} calls, the model made {len(got)} "
                                             "or changed their arguments, three times")
    for c in got:
        if c["is_error"]:
            if tolerate_errors:
                continue
            raise ToolError("tool error", c["content"][:200])
        c["content"] = resolve_spill(c["content"])
        if not _valid_result(c["tool"], c["content"]):
            raise ToolError("unexpected result", c["content"][:200])
    return got


# --- items and paging --------------------------------------------------------------------

def top_level_values(text):
    return [v for v in json_values(text) if isinstance(v, (dict, list))]


def count_items(content):
    n = 0
    for v in top_level_values(content):
        if isinstance(v, list):
            n += len(v)
        elif not any(k in v for k in HINT_KEYS):
            n += 1
    return n


def next_args(args, content):
    """Args for the next page, or None on the last page."""
    values = top_level_values(content)
    last = values[-1] if values and isinstance(values[-1], dict) else {}
    if last.get("moreResults") is False:
        return None
    nxt = dict(args)
    if last.get("nextOffset") is not None:
        nxt.pop("cursor", None)
        nxt["offset"] = last["nextOffset"]
        return nxt
    if last.get("nextCursor") is not None:
        nxt.pop("offset", None)
        nxt["cursor"] = last["nextCursor"]
        return nxt
    if last.get("moreResults"):
        raise ToolError("paging", "page says there is more but gives no next offset or cursor")
    return None


def has_end_hint(content):
    values = top_level_values(content)
    return bool(values) and isinstance(values[-1], dict) and any(k in values[-1] for k in HINT_KEYS)


def fetch_pages(runner, tool, args, max_pages):
    """Returns (records, items, capped). `capped` is the page count when the source stopped
    early, else 0. A full page with no end hint may hide more items, so it counts as capped."""
    records, items = [], 0
    for page in range(1, max_pages + 1):
        (call,) = run_round(runner, [{"tool": tool, "args": args}])
        records.append(call)
        n = count_items(call["content"])
        items += n
        args = next_args(call["args"], call["content"])
        if args is None:
            full = n == call["args"].get("limit") and not has_end_hint(call["content"])
            return records, items, page if full else 0
    return records, items, max_pages


# --- sources -----------------------------------------------------------------------------

@dataclass
class Ctx:
    runner: object
    gh: object
    me: str
    me_name: object
    now: datetime
    max_pages: int
    chunk: object = None
    after: object = None


@dataclass
class Fetched:
    """What one source read. `capped` is the ledger line when it stopped early; `resume_from` is
    where the next run must start then, and `clean_before` says a chunk before that point finished."""
    records: list
    items: int
    capped: str = ""
    resume_from: object = None
    clean_before: bool = False
    issue_errors: int = 0
    notes: list = field(default_factory=list)


def iso_z(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def spans(source, ctx):
    """(start, end) windows for one source, oldest first. `end` None means no upper bound."""
    if source == "calendar":
        return [(ctx.after, ctx.now + CALENDAR_AHEAD)]
    if ctx.chunk is None:
        return [(ctx.after, None)]
    out, start = [], ctx.after
    while start < ctx.now:
        out.append((start, min(start + ctx.chunk, ctx.now)))
        start = out[-1][1]
    return out


def fetch_window(source, ctx):
    got = Fetched([], 0)
    marks = {"ME": ctx.me, "ME_NAME": ctx.me_name}
    for done, (start, end) in enumerate(spans(source, ctx)):
        capped = 0
        for name, fixed, size in WINDOW[source]:
            args = {k: marks.get(v, v) for k, v in fixed.items()}
            args.update(afterDateTime=iso_z(start), limit=size, offset=0)
            if end:
                args["beforeDateTime"] = iso_z(end)
            recs, n, cap = fetch_pages(ctx.runner, M365 + name, args, ctx.max_pages)
            got.records += recs
            got.items += n
            capped = capped or cap
        if capped:
            got.capped, got.resume_from, got.clean_before = f"capped at {capped} pages", start, done > 0
            break
    return got


def fetch_github(ctx):
    login = ctx.gh(["api", "user", "--jq", ".login"]).strip()
    if login == PERSONAL_GH:
        raise PersonalAccount(login)
    since = ctx.after.strftime("%Y-%m-%d")
    queries = [
        ["--review-requested=@me", "--state=open"],
        ["--involves=@me", f"--updated=>={since}"],
    ]
    got = Fetched([], 0)
    for q in queries:
        argv = ["search", "prs", *q, "--limit", str(GH_LIMIT), "--json", GH_FIELDS]
        out = ctx.gh(argv)
        got.records.append({"tool": "gh", "args": {"argv": argv, "login": login}, "content": out})
        n = count_items(out)
        got.items += n
        if n == GH_LIMIT:
            got.capped = f"capped at gh limit {GH_LIMIT}"
    return got


def _when(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def event_number(event):
    p = event.get("payload") or {}
    kind = event.get("type")
    if kind in ("IssueCommentEvent", "IssuesEvent"):
        return (p.get("issue") or {}).get("number")
    if kind == "PullRequestEvent":
        return p.get("number") or (p.get("pull_request") or {}).get("number")
    if kind in ("PullRequestReviewEvent", "PullRequestReviewCommentEvent"):
        return (p.get("pull_request") or {}).get("number")
    return None


def fetch_github_activity(ctx):
    login = ctx.gh(["api", "user", "--jq", ".login"]).strip()
    if login == PERSONAL_GH:
        raise PersonalAccount(login)
    got = Fetched([], 0)

    def call(argv):
        out = ctx.gh(argv)
        got.records.append({"tool": "gh", "args": {"argv": argv, "login": login}, "content": out})
        return out

    # (repo, number) -> newest activity time, so a cap drops the oldest items, not the highest numbers
    touched, in_window, full_window = {}, 0, False

    def touch(key, when):
        touched[key] = max(touched.get(key, when), when)

    for page in range(1, ACTIVITY_PAGES + 1):
        events = json.loads(call(["api", f"users/{login}/events?per_page=100&page={page}"]))
        recent = [e for e in events if _when(e["created_at"]) >= ctx.after]
        in_window += len(recent)
        for e in recent:
            n = event_number(e)
            if n:
                touch((e["repo"]["name"], n), _when(e["created_at"]))
        if len(events) < 100 or len(recent) < len(events):
            break
        full_window = page == ACTIVITY_PAGES
    since = ctx.after.strftime("%Y-%m-%d")
    out = call(["search", "prs", "--involves=@me", f"--updated=>={since}", "--limit", str(GH_LIMIT),
                "--json", "number,repository,updatedAt"])
    found = json.loads(out)
    for item in found:
        touch((item["repository"]["nameWithOwner"], item["number"]), _when(item.get("updatedAt") or iso_z(ctx.after)))
    items = sorted(touched, key=lambda k: (-touched[k].timestamp(), k))
    for repo, number in items[:ACTIVITY_TIMELINES]:
        call(["api", f"repos/{repo}/issues/{number}/timeline?per_page=100", "--paginate", "--slurp"])
    got.items = in_window + min(len(items), ACTIVITY_TIMELINES)
    if full_window:
        got.capped = f"capped at events limit {ACTIVITY_PAGES * 100}"
    elif len(found) == GH_LIMIT:
        got.capped = f"capped at gh limit {GH_LIMIT}"
    elif len(items) > ACTIVITY_TIMELINES:
        got.capped = f"capped at {ACTIVITY_TIMELINES} timelines"
    return got


def jira_page(content):
    """(issue keys, pageInfo) of one search result. The shape is {"issues": {"nodes": [...]}}."""
    try:
        issues = json.loads(content)["issues"]
        nodes, info = issues["nodes"], issues.get("pageInfo") or {}
        if not isinstance(nodes, list) or not isinstance(info, dict):
            raise TypeError("wrong shape")
        keys = [n["key"] for n in nodes]
    except (ValueError, AttributeError, KeyError, TypeError):
        raise ToolError("unexpected result", content[:200]) from None
    return keys, info


def fetch_jira(ctx):
    (site,) = run_round(ctx.runner, [{"tool": ATL + "getAccessibleAtlassianResources", "args": {}}])
    sites = [v for arr in top_level_values(site["content"]) if isinstance(arr, list) for v in arr]
    cloud = next((v["id"] for v in sites if "read:jira-work" in v.get("scopes", [])), None)
    if not cloud:
        raise ToolError("no jira site")
    got, keys = Fetched([site], 0), []
    args = {"cloudId": cloud, "jql": JIRA_JQL, "fields": JIRA_FIELDS, "maxResults": 50}
    for _ in range(ctx.max_pages):
        (page,) = run_round(ctx.runner, [{"tool": ATL + "searchJiraIssuesUsingJql", "args": args}])
        got.records.append(page)
        page_keys, info = jira_page(page["content"])
        keys += page_keys
        if not info.get("hasNextPage"):
            break
        if not info.get("endCursor"):
            raise ToolError("unexpected result", "page has a next page but no endCursor")
        args = {**args, "nextPageToken": info["endCursor"]}
    else:
        got.items, got.capped = len(keys), f"capped at {ctx.max_pages} pages"
        return got
    got.items = len(keys)
    for i in range(0, len(keys), JIRA_BATCH):
        calls = run_round(ctx.runner, [{"tool": ATL + "getJiraIssue", "args": {
            "cloudId": cloud, "issueIdOrKey": key, "expand": "changelog",
            "fields": JIRA_FIELDS + ["comment"], "responseContentFormat": "markdown"}}
            for key in keys[i:i + JIRA_BATCH]], tolerate_errors=True)
        for c in calls:
            if c["is_error"]:
                got.issue_errors += 1
                got.notes.append(f"jira {c['args'].get('issueIdOrKey')}: tool error: {c['content'][:200]}")
            else:
                got.records.append(c)
    return got


def fetch_source(source, ctx):
    if source == "github":
        return fetch_github(ctx)
    if source == "github_activity":
        return fetch_github_activity(ctx)
    if source == "jira":
        return fetch_jira(ctx)
    return fetch_window(source, ctx)


# --- store -------------------------------------------------------------------------------

def read_state(root):
    p = root / "state.json"
    state = json.loads(p.read_text()) if p.exists() else {}
    if not isinstance(state, dict):
        raise ValueError("state.json is not a JSON object")
    for key in ("cursors", "last_ok", "covered_from"):
        if not isinstance(state.setdefault(key, {}), dict):
            raise ValueError(f"state.json {key} is not a JSON object")
    return state


def mkdir_private(path):
    path = Path(path)
    missing = []
    while not path.exists():
        missing.append(path)
        path = path.parent
    for d in reversed(missing):
        d.mkdir(mode=0o700)
        d.chmod(0o700)


def write_private(path, text):
    """Temp file in the same folder, then os.replace: a crash never leaves a half-written file."""
    path = Path(path)
    mkdir_private(path.parent)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path, obj):
    write_private(path, json.dumps(obj, indent=2, ensure_ascii=False))


def write_ledger(root, run_id, now, ledger, details):
    """Ledger lines hold fixed reasons only. Exception text and tool output can hold private
    comms, so they go to logs/<run_id>.log."""
    write_json(root / "ledger" / f"{run_id}.json", {"run_id": run_id, "started_at": now.isoformat(), "sources": ledger})
    if details:
        write_private(root / "logs" / f"{run_id}.log", "\n".join(details) + "\n")


def store_records(root, source, run_id, now, records, provenance):
    day = now.astimezone(timezone.utc).strftime("%Y-%m-%d")
    for n, rec in enumerate(records, 1):
        write_json(root / "raw" / source / day / f"{run_id}-{n}.json", {
            "source": source, "tool": rec["tool"], "args": rec["args"], "run_id": run_id,
            "fetched_at": now.isoformat(), "provenance": provenance, "content": rec["content"],
        })


def move_mark(marks, source, when, pick):
    """`pick` is max to move a mark later, min to move it earlier: a mark never goes the other way."""
    old = marks.get(source)
    marks[source] = (when if old is None else pick(datetime.fromisoformat(old), when)).isoformat()


def prune(root, *, older_than, now):
    """Delete raw day folders and run logs whose date is older than now - older_than. Never
    touches state.json or ledger/. Returns the number removed."""
    cutoff, removed = now - older_than, 0
    for day in Path(root).glob("raw/*/*"):
        try:
            end = datetime.strptime(day.name, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        except ValueError:
            continue
        if end <= cutoff and day.is_dir() and not day.is_symlink():
            shutil.rmtree(day)
            removed += 1
    for log in Path(root).glob("logs/*.log"):
        try:
            when = datetime.strptime(log.name[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if when < cutoff and log.is_file():
            log.unlink()
            removed += 1
    return removed


def new_run_id(now):
    return f"{now.astimezone(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def failure_reason(source, e):
    if isinstance(e, ToolError):
        return e.reason
    if isinstance(e, SpillError):
        return "spill"
    return "gh failed" if source in ("github", "github_activity") else "claude failed"


def window_start(source, anchor, since, now):
    if since:
        return since
    if anchor is None:
        return now - timedelta(days=FIRST_RUN_DAYS)
    start = datetime.fromisoformat(anchor)
    # gh's `updated` filter is a date, and a PR can change after the last run's own start time
    return start - timedelta(days=1) if source in ("github", "github_activity") else start


def skip_line(source, me_name, stopped):
    """The ledger line of a source that is not fetched at all, else None."""
    if stopped:
        return "not fetched: run stopped after a guard abort"
    if source in NOT_FETCHED:
        return f"not fetched: {NOT_FETCHED[source]}"
    if source not in WINDOW and source not in ("github", "github_activity", "jira"):
        return "error: unknown source"
    if not me_name and any(v == "ME_NAME" for _, fixed, _ in WINDOW.get(source, []) for v in fixed.values()):
        return "not fetched: no display name from get_me"
    return None


def fetch_one(source, base, state, root, run_id, since, details):
    """Fetch one source, store what it read, and move its marks. Returns (ledger line, guard abort)."""
    # window sources keep a cursor; snapshot sources keep only the time of the last good run
    marks = state["cursors"] if source in WINDOW else state["last_ok"]
    anchor = marks.get(source)
    anchor_dt = datetime.fromisoformat(anchor) if anchor else None
    ctx = replace(base, after=window_start(source, anchor, since, base.now))
    try:
        got = fetch_source(source, ctx)
    except GuardError as e:
        return f"aborted: guard {e.tool}", True
    except PersonalAccount:
        return "not fetched: active gh account is the personal one", False
    except Exception as e:
        details.append(f"{source}: {type(e).__name__}: {e}")
        return f"error: {failure_reason(source, e)}", False
    details.extend(got.notes)
    # A capped source keeps what it read, so the pages are not paid for twice. Its cursor moves to
    # the start of the capped chunk, so the next run resumes there and never skips it. A --since
    # later than the cursor leaves it where it was.
    store_records(root, source, run_id, ctx.now, got.records, "verbatim")
    if got.capped:
        if source in WINDOW and not (since and anchor_dt and since > anchor_dt):
            move_mark(marks, source, got.resume_from or ctx.after, max)
        if got.clean_before:
            move_mark(state["covered_from"], source, ctx.after, min)
        # a stream cap is not fetchable later (the events API keeps 300), and a stuck mark would
        # widen every later window and cap it again, so the gap is reported once and the mark moves
        if source in STREAM and not (since and (anchor_dt is None or since > anchor_dt)):
            move_mark(marks, source, ctx.now, max)
        return got.capped, False
    if got.issue_errors:
        return f"partial: {len(got.records)} calls, {got.items} items, {got.issue_errors} issue errors", False
    # a --since later than the mark, or with no mark at all, leaves an unfetched gap
    if not (since and (anchor_dt is None or since > anchor_dt)):
        move_mark(marks, source, ctx.now - CURSOR_OVERLAP if source in WINDOW else ctx.now, max)
    if source in WINDOW:
        move_mark(state["covered_from"], source, ctx.after, min)
    return f"fetched {len(got.records)} calls, {got.items} items", False


def run(sources, *, root, now, runner, me, max_pages=40, gh=None, since=None, me_name=None,
        preset=None, notes=(), chunk=None):
    """Fetch each source once. Returns {source: ledger line}. `preset` maps a source to a ledger
    line the caller already knows, so it is not fetched; `notes` go to the run log. `chunk` splits
    a window source's window into spans of that length, oldest first. State and ledger are saved
    after each source, so a crash keeps the finished ones."""
    root = Path(root)
    run_id = new_run_id(now)
    preset = preset or {}
    ledger, details, stopped = {}, list(notes), False
    try:
        state = read_state(root)
    except (ValueError, OSError) as e:
        # never write state.json here: it would destroy a file we could not read
        ledger = {s: "error: state unreadable" for s in sources}
        write_ledger(root, run_id, now, ledger, [*details, f"state.json: {type(e).__name__}: {e}"])
        return ledger
    base = Ctx(runner, gh or real_gh, me, me_name, now, max_pages, chunk)
    for source in sources:
        line = preset.get(source) or skip_line(source, me_name, stopped)
        if line is None:
            line, aborted = fetch_one(source, base, state, root, run_id, since, details)
            stopped = stopped or aborted
        ledger[source] = line
        write_json(root / "state.json", state)
        write_ledger(root, run_id, now, ledger, details)
    return ledger


# --- real boundaries -----------------------------------------------------------------------

def real_gh(argv):
    p = subprocess.run(["gh", *argv], capture_output=True, text=True, timeout=120)
    if p.returncode:
        raise RuntimeError(f"gh exited {p.returncode}: {p.stderr.strip()[:200]}")
    return p.stdout


def _project_dir(cwd):
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(Path(cwd).resolve()))


def _drop_empty_project_dir(cwd):
    """A spill makes an empty ~/.claude/projects/<cwd> folder even with no session saved.
    Remove it only when empty, so nothing of Alex's is ever deleted."""
    d = _project_dir(cwd)
    for sub in (d / "memory", d):
        try:
            sub.rmdir()
        except OSError:
            pass


def _drop_tool_results(cwd):
    """A killed run leaves its spilled results behind, and they hold private text. Only this
    cwd's own project folder is touched."""
    d = _project_dir(cwd)
    for f in d.glob("*/tool-results/*"):
        if f.is_file():
            f.unlink(missing_ok=True)
    for sub in [*d.glob("*/tool-results"), *d.glob("*")]:
        try:
            sub.rmdir()
        except OSError:
            pass


def claude_runner(root):
    """Real runner. The prompt goes on stdin because the variadic --allowedTools swallows a
    positional prompt. cwd is <root>/run so no session lands under a real project."""
    cwd = Path(root) / "run"
    mkdir_private(cwd)

    def runner(calls, allowed):
        prompt = (
            "Make exactly these tool calls, in this order, with exactly these arguments. "
            "Call no other tool. Do not retry a failed call and do not change its arguments. "
            "After the last call, reply DONE.\n" + json.dumps(calls, indent=1))
        # dontAsk denies every tool not in --allowedTools; the default mode ran an unlisted one (live 2026-11-13).
        # --allowedTools is variadic and goes last.
        cmd = ["claude", "-p", "--model", "haiku", "--output-format", "stream-json", "--verbose",
               "--tools", "", "--permission-mode", "dontAsk", "--no-session-persistence",
               "--allowedTools", *allowed]
        # auto-memory would create an empty ~/.claude/projects/<cwd> folder even with no session saved
        env = {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "MAX_MCP_OUTPUT_TOKENS": MCP_OUTPUT_TOKENS}
        try:
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd, env=env,
                               timeout=CLAUDE_TIMEOUT_S)
        finally:
            _drop_tool_results(cwd)
            _drop_empty_project_dir(cwd)
        if p.returncode:
            raise RuntimeError(f"claude exited {p.returncode}: {(p.stderr or p.stdout)[-200:].strip()}")
        return p.stdout

    return runner


def lookup_me(runner):
    tool = M365 + "get_me"
    (call,) = run_round(runner, [{"tool": tool, "args": {}}])
    for v in top_level_values(call["content"]):
        if isinstance(v, dict):
            for key in ("mail", "userPrincipalName"):
                if v.get(key):
                    return v[key], v.get("displayName")
    raise ToolError("get_me returned no mail or userPrincipalName")


# --- CLI ---------------------------------------------------------------------------------

def parse_age(text):
    m = re.fullmatch(r"(\d+)([dh])", text)
    if not m:
        raise ValueError(f"bad age: {text}")
    return timedelta(**{"days" if m.group(2) == "d" else "hours": int(m.group(1))})


def parse_since(text, now):
    if re.fullmatch(r"\d+[dh]", text):
        return now - parse_age(text)
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def exit_code(ledger):
    """A source that is not built yet is reported, not failed: an exit that is always 1
    teaches the reader to ignore it. Any other gap fails the run."""
    if any(v.startswith("aborted: guard") for v in ledger.values()):
        return 3
    ok = all(v.startswith("fetched") or (s in NOT_FETCHED and v == f"not fetched: {NOT_FETCHED[s]}")
             for s, v in ledger.items())
    return 0 if ok else 1


def cmd_run(a):
    now = datetime.now(timezone.utc)
    root = Path(a.root).expanduser()
    names = a.sources.split(",") if a.sources else SOURCES
    bad = [s for s in names if s not in SOURCES]
    if bad:
        print(f"unknown source: {', '.join(bad)}; known: {', '.join(SOURCES)}", file=sys.stderr)
        return 2
    runner = claude_runner(root)
    try:
        since = parse_since(a.since, now) if a.since else None
    except ValueError:
        print(f"bad --since: {a.since}", file=sys.stderr)
        return 2
    me, me_name = a.me, a.me_name
    preset, notes = {}, []
    if not me and any(s in WINDOW for s in names):
        try:
            me, found_name = lookup_me(runner)
            me_name = me_name or found_name
        except Exception as e:
            # only the window sources need `me`; jira and github still run
            preset = {s: "error: get_me failed" for s in names if s in WINDOW}
            notes = [f"get_me: {type(e).__name__}: {e}"]
    ledger = run(names, root=root, now=now, runner=runner, me=me, max_pages=a.max_pages, since=since,
                 me_name=me_name, preset=preset, notes=notes, chunk=CHUNK)
    for s, line in ledger.items():
        print(f"{s}: {line}")
    return exit_code(ledger)


def cmd_prune(a):
    try:
        age = parse_age(a.older_than)
    except ValueError:
        print(f"bad --older-than: {a.older_than}", file=sys.stderr)
        return 2
    removed = prune(Path(a.root).expanduser(), older_than=age, now=datetime.now(timezone.utc))
    print(f"pruned {removed}")
    return 0


def cmd_status(a):
    root = Path(a.root).expanduser()
    try:
        state = read_state(root)
    except (ValueError, OSError) as e:
        print(f"state unreadable: {root / 'state.json'}: {type(e).__name__}", file=sys.stderr)
        return 1
    for s, c in sorted(state["cursors"].items()):
        print(f"cursor {s}: {c}")
    for s, c in sorted(state["last_ok"].items()):
        print(f"last ok {s}: {c}")
    ledgers = sorted((root / "ledger").glob("*.json")) if (root / "ledger").exists() else []
    if not ledgers:
        print("no runs yet")
        return 0
    last = json.loads(ledgers[-1].read_text())
    print(f"last run {last['run_id']}")
    for s, line in last["sources"].items():
        print(f"  {s}: {line}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gather")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--sources")
    r.add_argument("--since")
    r.add_argument("--max-pages", type=int, default=40)
    r.add_argument("--me")
    r.add_argument("--me-name")
    sub.add_parser("status")
    sub.add_parser("prune").add_argument("--older-than", default=RETENTION)
    # `--root` after the subcommand reads naturally too
    for p in sub.choices.values():
        p.add_argument("--root", default=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    return {"run": cmd_run, "prune": cmd_prune, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
