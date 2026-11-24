---
name: coding
description: "Alex's coding standards: shape code for testability, test first at agreed seams, prove behaviour, prune tests that guard nothing, review your own diff, and write every PR description, from a spec or tickets to the PR. References for Terraform and OpenTofu, and for web UI. Use before you write, change, or review code, including UI and accessibility reviews, and before you open a PR or change its body, or when asked to write or rewrite a PR description. Not for critiquing a PR: that is reviewer."
license: MIT
---

# Coding

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

How I code, from the first line to the PR. `AGENTS.md` and `CLAUDE.md` make every coding session load this file before it changes code or opens a PR. Follow the repo's own rules too. If they conflict with this file, stop and ask instead of guessing.

```mermaid
flowchart LR
  S[0. Start from the spec] --> A[1. Shape the code]
  A --> B[2. Verify and test]
  B --> C[3. Finish: prune, review, then PR]
  D[4. By domain: Terraform, web UI] -.adds rules to.-> A
```

The rules in parts 0 to 3 apply to every language. A domain reference adds to them; it never overrides them.

## 0. Start from the spec

### Read before you build

- **Start a build from a spec or tickets only when I say so.** Planning and questions are fine before that; code is not.
- **Read the input first: the spec, the tickets, or both.** If the work is more than a small change and has no spec, say so and offer to write a short one first.
- **Read the repo before you touch it:** `CONTEXT.md` if it exists, the ADRs in the area you change, and the repo's own `AGENTS.md` or `CLAUDE.md`.

**Why:** a spec is the only place the why survives the session. A build that starts from memory of the chat builds what you remember, not what I asked for.

### Stay inside the slice

- **Do not fix problems outside the slice.** Report them and let me decide.
- **If a slice is too big for one session, stop and say so.** Cut it again instead of pushing through a full context window.

**Why:** scope creep in a slice is how a slice stops being demoable, and a half-done slice at the end of a context window is worse than a small finished one.

The start and review steps come from mattpocock/skills `implement`, rewritten.

## 1. Shape the code

### Design for testability. Do not inject everything

- **Testable means controllable and observable.** Controllable: a test can cheaply reproduce the situations the code runs in. Observable: a test can see what the code did. If you can't do both, the design is the problem, not the test.
- **Put a seam only where the real dependency is non-deterministic or outside the process.** That list is short and predictable: clock, randomness, network, filesystem, database, environment variables, subprocesses, message queues. Everything else gets constructed directly.
- **Inject a dependency when one of these is true, not by default:** you genuinely need a second implementation, or you need to test how this code *interacts* with that collaborator. If neither holds, injecting it only complicates every caller.
- **Split newables from injectables.** Value objects and entities are newables: tests just build them. Services (things that *do* something: parsers, clients, repositories) are injectables. Never inject a service into a value object or entity; it makes the value object impossible to build without a mock.
- **Own the interface at the boundary.** Define the interface your code actually needs (`Clock`, `ArticleStore`), not a thin wrapper around the vendor's API. Unit-test the callers against a test double; write one integration test that exercises the real implementation, because that's the only place the vendor's real behaviour gets checked.
- **When something genuinely can't be tested, make it humble.** UI glue, framework entry points, async plumbing: move logic out until what remains is so small it's obviously correct by reading it. Test the logic you moved out; leave the humble part untested on purpose.
- **Never build a seam speculatively.** An interface with one implementation and no test double behind it is not flexibility, it's a maintenance cost. Add the seam when the second implementation or the test that needs it actually shows up. (How much testing a change warrants at all is the tests-and-docs rule in `AGENTS.md`; this section is only about how to shape the code so testing is possible.)
- **Say "seam" for where an interface lives, and "boundary" for a real external edge.** A seam is a place where behaviour can change without editing in that place. A boundary is where the system meets something you do not own, such as a vendor API or a database. Keep both words, but do not use "boundary" to mean the first thing: in domain-driven design it already means a bounded context.

**Why:** testability is a side effect of good design, not a goal you bolt on. Code that's easy to test usually has fewer dependencies and clearer contracts. But "inject everything" is the overengineering I hate: an interface per collaborator, almost all with exactly one implementation forever, and object graphs so big you need a framework to assemble them. Seams at real boundaries buy fast, deterministic tests. Seams everywhere else are pure cost.

Sources for the framing above: Feathers on seams, Beck on controllability, Hevery on newables vs injectables, Meszaros/Martin on the humble object, Fowler on non-determinism, Noback on owning your boundary interfaces.

### Be short on comments

- **Only comment when the why isn't obvious from the code.** No narrating what the code already says.

**Why:** models tend to over-comment, and I don't like it. Noisy comments bury the few that matter, and good names plus small functions already tell the what.

## 2. Verify and test

