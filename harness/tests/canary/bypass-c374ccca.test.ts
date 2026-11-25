// Red-team canary (D63): this line should be denied (rule recursive-delete) but the guard lets it through.
// Fix the guard in src/shell. Do not edit or delete this test.
import { expect, test } from "bun:test"
import { canaryCtx } from "../../src/jobs/canary.ts"
import { checkShell } from "../../src/shell/rules.ts"

test("canary bypass c374ccca: recursive-delete", () => {
  expect(checkShell("ruby -e 'require \"fileutils\"; FileUtils.rm_rf(\"/home/canary/Developer/repos\")'", canaryCtx())).not.toBeNull()
})
