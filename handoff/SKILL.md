---
name: handoff
description: Read and keep current a repo's HANDOFF.md, the note a fresh session with zero memory uses to pick up the work. Use when the repo has a HANDOFF.md (repo root first, then docs/), before you start work there, at every milestone or change of direction, when you leave a process running, or when Alex asks to write, update, trim, or read the handoff. Not for decisions, those go in the repo's ADRs, and not for session history, that is archeologist.
---

# handoff

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. If the host has no question
tool, use `❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

## Why this exists

Alex runs many sessions at once and abandons them mid-flight. A file written only at
"session end" is stale exactly when he needs it. A fresh session can read the repo, but it
cannot know where to look. The handoff tells it where.

## Find the file

1. `HANDOFF.md` at the repo root.
2. If not there, `docs/HANDOFF.md`.

Use the first one you find. Never create a second copy in the other place. If neither
exists, do not create one unless Alex asks; then put it at the repo root.

## When to read and write

- **Read** it before you touch anything in the repo.
- **Write** it at every milestone, at every change of direction, and before you leave a
  process running. Not only at the end: the end may never come.
- **Write** it when Alex makes a call that changes what the next session does.

## Shape

Rewrite the file to the current truth. Do not append a new paragraph per session: git keeps
the old versions (`git log -p <path>`), so cut what is done or no longer true.

```markdown
# HANDOFF: <repo>

Updated: <YYYY-MM-DD HH:MM TZ> (<one-line reason>)

## Current state
<what works, what is half done, on which branch, which PR>

## Next
1. <action, with the exact command or path>
2. ...
3. ...

## Blockers
- <what blocks, who or what unblocks it>

## Running processes
- <name>, port <n>, PID <n>, started <when>. Kill: `<command>`

## Pointers
- <paths, PR numbers, spec files, workspace folders a fresh session needs>
```

Keep at most three items under Next. Leave out a section that is empty, except Current
state and Next.

## Running processes

When a process of yours stays alive after your turn (a dev server, a watcher, a tunnel),
write its name, port, PID, and the kill command under Running processes. Remove the line
when you kill it. If the repo has no handoff file, put the same line in your final reply.

## What does not go in

- **Decisions and their why:** the repo's ADRs. Link the ADR.
- **History:** git. One line on why the file changed is enough.
- **Anything a fresh session can find in seconds:** file contents, code, the README.
- **Secrets, tokens, and private names** when the repo is public. Check before you write.

## Done when

A fresh session that reads only this file knows the current state, the next action and its
command, what blocks it, and what is still running.
