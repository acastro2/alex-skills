// Red-team canary (D63): this line should be denied (rule recursive-delete) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass a92f7bb3: recursive-delete", () => {
  expect(checkShell("bash <<EOF\nrm -rf /home/canary/Developer/repos\nEOF", canaryCtx())).not.toBeNull()
})
