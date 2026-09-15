---
name: tdd
description: "Test-driven development, red then green, one vertical slice at a time. Use when building a feature or fixing a bug test-first, when the user asks for a red-green loop, tracer-bullet work, or integration tests, or when another skill needs the TDD procedure."
license: MIT
---

# Test-Driven Development

TDD is the red then green loop. One seam, one failing test, the minimum code to pass it, repeat.

**The rules are not here.** What a test must prove, and how to shape code so testing is possible, live in the `code-rules` skill, under "Write the test first, at a seam you agreed" and "Prove the contract through behaviour". Read those two sections before you start. They are the source of truth, and this skill does not restate them.

This skill is the procedure, plus the examples.

## Before the first cycle

Read `CONTEXT.md` if it exists, so test names and interface vocabulary match the project's domain language. Respect ADRs in the area you are touching.

Then agree the seams. Ask: "What is the public interface, and which seams should we test?" Write the seams down and get them confirmed. No test is written at an unconfirmed seam.

When the shape of that interface is itself the open question, how deep the module is, where the seam belongs, what the interface should expose, read `../codebase-design/SKILL.md`. It owns the module, interface, depth, seam, adapter, leverage, and locality vocabulary. Treat it as a reference to consult, not a session to run.

## The loop

1. **Red.** Write one test at an agreed seam. Run it. Watch it fail. If it passes, either the test is wrong or the behaviour already exists. Fix the test before you write any code.
2. **Green.** Write the minimum code that makes it pass. No speculative parameters, no hooks for a test you have not written, no "while I am here".
3. **Next slice.** Pick the next seam and return to step 1.

Refactoring is not part of this loop. It comes after green, as its own step, and the tests must still pass unchanged.

## Anti-patterns

Two of these are the ones that bite hardest in a TDD loop, and both are rejected by the `code-rules` skill for the same reason: they cannot fail when the behaviour is wrong.

- **Tautological.** The assertion recomputes the expected value the way the code does, so the test passes by construction and can never disagree with the code. Expected values must come from an independent source: a known-good literal, a worked example, the spec.
- **Implementation-coupled.** The test mocks an internal collaborator, tests a private method, or verifies through a side channel. The tell is that it breaks when you refactor while behaviour stays the same.

And the one that looks like TDD but is not:

- **Horizontal slicing.** Writing all the tests first, then all the implementation. Bulk tests verify *imagined* behaviour: you test the shape of things rather than what a caller sees, the tests go insensitive to real change, and you lock in a test structure before you understand the implementation. Work in vertical slices instead. Each test is a tracer bullet that responds to what the last cycle taught you.

## Reference

- [references/tests.md](references/tests.md): good and bad test examples.
- [references/mocking.md](references/mocking.md): where to mock, and how to design an interface that is easy to mock at a real boundary.
