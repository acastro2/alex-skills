# Where to Mock

Mocking is a decision about where the seams are, so the rule lives in the `code-rules` skill ("Put a seam only where the real dependency is non-deterministic or outside the process"). This file is the boundary case, in concrete terms.

## Mock at real boundaries only

A boundary is where the system meets something you do not own:

- External APIs (payment, email, identity)
- Databases, sometimes: prefer a real test database
- Time and randomness
- The filesystem, sometimes

Never mock:

- Your own classes or modules
- Internal collaborators
- Anything where you own both sides of the call

If you find yourself mocking an internal collaborator to make a test run, you are looking at a design problem, not a test problem. Either the logic under test is in the wrong place, or the module is too shallow to test through its interface.

## Do not inject by default

Matt Pocock's original advice here is "use dependency injection". That is too broad, and it contradicts the `code-rules` skill, which asks for a seam only when one of these is true:

- You genuinely need a second implementation
- You need to test how this code *interacts* with that collaborator
- The dependency is non-deterministic or outside the process

Otherwise, construct the thing directly. An interface with one implementation and no test double behind it is a maintenance cost, not flexibility.

## Design the boundary interface for mockability

This part only applies at a boundary you have already decided to create.

**Prefer a specific operation per call over one generic fetcher.** A generic fetcher forces conditional logic into the mock, so the mock stops describing the contract.

```typescript
// GOOD: each operation is independently mockable, and the mock has no branches
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: one mock has to branch on the endpoint to return the right shape
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

The specific-operations version wins on four counts:

- Each mock returns one shape, with no conditional logic in test setup
- You can see at a glance which endpoints a test exercises
- Type safety is per operation
- The interface is owned by you, so a vendor SDK change lands in one adapter instead of every test
