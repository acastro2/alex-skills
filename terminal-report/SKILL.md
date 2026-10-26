---
name: terminal-report
description: "Shape a report, analysis, status update, or findings summary that an agent hands Alex in the terminal, so he can decide from one screen. Encodes the row budget, the answer-first layout, when a visual earns its space, and the one-line evidence rule. Use when writing or reviewing any multi-section reply, research write-up, status report, review summary, comparison, or analysis meant to be read in the TUI. Not for HTML, browser artifacts, decks, or documents saved as a file."
---

# Terminal report

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

A report is any reply with more than one section. It is read in a terminal pane, not a page.

The cost is **rows**, not words. A terminal pane shows a few dozen rows, and everything below the fold is scrollback. Alex does not scroll back to find the point. So the report is built to fit, or it is written to a file and linked.

Tone and word choice come from `../alex-voice/SKILL.md`. This file owns shape only: what comes first, what earns space, and what to cut.

## Two readers, one report

The same report is read twice.

1. **The scan.** Five seconds, first three lines. Alex decides whether to keep reading, and often makes the call right there.
2. **The verify.** Thirty seconds. He checks the one visual and the evidence behind it, then acts.

Design for the scan first. A report that only works when read in full is a document, not a report.

## The layout

Four zones, in this order, always.

```
1  ANSWER      1 to 3 lines. The finding, with its number.
2  PROOF       One visual, or one table. The thing that carries the claim.
3  EVIDENCE    0 to 5 lines. One fact per line. Source on the same line.
4  NEXT        1 line. The decision you need, or nothing.
```

Nothing sits above the answer. No preamble, no "I looked into", no restating the question. The first line is the finding.

**Row budget: 40 rows. Hard cap 60.** Over the cap, the detail goes to a file and the reply keeps the answer and the link. Count rendered rows, not source lines: one line of prose costs one row, but a `chart` fence costs the chart's `height` (8 to 14 rows by default). A reply that needs 80 rows to make one point has not decided what the point is.

## Zone rules

**Answer.** One bold line, then at most two plain lines. Put the number in the line, not in the proof. If the finding needs a caveat, the caveat costs one line and never a whole section.

**Proof.** One visual. Two only when they answer two different questions, and never side by side to look thorough. A chart when the reader needs the *shape*; a table when he will read *exact figures* one at a time. No visual at all when the finding is one number.

**Evidence.** One line each, at most five. Format: the fact, then where it came from. Not prose, not a paragraph with the source at the end. If a line wraps past the pane width, the fact is too big and needs cutting.

**Next.** One line: the decision, the approval, or the action. If nothing is needed, end at the evidence. Never write "let me know if you have questions".

## When a visual earns its space

A visual must replace at least three numbers that would otherwise sit in prose. Fewer than three, write a sentence.

- **The title is the claim.** "Churn doubled after the March price change" earns a chart. "Churn by month" is decoration, because it states a dataset, not a finding.
- **Never narrate the picture.** The chart is the sentence. Repeating its numbers in prose above it wastes the rows the chart just spent.
- **No chart for one number, two numbers, or a list of three.** A gauge for a single percentage is a sentence with extra rows.
- **Do not decorate.** A visual that repeats what the answer line already said is noise, and it makes a weak report look confident.

Charts in this terminal are drawn from a `chart` fence, and the renderer owns that contract: copy the worked chart in [references/example.md](references/example.md) instead of inventing options. This skill owns layout, not chart syntax.

## Anti-patterns, by name

| Pattern | What it looks like | Fix |
|---|---|---|
| **The journey** | "First I checked X, then I moved to Y" | Delete. Keep the finding. |
| **The buried lede** | The answer arrives in section 4 | Move it to line 1 |
| **The restatement** | A "Summary" that repeats the opening | Delete the section |
| **The decoration chart** | A pie under a sentence that already said "62%" | Delete the chart |
| **The hedge stack** | might, could, potentially, seems, possibly | One hedge maximum, or commit |
| **The orphan heading** | A heading with one line under it | Inline the line |
| **The wall** | 60+ rows with no visual break | Cut, or write a file |

## Check it before you send

Four mechanical checks. All four take under a minute.

1. **Read lines 1 to 3 only.** Can you decide? If not, the answer is not in the answer zone.
2. **Read the bold text only.** Headings plus the first line must tell the whole story.
3. **Read the visual titles only.** Each must be a claim, not a dataset name.
4. **Count rows.** Prose lines plus each chart's `height`. Over 40? Cut. Over 60? Write a file.

A worked before and after, with row counts, is in [references/example.md](references/example.md).
