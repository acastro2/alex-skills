#!/usr/bin/env python3
"""Read and edit the board table of a wiki page's HTML without touching any other byte.

Works on the page HTML the Atlassian connector returns with `contentFormat: html`. The page
holds one board table among other content. The board is found by its header texts, which
must equal the given columns exactly, in order.

Edits splice new text into the original string by character offset. The document is never
parsed into a tree and written back, so every byte outside an edited cell stays the same.
The first column is the row key.

CLI:
    board_table.py read  <page.html> --columns "Title,Stage,..."
        print the rows as JSON
    board_table.py apply <page.html> <changes.json> --columns "Title,Stage,..."
        print the new page HTML on stdout

A change is {"row": <key>, "column": <col>, "value": <str | {"text", "href"}>}
or {"new_row": {<every column>: <value>}}. A BoardError exits with code 2.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

Value = str | dict

_TABLE = re.compile(r"<table\b.*?</table>", re.DOTALL)
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
_HEADER_CELL = re.compile(r"<th\b[^>]*>(.*?)</th>", re.DOTALL)
_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.DOTALL)
_PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p>", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_LINK = re.compile(r'\s*<a\b[^>]*\bhref="([^"]*)"[^>]*>(.*?)</a>\s*', re.DOTALL)


class BoardError(Exception):
    pass


@dataclass
class _Row:
    cells: dict[str, tuple[int, int]]  # column -> (start, end) of the text to replace
    values: dict[str, Value]


@dataclass
class _Board:
    rows: list[_Row]
    insert_at: int  # offset where a new row goes: the end of the body


def _text(fragment: str) -> str:
    return htmllib.unescape(_TAG.sub("", fragment)).strip()


def _value(inner: str) -> Value:
    link = _LINK.fullmatch(inner)
    if link:
        return {"text": _text(link.group(2)), "href": htmllib.unescape(link.group(1))}
    return _text(inner)


def _find_board(page: str, columns: list[str]) -> _Board:
    matches = []
    for table in _TABLE.finditer(page):
        rows = list(_ROW.finditer(table.group(0)))
        if not rows:
            continue
        headers = [_text(h.group(1)) for h in _HEADER_CELL.finditer(rows[0].group(1))]
        if headers == columns:
            matches.append((table, rows))
    if not matches:
        raise BoardError(f"no board table with columns {columns}")
    if len(matches) > 1:
        raise BoardError(f"{len(matches)} tables have columns {columns}; expected one")

    table, rows = matches[0]
    base = table.start()
    body = []
    for row in rows[1:]:
        row_base = base + row.start(1)
        cells = list(_CELL.finditer(row.group(1)))
        if len(cells) != len(columns):
            raise BoardError(f"a board row has {len(cells)} cells, expected {len(columns)}")
        spans, values = {}, {}
        for column, cell in zip(columns, cells):
            inner = cell.group(1)
            paragraph = _PARAGRAPH.fullmatch(inner)
            if paragraph:
                start, end = row_base + cell.start(1) + paragraph.start(1), row_base + cell.start(1) + paragraph.end(1)
                inner = paragraph.group(1)
            else:
                start, end = row_base + cell.start(1), row_base + cell.end(1)
            spans[column] = (start, end)
            values[column] = _value(inner)
        body.append(_Row(spans, values))

    close_body = page.rfind("</tbody>", base, table.end())
    insert_at = close_body if close_body != -1 else table.end() - len("</table>")
    return _Board(body, insert_at)


def read_board(html: str, columns: list[str]) -> list[dict]:
    return [dict(row.values) for row in _find_board(html, columns).rows]


def _key(value: Value) -> str:
    return value["text"] if isinstance(value, dict) else value


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render(value: Value) -> str:
    if isinstance(value, str):
        return _escape(value)
    if isinstance(value, dict) and set(value) == {"text", "href"} and all(isinstance(v, str) for v in value.values()):
        href = _escape(value["href"]).replace('"', "&quot;")
        return f'<a href="{href}">{_escape(value["text"])}</a>'
    raise BoardError(f"a value must be a string or {{text, href}}, got {value!r}")


def apply_changes(html: str, columns: list[str], changes: list[dict]) -> str:
    board = _find_board(html, columns)
    by_key: dict[str, list[_Row]] = {}
    for row in board.rows:
        by_key.setdefault(_key(row.values[columns[0]]), []).append(row)
    taken = set(by_key)

    edits: dict[tuple[int, int], str] = {}
    new_rows = []
    for change in changes:
        if "new_row" in change:
            new = change["new_row"]
            if set(new) != set(columns):
                missing, extra = set(columns) - set(new), set(new) - set(columns)
                raise BoardError(f"new_row columns do not match the board: missing {sorted(missing)}, extra {sorted(extra)}")
            title = _key(new[columns[0]])
            if title in taken:
                raise BoardError(f"a row titled {title!r} already exists")
            taken.add(title)
            cells = "".join(f"<td><p>{_render(new[c])}</p></td>" for c in columns)
            new_rows.append(f"<tr>{cells}</tr>")
            continue
        rows = by_key.get(change.get("row"), [])
        if len(rows) != 1:
            raise BoardError(f"expected one row titled {change.get('row')!r}, found {len(rows)}")
        if change.get("column") not in columns:
            raise BoardError(f"unknown column {change.get('column')!r}")
        edits[rows[0].cells[change["column"]]] = _render(change["value"])

    # Splice from the end so earlier offsets stay valid.
    out = html[:board.insert_at] + "".join(new_rows) + html[board.insert_at:]
    for (start, end), text in sorted(edits.items(), reverse=True):
        out = out[:start] + text + out[end:]
    return out


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    read = sub.add_parser("read")
    read.add_argument("page")
    apply = sub.add_parser("apply")
    apply.add_argument("page")
    apply.add_argument("changes")
    for p in (read, apply):
        p.add_argument("--columns", required=True)
    args = parser.parse_args(argv)

    columns = [c.strip() for c in args.columns.split(",")]
    page = Path(args.page).read_text()
    try:
        if args.command == "read":
            print(json.dumps(read_board(page, columns), indent=2, ensure_ascii=False))
        else:
            changes = json.loads(Path(args.changes).read_text())
            sys.stdout.write(apply_changes(page, columns, changes))
    except BoardError as error:
        print(f"board_table: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
