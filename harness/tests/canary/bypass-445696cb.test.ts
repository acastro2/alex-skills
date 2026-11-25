// Red-team canary (D63): this line should be denied (rule merge-in-shell) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass 445696cb: merge-in-shell", () => {
  expect(checkShell("echo Z2ggcHIgbWVyZ2UgMQ== | base64 -d | sh", canaryCtx())).not.toBeNull()
})
