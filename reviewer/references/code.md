# Code layer: PRs, branches, diffs

Read `../../code-rules/SKILL.md` and the repo's own rules (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, standards docs) first. The repo wins over everything here. If a team standards skill is available (for example `attain-standards`, or `attain-change-control` for anything that ships to production at Attain), load it too.

## Pin the diff

A diff file, a patch, or a PR number the user gave is the target: review it directly and skip the git steps below. Otherwise review against a fixed point the user named: a branch, SHA, tag, or `main`. If none is named, ask. Compare against the merge-base, and fail early on a bad ref or an empty diff:

```bash
git rev-parse <fixed-point>
git diff <fixed-point>...HEAD
git log <fixed-point>..HEAD --oneline
```

If there is a PR, also read its description and existing comments (`gh pr view --comments`), and check that earlier comments were addressed.

Look for: the intent and user impact, the risk areas (auth, money, data writes, migrations, external APIs), the rollout and rollback plan, and what tests were run. Do not stop to ask for them. Note each one you cannot find as **Worth checking** under the axis it affects. Stop and ask only when the goal of the change itself is unknown.

## Three axes, kept separate

Review the same diff three times and report each axis under its own heading. Do not merge them or rank across them: code can follow every standard and still build the wrong thing, or do exactly what the ticket said and still be unsafe to ship.

1. **Spec.** Find the work item: references in commit messages (`AB#1234`, `#45`), a path or URL the user gave, or a spec under `docs/` or `specs/`. At Attain, work items live in Azure DevOps: fetch the item with the Azure DevOps connector if this session has it, or the `ado` agent, and read the description, the acceptance criteria, and the comments. If neither is available, ask the user to paste the item. Report what was asked but is missing or partial, what was built but not asked for, and what looks implemented but wrong. Quote the work item line for each. If there is no spec, say so and skip the axis.
2. **Standards.** Every place the diff breaks a documented repo standard (cite the rule), plus any smell from the baseline below. Documented breaches can be hard violations. Smells are always judgment calls.
3. **Production risk.** What breaks in production. Blockers first:
   - 🚨 Security and privacy: authz bypass, injection, secrets, personal data in logs or responses.
   - 🚨 Data loss or corruption: multi-step writes with no transaction, unsafe deletes, broken migrations.
   - 🚨 Breaking contract changes with no versioning or migration path. Wrong logic, missing validation.
   - ⚠️ Silent failures, no timeouts, retries with no backoff, no idempotency.
   - ⚠️ Unbounded reads, N+1 queries, hot-path complexity.
   - ⚠️ No logs, metrics, or traces for the failure you can already imagine.
   - 💡 Small operational gaps: a missing log field, a vague error message. Code smells (naming, duplication, coupling) belong to Standards, not here. The three Nice-to-have limit is for the whole review, not per axis.

Then check tests against risk: critical paths, permissions, and error cases covered, and tests that assert behavior, not implementation.

For a large diff, run Spec and Standards as two read-only subagents in parallel (`Explore` in Claude Code, `scout` in OpenCode or Pi) and keep Production risk in the main thread. Give each subagent the diff command, the commit list, and everything it needs, because it cannot see this conversation.

## Verify before you assert

- Trace the path before you call it a bug. Read callers and callees. Cite the lines that prove it.
- Check these before you claim them. Reviewers get them wrong often:
  - "This never returns": an early return in a caller may stop that path.
  - "This error is not handled": the caller may handle it.
  - "This is unused": reflection, serialization, or framework wiring may use it.
  - "This is always true": guards or type narrowing upstream may change that.
  - "Missing null check": earlier validation may guarantee a value.
- Statements like "never", "always", and "impossible" need proof you would bet money on. If you would not, ask: "Is it intentional that X happens when Y?"

## Smell baseline

Fowler's code smells, as judgment calls. Suppress any the repo endorses or tooling already enforces. Name it as "possible <smell>" and quote the hunk.

| Smell | Fix |
| --- | --- |
| Mysterious name | Rename. If no honest name comes, the design is unclear. |
| Duplicated code | Extract the shared shape and call it from both places. |
| Feature envy | Move the method next to the data it uses. |
| Data clumps | The same fields travel together: make them one type. |
| Primitive obsession | Give the domain concept its own small type. |
| Repeated switches | Same branching on the same type in several places: one map or polymorphism. |
| Shotgun surgery | One change, edits everywhere: gather what changes together. |
| Divergent change | One module edited for unrelated reasons: split it. |
| Speculative generality | Hooks or parameters for needs nobody has: delete and inline. |
| Message chains | Long `a.b().c().d()` walks: hide the walk behind one method. |

## Output additions

Under the verdict line, add the fixed point used. Then report **Spec**, **Standards**, and **Production risk** as their own sections, each with its own Blocker, Should-fix, and Nice-to-have findings. An axis with no findings is one line ("Standards: nothing found"), not a section, so a small diff gets a small review. For each risk finding give: the risk, a concrete failing scenario, and the fix. End with one line: finding count per axis and the worst issue in each.
