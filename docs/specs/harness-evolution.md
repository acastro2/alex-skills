# Harness evolution: rules in code, not prose

Status: plan only. Nothing is built. Written 2026-11-25. Decisions D1 to D3 were taken by Alex on 2026-11-25 (see the table). D4 to D7 are open.

Evidence (scratch, not durable):
- Archeologist briefing, session `ses_dec5cba8bffeG7XseU2P5tAuyM`. It covers 2026-11-19 to 2026-11-25 only: this Linux box has 6 days of history and no Mac stores.
- OpenCode features: `ses_dec5c94cdffe1v7zVO7K45B0Q3`. Checked on OpenCode v2.4.1.
- Claude Code features: `ses_dec5c74ffffeXTLt2kV33YEDxE`. Checked on Claude Code 2.1.332.
- Practice: `ses_dec5c5a5affeXDt64DMht0sGg7`.

## Why

Every rule in `~/.config/opencode/AGENTS.md` and `~/.claude/CLAUDE.md` is prose. The model can decide a prose rule does not apply, and it did:

- On 2026-11-21 a worker ran `rm -r ~/Developer/ChamberlainGroup-myQ-Shared`, and about 54 repos had to be cloned again. The fix was another prose rule.
- "Load `coding`" and "no git writes" were pasted by hand into 69 of 158 worker prompts in 6 days.
- The post-worker check (restore the tests from base, hash them, re-run) was done by hand in 74 sessions.
- The acastro2 push trick was typed 250 times in 48 sessions.

Two facts make prose rules weaker than they look:

- OpenCode `cli.json` sets `session.permissions: "autoaccept"`. Every `ask` rule is approved automatically, so only `deny` is a fence.
- In both tools, a deny rule matches the command text only. `git -C . push`, `/usr/bin/git push` and `bash -c '...'` get past a `git push` rule. The Claude Code docs say deny rules are not a security boundary. A hook that parses the full command is the real fence.

