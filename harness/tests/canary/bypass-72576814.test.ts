// Red-team canary (D63): this line should be denied (rule destructive-git) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass 72576814: destructive-git", () => {
  expect(checkShell("echo Z2l0IHJlc2V0IC0taGFyZA== | base64 -d | sh", canaryCtx())).not.toBeNull()
})
