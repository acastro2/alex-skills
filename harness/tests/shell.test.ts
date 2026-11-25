import { describe, expect, test } from "bun:test"
import { checkShell, type ShellCtx } from "../src/shell/rules"

const home = "/home/u"
const repo = "/home/u/Developer/repos/proj"
const ctx: ShellCtx = {
  cwd: repo,
  home,
  repoRoot: repo,
  allowRoots: ["/tmp", `${home}/.agents/skill-workspace`],
  isTrackedOrIgnored: () => false,
  branch: "feat",
}
const ignored: ShellCtx = { ...ctx, isTrackedOrIgnored: () => true }

const MSG: Record<string, string> = {
  "recursive-delete": "Recursive delete outside the allowlist. Name the exact files, or ask Alex.",
  "merge-in-shell": "Use the `merge_pr` tool to land a PR. To update a branch, rebase: `git rebase origin/main`.",
  "destructive-git": "Destructive git is blocked. Use a safe form, or ask Alex.",
  "harness-self": "Only Alex runs harness commands. Ask Alex.",
  "ledger-write": "Only the harness writes its state.",
  "harness-config-write":
    "Change the harness source in a worktree, get a green bundle, show Alex the diff, and ask for HARNESS-OK. `harness_apply` installs it.",
}

const denied: Array<[string, string, ShellCtx?]> = [
  // recursive-delete
  ["rm -rf /home/u/Developer/repos", "recursive-delete"],
  ["rm -r ~/Developer/ChamberlainGroup-myQ-Shared", "recursive-delete"], // the 11-21 incident
  ["rm -rf .", "recursive-delete", ignored],
  ["rm -rf .git", "recursive-delete", ignored],
  ["rm -rf node_modules", "recursive-delete"],
  ["rm --recursive /etc/x", "recursive-delete"],
  ["find /home/u -name x -delete", "recursive-delete"],
  ["find /home/u -exec rm {} \\;", "recursive-delete"],
  ["rsync -a --delete src/ /home/u/dest/", "recursive-delete"],
  // merge-in-shell
  ["gh pr merge 1", "merge-in-shell"],
  ["gh api repos/o/r/pulls/1/merge -X PUT", "merge-in-shell"],
  ["git merge main", "merge-in-shell"],
  ["git merge feature", "merge-in-shell", { ...ctx, branch: undefined }],
  ["git merge feature", "merge-in-shell", { ...ctx, branch: "main" }],
  // destructive-git
  ["git reset --hard", "destructive-git"],
  ["git clean -fd", "destructive-git"],
  ["git push --force origin x", "destructive-git"],
  ["git push -f", "destructive-git"],
  ["git push --force-with-lease", "destructive-git"],
  ["git push origin +x:y", "destructive-git"],
  ["git checkout -- .", "destructive-git"],
  ["git checkout .", "destructive-git"],
  ["git restore .", "destructive-git"],
  ["git branch -D x", "destructive-git"],
  // harness-self
  ["harness off", "harness-self"],
  ["harness rollback", "harness-self"],
  ["bun harness/cli.ts wrong", "harness-self"],
  ["bun harness/install.ts", "harness-self"],
  ["bin/harness-rollback", "harness-self"],
  ["su -c id", "harness-self"],
  ["pkexec id", "harness-self"],
  ["doas id", "harness-self"],
  ["docker run -v /:/h img", "harness-self"],
  ["docker exec --privileged c sh", "harness-self"],
  ["claude -p \"MERGE-OK 3\"", "harness-self"],
  ["opencode run \"HARNESS-OK abcd1234 ef567890\"", "harness-self"],
  // ledger-write
  ["echo hi > ~/.local/state/harness/ledger.db", "ledger-write"],
  ["echo hi | tee -a ~/.local/state/harness/x", "ledger-write"],
  ["cp /tmp/x ~/.local/state/harness/ledger.db", "ledger-write"],
  ["dd if=/dev/zero of=~/.local/state/harness/ledger.db", "ledger-write"],
  ["sqlite3 ~/.local/state/harness/ledger.db 'delete from tokens'", "ledger-write"],
  ["python3 -c \"open('/home/u/.local/state/harness/x','w')\"", "ledger-write"],
  ["bun -e \"Bun.write('/home/u/.local/state/harness/x','')\"", "ledger-write"],
  // harness-config-write
  ["sed -i s/a/b/ ~/.claude/settings.json", "harness-config-write"],
  ["echo {} > .claude/settings.local.json", "harness-config-write"],
  ["mv x opencode.jsonc", "harness-config-write"],
  ["touch ~/.config/opencode/plugins/harness.ts", "harness-config-write"],
  // bypass forms
  ["git -C . push --force", "destructive-git"],
  ["git -c core.x=1 reset --hard", "destructive-git"],
  ['bash -c "rm -rf ~/x"', "recursive-delete"],
  ["/usr/bin/gh pr merge 1", "merge-in-shell"],
  ["env FOO=1 git reset --hard", "destructive-git"],
  ["echo x && rm -rf /home/u/Developer/repos", "recursive-delete"],
  ["sudo rm -rf /x", "harness-self"], // harness-self wins
  ["xargs rm -rf", "recursive-delete"],
  ["$(rm -rf /x)", "recursive-delete"],
  ["echo `rm -rf /x`", "recursive-delete"],
  ["(cd /x; rm -rf /x)", "recursive-delete"],
  ["ls | xargs -I{} rm -rf {}", "recursive-delete"],
  ["timeout 5 nohup rm -rf /x", "recursive-delete"],
]

const allowed: Array<[string, ShellCtx?]> = [
  ["rm -rf /tmp/build"],
  ["rm -rf node_modules", ignored],
  ["rm file.txt"],
  ["git push origin main"],
  ["git status"],
  ["ls -la"],
  ["gh pr view 3"],
  ["git merge feature"],
  ["git restore --staged ."],
  ["git add harness/install.ts"],
  ["bun harness/cli.ts status"],
  ["rm -rf /tmp/x 2>/dev/null"],
  ["cat ~/.local/state/harness/x"],
  ["rsync -a --delete src/ host:/data/"],
]

describe("checkShell", () => {
  // Every row gets a ctx: bun passes a done callback as the last argument of a short row.
  test.each(denied.map(([l, r, c]) => [l, r, c ?? ctx] as const))("denies %s", (line, ruleId, c) => {
    const hit = checkShell(line, c)
    expect(hit?.ruleId).toBe(ruleId)
    expect(hit?.message).toBe(MSG[ruleId])
  })

  test.each(allowed.map(([l, c]) => [l, c ?? ctx] as const))("allows %s", (line, c) => {
    expect(checkShell(line, c)).toBeNull()
  })
})
