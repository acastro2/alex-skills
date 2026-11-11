---
name: git-pull-acastro2
description: Pull a repo as Alex's second GitHub account, acastro2, without changing the active gh account. Use when he says git-pull-acastro2, asks for a gpr or a git pull --rebase as acastro2, or a pull fails with 403 or "repository not found" because the clone belongs to acastro2. HTTPS remotes only. The sibling for pushes is git-push-acastro2.
---

# git-pull-acastro2

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. If the host has no question
tool, use `❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

## What it does

Runs Alex's `gpr` alias (`git pull --rebase`) authenticated as the second GitHub account,
acastro2, and leaves the active gh account alone.

```bash
~/.agents/skills/git-pull-acastro2/scripts/git-pull-acastro2
```

Extra arguments go to `git pull` after `--rebase`, so a later flag wins:
`...git-pull-acastro2 --autostash`.

## Why it works

The global git credential helper for github.com is `gh auth git-credential`, and gh reads
`GH_TOKEN` before the active account. The script gets acastro2's token with
`gh auth token --user acastro2` and sets it for one command only. This is the same trick as
`git-push-acastro2` in dot_zshrc, with a pull instead of a push.

That one-command scope is the point. `gh auth switch` would change every other shell and
agent session, and an interrupted switch or restore leaves the machine on the wrong account.

## Limits

- HTTPS remotes only. With an SSH origin, `GH_TOKEN` is ignored and the machine key picks
  the account; the script prints that warning and runs the pull anyway.
- The token comes from the gh keyring. When it is missing the script stops with
  `not logged in as acastro2`; the fix is `gh auth login` and add acastro2.
- A pull pulls the tracked branch. To pull another repo, run it inside that working tree.

## Check who is acting

`GH_TOKEN=$(gh auth token --user acastro2) gh api user --jq .login` answers `acastro2`.