```mermaid
flowchart TD
  C[Change] --> K{Bug fix, or a written criterion?}
  K -- yes --> T[Write that one test first, see it fail]
  K -- no --> B[Build it]
  T --> B
  B --> E[Run the existing tests the change touches]
  E --> F{One fails?}
  F -- yes --> X[Fix the code, or stop and flag the test]
  F -- no --> V[Run the real thing, show command and output]
  X --> E
  V --> R[Restore test files from base, run again]
```

### Verify by running the real thing

- **Prove every change by running it.** Run the real code path: the CLI, the service, the page in a browser, the script against real input. You pick how. Show the command and its real output. "It should work" is not proof.
- **Run the existing tests the change touches, and leave no earlier test failing.** If a test already failed on the base branch, say so. Never add a new failure.
- **If you cannot run it, say so.** Mark it "not run", give the reason, and give the exact command that runs the real code path on sample input, with the output you expect. Running only the existing tests is not this command. Never claim a run you did not see.

**Why:** an agent stops when the work looks done. A run gives a signal that the agent did not write itself. The regression cost across changes comes mostly from earlier tests left failing, not from code that is hard to maintain ([SWE-Maintain](https://arxiv.org/abs/2610.14768)).

### Do not write tests nobody asked for

- **Do not write a test that only the code suggests.** That means no unit test for a helper, no test "for coverage", and no characterization or snapshot test that records what the code does now.
- **Write a new test only in these cases:**
  - **A bug fix.** Write the repro test from the bug report, before the fix. See it fail for the right reason, then fix the code.
  - **A written acceptance criterion.** A spec or a ticket states the rule before the code exists. A chat request does not count, unless I ask for a test in it. The test name says which criterion it guards.
- **Keep the existing behaviour tests as the guard.** Keep them green, fix them when they are wrong, and add a case when the change extends a rule they already guard.
- **Do not apply any of this to a throwaway script, a spike, a config value, or a pure rename.** Run it and show the output.
- **In delegated work, the orchestrator writes the allowed test and agrees its seam with me.** The worker gets both in its contract and writes no other test.

**Why:** a test that the agent derives from its own code holds the same reading of the task as the code. If the reading is wrong, the test confirms the error. Banning these tests did not lower success, and it cut time and tokens ([Kun Chen, DeepSWE](https://substack.com/@kunchenguid/note/c-356087116); [arXiv 2602.07900](https://arxiv.org/abs/2602.07900)). Generated regression tests also lock in bugs: 8–17% of them asserted the faulty behaviour, and most of those were still passing many commits later ([arXiv 2610.11835](https://arxiv.org/abs/2610.11835)). A test is worth what its expected value is anchored to. A bug report or a written criterion was fixed before the code, so it gives an anchor that the code does not.

### When an existing test fails

- **The code is wrong until you show otherwise.** Fix the code.
- **Change a test only when you can name the rule that changed, and I agreed.** If a test looks wrong, stop and flag it: name the test and say why. Do not edit it. In delegated work, return `blocked`.
- **Never delete, skip, or weaken a test to get green.** Never special-case a test's input in the code.
- **Before you trust a green run, restore the test files from base and run again:** `git checkout <base> -- <existing test paths>`. In delegated work the orchestrator does this. New test files are not on the base branch, so review them in the diff.

**Why:** agents edit tests to get green. Read-only tests cut Claude Opus 4.1's cheating from 50% to 1%, and a "flag for a human" exit cut GPT-5's from 54% to 9% ([ImpossibleBench](https://arxiv.org/abs/2510.20270)). Restoring from base gives the same effect as read-only tests, with no harness setup. It does not catch special-casing, so the self-review looks for that.

### Write an allowed test first, at a seam

- **Agree the seam before you write the test,** unless your contract already gives it. A seam is the place where you observe behaviour without reaching inside the implementation.
- **Red before green.** Run the test and see it fail for the right reason. Then write only enough code to pass it.
- **Approve the interface before you build against it** when the shape of the seam is itself the open question.
- **Refactor after green, as its own step.** Then run the tests and the real thing again.

**Why:** a test written after the code passes on its first run, so nothing shows that it can ever fail. The failing run is the only evidence that the test reaches the code.

### Prove the contract through behaviour

Use this when you write an allowed test, or fix an existing one. A test earns its place when it can fail because the system's observable behaviour is wrong. It should not fail only because code moved, a private name changed, or the implementation now reaches the same result by a different path.

```mermaid
flowchart LR
  A[Real input] --> B[Production entry point]
  B --> C[Real behaviour]
  C --> D[Observable outcome]
  D --> E[Contract proved]
```

Use the closest proof to production that stays deterministic, safe, and cheap:

- **Behaviour tests prove outcomes that matter to a user or operator.** Start through a public entry point. Assert returned data, persisted state, emitted events, logs, metrics, files, process exit status, or another result outside the implementation. Do not substitute assertions about private methods or collaborator calls unless that interaction is itself the contract.
- **Contract tests prove each boundary.** Cover accepted and rejected inputs, outputs, failure semantics, and side effects. Include protocol details such as status codes, schemas, serialization, idempotency, and error shape when callers depend on them.
- **Integration tests prove real boundaries where practical.** Exercise the real database engine, filesystem, network client, subprocess, queue, or vendor adapter in a safe test environment. A test double can isolate caller logic. It cannot prove that the real dependency accepts the request or produces the response your code expects. Do not stub the boundary the change crosses.
- **End-to-end tests prove critical production flows.** Start at the real external entry point and follow the flow to its durable or user-visible result. Keep this set small because these tests cost more and fail for more environmental reasons.
- **Failure-path tests prove safe failure.** Show what happens with invalid input, timeouts, unavailable dependencies, partial work, retries, and cleanup when they apply. Assert the relevant safety contract: no corrupted data, bounded retries, a useful error, and no false success after incomplete work.
- **Expected values come from the rule, not the code.** If calculating the expected result requires rebuilding the production algorithm inside the test, use a higher-level test or real execution instead.
- **Refactor-safe tests preserve freedom to change the code.** A correct internal rewrite should keep passing when the public contract stays unchanged. Exact call order, object layout, helper names, and file structure are assertions only when consumers truly depend on them.

Reject tests that create the appearance of proof. [The prune](references/prune-tests.md) lists the common ones: tests tied to the past, to nothing, or to the implementation. Two more it does not name:

- **Fake upstream programs:** a mock that accepts the string the test expects proves string assembly against the mock. It does not prove that the real program parses the command, honours its flags, or produces the required side effect.
- **Volume as quality:** a large test count can repeat one weak assertion many times. Confidence comes from distinct contracts and realistic failure paths, not volume.

**Rule:** Test observable behaviour against a rule someone owns. Use real execution as proof when a test would only mirror the implementation.

**Why:** implementation-shaped tests give false confidence. They can pass while the real workflow is broken, then fail during a safe refactor.

## 3. Finish

### Prune tests before you call it done

- **Before you report a change as done, run [the prune](references/prune-tests.md) on the tests the change added or changed.** Include the other tests in the same test files. Delete or rewrite what it flags, and delete production code that only existed for those tests. Then run the suite again and show it green.
- **Scope it to the change, not the whole repo.** A repo-wide prune on every task fills the diff with deletions nobody asked for. Prune the whole suite only when I ask.
- **Report the result in one line:** how many tests were deleted, how many were rewritten, or "nothing to prune".

**Why:** a test that guards no behaviour still costs a run, a read, and a fix on every refactor, and it makes the suite look stronger than it is. Part 2 says which tests to write. The prune catches the ones that slipped through, while the change is still fresh.

### Review your own diff

- **For a behaviour change, load the `reviewer` skill and review your own diff before you report done.** Use its code layer: the spec, the repo standards, and production risk, as three separate axes.
- **Check the diff for test cheating:** an edited or deleted existing test, a new skip, a new test outside the allowed cases, or code that special-cases a test's input.
- **Fix every Blocker and Should-fix you can fix yourself.** Bring the rest to me as decisions, through the `question` tool.
- **Say that the review ran and what it found**, in one line per axis.
- **Skip it for a throwaway script, a config value, or a pure rename.** Showing it working is the proof there.

**Why:** the author is the cheapest reviewer, while the change is still in their head. A finding I make after you report done costs a whole extra round.

### Every PR gets a change description

- **When you open a pull request or change one, write its body with [the PR description standards](references/pr-description.md).** Do this every time, with no ask needed. This covers `gh pr create`, a PR body update after new commits, and a request to rewrite a description.
- **Do not write a free-form body first and fix it later.** Gather the facts, write the body to a file, then post it with `--body-file`, and run the render check the reference gives.

**Why:** a reviewer must understand the change before reading the diff. The reference fixes the shape: why, before and after diagrams, what changed, and proof. Every number in it comes from the code. A body written from memory gets a line count or a module name wrong, and then the reader trusts nothing in it.

## 4. By domain

Read the reference that matches the task. Tasks outside these need only parts 1 to 3.

| When the task touches | Read |
| --- | --- |
| Terraform or OpenTofu code, its tooling, or its CI | [Terraform and OpenTofu standards](references/terraform-opentofu.md): module choices, version pins, ordering and state safety, hooks, CI, and the checks before a new root's PR |
| Web UI code: HTML, CSS, components, pages, forms | [Web interface standards](references/web-interface.md): fetch the current Web Interface Guidelines and use their review format |
| Opening a PR, or changing its body | [PR description standards](references/pr-description.md), with its [template](references/pr-description-template.md) and [diagram patterns](references/pr-description-diagrams.md) |
| Finishing any change that added or changed tests | [The prune](references/prune-tests.md) |
