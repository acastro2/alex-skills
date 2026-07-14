---
name: pr-reviewer
description: Review pull requests for production readiness behavioral correctness, security/privacy, data safety, resilience, performance, observability, and maintainability. Use when asked to review a PR diff/branch/changeset and produce actionable feedback with clear severity (blocker/should-fix/nit), concrete scenarios, and file references; include rollout and migration risk assessment.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: code-review
---

# PR Reviewer

## Operating rules

- Be risk-driven: focus on what can break in production.
- Prefer correctness and safety over style; let linters handle formatting.
- Don't invent repo behavior; cite evidence from the diff and code.
- Provide actionable feedback: risk → failing scenario → suggested fix.
- Match the team's tone and conventions; be direct and respectful.
- Judge against the Attain engineering baseline: load the `attain-standards` skill for the team's code-style, testing, GitHub, and OpenTofu conventions, and flag deviations from it.

### Verify before asserting

- **Never claim code is wrong without tracing the actual path.** If you say "this will never return" or "this logic is incorrect," you must cite the specific lines that prove it.
- **Read callers and callees before judging.** A function might look incomplete in isolation but be correct in context. Check how it's used.
- **If you can't verify, hedge.** Use "potential issue" or "worth verifying" instead of stating something is definitely broken.
- **Assume the author might know something you don't.** Complex logic often has non-obvious reasons. Ask before condemning.

## Intake (ask early if missing)

- What is the intent and user impact of this PR?
- What are the rollout and rollback plans? Any feature flags?
- What are the risk areas? (auth, money, data writes, migrations, external APIs)
- Any known edge cases, incidents, or tickets linked?
- What tests were run (unit/integration/e2e) and what's covered?

## Workflow

### 1) Gather context

Use whichever tools are available.

```bash
# If using GitHub CLI

gh pr view

gh pr diff

gh pr view --comments

# Locally

git log --oneline --decorate -20

git diff --stat

git diff
```

### 2) Triage changes (what changed and where)

- Identify the primary surface area:
  - API routes/handlers, background jobs, migrations, config, infra, UI.
- Identify blast radius:
  - "Who calls this?" "What data does it touch?" "What permissions are involved?"
- Look for high-risk markers:
  - auth, billing, data writes, concurrency, retries, caches, schema changes.

### 2b) (Optional) Delegate to elder-knowledge for graph-backed blast-radius analysis

> **Note:** `elder-knowledge` and its blast-radius MCP server are **not bundled in this plugin** — they're a separate, optional capability. If the subagent isn't available, skip this step and do the blast-radius reasoning manually (step 2a covers the heuristics). Don't block the review on it.

For non-trivial PRs (exported APIs, cross-repo shared code, schema changes), delegate
graph investigation to the `elder-knowledge` subagent *if it exists in this environment*.
When present, it owns the blast-radius tools exclusively.

**When to delegate:**
- Changed files export public symbols consumed elsewhere
- The PR touches shared libraries, SDKs, or API contracts
- Schema/migration changes that downstream services depend on
- More than a handful of files changed across module boundaries

**When to skip (bypass the subagent):**
- Typo/comment/formatting-only changes
- Single-file leaf changes with no exports
- Test-only changes
- The blast-radius MCP server is known-offline or unindexed for the repo

**How to delegate:**
Invoke via the task tool with `subagent_type: "elder-knowledge"`, or use
`@elder-knowledge` if the task tool doesn't expose it. Pass context EXPLICITLY
(the subagent cannot see this conversation):

```
@elder-knowledge Produce a severity-ranked blast-radius briefing for this PR.

Changed files:
<paste file list from git diff --stat>

Diff (or resolved symbols):
<paste unified diff or summarized symbol changes>
```

**Consuming the briefing:**
- Treat CRITICAL/HIGH findings as required review checkpoints.
- For each co-change gap, confirm the PR handles it or flag it with the owner.
- If the briefing says NO DATA / stale index, note in your review that blast-radius
  could not be verified for those symbols: do not assume "safe."
- Incorporate the briefing findings into your final review under a
  "### Blast-Radius Risk" section.

### 3) Review by priority (blockers first)

#### A. Blockers (do not merge)

- Security/privacy issues: authz bypass, injection, secrets, unsafe deserialization, PII leakage.
- Data loss/corruption: non-atomic multi-step writes, unsafe deletes, broken migrations.
- Breaking changes: incompatible API/contract changes without versioning/migration path.
- Incorrect behavior: obviously wrong logic, missing validation, incorrect error codes.

#### B. Should-fix (before or soon after merge)

- Error handling and resilience: silent failures, missing retries/backoff where needed, no timeouts.
- Performance: N+1 queries, unbounded reads/writes, O(n²) on hot paths, missing indexes.
- Observability: missing critical logs/metrics/traces, no context for debugging.
- Operational safety: config defaults unsafe, rate limits missing, no idempotency.

#### C. Nice-to-have

