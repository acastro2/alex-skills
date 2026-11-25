// Red-team canary (D63): this line should be denied (rule recursive-delete) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass 8d8e8838: recursive-delete", () => {
  expect(checkShell("echo cm0gLXJmIC9ob21lL2NhbmFyeS9EZXZlbG9wZXIvcmVwb3M= | base64 -d | sh", canaryCtx())).not.toBeNull()
})
