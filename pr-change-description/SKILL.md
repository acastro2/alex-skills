---
name: pr-change-description
description: "Write or rewrite a pull request description as a change description: why it changed, a Mermaid before and after diagram, and what is different now, scaled to the size of the PR. A small PR gets one diagram pair and a short why; a large or risky PR gets a section per area, a behaviour-change table, how the safety was proven, and a review path by commit. Every number comes from the code. Use when asked to write, rewrite, or deepen a PR description, to explain a change or a refactor with before and after diagrams, or when a PR is too big to understand from the diff. Not for critiquing a PR (that is reviewer) or for standalone architecture diagrams (that is archify)."
---

# PR change description

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

A PR description tells the reader what changed and why, so they understand the change before they open the diff. The core is always the same three things: why it changed, what it looked like before, and what it looks like now. The diagrams carry the structure; the prose carries the reason.

Voice comes from `../alex-voice/SKILL.md`, docs register. This file owns the shape.

## Scale to the PR

Pick the size from the change, not from the line count alone. A 40-line change to a lease or a payment path is large; a 2,000-line rename is small.

| Size | When | What it gets |
| --- | --- | --- |
| Small | One area, one idea, no change in failure behaviour | One or two sentences of why, one before and after diagram (or one diagram with both), what changed in bullets, how it was tested. Nothing else: no review path, no behaviour-change table, no watch-after-deploy section |
| Medium | Two or three areas, or a changed contract | The small shape per area, plus a behaviour-change table |
| Large or risky | Several areas, moved code, a new seam, changed failure paths, or many fixture files | The full template in `references/template.md` |

Skip the diagram only when the change has no structure to show (a typo, a version bump, a config value). Then the description is the why and the what in a few lines.

## 1. Gather the facts first

Every number and name in the description must come from the code. A wrong line count or a module that does not exist costs the description its trust.

| Fact | How |
| --- | --- |
| Commit list, oldest first | `git log --reverse --format='%h %s' <base>..HEAD` |
| Line counts of key files, before and after | `git show <base>:<path> \| wc -l` and `wc -l <path>`; write "deleted" or "moved to X" when gone |
| Production vs test vs fixture split | `git diff --shortstat <base> HEAD -- <src>`, the same for tests excluding fixtures, and for fixtures |
| Deleted and renamed modules | `git diff --name-status <base> HEAD -- <src>` (rows `D` and `R`) |
| The new interfaces | `grep -n "^def \|^class \|    def "` on the new modules; read the entry points |
| Test counts per area | `pytest <path> --co -q` per test folder |
| Intended behaviour changes | the spec, proposal, ticket, or ADR the PR answers to |
| Gate results | only runs you did and saw in this session |

A small PR needs only the rows it uses. If a fact cannot be checked, leave it out or mark it "not verified". Never estimate.

## 2. Write it

For a small PR, write: why (one or two sentences), the before and after diagram, what changed (bullets), how it was tested (the run you saw). Stop there. A small PR has one or two commits, and the reader reads them in order without a review path. If the small PR changes behaviour (a new default, a new status code), say it as one bullet under what changed, such as "An expired token now gets one refresh before the call fails". A table for one change is the medium shape.

For a medium or large PR, follow `references/template.md`. The full order:

1. **Opener**: what the PR does in one sentence, its size, and how much of it is fixtures. Point to the spec and the rules it follows.
2. **The whole change**: one before and one after diagram of the system, then a size table of the key files with a "Why" column.
3. **One section per area**: Why (the drift or the pain, as bullets), Before diagram, After diagram, an optional sequence diagram of one call or one failure path, and "What to check" with file pointers and the tests that prove it.
4. **Behaviour changes**: a table with the change number, the change, and who notices. State what stays byte-identical.
5. **How the safety was proven**: a diagram of the method, then the measured numbers.
6. **Review path**: a table of commit groups, what each does, and what to read. Say what to skip.
7. **Things to watch after deploy**: two to four lines, only real ones.

Rules at every size:

- **The before diagram shows the pain.** Put the problem on the edges and nodes ("own bulk loop, no retry", "1,300 lines", "no lease"). A before diagram that looks clean gives no reason for the change.
- **The after diagram shows the seam.** Group the new module in a `subgraph`, keep callers outside it, and label the one interface they cross.
- **Use a sequence diagram for order and failure.** Publish order, a lease claim and its rollback, a retry: each is an ordered list of calls, and an `alt` / `else` block shows the failure branch better than a paragraph.
- **Use a state diagram for a lifecycle**, such as a lease, a job, or a document status.
- **One idea per diagram.** If a diagram needs a paragraph to explain it, split it or redraw it.
- **Say what did not change.** "The public API is byte-identical" tells the reader what they can skip.
- **Name the evidence, not adjectives.** "770 passed, 1 skipped; main has 333" beats "well tested".
- **List deviations and the edge cases no test covers.** The reader finds them anyway; finding them in the description keeps trust.

Diagram syntax that renders on GitHub, and patterns per kind of change: `references/diagrams.md`.

## 3. Publish and verify

1. Write the body to a file outside the repo and post it with `gh pr edit <n> --body-file <file>` (or `gh pr create --body-file`). GitHub caps a body at 65,536 characters; check with `wc -c`.
2. Run `python3 ../alex-voice/scripts/voice_check.py <file> --register docs` and fix every blocker.
3. **Check that every diagram renders.** A Mermaid syntax error shows as an error box only on the PR page. Open the PR with the `browser-control` skill and run the check in `references/diagrams.md`. The number of rendered frames must equal the number of `mermaid` blocks, and no frame may contain a syntax error.
4. When the PR changes, update the description: the size table, the test counts, the review path, and any diagram whose flow changed. A stale description is worse than none.

Report the PR link, the number of diagrams, and the render check result.