- Maintainability: unclear naming, hard-to-test coupling, duplication, overly complex functions.
- Developer UX: missing docs for non-obvious behavior, unclear error messages.

### 4) Check tests and verification

- Confirm coverage aligns with risk:
  - critical paths, permissions, error cases, edge cases, integrations.
- Avoid tests that are tightly coupled to implementation when behavior assertions are possible.

Language note (only if applicable):

- Go tests belong in `*_test.go` in the same package/directory as the code under test (common convention).

### 5) Check history and previous review feedback

```bash
# History for intent and risk

git log -p -- path/to/file

git blame path/to/file

# Previous PR comments

gh pr view --comments
```

- Verify previous comments are addressed or explicitly deferred with rationale.

## Common red flags (examples)

- Injection risk (string interpolation in queries)
- Missing authorization checks on privileged operations
- Destructive operations without guardrails (confirmation, scoping, soft-delete)
- Multi-step write flows without transactions or compensating actions
- Swallowing errors:

```ts
try { await doImportantThing() } catch {}
```

- Unbounded reads/writes:

```ts
await db.users.findMany() // no filters/limit on hot path
```

- N+1 patterns (looping over async fetches)

## Common false positives to avoid

Before asserting something is wrong, check these patterns where reviewers often get it wrong:

- **"This code path never returns"** — Did you check all callers? Early returns in callers may prevent the problematic path.
- **"This error isn't handled"** — Did you check the caller? Errors are often handled one level up.
- **"This variable is never used"** — Did you check for reflection, serialization, or framework magic?
- **"This condition is always true/false"** — Did you trace all the ways the input can arrive? Type narrowing and guards may not be obvious.
- **"This function should return X"** — Did you understand the contract? The behavior may be intentional for edge cases.
- **"Missing null check"** — Did you verify the value can actually be null at that point? Earlier validation may guarantee it's set.

When in doubt, frame as a question: "Is it intentional that X happens when Y?" rather than "Bug: X happens when Y."

## Review output template

```markdown
## PR Review: <title>

### Summary
<What changed + overall assessment>

### Blast-Radius Risk
<Include if elder-knowledge briefing was obtained>
- Overall risk: <from briefing>
- Key findings: <severity-ranked, from briefing>
- Co-change gaps: <absent-but-historically-coupled files, with owners>
- Owners to involve: <teams/people from briefing>
- Data quality: <any NO DATA / stale-index caveats>

### Blockers
- <Issue> — `path/to/file.ext:line`
  - Risk: <what goes wrong>
  - Scenario: <concrete failing example>
  - Suggestion: <specific fix>

### Should-fix
- ...

### Nice-to-have
- ...

### Test / Verification Notes
- Coverage: <what is tested / missing>
- Risk areas: <what deserves extra confidence>

### Previous Comments
- <comment link/summary>: <addressed / partially / not addressed>

### Positive Highlights
- <what was done well>
```

## Feedback writing guidance

- Prefer "because" explanations tied to production impact.
- Propose a concrete next step:
  - code change suggestion
  - test to add
  - monitoring/alert to include
  - rollout/flagging strategy

### Confidence levels

Use explicit confidence markers based on how much you've verified:

| Marker | Meaning | When to use |
|--------|---------|-------------|
| **Confirmed** | Traced the code path, certain this is wrong | You read the relevant files and can cite exact lines |
| **Likely issue** | Strong evidence but couldn't fully verify | Missing context but pattern is suspicious |
| **Worth checking** | Potential issue, needs author input | You're unsure; asking is better than asserting |

### Examples

```markdown
Instead of: "This could cause issues."
Say: "If `user.email` is null, this throws at `...:45`. Add validation upstream or guard here."

Instead of: "Refactor this."
Say: "Extract `validatePayment()` so the rules can be unit-tested and reused in <other call site>."

Instead of: "This will never return a value." (unverified assertion)
Say: "**Worth checking:** I don't see where `getValue()` returns for the empty case — is this handled by the caller at `consumer.ts:23`?"
```

## Self-review before finalizing

Before presenting your review, verify your own assertions:

1. **For each blocker/should-fix:** Can you cite the specific line numbers that prove it? If not, downgrade confidence or gather more context.
2. **Challenge yourself:** "What would make this actually correct?" — if there's a plausible answer, ask instead of assert.
3. **Re-read your claims:** Would you bet money on each assertion? If not, hedge it.
4. **Check for overconfidence:** Statements like "will never," "always fails," "impossible" require ironclad evidence.

## Final checklist (before approving)

- [ ] No authz/authn regressions; secrets not exposed
- [ ] Data writes are safe (transactions/idempotency/guardrails)
- [ ] Breaking changes are intentional and documented
- [ ] Error handling is explicit; timeouts/retries are sensible
- [ ] Performance implications are understood (hot paths, queries)
- [ ] Observability exists for failures and key operations
- [ ] Tests align with risk; critical paths and edge cases covered
- [ ] Rollout/rollback plan is reasonable
