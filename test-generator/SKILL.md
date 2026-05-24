---
name: test-generator
description: Generate refactoring-safe tests that validate intent and observable outcomes (contracts, user-visible behavior, business rules) instead of implementation details. Use when adding/fixing unit, integration, or e2e tests; when translating requirements/bugs into scenarios; or when assessing test gaps and proposing the smallest high-confidence test set that matches existing repo conventions.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: testing
---

# Test Generator (behavior-first)

## Operating rules

- Test observable behavior (contracts and outcomes), not internal structure.
- Follow existing repo conventions: framework, helpers, file layout, naming, fixtures.
- Prefer the lowest-cost test that gives high confidence:
  - unit for pure business rules, integration for boundaries, e2e for true journeys.
- Make tests deterministic: control time, randomness, and external I/O.
- Write actionable failures: assertions should explain what broke and why it matters.

## Intake (ask early)

- What’s the goal: prevent regression, reproduce a bug, or document intended behavior?
- What is the “public surface”: API endpoint, CLI command, UI screen, job handler?
- What are the inputs and expected outputs/side effects?
- What systems are involved: DB, cache, queue, external API, filesystem?
- What test types exist already (unit/integration/e2e) and what framework?

## Workflow

### 1) Discover the test harness

- Locate existing tests and patterns:
  - directories: `tests/`, `__tests__/`, `spec/`, `cypress/`, `playwright/`, `e2e/`
  - configs: `jest.config.*`, `vitest.config.*`, `pytest.ini`, `pyproject.toml`, `go.mod`, `Cargo.toml`
- Reuse existing helpers (factories, fixtures, test DB, request clients).

Suggested searches:

```bash
rg -n "jest|vitest|mocha|pytest|unittest|playwright|cypress" .
rg -n "factory|fixture|test\s*utils|mock\b|seed" .
rg -n "describe\(|it\(|test\(" .
```

### 2) Choose the test level (pick one primary)

- Unit test when:
  - pure function/business rule, no I/O, cheap to run.
- Integration test when:
  - crossing boundaries (HTTP↔service↔DB), serialization, auth, transactions.
- E2E test when:
  - validating a real user journey across multiple components.

Rule of thumb: if a unit test would require heavy mocking to be meaningful, consider integration instead.

### 3) Derive scenarios from the contract

For each target behavior, write 1–3 scenarios in Given/When/Then:

- Given <context/state>
- When <action>
- Then <observable outcome(s)>

Include:

- happy path
- one realistic edge case
- one failure mode (permissions/validation/timeout)

### 4) Pick assertions that survive refactors

Prefer assertions on:

- API: status codes, response body, headers, error shape
- DB: persisted state changes (via public query/read path)
- events: message published, job enqueued, webhook sent (observable)
- UI: text, enabled/disabled state, navigation, visible errors

Avoid assertions on:

- private methods, internal caches, call counts to implementation-private collaborators
- exact log text (unless logs are the contract)
- DOM structure that isn’t user-visible (frontend)

### 5) Implement the test (AAA)

Use Arrange/Act/Assert with a business-first name.

```ts
// Arrange: set up state as the user/system would see it
// Act: perform one action
// Assert: verify the observable outcome(s)
```

Guidelines:

- Keep one primary assertion theme per test.
- Prefer table-driven tests for many inputs/outputs of the same rule.
- Use realistic data; avoid magic constants without meaning.

### 6) Control flakiness sources

- Time: freeze/mock clock; avoid `sleep`.
- Randomness: seed RNG or inject deterministic IDs.
- Concurrency: await async work; assert eventual consistency with bounded retries.
- External I/O: use test doubles at the boundary, not deep mocks.

### 7) Run the smallest relevant tests

- Run the test file/suite you touched first; widen only as needed.
- If failures reveal missing setup (DB migration, fixtures), fix the harness, not the assertions.

## What to test vs. what not to test

### Do test

- Public API contracts: input → output
- Business rules: domain outcomes and invariants
- Permission rules: allow/deny behaviors
- Error behavior: correct error type/status and user-visible message
- Integration boundaries: serialization, persistence, external calls (at a seam)

### Don’t test

- private/internal state
- framework internals
- “coverage for coverage’s sake”

## Examples (behavior-focused)

### Backend/business rule (Python)

```python
# test: users can’t complete orders without payment

def test_complete_order_requires_payment(client, order_factory):
    order = order_factory(status="pending", paid=False)

    resp = client.post(f"/orders/{order.id}/complete")

    assert resp.status_code == 409
    assert resp.json["error"] == "payment_required"
```

### Frontend (React Testing Library)

```ts
it("disables checkout when cart is empty", () => {
  render(<CheckoutButton cart={[]} />)
  expect(screen.getByRole("button", { name: /checkout/i })).toBeDisabled()
})
```

### Integration (HTTP + persistence)

- Assert both the response and the persisted state change.
- Prefer reading state back through a public query/API.

## Anti-patterns (quick checks)

- Over-mocking: mocks nested inside mocks to make a unit test “work”.
- Brittle assertions: checking exact DOM structure, internal call counts, or private fields.
- Multi-purpose tests: one test verifies five unrelated outcomes.

Bad:

```ts
expect(obj._internalCache).toHaveLength(3)
```

Better:

```ts
expect(obj.get("key")).toBe("value")
```

## Quality checklist

- [ ] Test name states behavior (what/when/then)
- [ ] Assertions are on observable outcomes
- [ ] Test survives refactoring without behavior change
- [ ] Flakiness sources controlled (time/randomness/I\O)
- [ ] Includes at least one failure mode for risky behavior
- [ ] Uses existing repo patterns and helpers
