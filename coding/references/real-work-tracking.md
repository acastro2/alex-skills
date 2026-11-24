# Real-work tracking

The evals show that the agent follows `coding` part 2. They do not show that the code got better. This log does. Keep it for 2 to 4 weeks, then decide.

## What to log

One row per event, in the repo's handoff file or a note in the vault:

| Date | Repo | Event | Fix changed | Tokens or cost | Note |
| --- | --- | --- | --- | --- | --- |
| 2026-11-25 | example | existing test failed | code | USD 0.40 | rule: refunds round down |

- **Event:** `existing test failed`, `bug reached review`, `bug reached production`, or `test edited`.
- **Fix changed:** `code` or `test`. A test fix needs the named rule that changed, and Alex's approval.
- **Tokens or cost:** from the session, when the host shows it.

## How to read it

- **Bugs that reach review or production go up:** bring tests back for that kind of work, and name the kind.
- **Most failing tests are fixed in the test:** the tests are tied to the implementation. Run the prune on them.
- **Cost per task goes down and bugs do not go up:** the rule works. Keep it.

**Why:** a test that fails tells you something only when the fix goes into the code. DocSpring suggests recording, for every failing test, whether the fix changed the code or the expected value ([DocSpring](https://docspring.com/blog/posts/unit-tests-ai-agents/)).