The practice behind this is harness engineering: when an agent makes a mistake, add a fix in code so it cannot happen again ([Hashimoto](https://mitchellh.com/writing/my-ai-adoption-journey), [Böckeler](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html), [OpenAI](https://openai.com/index/harness-engineering/)). A rule with no exceptions goes in a hook. A preference stays in prose.

## Shape

One guard script holds the logic. Each tool gets a thin adapter that calls it. The prose files keep only the why.

```mermaid
flowchart LR
  subgraph alex-skills/harness
    G[guard.py<br/>parse command, decide]
    V[verify_worker.py]
    T[tests/]
  end
  G --> CA[Claude adapter<br/>PreToolUse, UserPromptSubmit, Stop]
  G --> OA[OpenCode plugin<br/>permission.evaluate, tool.execute, session.prompt]
  V --> CA
  V --> OA
  CA --> CS[~/.claude/settings.json]
  OA --> OC[~/.config/opencode/plugins]
  CS --> P[CLAUDE.md / AGENTS.md<br/>why only]
  OC --> P
```

Why one script: two copies drift. Why thin adapters: each tool's hook API changes between versions (OpenCode V2 renamed every hook), and only the adapter has to follow.

## Decisions

| # | Decision | Answer | Why |
| --- | --- | --- | --- |
| D1 | Scope of this change | Plan doc only | Alex picked it, 2026-11-25 |
| D2 | `gh pr merge` | Deny, unless Alex's prompt has a one-time token | Alex picked it over a hard deny. He keeps the merge in chat. |
| D3 | Where the code lives | `alex-skills/harness/` | Alex picked it over a new repo. One fewer repo. |
| D4 | Token word and lifetime | Open. Proposal: `MERGE-OK`, one merge, then gone | |
| D5 | Recursive `rm` allowlist | Open. Proposal: the scratchpad, `~/.agents/skill-workspace`, and paths inside the current git repo that git tracks or ignores | |
| D6 | Stop hook: warn or block on a stale `HANDOFF.md` | Open. Proposal: warn | A block can loop on a session that has nothing to record |
| D7 | Repo lock for parallel sessions: warn or block | Open. Proposal: warn, and show the other session's ID | |

## Phase 0. Prove the two unverified facts

Do this first. The design depends on both, and the docs do not answer them.

| Fact | Test | Done when |
| --- | --- | --- |
| OpenCode `permission.hook("evaluate")` with `effect = "deny"` stops a `shell` call, under `autoaccept` | A scratch plugin denies `echo HARNESS-PROBE`, and a session runs it | The command does not run, and the agent sees the reason |
| A per-call subagent `model` overrides the agent's frontmatter `model` | Call `general` with a `model` that differs from its frontmatter, then read `session_v2.model` | The row shows the per-call model |

If the first fails, the OpenCode adapter uses `tool.hook("execute.before")` to replace the command with one that fails with the reason. Test that the same way. If both fail, stop and bring it to Alex.

## Phase 1. Guard (closes the worst risks)

`harness/guard.py` reads one tool call as JSON on stdin and prints a decision: `allow`, or `deny` plus a reason the agent can act on. It parses the command with `shlex` and walks `bash -c`, `sh -c`, `env`, `xargs`, `git -C` and absolute paths before it matches.

Rules:

| Rule | Denies | Reason the agent sees |
| --- | --- | --- |
| Recursive delete | `rm -r`, `rm -rf`, `find -delete`, `rsync --delete` outside the D5 allowlist | "Recursive delete outside the allowlist. Name the exact files, or ask Alex." |
| Merge | `gh pr merge`, `gh api .../merge`, `git merge` into `main` or `master`, `git push` of a merge to `main` that has no PR | "Merge needs Alex's token in this session (D2)." |
| Destructive git | `git reset --hard`, `git clean`, `git push --force` and `-f`, `git checkout -- .` | Same rules as today's `opencode.jsonc` deny list, now in both tools |
| Token tamper | Any write to the token folder | "Only Alex's prompt can create a merge token." |

The merge token, per tool:

- **Claude Code:** a `UserPromptSubmit` hook sees `MERGE-OK` in Alex's prompt and writes `~/.local/state/harness/tokens/<session_id>`. The `PreToolUse` guard allows one merge and deletes the file.
- **OpenCode:** `session.hook("prompt")` sees the word and sets a flag in plugin memory for that session. `permission.hook("evaluate")` allows one merge and clears it.

Why a hook writes the token: the agent can write files, so a token the agent can create proves nothing. The guard denies writes to the token folder, and the OpenCode flag lives in memory the agent cannot reach.

Done when:
- `pytest harness/tests` passes. It has one case per rule, plus the bypass forms (`git -C . push --force`, `bash -c "rm -rf ~/x"`, `/usr/bin/gh pr merge 1`).
- A live probe in each tool shows a denied `rm -rf <scratch outside allowlist>` with the reason, and an allowed merge on a test repo after `MERGE-OK`. The test repo is a throwaway under `~/.agents/skill-workspace/`.

## Phase 2. Worker spawn hook

On every `subagent` call (OpenCode) and `Agent`/`Task` call (Claude Code):

- Deny the call when `model` is missing. Reason: "Set `model`, see AGENTS.md Execution."
- Add the worker contract to the prompt: load `coding` first, no git writes, flag a wrong test and do not edit it, and return the proof bundle. Skip it for `archeologist` and other read-only agents.

Claude Code allows the prompt change through `updatedInput`. For OpenCode, test in Phase 0 that `tool.hook("execute.before")` can replace the input. If it cannot, deny with the contract text so the parent re-sends.

Done when: a subagent call with no `model` is denied in both tools, and a worker's first message shows the contract.

## Phase 3. `verify_worker.py`

One command replaces the manual loop that ran in 74 sessions:

```
harness/verify_worker.py --base <ref> --tests '<globs>' -- <acceptance commands>
```

It does the following:
1. Hash the test files.
2. Restore them from `<base>`.
3. Run each acceptance command, and print its exit code and the last 40 lines.
4. Print `git diff --stat` and the files outside an optional `--allow` list.
5. Exit non-zero on any failure.

Add a `tool.hook("execute.after")` / `PostToolUse` on the subagent tool that prints `git status --short`. Then the parent sees the worker's changes without asking.

Done when: run on a seeded repo, it catches a worker that edited a test (red), and passes a clean worker (green).

## Phase 4. Small fixes, no hook needed

- **acastro2 pushes:** set `credential.https://github.com/acastro2.helper` in the global git config, so pushes to acastro2 repos use that account's token. This removes the 250 hand-typed helpers. The command goes in mac-bootstrap, not in a skill.
- **Broken symlinks:** `~/.claude/commands/ub-mode.md` and `~/.config/opencode/commands/ub-mode.md` point at `/Users/acastro/...`. Make them relative, or create them from mac-bootstrap per host.

Done when: `git push` in `alex-skills` works with no `-c credential.helper`, and both `ub-mode` links resolve on Linux and on the Mac.

## Phase 5. Stop hook and parallel sessions

- **Stop:** warn when the repo has a `HANDOFF.md` older than the last commit of this session, or when a process this session started is still running. Claude Code: `Stop` hook. OpenCode: the session idle event (check the V2 name in Phase 0).
- **Lock:** on session start, write `.git/harness-lock/<session_id>` with the PID and the start time. Warn when another live session holds a lock in the same repo, and name it.
- **Done signal:** when a background worker finishes, send one Rex or Herdr notification. This answers "did the task return?" without polling.

Done when: two sessions in one repo see each other's ID, and a finished worker shows a notification.

## Phase 6. Cut the prose

For each rule now enforced in code, cut the "what" from `AGENTS.md` and `CLAUDE.md`, and keep one line of why plus a pointer to the guard. Target: both files under 70 lines. Why: OpenAI keeps its AGENTS.md at about 100 lines, and every enforced rule left in prose is context the model reads for nothing.

Done when: the line counts drop, and a short eval shows no rule loss. Run the `coding` worker eval and one merge-attempt eval before and after the cut.

## Later, end to end

Not in this plan. Each needs its own spec.

- Automations: `gather` and `bard` sweeps, the morning brief, and a weekly `upstream_audit.py` run that opens a PR.
- `anthropics/claude-code-action` for PR review on `alex-skills`.
- A doc-gardening job that checks `HANDOFF.md` and the README tables against the repo.
- Package the adapters as a Claude Code plugin (`.claude-plugin/plugin.json`), so the Mac and this box install the same thing.

## Risks

- **skillcheck may flag `harness/`.** It has no `SKILL.md`. Check `skillcheck/policy.py` for a non-skill folder rule before Phase 1. Add the folder to the exclusions if needed.
- **A hook timeout lets the call through.** In Claude Code, a timed-out `PreToolUse` hook does not block. Keep `guard.py` pure Python with no network, and set a 5-second timeout.
- **`--bare` skips hooks.** `claude -p --bare` runs with no hooks, so the eval harnesses run without the guard. That is fine for evals, but never use `--bare` for real work.
- **Plugin subagents ignore `hooks`.** Put the hooks in `settings.json`, not in a plugin's agent frontmatter.
- **Another session edits the same files.** Commit each phase with a pathspec.
