# Harness evolution: rules in code, not prose

Status: plan only. Nothing is built. Written 2026-11-25. Grilled with Alex four times, the last on the worktree lifecycle and proof of work (D38 to D48). Every candidate from the second architecture review is folded in (D49 to D53). The frontier is empty. Every decision is taken (see Decisions), including Alex's later additions on worktrees, cleanup and the HANDOFF protocol (D7, D20 to D23). The design was reviewed with `improve-codebase-architecture` and grilled with Alex on 2026-11-25: the policies now sit behind one core module with one ledger, not in separate scripts.

Evidence (scratch, not durable):
- Archeologist briefing, session `ses_dec5cba8bffeG7XseU2P5tAuyM`. It covers 2026-11-19 to 2026-11-25 only: this Linux box has 6 days of history and no Mac stores.
- OpenCode features: `ses_dec5c94cdffe1v7zVO7K45B0Q3`. Checked on OpenCode v2.4.1.
- Claude Code features: `ses_dec5c74ffffeXTLt2kV33YEDxE`. Checked on Claude Code 2.1.332.
- Practice: `ses_dec5c5a5affeXDt64DMht0sGg7`, plus Anthropic's [3 patterns for harnessing Claude's intelligence](https://claude.com/resources/articles/harnessing-claudes-intelligence) (April 2026), added after Alex asked.

## Why

Every rule in `~/.config/opencode/AGENTS.md` and `~/.claude/CLAUDE.md` is prose. The model can decide a prose rule does not apply, and it did:

- On 2026-11-21 a worker ran `rm -r ~/Developer/ChamberlainGroup-myQ-Shared`, and about 54 repos had to be cloned again. The fix was another prose rule.
- "Load `coding`" and "no git writes" were pasted by hand into 69 of 158 worker prompts in 6 days.
- The post-worker check (restore the tests from base, hash them, re-run) was done by hand in 74 sessions.
- The acastro2 push trick was typed 250 times in 48 sessions.

Two facts make prose rules weaker than they look:

- OpenCode `cli.json` sets `session.permissions: "autoaccept"`. Every `ask` rule is approved automatically, so only `deny` is a fence.
- In both tools, a deny rule matches the command text only. `git -C . push`, `/usr/bin/git push` and `bash -c '...'` get past a `git push` rule. The Claude Code docs say deny rules are not a security boundary. A hook that parses the full command is the real fence.

Alex also spends his time steering, not building. In the same 6 days, 334 of his 1,202 top-level prompts (28%) only told the agent to take an obvious next step, and 584 (49%) were 6 words or fewer. The top kinds, from keyword matches on the OpenCode store and Claude Code `history.jsonl` (approximate counts):

| Prompt | Count | What it means |
| --- | --- | --- |
| "merged", "both merged", "approved", "sent" | 82 short ones, 102 in all | Alex acts as the agent's GitHub webhook |
| `/mcp`, `/model`, `/resume`, `/reload-skills` | 55 | Harness upkeep |
| A screenshot pasted as feedback | 41 | Alex does the UI check by hand |
| "link?", "links" | 36 | The links rule leaks |
| "commit and push" | 32 | The agent stops before the obvious step |
| "continue", "do it", "yes", "ok" | 31, plus 35 automatic "Continue." | The agent stops with todos open |
| "so what now?", "did it return?" | 17 | No view of the state |
| "CI failing", "merge conflict", "same error" | 17 | Alex relays CI to the agent |
| "nudge it, faster" | 12 | Alex watches the workers |
| "it's already merged", "already sent" | 9 | The agent reports old state as current |
| "you can, use browser control" | 1 here, likely more on the Mac | The agent gives up a task it can do in the browser |

"Use the question tool" appears once in these 6 days. Either it happens on the Mac, or that rule already mostly works.

The practice behind this is harness engineering: when an agent makes a mistake, add a fix in code so it cannot happen again ([Hashimoto](https://mitchellh.com/writing/my-ai-adoption-journey), [Böckeler](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html), [OpenAI](https://openai.com/index/harness-engineering/)). A rule with no exceptions goes in a hook. A preference stays in prose.

## Shape

One core holds every policy behind one interface, `decide(event) → decision`. Inside it, six modules each own one concern and their own ledger tables. Each tool gets one thin adapter, and one manifest says how each adapter is wired. The prose files keep only the why.

```mermaid
flowchart LR
  MF[install manifest] --> CC
  MF --> OC
  CC[Claude Code adapter<br/>mcp_tool hooks + guard-lite] -. seam .-> CORE
  OC[OpenCode adapter<br/>plugin imports core] -. seam .-> CORE
  subgraph CORE[harness core: decide event to decision]
    AU[authority]
    DR[destructive rules]
    ST[stop checks]
    WL[worker lifecycle and proof]
    WT[worktree lifecycle]
    JU[judgment]
  end
  ST --> JU
  GL[guard-lite.ts] --> DR
  CORE --> L[(ledger storage<br/>private to the modules)]
  K[waker] --> WL
  K --> WT
  K -. seam .-> KA[OpenCode automation<br/>Claude Monitor<br/>Rex or Herdr notify]
  CORE --> P[AGENTS.md / CLAUDE.md<br/>why only]
```

| Module | Interface | Owns |
| --- | --- | --- |
| Authority (D50) | `fromAlex(prompt)`, `holds(session, grant)`, `protects(toolCall)` | merge and other grants, the kill switch, `harness wrong`, and every rule that stops an agent acting as Alex |
| Destructive rules (D51) | `classify(command, cwd) → deny reason or none` | the shell parser, the D5 allowlist, recursive delete, merge in shell, destructive git. No ledger, no network |
| Stop checks | `check(turn) → send back or pass` | the Stop check table |
| Worker lifecycle and proof | `onSpawn(call)`, `onReturn(call)` | `workers`, `bundles`, the failure ladder |
| Worktree lifecycle | `onEvent(worktree event)` | `worktrees`, `workstreams`, landing and cleanup |
| Judgment (D52) | `judge(questions, summary) → answers with source` | the Jev call, its 3-second timeout and the keyword fallback |

Why this shape (from two architecture reviews):
- **Core, not 8 scripts.** In the first draft, each policy read its tool's raw hook JSON, so a hook format change leaked into 8 modules. Only the 2 adapters know the tool formats now. Two adapters make the seam real.
- **Ledger storage, not 9 stores.** One SQLite file holds all state, so the OpenCode server restart loses nothing.
- **Worker lifecycle, not a command to remember.** The core verifies on every worker return.
- **One waker.** The PR watcher, the done signal and the watchdog share one poll-and-wake module.
- **Authority in one module.** Everything only Alex can do was checked in 9 places, and the forged-prompt hole (D35) came from that spread. One module means one test suite for "an agent cannot act as Alex".
- **Destructive rules shared.** `guard-lite.ts` would otherwise be a second copy of the shell parser and the allowlist, and the fallback would drift from the main path.
- **Install manifest.** The Claude Code adapter uses 4 transports, and D36 must know which config entries are the harness's. One manifest feeds the installer, the adapters and D36.
- **Judgment in one module.** One Jev call per stop instead of 4, and the fallback is written once.
- **Domain interfaces on the ledger.** A generic `record` and `query` would make every caller know each table's columns and expiry. Each module owns its tables instead.

### Interface

`decide(event) → decision`. The tests use the same interface: JSON event in, decision out.

| Event | Claude Code hook | OpenCode hook |
| --- | --- | --- |
| `tool.before` | `PreToolUse` | `permission.hook("evaluate")`, `tool.hook("execute.before")` |
| `tool.after` | `PostToolUse` | `tool.hook("execute.after")` |
| `prompt` | `UserPromptSubmit` (command hook, D35) | `session.hook("prompt")` |
| `stop` | `Stop` | session idle event (name to confirm in Phase 0) |
| `session.start` | `SessionStart` (command hook) | session created event (Phase 0) |
| `session.end` | `SessionEnd` | equivalent to confirm in Phase 0 |

| Decision | Claude Code | OpenCode |
| --- | --- | --- |
| `allow` | `permissionDecision: allow` | no change |
| `deny` + message | `permissionDecision: deny`; on `stop`, exit 2 sends the agent back | `effect = "deny"`; on `stop`, a prompt into the session |
| `modify` + new input or context | `updatedInput`, `additionalContext` | input change in `execute.before`, output change in `execute.after` (Phase 0) |
| `ask` + message | `permissionDecision: ask` | `deny` with "ask Alex with the question tool, then retry", because `autoaccept` passes every ask |

**Failure mode.** If the core crashes or times out, the adapter denies calls that match a destructive rule (recursive delete, merge, destructive git) and allows everything else. Why: a timed-out Claude Code `PreToolUse` hook lets the call through, so the adapter must enforce this itself.

**Runtime.** TypeScript on Bun. mac-bootstrap installs a pinned Bun on the Mac and the VM. In Claude Code, the `harness-hooks` MCP server hosts the core, and `mcp_tool` hooks call its `decide` tool (D32). `SessionStart` and `UserPromptSubmit` are command hooks, and `guard-lite.ts` backs up the destructive rules (D33). The OpenCode plugin imports the core in-process, because OpenCode runs plugins on Bun, so each call costs nothing extra. Tests run with `bun test harness/`, and `scripts/check.sh` runs them in CI.

### Ledger

One SQLite file per host at `~/.local/state/harness/ledger.db`, opened with `bun:sqlite` in WAL mode, so several sessions can write at once. It is private storage, not an interface: each module in the Shape table owns its tables and offers domain operations (D53). Only those modules import the storage. The guard denies agent writes to it. It is per host: a merge token on the Mac does not work on the VM.

| Table | Holds | Kept |
| --- | --- | --- |
| `decisions` | every decision: session, event, rule id, outcome, reason. Each row holds the hash of the row before it (D46) | 30 days |
| `bundles` | proof bundles: did, works, verified (D41) | 30 days, and the PR body and git note keep the summary |
| `tokens` | merge grants from Alex's prompts | until used or 30 minutes |
| `watches` | PRs and workers the waker polls, with the last state seen | until done or 24 hours |
| `workers` | each spawn: base SHA, test file hashes, acceptance commands, last activity | 30 days |
| `sessions` | live sessions per repo | until `session.end` |
| `worktrees` | session, repo, path, branch, workstream, state (`active`, `landed`, `held`, `removed`) | until removed |
| `workstreams` | owner, worktrees in order, state, next steps, running processes, updated (D38) | until the workstream ends |
| `processes` | processes a session started, with a `keep` flag | until killed, or reported at the next `session.start` |
| `sendbacks` | stop send-backs per turn, for the cap | 30 days |

## Decisions

All taken by Alex on 2026-11-25.

| # | Decision | Answer | Why |
| --- | --- | --- | --- |
| D1 | Scope of this change | Plan doc only | Build comes after the plan |
| D2 | `gh pr merge` | Deny in shell. Merges go through the typed `merge_pr` tool, which needs Alex's token | Alex keeps the merge in chat, and a typed tool is easier to gate than a parsed command |
| D3 | Where the code lives | `alex-skills/harness/` | One fewer repo. skillcheck only reads folders with a `SKILL.md` (`skillcheck/core.py:63`), so it ignores `harness/` |
| D4 | Merge token | `MERGE-OK` in Alex's prompt: one merge of any PR in that session, within 30 minutes | Short to type, and an old prompt cannot authorize a merge hours later |
| D5 | Recursive delete allowlist | The session scratchpad, `~/.agents/skill-workspace`, `/tmp`, and tracked or ignored paths inside the current repo. Never the repo root, never `.git` | Would have blocked the 11-21 delete |
| D6 | Stale `HANDOFF.md` | The Stop check sends the agent back | Alex wants the handoff current at every milestone, and the cap stops a loop |
| D7 | Worktrees | An agent never writes in a repo's main checkout. Every writing session works in its own worktree, and the ledger keeps a pointer to it. This replaced a warn-only lock | Agents stop stepping on each other and on Alex |
| D8 | Steering fixes | In this spec, as Phase 2 | Alex picked it |
| D9 | When a watched PR merges | Resume the session and run the next step: the todo list first, then the HANDOFF Next list. If neither has a step, notify Alex | It never invents work |
| D10 | Stop cap | 5 send-backs per turn, then stop and say which check failed | Alex picked 5 over 3 |
| D11 | Core runtime | TypeScript on Bun, pinned, installed on both hosts | Native to OpenCode plugins |
| D12 | Adapters | OpenCode imports the core in-process; Claude Code spawns `bun core.ts` | One runtime and one code path |
| D13 | Events | The 6 in the Interface table | `session.end` gives a point to record leftovers |
| D14 | Decisions | `allow`, `deny`, `modify`, `ask`, plus an optional message | `ask` maps to a question-tool deny in OpenCode |
| D15 | Failure mode | Closed for destructive rules, open for the rest | A broken core never deletes repos and never blocks ordinary work |
| D16 | Ledger | SQLite per host, 30-day decision log | Several writers, queryable, in Bun |
| D17 | Worker acceptance | A `general` spawn with no `ACCEPTANCE:` block is denied. Read-only agents are exempt | The core needs the commands to re-run them |
| D18 | Verify result | Added as context next to the worker's reply | The parent sees the claim and the check side by side |
| D19 | Waker | One watch per session, every 2 minutes, expires after 24 hours | An OpenCode automation can only wake the session that created it |
| D20 | `session.end` | Kill the processes the session started, except the ones it registered with `keep` and named in its reply. Report the kept ones at the next start | The VM has little room for leftovers, and a server Alex asked for stays up only when it is named |
| D21 | Worktree home | `~/.worktrees/<repo>/<name>` | Outside every repo, so OpenCode does not load a second copy of a skill, and one folder is easy to measure on the VM |
| D22 | Cleanup | When a watched PR merges, the waker removes its worktree and local branch, only if the worktree is clean. The Stop check sends the agent back for unnamed running servers or scratch files over 500 MB | Disk on the VM stays bounded, and nothing with unsaved work is deleted |
| D23 | HANDOFF protocol | Agents coordinate through the `workstreams` table and the rendered `HANDOFF.live.md` (D38). The committed `HANDOFF.md` keeps only lasting context, 150 lines at most | Agents read who does what and where, and done work is removed, so the file stays current |
| D24 | Rollout | Every rule is live from day one. No shadow week | Alex wants the time savings at once. `harness wrong` (D28) is the safety valve |
| D25 | Kill switch | `harness off` and `harness on`: one global flag in the ledger that only Alex can set | One command recovers every session if the core has a bug |
| D26 | Landing | Fast-forward only. The agent rebases its worktree branch on `origin/main`. In personal repos (remote owner `acastro2`) it pushes to `main`. In work repos it opens a PR, merged by rebase or ff, never a merge commit. After each landing the harness, not the agent, runs `git merge --ff-only` in the main checkout | A straight history, and the local `main` never drifts |
| D27 | Semantic Stop checks | Jev judges 4 checks (asks Alex something, false "can't", stale state, state footer) from a short turn summary, and sends back at 0.80 or above. If Jev is blocked or takes over 3 seconds, strict keyword rules decide and the ledger logs `jev-unavailable` | Jev can be blocked, so it never runs without a fallback |
| D28 | Tuning | `harness wrong` marks the last send-back false, and the agent continues. A rule marked wrong 3 times in a day goes log-only until `harness on <rule>` | A bad rule cannot cost turns all day |
| D29 | Harness MCP server | One stdio MCP server in `harness/`, loaded by both tools, for every action an agent takes on purpose: `merge_pr`, `worktree_new`, `keep_process`, `harness_status`. It calls the same core and ledger. Enforcement stays in hooks, and the kill switch stays the ledger flag | An MCP server only offers tools the model may call, so it cannot enforce. Typed tools are easier to gate and log than parsed shell commands |
| D30 | Scope | Every git repo on both hosts, except the Obsidian vault and `~/.agents/skill-workspace` | The 11-21 wipe hit a work repo, so opt-in would have missed it |
| D31 | Who runs `harness` commands | Only Alex: typed in a prompt (read by the `prompt` event, like `MERGE-OK`) or in a terminal he runs. The guard denies agent shell calls to `harness off`, `on` and `wrong` | An agent must never switch the harness off |
| D32 | Claude Code adapter | `tool.before`, `tool.after` and `stop` are `mcp_tool` hooks that call `decide` on the `harness-hooks` MCP server, with `onFailure: "continue"`. `SessionStart` and `UserPromptSubmit` are command hooks. This replaces the Claude half of D12 | A warm process and no spawn cost per call. `mcp_tool` hooks are skipped at launch `SessionStart` ([hooks](https://code.claude.com/docs/en/hooks)) |
| D33 | Fail closed with MCP | Next to the main hook, a command hook `bun guard-lite.ts` checks only the destructive patterns, with `onFailure: "block"` (Claude Code 2.1.328 or later) | If the MCP server dies, deletes, merges and destructive git are still blocked, and other work goes on (D15) |
| D34 | Two MCP servers | `harness-hooks` serves only `decide`, and the model is denied it (`mcp__harness-hooks__*`). `harness` serves the 4 agent tools, with `codemode: false` in OpenCode. OpenCode keeps the in-process core and does not load `harness-hooks` | If the model could call `decide`, it could fake a prompt with `MERGE-OK` |
| D35 | Grants channel | `MERGE-OK` and `harness off`, `on`, `wrong` are read only by the command `UserPromptSubmit` hook (OpenCode: the in-process `prompt` hook), never through MCP | The one channel an agent cannot reach |
| D36 | Config protection | `harness-config-write` denies agent changes to the hook and MCP entries in `~/.claude/settings.json` and `~/.config/opencode/opencode.jsonc`, and to the harness plugin files. Edit and Write tool changes elsewhere in those files are parsed and allowed. Any shell write to those files is denied | Without it, an agent can delete the hooks. The core cannot parse a `sed -i` |
| D37 | Installing the harness | Only mac-bootstrap installs the harness: it pins Bun and runs `bun harness/install.ts`, which writes the entries. Alex runs mac-bootstrap; nothing else installs or changes the entries (Alex, 2026-11-25). `harness-self` also denies agent calls to `install.ts`. The core registers any worktree under `~/.worktrees/` on its first write, so `worktree_new` is a shortcut, not a gate | One reviewed path changes the harness, and a dead MCP server cannot block all writes |
| D38 | Live handoff | Live coordination lives in the ledger `workstreams` table. The harness renders it into a read-only `HANDOFF.live.md` in every worktree at `session.start` and after each change. Agents update it with the `workstream_update` MCP tool | With one worktree per session, a committed file is invisible to other agents until it lands, and parallel edits conflict |
| D39 | Worktree per branch | One worktree per branch (one PR or one ff landing). A workstream owns several worktrees in order | Removing a worktree on landing (D22) never kills ongoing work |
| D40 | Worktree states | `active`, `landed`, `held`, `removed`. The lifecycle module does each transition's work: fast-forward `main`, remove the worktree and branch, close the workstream entry. A `held` worktree messages its owner; after 24 hours with no live owner, Alex gets one notification | Landing steps stop being prose, and uncommitted work is never deleted |
| D41 | Proof bundle | Hooks record "did" (commits, diff, tool-call log with hashes, test file hashes) and "works" (claimed runs, screenshots taken after the last edit). The agent writes only `summary` and `known_gaps`. "Verified" is the harness's own re-run | Vendors let the agent make its own evidence; the harness must not |
| D42 | Where the re-run happens | In the worker's own worktree, with test files restored from base. The worktree must be clean first; if not, the verdict is `partial: uncommitted changes` | Alex picked the worker's worktree. The clean check stops a pass that depends on files that never land |
| D43 | Verdict | Code sets green, red or partial from exit codes. Jev scores the raw evidence as advice only and never sees the agent's pass claim | Verifiers shown the pass signal accept more hacks ([arXiv 2511.21654](https://arxiv.org/html/2511.21654)) |
| D44 | Push gate | No bundle for the head commit: push denied. Red or partial: only to a PR branch, labelled in the PR body. Green: may land anywhere. The verdict goes in git notes (`refs/notes/harness`) and the PR body, not a commit trailer | Nothing reaches `main` without the harness's own green. A trailer would change the SHA it proves |
| D45 | Failure ladder | 3 red verdicts in a row on one branch: round 1 back to the worker, round 2 on the strong model, round 3 inline, then stop and ask Alex. No skipped flaky tests, no retries | Matches the existing escalation rule, now enforced from the ledger |
| D46 | Ledger integrity | Hash-chain the `decisions` and `bundles` rows; `harness status` checks the chain. No signing | Every agent runs as Alex's user, so it could read any signing key. The `ledger-write` rule is the real control |
| D47 | Proof for the main session | A Stop check sends the orchestrator back when it says "done", "fixed" or "works" with no green bundle in that turn for the change it means | Done means shown, not claimed, for every session |
| D48 | Bundle in the PR | The PR body gets 6 lines: head SHA, verdict, acceptance table, screenshot links, bundle ID, and `known_gaps` | A reviewer sees the harness's proof, not the agent's story |
| D49 | Install manifest | One manifest lists each event, its transport, matcher, `onFailure` and an entry id. `install.ts` writes both tools' config from it, the adapters route by it, and `harness-config-write` protects exactly the entries it names | Folded from review 2. D36 gets a precise target, and the installed config cannot drift from the source |
| D50 | Authority module | `fromAlex`, `holds` and `protects` own every grant, switch and anti-forgery rule (`ledger-write`, `harness-self`, `harness-config-write`, the `decide` deny). The prompt hook in both tools, `cli.ts` and `merge_pr` all call it | Folded from review 2. The security story is one module and one test suite |
| D51 | Destructive rules module | `classify(command, cwd)` holds the shell parser and the D5 allowlist. The core, `guard-lite.ts` and the OpenCode failure path all call it. `guard-lite.ts` is about 20 lines | Folded from review 2. The fallback can never protect less than the main path |
| D52 | Judgment module | `judge(questions, summary)` sends all of a stop's semantic questions to Jev in one call, applies the 3-second timeout and the keyword fallback, and logs `jev-unavailable` | Folded from review 2. One Jev round trip per stop, and the fallback is written once |
| D53 | Ledger interface | The ledger is private storage. Each module owns its tables and offers domain operations, such as `grant` and `consume` in authority, and `register` and `land` in the worktree lifecycle | Folded from review 2. Schema and expiry stay with their owner |

## Phase 0. Prove the unverified facts

Do this first. The design depends on these facts, and the docs do not answer them. Each test becomes an adapter test in Phase 1.

| Fact | Test | Done when |
| --- | --- | --- |
| OpenCode `permission.hook("evaluate")` with `effect = "deny"` stops a `shell` call under `autoaccept` | A scratch plugin denies `echo HARNESS-PROBE`, and a session runs it | The command does not run, and the agent sees the reason |
| `bun:sqlite` loads inside OpenCode's plugin runtime | A scratch plugin opens a database and writes one row | The row is in the file |
| OpenCode `tool.hook("execute.before")` can change a tool's input, and `execute.after` can change its output | A scratch plugin adds a line to a `subagent` prompt and to a shell result | Both changes show in the session |
| A per-call subagent `model` overrides the agent's frontmatter `model` | Call `general` with a `model` that differs from its frontmatter, then read `session_v2.model` | The row shows the per-call model |
| An automation or a background wait can wake an idle session (OpenCode `automation` `send`, Claude Code `Monitor` or a background shell) | Start a 1-minute watch that sends `HARNESS-WAKE`, then let the session go idle | The session resumes and answers with no prompt from Alex |
| The OpenCode V2 events for idle, session created and session end | Log every `session.hook` event name in a scratch plugin across one session | The names are in the Interface table |
| Each tool's todo list can be read by the core at `stop` | Log the todo items a scratch adapter sees in one turn, in both tools | The pending items show in the log |
| What counts as `session.end` in OpenCode when the TUI closes but the session stays on the server | Close a TUI on a session with a test server running, and log the events | The event name is in the Interface table, and its timing is recorded |
| Jev answers inside 3 seconds from a hook, and the fallback runs when it does not | Call Jev from a scratch Stop adapter, then once with the network blocked | A typed answer, then a `jev-unavailable` row |
| A permission deny on `mcp__harness-hooks__*` blocks the model, while `mcp_tool` hooks can still call `decide` | Deny the tool, then call it from the model and from a hook | The model call is denied and the hook call returns a decision. If not, `decide` moves to command hooks |
| `guard-lite.ts` with `onFailure: "block"` blocks a destructive call when the MCP server is down | Stop the `harness-hooks` server, then run `rm -r` on a path outside the allowlist | The call is blocked, and a plain `ls` still runs |
| A Claude Code command can read its own session ID | A `SessionStart` hook writes `session_id` to an env file, and a command reads it | The command prints the ID |

If the deny test fails, the OpenCode adapter uses `execute.before` to replace the command with one that fails with the reason. If `bun:sqlite` does not load, the OpenCode adapter spawns `bun core.ts` like Claude Code. If the wake test fails, the waker uses the Rex or Herdr notification only. If more than one of these fails, stop and bring it to Alex.

## Phase 1. Core, ledger, adapters, guard

Build the core, the install manifest (D49), the authority module (D50) and the destructive rules module (D51) first. Together they close the worst risks and hold the whole security story, and they prove the seam with both adapters.

Guard rules (each has a rule id, so Phase 8 can switch it off). `recursive-delete`, `merge-in-shell` and `destructive-git` live in the destructive rules module. `harness-self`, `harness-config-write` and `ledger-write` live in the authority module:

| Rule id | Denies | Message to the agent |
| --- | --- | --- |
| `recursive-delete` | `rm -r`, `rm -rf`, `find -delete`, `rsync --delete` outside the D5 allowlist | "Recursive delete outside the allowlist. Name the exact files, or ask Alex." |
| `merge-in-shell` | Every `gh pr merge`, `gh api .../merge`, `git merge` into `main` or `master`, `git push` of a merge to `main` that has no PR | "Use the `merge_pr` tool." |
| `destructive-git` | `git reset --hard`, `git clean`, `git push --force` and `-f`, `git checkout -- .` | Same rules as today's `opencode.jsonc` deny list, now in both tools |
| `push-gate` | A `git push` of a head commit with no bundle, or a red or partial bundle pushed to `main` (D44) | "Verify first: the harness needs a green bundle for this exact commit to land on main." |
| `ledger-write` | Any write to `~/.local/state/harness/` | "Only the harness writes its state." |
| `harness-self` | An agent shell call to `harness off`, `harness on`, `harness wrong` or `harness/install.ts` (D31, D37) | "Only Alex runs harness commands." |
| `harness-config-write` | A change to the hook or MCP entries in `settings.json` or `opencode.jsonc`, a change to the harness plugin files, or any shell write to those files (D36) | "Change the harness source in a worktree. mac-bootstrap installs it." |
| `main-checkout-write` | An edit or write tool on a path in a repo's main checkout, and `git commit`, `git checkout`, `git merge` or `git rebase` run there (D7) | "Work in a worktree: call `worktree_new`. It records the pointer for other agents." |

The guard parses the full command and walks `bash -c`, `sh -c`, `env`, `xargs`, `git -C` and absolute paths before it matches. Why: deny rules in both tools match only the command text.

**Control commands.** Alex types `harness off`, `harness on`, `harness on <rule>` or `harness wrong` in a prompt, and the `prompt` event applies it. From his own terminal, `bun harness/cli.ts <command>` does the same when a session is stuck. `harness status` shows the flag, the log-only rules and today's send-backs.

**Landing (D26).** After an agent pushes, the core's `tool.after` policy checks that the push was fast-forward, then runs `git merge --ff-only origin/main` in the main checkout itself. The `main-checkout-write` rule does not apply to the harness, only to agents.

**Merge.** `merge_pr` is one stdio MCP server in `harness/` (D29), with `repo` and `pr` fields. It merges by rebase or fast-forward only. Why: Anthropic recommends a dedicated tool for hard-to-reverse actions, because the harness then sees typed arguments it can gate, log and replay ([article](https://claude.com/resources/articles/harnessing-claudes-intelligence)). The token flow:
1. A `prompt` event with `MERGE-OK` from Alex writes a row to `tokens`.
2. `merge_pr` reads the row, merges one PR and deletes the row.
3. With no valid row, `merge_pr` returns "Merge needs Alex's token."

Why the ledger holds the token: the agent can write files, but the `ledger-write` rule stops it from writing there, so only Alex's prompt can make a token.

Done when:
- `bun test harness/` passes. The authority suite tries every forgery path: an agent calls `decide` with a fake prompt, writes the ledger, runs `harness off` or `install.ts`, and edits a manifest entry; each one is denied. The destructive rules suite runs once and covers the core, `guard-lite.ts` and the OpenCode failure path. The suites also have one case per rule, the bypass forms (`git -C . push --force`, `bash -c "rm -rf ~/x"`, `/usr/bin/gh pr merge 1`), the token expiry, the failure mode, the kill switch, and an agent call to `harness off` that is denied.
- A live probe in each tool shows a denied `rm -rf <path outside allowlist>` with the message, and a merge on a throwaway repo under `~/.agents/skill-workspace/` that works only after `MERGE-OK`.

## Phase 2. Steering: PR watcher and Stop hook

This phase gives Alex his time back. The PR watcher and the Stop hook remove about 230 of the 334 steering prompts.

```mermaid
flowchart LR
  A[Agent opens PR] --> W[PR watcher]
  W -->|merged / approved| R[Resume session:<br/>next planned step]
  W -->|CI red / conflict| F[Resume with<br/>failing check logs]
  R --> S{Stop hook}
  F --> S
  S -->|todos left, uncommitted,<br/>no link, no screenshot| R
  S -->|clean| Y[Alex: only real decisions]
```

**PR watcher (the waker).** It also keeps state fresh: the stale-state check reads PR state from the watcher's last poll in the ledger, not from the agent's memory. When an agent runs `gh pr create` or pushes to a PR branch, the core's `tool.after` policy adds a row to `watches` with the session ID. The waker polls `gh pr view <n> --json state,reviewDecision,mergeable,statusCheckRollup` every 2 minutes (D19) and wakes the session on a change:

| Change | What the session gets |
| --- | --- |
| Merged (D9) | "PR #n merged. Run the next planned step." The step comes from the todo list, then the HANDOFF Next list. With neither, Alex gets a notification instead. |
| Approved | "PR #n approved. Merge needs Alex's token." The agent never merges by itself. |
| A check failed | The failed job name and the last 80 log lines (`gh run view --log-failed`) |
| Conflict | "PR #n has a conflict with its base. Rebase and re-run the acceptance commands." |

- OpenCode: one `automation` with an `every` trigger and a `code` action. It returns `send: { prompt }` to the session that opened the PR, and `done: true` once the PR is closed or merged and the next step has started.
- Claude Code: a background `Monitor` or a `gh pr checks --watch` background shell that ends the wait. Check in Phase 0 which one wakes an idle session. If neither can, use a Rex or Herdr notification, and Alex types one word.

**Stop checks.** On the `stop` event, the core reads the turn and returns `deny` with a message, which sends the agent back. Each check has a rule id:

| Check | Sends back when | Prompts it removes |
| --- | --- | --- |
| Commit | The repo has verified changes that this session made, and they are not committed and pushed. Never other sessions' files. | 32 "commit and push" |
| Links | The turn ran `git push`, `gh pr create`, a ticket or comment create, or a page publish, and the reply has no URL for it | 36 "link?" |
| Continue | The todo list has a pending item and the reply does not ask Alex anything | 31 "continue", 35 automatic "Continue." |
| UI proof | The turn changed UI files and has no `browse` screenshot after the last change | most of the 41 screenshots |
| State | The reply does not end with what is done, what is running, and the next step | 17 "what now?" |
| Handoff | This session's `workstreams` entry was not updated since its last commit (D6, D38) | the handoff reminders |
| Proof | The reply says "done", "fixed" or "works" with no green bundle in this turn for that change (D47) | claims that are not shown |
| Processes | A process this session started is still running and is not named in the reply | the server scavenger hunt |
| Cleanup | Scratch files for this session are over 500 MB, or a merged worktree of this session is still on disk (D22) | disk filling on the VM |
| Handoff protocol | The committed `HANDOFF.md` is over 150 lines, or holds live workstream state that belongs in the ledger (D23) | handoffs that only grow |
| Stale state | The reply says a PR is open, a review is waiting, or something waits for Alex, and the turn did not check it live (`gh pr view`, the ticket, the inbox) after the last time Alex spoke | 9 "it's already merged", "already sent" |
| False "can't" | The reply says the agent cannot do something, or asks Alex to do it by hand, and the task is in a browser while `browse` is connected. Only login, 2FA, a passkey, a captcha or a payment confirmation go to Alex, through `handoff`. | "you can, use browser control" |

The four judgment checks (ask Alex something, false "can't", stale state, state footer) go through the judgment module (D52): one Jev call per stop with a short turn summary, and a send-back at 0.80 or above (D27). The summary holds no transcript, no secrets and no file contents. When Jev is blocked or slow, strict keyword rules decide.

The cap (D10) stops a loop: after 5 send-backs in one turn, the core lets the agent stop and say which check failed. The `sendbacks` table counts them.

**Upkeep.** Pin model and effort in each agent's frontmatter and in `settings.json`, so `/model` and `/effort` stop being needed at session start. Reload skills when a file in `~/.agents/skills` changes. Claude Code has a `FileChanged` hook event, and the existing `sync-agents-skills.sh` is the start.

Done when:
- A test PR on a throwaway repo goes from opened to merged, and the session resumes with no prompt from Alex.
- A failed check comes back as logs in the session.
- `bun test harness/` has one case per Stop check, plus the cap.
- After one week of use, a re-run of the prompt count shows the steering share down from 28%.

## Phase 3. Worker lifecycle and proof of work

One policy covers a worker from spawn to return, and every change ends in a proof bundle the agent cannot fake. The research behind this: `/tmp/claude-502/-home-acastro20-guest--agents-skills/2dd99377-ceae-4a96-b0d9-f4df8b62dd57/scratchpad/proof-of-work.md` (scratch), from the [Claude Code team on verification](https://claude.dev/blog/how-the-claude-code-team-thinks-about-verification/), [Anthropic on long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) and [agent receipts](https://github.com/danielmeppiel/agent-contracts/blob/main/spec/receipt.md).

```mermaid
sequenceDiagram
  participant P as Parent
  participant C as Core: worker lifecycle
  participant W as Worker
  participant L as Ledger
  P->>C: subagent call (tool.before)
  C->>C: deny if no model or no ACCEPTANCE block
  C->>L: base SHA, test hashes, commands
  C->>W: prompt plus the worker contract
  W->>C: every tool call (tool.after)
  C->>L: did: commits, diff, tool log. works: claimed runs, screenshots
  W-->>C: return with summary and known_gaps
  C->>C: clean check, restore tests, re-run, real run
  C->>L: verified: verdict green, red or partial
  C-->>P: worker reply plus the bundle as context
```

**Spawn** (`tool.before` on `subagent`, `Agent` or `Task`):
- Deny when `model` is missing, or a `general` spawn has no `ACCEPTANCE:` block (D17). Read-only agents are exempt.
- Record the base SHA, test file hashes and acceptance commands in `workers`.
- Add the worker contract to the prompt (`modify`): load `coding` first, no git writes outside its worktree, flag a wrong test and do not edit it, end with `summary` and `known_gaps`.

**Proof bundle (D41).** Each field has one owner, so the agent writes only what it cannot fake:

| Level | Field | Captured by |
| --- | --- | --- |
| Did | `session`, `model`, `effort`, `base_sha`, `head_sha`, `commits[]`, `diff_stat`, `outside_allowlist[]` | hooks |
| Did | `tool_calls[]`: tool, args hash, exit code, output hash, time | hooks |
| Did | test file hashes before and after | hooks |
| Works | `runs[]` the agent ran, tagged "claimed" | hooks |
| Works | `ui_proof[]`: `browse` screenshots taken after the last edit | hooks |
| Verified | `clean`: the worktree had no uncommitted changes (D42) | harness |
| Verified | `rerun[]`: each acceptance command with test files restored from base | harness |
| Verified | `real_run`: the command that runs the real thing, from the contract | harness |
| Verified | `verdict`: green, red or partial, set by code (D43) | harness |
| Verified | `advisory`: Jev's score on the raw evidence, never the claim | harness |
| Agent | `summary`, `known_gaps` | agent |

**Verify on return** (`tool.after`):
1. If the worktree is not clean, stop: verdict `partial: uncommitted changes`.
2. Compare the test file hashes with the record, then restore the test files from the base SHA.
3. Run each acceptance command and the real run. Keep each exit code and the last 40 lines.
4. Set the verdict by code, ask Jev for its advisory score, and write the bundle to `bundles`.
5. Add the bundle to the worker's reply as context (D18), so the parent sees the claim and the proof side by side.

**Where the proof goes:**
- The full bundle stays in the ledger, hash-chained (D46).
- The verdict goes in git notes (`refs/notes/harness`) on the head commit, and the 6-line summary in the PR body (D48).
- The `push-gate` rule denies a push with no bundle, and keeps red or partial off `main` (D44).
- The workstream entry links the bundle ID, so `HANDOFF.live.md` shows it.

**Failure ladder (D45).** After a red verdict, round 1 goes back to the worker, round 2 runs on the strong model, round 3 is done inline by the orchestrator. After 3 reds in a row on one branch, the work stops and Alex is asked. No skipped flaky tests and no retries along the way.

**The main session too (D47).** The Stop check sends the orchestrator back when it says "done", "fixed" or "works" with no green bundle in that turn.

The waker also watches each background worker. With no new tool call in 10 minutes, the worker gets the nudge Alex types today: "stop exploring, run the acceptance commands once, return". When a worker finishes, Alex gets one Rex or Herdr notification.

Done when:
- On a seeded repo, a worker that edited a test comes back red, a worker with uncommitted changes comes back partial, and a clean worker comes back green.
- A push with no bundle is denied, and a red bundle cannot fast-forward to `main`.
- `harness status` detects a hand-edited `bundles` row through the hash chain.
- A stalled worker gets one nudge, and a finished worker shows one notification, with no prompt from Alex.

## Phase 4. Small fixes, no hook needed

- **Bun:** mac-bootstrap installs a pinned Bun on the Mac and the VM (D11).
- **acastro2 pushes:** set `credential.https://github.com/acastro2.helper` in the global git config, so pushes to acastro2 repos use that account's token. This removes the 250 hand-typed helpers. The command goes in mac-bootstrap.
- **Broken symlinks:** `~/.claude/commands/ub-mode.md` and `~/.config/opencode/commands/ub-mode.md` point at `/Users/acastro/...`. Make them relative, or create them from mac-bootstrap per host.

Done when: `bun --version` prints the pin on both hosts, `git push` in `alex-skills` works with no `-c credential.helper`, and both `ub-mode` links resolve on Linux and on the Mac.

## Phase 5. Worktree lifecycle, cleanup, live handoff

One worktree lifecycle module owns every worktree from creation to removal, so landing steps are code, not prose.

```mermaid
stateDiagram-v2
  [*] --> active: worktree_new or first write under ~/.worktrees
  active --> landed: green ff push to main, or PR merged
  landed --> removed: worktree clean
  landed --> held: uncommitted changes
  held --> removed: owner cleans it
  removed --> [*]
```

**Worktrees (D7, D21, D39).** One worktree per branch, at `~/.worktrees/<repo>/<name>`. The `worktree_new` MCP tool creates it, records it, and moves the session there (OpenCode `session.move`; Claude Code `--worktree` or `isolation: worktree` for subagents). A worktree made by hand under `~/.worktrees/` is registered on its first write (D37). The `main-checkout-write` rule denies agent writes in the main checkout.

**Transitions (D40).** The lifecycle module does each step itself:

| Transition | What the module does |
| --- | --- |
| `active` to `landed` | Runs `git merge --ff-only origin/main` in the main checkout (D26), links the bundle, and marks the workstream step done |
| `landed` to `removed` | `git worktree remove` (never `--force`), deletes the local branch, updates `HANDOFF.live.md` |
| `landed` to `held` | Messages the owner session. After 24 hours with no live owner, notifies Alex once |

If the main checkout has uncommitted changes of its own (Alex editing by hand), the fast-forward is skipped and Alex gets a notice.

**Live handoff (D23, D38).**
- The `workstreams` table holds each live workstream: owner, worktrees in order, state, next steps, running processes, updated.
- The harness renders it into a read-only `HANDOFF.live.md` in every worktree at `session.start` and after each change. Agents read it to see who does what, and where.
- Agents change their own entry with the `workstream_update` MCP tool, never by editing the file.
- The committed `HANDOFF.md` keeps only lasting context: repo gotchas and long-running items, 150 lines at most. The `handoff` skill changes to match, and the repo's own `docs/HANDOFF.md` is the first one to clean up.

**Cleanup (D20, D22).**
- On `session.end`, the core kills each process in `processes` for that session, unless it has the `keep` flag. An agent sets `keep` with the `keep_process` tool only for a server Alex asked to keep up, and the Stop check makes it name the process in the reply.
- The Stop check sends the agent back when its scratch files are over 500 MB or a removed worktree is still on disk.

Done when:
- Two sessions in one repo each get a worktree, and each sees the other in `HANDOFF.live.md` at start.
- A write in the main checkout is denied with the worktree message.
- A green ff landing fast-forwards the main checkout, removes the clean worktree and its branch, and updates the live file.
- A landing with uncommitted changes goes to `held`, and the owner gets the message.
- `session.end` kills an unkept test server and keeps a server flagged `keep`.

## Phase 6. Fork to a new tab

Alex often wants to explore two paths from one conversation. Today `/fork` replaces the session he is in. The goal: one command opens the fork in a new Rex tab, already running, and the original session does not stop or change.

```mermaid
sequenceDiagram
  participant A as Alex
  participant O as Original session
  participant F as fork_tab.sh
  participant R as Rex
  participant N as Forked session
  A->>O: /fork-tab try the plugin route
  O->>F: session ID, prompt, optional worktree
  F->>N: fork with full history, send the prompt
  F->>R: rex window new --focus=false -- open N
  R-->>A: new tab, still in the original
  O-->>A: original keeps working
```

Verified on 2026-11-25:
- **OpenCode:** `opencode run -s <session> --fork --title <t> --format json "<prompt>"` made a new session with the full history. It answered a question about this conversation, while the original session kept running. The JSON events carry the new `sessionID`. `--worktree <name>` also exists on `opencode run`.
- **Claude Code:** `claude --resume <id> --fork-session` exists in `claude --help` (2.1.332). Not run yet.
- **Rex:** `rex window new -s SESSION LABEL --focus=false -- COMMAND` opens a tab and keeps Alex's current tab active.

`harness/fork_tab.sh` does the following:
1. OpenCode: run `opencode run -s "$OPENCODE_SESSION_ID" --fork --title "<t>" --format json "<prompt>"`, read the new session ID from the events, then `rex window new -s "$REX_SESSION" "<t>" --focus=false -- opencode -s <new id>`.
2. Claude Code: `rex window new -s "$REX_SESSION" "<t>" --focus=false -- claude --resume <id> --fork-session "<prompt>"`.
3. The fork always gets its own worktree through the `worktree_new` tool (D7), so the two paths never edit the same files.
4. Under Herdr (`HERDR_ENV=1`), open a Herdr tab instead of a Rex tab.

Entry points: an OpenCode command `/fork-tab <prompt>` and a Claude Code command or skill `/fork-tab <prompt>`. Each calls the script with its own session ID.

Open questions for Phase 0:
- How does a Claude Code command read its own session ID? Hooks get `session_id` on stdin. A `SessionStart` hook can write it to an env file. Not verified.
- Does `claude --resume <id> --fork-session "<prompt>"` start the fork with the prompt in the interactive TUI? Not run yet.

Done when: `/fork-tab` from a running session opens a new tab that already answers the prompt with the full history, Alex's tab stays focused, and the original turn goes on with no change.

## Phase 7. Cut the prose

For each rule now enforced in code, cut the "what" from `AGENTS.md` and `CLAUDE.md`, and keep one line of why plus the rule id. Target: both files under 70 lines. Why: OpenAI keeps its AGENTS.md at about 100 lines, and every enforced rule left in prose is context the model reads for nothing.

Done when: the line counts drop, and a short eval shows no rule loss. Run the `coding` worker eval and one merge-attempt eval before and after the cut.

## Phase 8. Prune by eval

Anthropic's point: every harness part encodes a limit of the model, and a newer model can make it dead weight ([article](https://claude.com/resources/articles/harnessing-claudes-intelligence)). So the harness gets the same test as a skill.

- For each prose rule left after Phase 7, run one eval with the rule and one without it, on the current model.
- Switch a harness rule off by its id for one eval run with `HARNESS_DISABLE=<rule-id>`. The decision log in the ledger shows which rule fired.
- Remove each rule that changes nothing. Keep the eval, so the next model change re-runs it.
- Count the MCP tools loaded in a session. Tools sit in the cached prefix, so a long or changing list costs cache hits and attention. Move rarely used servers behind Code Mode search.
- Test Claude Code auto mode (a second model judges each shell command) as a backstop behind the guard rules. It does not replace the guard: it is a judgment, and the guard rules have no exceptions.

Done when: every remaining prose rule has an eval that shows it changes the output.

## Later, end to end

Not in this plan. Each needs its own spec.

- Automations: `gather` and `bard` sweeps, the morning brief, and a weekly `upstream_audit.py` run that opens a PR.
- `anthropics/claude-code-action` for PR review on `alex-skills`.
- A doc-gardening job that checks `HANDOFF.md` and the README tables against the repo.
- Package the adapters as a Claude Code plugin (`.claude-plugin/plugin.json`), so the Mac and this box install the same thing.

## Risks

- **The `harness-hooks` server is down.** The main hooks continue, and `guard-lite.ts` still blocks the destructive calls (D33). The Stop checks and the worker lifecycle do not run until it is back, and `harness status` shows it.
- **A hook timeout lets the call through.** In Claude Code, a timed-out `PreToolUse` hook does not block. The adapter applies the failure mode (D15) itself, and the core has no network calls on `tool.before`.
- **An in-process core can crash the OpenCode plugin.** The adapter wraps each call and applies the failure mode on any exception.
- **`--bare` skips hooks.** `claude -p --bare` runs with no hooks, so the eval harnesses run without the guard. That is fine for evals, but never use `--bare` for real work.
- **Plugin subagents ignore `hooks`.** Put the Claude Code hooks in `settings.json`, not in a plugin's agent frontmatter.
- **Another session edits the same files.** Commit each phase with a pathspec.
