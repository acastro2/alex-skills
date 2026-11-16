---
name: handoff
description: Read, check, and keep current a repo's HANDOFF.md, the note a fresh session with zero memory uses to pick up the work. Use when the repo has a HANDOFF.md (repo root first, then docs/), at every milestone or change of direction, when you leave a dev server, watcher, or other process running, or when Alex asks to write, update, trim, or read the handoff, or to save where the work stands for the next session. Not for decisions, those go in the repo's ADRs, and not for session history, that is archeologist.
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

Two failures to prevent: a stale file read as fact, and one session's save deleting
another's.

## Find the file

1. `HANDOFF.md` at the repo root.
2. If not there, `docs/HANDOFF.md`.

Use the first one you find. Never create a second copy in the other place. If neither
exists, do not create one unless Alex asks; then put it at the repo root.

## Read, then check it against the repo

Read it before you touch anything in the repo. Then check it, because the file can be
older than the repo:

1. Take the `HEAD <sha>` from the `Updated:` line. Run `git log --oneline <sha>..HEAD` and
   `git status --short`.
2. Compare with what your workstream block claims: branch, PR, uncommitted files, running
   processes (`lsof -i :<port>`, `ps -p <pid>`).
3. If a claim is false, fix that line before you work, and say the fix in one line. The
   repo wins over the file.

## Write without losing another session's work

Write at every milestone, at every change of direction, when Alex makes a call that changes
what the next session does, and before you leave a process running. Not only at the end:
the end may never come.

Every write:

1. Re-read the file just before you write. Another session may have changed it since you
   read it.
2. Edit only your workstream's block. Leave every other block as it is, even when it looks
   stale: its session may still be running. Report the stale block to Alex instead.
3. Update the `Updated:` line, with the current `HEAD` sha.

Inside your block, rewrite to the current truth. Do not append a paragraph per session:
git keeps the old versions (`git log -p <path>`), so cut what is done or no longer true.

## Shape

```markdown
# HANDOFF: <repo>

Updated: <YYYY-MM-DD HH:MM TZ>, HEAD <short sha> (<one-line reason>)

## <workstream name>

State: <what works, what is half done, branch, PR>. Checked <date> by <command>, or "not re-checked".

Next:
1. <action, with the exact command or path>
2. ...
3. ...

Blockers:
- <what blocks, who or what unblocks it>

Gotchas and dead ends:
- <what a fresh session would get wrong, or tried and failed, and why>

## Running processes
- <name>, port <n>, PID <n>, started <when>, workstream <name>. Kill: `<command>`

## Pointers
- <paths, PR numbers, spec files, workspace folders every workstream needs>
```

- One `##` block per workstream. A repo with one line of work has one block.
- At most 400 words per workstream block and at most three Next items. Over the limit, cut
  what is done.
- In a block, leave out Blockers or Gotchas when they are empty. State and Next stay.
- Each State claim says how and when it was checked. A claim you did not check this session
  is "not re-checked", not a fact.
- When a workstream is done, delete its block. Its record is in git.

## Running processes

When a process of yours stays alive after your turn (a dev server, a watcher, a tunnel),
write its name, port, PID, and the kill command under Running processes. Remove the line
when you kill it. If the repo has no handoff file, put the same line in your final reply.

## What does not go in

- **Decisions and their why:** the repo's ADRs. Link the ADR. A dead end is not a decision:
  it goes under Gotchas and dead ends.
- **History:** git. One line on why the file changed is enough.
- **Anything a fresh session can find in seconds:** file contents, code, the README.
- **Secrets and tokens: never**, in any repo. **Private names** (employers, ticket keys,
  people, account ids): only when the repo is private. Check with
  `gh repo view --json visibility` before you write them.

## Done when

A fresh session that reads only this file, and runs the check above, knows for its
workstream the current state, the next action and its command, what blocks it, what not to
try again, and what is still running.
