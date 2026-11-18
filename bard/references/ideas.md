# Ideas (`Bard/Ideas/`)

An idea is a proposal that nobody has decided or built yet: "we could ...", "next we should ...",
"what if the Hub ...". It is the only note type that lives in a subfolder. Why: an idea is a
different kind of thing from knowledge. Knowledge says what is true. An idea says what could be.
Kept apart, the knowledge notes stay trustworthy, and the ideas stay easy to review as a list.

`file.inFolder("Bard")` also matches subfolders, so ideas stay in `Bard.base`. Wikilinks resolve
by note name in any folder, so links to and from ideas work the same as for other notes.

## When a candidate is an idea

Set K `kind` returns `idea` (see [Typed gates](jev-gates.md)). Its criterion asks for both of
these; a candidate with only one of them is a drop:

- It names a **problem** that is real today (a cost, a delay, a failure, a gap).
- It names a **mechanism**: what would change, and where.

"We should make it better" fails both, so drop it. Once a choice is made, write a `decision`
note. Once the thing is built, write an `artifact` or `impact` note.

## Two entry points

1. **On demand: `/bard idea <text>`**, or Alex says "save this idea" or "add an idea to bard".
   Write the note straight away, skipping the sweep's watermark and lanes. When Alex asks for
   research, use the `search` skill (Context7 for library docs, Exa for the web), and read the
   repos he names. Cite only sources you read in this run.
2. **In a sweep.** A swept session, meeting, or thread that proposes something new gets Set K.
   On `idea`, write it to `Bard/Ideas/`. Never turn it into a board item: an idea has no next
   action yet. When Alex says to start it, the board item links the idea note.

## Format

The same OKF envelope as every note (SKILL.md STEP 3), plus `status`:

```yaml
type: idea
status: seed              # seed | shaping | ready | adopted | dropped
title: <claim: what the idea gets you, in one line>
description: <one line>
up: "[[Topic Hub]]"
tags: [idea/<area>, topic/x, bard/new]
timestamp: <ISO 8601: session start, or now for /bard idea>
source: <session_id>
repo: <repo>              # when known
resource: ""              # a real verified URL, or omit
```

- `seed`: captured, not researched.
- `shaping`: researched, with open questions.
- `ready`: Alex could start it tomorrow.
- `adopted`: work started. Link the decision or board item.
- `dropped`: Alex said no. Keep the note and the reason: a dropped idea stops the same idea
  from coming back.

Body sections. Write only the ones with real content:

`## Problem` (with evidence), `## Idea`, `## How it would work` (a Mermaid diagram when it has
more than two parts), `## Why here` (why this platform or team), `## Rollout` (phases with a
"done when"), `## Guardrails`, `## Open questions`, `## Related`.

Provenance rules do not relax for ideas: every fact about today (a file, a setting, a date, a
limit) is cited or verified. The proposal itself is the only part that is not a fact.

## Editing an idea

Ideas change, so they are the one knowledge note bard edits in place, but only when Alex asks:
"move it to shaping", "add this to the idea", "drop it". Never change `status` on bard's own
judgment, and never in a sweep. Why: the status is Alex's call, like the board's priority.

## Filename

`Bard/Ideas/<Title>.md`, with the same title rules as every note (SKILL.md, Filename convention).
