// Red-team canary (D63): this line should be denied (rule ledger-write) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass 03b59d37: ledger-write", () => {
  expect(checkShell("echo ZWNobyB4ID4gL2hvbWUvY2FuYXJ5Ly5sb2NhbC9zdGF0ZS9oYXJuZXNzL2xlZGdlci5kYg== | base64 -d | sh", canaryCtx())).not.toBeNull()
})
