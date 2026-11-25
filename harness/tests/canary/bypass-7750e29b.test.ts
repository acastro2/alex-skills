// Red-team canary (D63): this line should be denied (rule destructive-git) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass 7750e29b: destructive-git", () => {
  expect(checkShell("git branch --delete --force feat", canaryCtx())).not.toBeNull()
})
