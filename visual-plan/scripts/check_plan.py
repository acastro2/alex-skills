#!/usr/bin/env python3
"""Fast structural check for a visual-plan HTML file.

Replaces hand re-reading the whole document for tag balance, leftover
template placeholders, and broken Mermaid blocks. Run it right after
writing the file, before opening it for the user:

    python3 scripts/check_plan.py plan-my-feature.html

Exit code 0 = pass (warnings allowed), 1 = at least one failure.
Stdlib only; no dependencies.
"""

import re
import sys
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "source", "track", "wbr"}

MERMAID_STARTERS = (
    "flowchart", "graph", "sequencediagram", "statediagram", "erdiagram",
    "classdiagram", "gantt", "pie", "xychart", "journey", "timeline",
    "quadrantchart", "mindmap", "block-beta", "sankey",
)


class TagBalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"line {self.getpos()[0]}: closing </{tag}> with no open tag")
            return
        # tolerate interleaved close by searching the stack (browsers do too),
        # but report it, since it usually means a missing close somewhere
        if self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            names = [t for t, _ in self.stack]
            if tag in names:
                while self.stack and self.stack[-1][0] != tag:
                    t, line = self.stack.pop()
                    self.errors.append(f"line {line}: <{t}> never closed (implicitly closed by </{tag}>)")
                self.stack.pop()
            else:
                self.errors.append(f"line {self.getpos()[0]}: stray </{tag}>")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"FAIL cannot read {path}: {e}")
        return 1

    failures, warnings = [], []

    # 1. leftover template slots
    slots = re.findall(r"\{\{[^}]*\}\}", text)
    if slots:
        failures.append(f"{len(slots)} leftover template placeholder(s), e.g. {slots[0][:60]!r}")
    if "PLAN_TITLE" in text:
        failures.append("PLAN_TITLE placeholder still present (title/<h1> not filled)")

    # 2. tag balance
    checker = TagBalanceChecker()
    checker.feed(text)
    checker.close()
    for tag, line in checker.stack:
        checker.errors.append(f"line {line}: <{tag}> never closed")
    failures.extend(checker.errors)

    # 3. mermaid blocks: known diagram type on the first non-blank line,
    #    and the CDN script present if any block exists
    blocks = re.findall(r'<pre class="mermaid">(.*?)</pre>', text, re.S)
    for i, block in enumerate(blocks, 1):
        first = next((l.strip() for l in block.splitlines() if l.strip()), "")
        word = re.split(r"[\s(]", first, 1)[0].lower().rstrip(":")
        if not word:
            failures.append(f"mermaid block {i} is empty")
        elif not word.startswith(MERMAID_STARTERS):
            failures.append(f"mermaid block {i} starts with {first[:40]!r}, not a known diagram type")
    if blocks and "mermaid" not in text.split("</body>")[-2 if "</body>" in text else 0][-2000:] \
            and '<script src="https://cdn.jsdelivr.net/npm/mermaid' not in text:
        failures.append("mermaid blocks present but no Mermaid <script> tag found")

    # 4. structure expectations from the skill
    if text.count('class="qform"') > 1:
        warnings.append("more than one open-questions block; the skill wants a single one at the bottom")
    if "—" in text:
        n = text.count("—")
        warnings.append(f"{n} em dash(es) in the document; house style bans them, use colons or commas")
    if re.search(r"unlike the previous version|this revision", text, re.I):
        warnings.append("revision language found; the plan must read as a standalone proposal")

    for f in failures:
        print(f"FAIL {f}")
    for w in warnings:
        print(f"WARN {w}")
    if not failures:
        print(f"PASS {path} ({len(blocks)} mermaid block(s), {len(text)} bytes)"
              + (f", {len(warnings)} warning(s)" if warnings else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
