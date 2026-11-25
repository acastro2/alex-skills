// Red-team canary (D63): this line should be denied (rule harness-self) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass 10965a94: harness-self", () => {
  expect(checkShell("echo aGFybmVzcyBvZmY= | base64 -d | sh", canaryCtx())).not.toBeNull()
})
