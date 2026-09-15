---
name: resolving-merge-conflicts
description: "Work through an in-progress git merge or rebase conflict hunk by hunk, resolving by intent traced to each side's primary source, then finish the operation. Use when a merge or rebase is in progress and conflicting, or when the user asks how to resolve a conflict. Never runs --abort."
license: MIT
---

# Resolving Merge Conflicts

Resolve by **intent**, not by picking lines. A conflict is two changes that both made sense; the job is to find out what each one wanted and keep both if you can.

## 1. See the current state

Check the git history and the conflicting files.

```bash
git status
git log --oneline --graph --decorate -20
git diff --name-only --diff-filter=U
```

Note which operation is in progress: a merge, a rebase, a cherry-pick, or a revert. They finish differently.

## 2. Find the primary sources

For each side of each conflict, understand deeply why the change was made and what the original intent was. Read the commit messages, check the pull requests, check the original work items.

A side with no discoverable intent is the side you should be most suspicious of keeping.

## 3. Resolve each hunk

- Preserve both intents where possible.
- Where they are genuinely incompatible, pick the one matching the merge's stated goal and note the trade-off for the user.
- **Do not invent new behaviour.** A conflict is not a licence to improve things. If both sides look wrong, ask.
- **Always resolve. Never `--abort`.**

## 4. Run the project's checks

Find the repo's automated checks and run them, typically typecheck, then tests, then format. Fix anything the merge broke. A merge that resolves cleanly but fails the tests is not resolved.

## 5. Finish the operation

Complete the merge or rebase: stage the resolved files and continue the rebase until all commits are rebased.

**Leave the commit to the user.** The git rules require approval for every git write, so stage nothing and commit nothing yourself. Report the resolved files, the checks you ran and their output, and the exact command that finishes the operation. If a rebase is mid-flight, say which command continues it.
