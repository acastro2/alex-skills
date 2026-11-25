// Red-team canary (D63): this line should be denied (rule recursive-delete) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass cf075ee1: recursive-delete", () => {
  expect(checkShell("busybox rm -rf /home/canary/Developer/repos", canaryCtx())).not.toBeNull()
})
