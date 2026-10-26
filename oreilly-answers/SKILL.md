---
name: oreilly-answers
description: "Ask O'Reilly Answers (learning.oreilly.com/answers2, the AI answer engine over the O'Reilly book library) research questions through browser-control in Alex's logged-in browser, wait for each answer to finish, and save the clean answer text with its book sources as Markdown. Use when Alex asks to check O'Reilly, ask O'Reilly Answers, get book-backed answers, or back a design decision with the O'Reilly library. Not for public web search (use the search skill) and not an MCP: there is no O'Reilly API here."
---

# O'Reilly Answers

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

Ask questions in Alex's own browser session and capture the answers with their book citations. Needs the `browser-control` skill working and Alex logged in to learning.oreilly.com in that browser.

## Run it

1. Write the questions to a file, one per line. Plain, specific questions get the best answers; one topic per question.
2. Run the batch. It creates or reuses the browser-control session `oreilly`:

   ```bash
   ~/.agents/skills/oreilly-answers/scripts/ask.sh questions.txt "<out-dir>"
   ```

   Run it in the background: each question takes about 30 to 90 seconds. One line per question reports `ok` or `FAILED`.
3. Read `<out-dir>/answers.md`. Raw page captures stay in `<out-dir>/raw/q<N>.json` for re-rendering with `scripts/to_md.py <out-dir>/raw`.

## How a question runs

`scripts/ask.js` opens a fresh Answers page, fills the box, asks, waits for the `questionId` URL, then scrolls and waits until the text stops growing for about 8 seconds. A capture counts as complete only when "Was this response helpful?" is on the page, because that prompt renders after the answer finishes.

## Check every run

- **The answer is for the question you asked.** `--check` compares the asked text with the file line. A shell `>` under zsh `noclobber` once failed silently and re-asked question 1 five times; `ask.sh` writes the question with Python for that reason.
- **The capture is complete.** A `FAILED` line or "(incomplete capture)" in the Markdown means re-run that one question.
- **The sources hold up.** Answers is generated text. It sometimes cites a book only by analogy (for example an AI-agent book for a planning point). Check any number or claim you will rely on against the cited book before it reaches a document, and say when a citation is weak.

## Gotchas

- Every ask adds an entry to Alex's Answers history, re-asks included. Do not loop on a failing question.
- One browser-control relay drives one browser. Do not run two batches at once.
- The question file path is fixed at `~/.cache/oreilly-answers/q.txt` because `ask.js` runs inside the relay, not your shell.
