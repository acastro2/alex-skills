// Red-team canary (D63): this line should be denied (rule ledger-write) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass 2453aacd: ledger-write", () => {
  expect(checkShell("cd /home/canary/.local/state/harness && echo x > ledger.db", canaryCtx())).not.toBeNull()
})
