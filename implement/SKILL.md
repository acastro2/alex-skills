---
name: implement
description: "Implement a piece of work from a spec or a set of tickets, driving test-first development at pre-agreed seams and closing with a review before you commit. Use when the user says to build, implement, or ship planned work."
license: MIT
---

# Implement

Build the work described by the spec or tickets in front of you.

## Steps

1. **Read the input.** A spec, a set of tickets, or both. If the work is more than a small change and there is no spec, say so and offer to write one first (`/skill:to-spec`). A spec is the only place the "why" survives the session.
2. **Explore the repo.** Read `CONTEXT.md` if it exists, and any ADRs in the area you are touching. Read the repo's own `AGENTS.md` or `CLAUDE.md` if it has one.
3. **Agree the seams with the user before writing a test.** State the seams under test and get them confirmed. Rules: the `code-rules` skill, section "Write the test first, at a seam you agreed".
4. **Work one vertical slice at a time, test-first.** One seam, one failing test, the minimum code to pass it, repeat. The procedure and examples are in `../tdd/SKILL.md`.
5. **Run the checks as you go.** Typecheck often, run the single relevant test file often, and the full suite once at the end.
6. **Ask for the review before you close.** `pr-reviewer` checks the diff on three axes: the spec it answers to, the repo standards, and production risk. It is user-invoked, so you cannot start it. Tell the user to run it (`/skill:pr-reviewer`) over the diff. If the project has no reviewer skill, do a review pass yourself against the repo's standards.
7. **Leave the commit to the user.** Stage nothing and commit nothing. Report what changed, what passed, and what is left to commit.

## Rules

- The coding rules are the source of truth for how the code is shaped. Read the `code-rules` skill before changing code.
- Do not fix problems outside the slice. Report them and let the user decide. Scope creep in a slice is how a slice stops being demoable.
- Stop and ask when a decision belongs to the user. A wrong guess costs more than a question.
- If a slice turns out to be too big for one session, stop and say so. Cut it again rather than pushing through a full context window.
