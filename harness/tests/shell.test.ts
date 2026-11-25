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
  "recursive-delete": "Recursive delete outside the allowlist, or of a path the harness cannot see (a $VAR or $(...)). Write the literal path, or ask Alex.",
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
  ["python3 -I -c \"import json; d=json.load(open('/home/u/.claude/settings.json')); json.dump(d, open('/home/u/.claude/settings.json','w'))\"", "harness-config-write"],
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
  // canary misses (D63): wrappers, ${IFS}, heredocs, aliases, cd tracking, interpreters
  ["rm${IFS}-rf${IFS}/home/u/Developer/repos", "recursive-delete"],
  ["rm$IFS-rf$IFS/home/u/Developer/repos", "recursive-delete"],
  ["busybox rm -rf /home/u/Developer/repos", "recursive-delete"],
  ["command rm -rf /home/u/Developer/repos", "recursive-delete"],
  ["\\rm -rf /home/u/Developer/repos", "recursive-delete"],
  ["env rm -rf /home/u/Developer/repos", "recursive-delete"],
  ["nice rm -rf /home/u/Developer/repos", "recursive-delete"],
  ["timeout 5 rm -rf /home/u/Developer/repos", "recursive-delete"],
  ["bash <<EOF\nrm -rf /home/u/Developer/repos\nEOF", "recursive-delete"],
  ["sh <<'X'\nrm -rf /home/u/Developer/repos\nX", "recursive-delete"],
  ["cat <<EOF | sh\nrm -rf /home/u/Developer/repos\nEOF", "recursive-delete"],
  ["bash <<< 'rm -rf /home/u/Developer/repos'", "recursive-delete"],
  ["git -c alias.x='!rm -rf /home/u/Developer/repos' x", "recursive-delete"],
  ["cd /home/u/Developer && rm -rf repos", "recursive-delete"],
  ["cd / && rm -rf home", "recursive-delete"],
  ["cd $X && rm -rf build", "recursive-delete"],
  ["(cd /tmp && true); rm -rf build", "recursive-delete"], // the cd is scoped to the subshell
  ["python3 -c \"import shutil; shutil.rmtree('/home/u/Developer/repos')\"", "recursive-delete"],
  ["python3 -c \"import shutil,sys; shutil.rmtree(sys.argv[1])\" x", "recursive-delete"],
  ["perl -e 'use File::Path; rmtree(\"/home/u/Developer/repos\")'", "recursive-delete"],
  ["ruby -e 'require \"fileutils\"; FileUtils.rm_rf(\"/home/u/Developer/repos\")'", "recursive-delete"],
  ["node -e \"require('fs').rmSync('/home/u/Developer/repos',{recursive:true})\"", "recursive-delete"],
  ["bun -e \"require('fs').rmdirSync(p,{recursive:true})\"", "recursive-delete"],
  ["git branch --delete --force feat", "destructive-git"],
  ["git branch -d -f feat", "destructive-git"],
  ["git branch --force -d feat", "destructive-git"],
  ["git branch -df feat", "destructive-git"],
  ["cd /home/u/.local/state/harness && rm ledger.db", "ledger-write"],
  ["cd /home/u/.local/state/harness && echo x > ledger.db", "ledger-write"],
  ["cd ~/.local/state/harness; touch ledger.db", "ledger-write"],
  ["cd /home/u/.claude && echo {} > settings.json", "harness-config-write"],
]

// Decoded text piped into a shell: harness-self with its own message.
const DECODED_MSG = "Running decoded text as a shell is not allowed. Run the command itself."
const decoded = [
  "echo cm0gLXJmIC9ob21lL2NhbmFyeS9EZXZlbG9wZXIvcmVwb3M= | base64 -d | sh",
  "echo cm0gLXJmIC9ob21lL2NhbmFyeS9EZXZlbG9wZXIvcmVwb3M= | base64 -d | bash",
  "echo Z2ggcHIgbWVyZ2UgMQ== | base64 --decode | sh",
  "echo 726d202d7266202f78 | xxd -r -p | sh",
  "openssl enc -d -base64 -in x | zsh",
  "echo x | base64 -d | gunzip | dash",
  'eval "$(echo cm0gLXJmIC94 | base64 -d)"',
  'bash -c "$(base64 -d x.b64)"',
]

const allowed: Array<[string, ShellCtx?]> = [
  // Seen live: a read-only script that loads settings.json was denied as a config write.
  ["python3 -I -c \"import json; d=json.load(open('/home/u/.claude/settings.json')); print(len(d['hooks']))\""],
  ["bun -e \"console.log(require('fs').readFileSync('/home/u/.local/state/harness/ledger.db').length)\""],
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
  // Not false positives: the canary fixes must not widen the net.
  ["python3 -c \"import shutil; shutil.rmtree('/tmp/x')\""],
  ["node -e \"require('fs').rmSync('/tmp/x',{recursive:true})\""],
  ["node -e \"require('fs').rmSync(p,{force:true})\""],
  ["git branch -d feat"],
  ["git branch --delete feat"],
  ["git branch -f feat HEAD~1"],
  ["cd /tmp && rm -rf build"],
  ["cd /tmp; rm -rf build/out"],
  ["(cd /home/u && ls); rm -rf /tmp/x"],
  ["base64 -d file > out.bin"],
  ["echo aGk= | base64 -d"],
  ["echo aGk= | base64 -d | cat"],
  ["bash script.sh"],
  ["cat <<EOF > /tmp/x\nrm -rf /home/u/Developer/repos\nEOF"],
  ["git -c alias.co=checkout co main"],
  ["busybox ls -la"],
  ["echo ${IFS}"],
]

describe("checkShell", () => {
  // Every row gets a ctx: bun passes a done callback as the last argument of a short row.
  test.each(denied.map(([l, r, c]) => [l, r, c ?? ctx] as const))("denies %s", (line, ruleId, c) => {
    const hit = checkShell(line, c)
    expect(hit?.ruleId).toBe(ruleId)
    expect(hit?.message).toBe(MSG[ruleId])
  })

  test.each(decoded.map((l) => [l, ctx] as const))("denies decoded text run as a shell: %s", (line, c) => {
    const hit = checkShell(line, c)
    expect(hit?.ruleId).toBe("harness-self")
    expect(hit?.message).toBe(DECODED_MSG)
  })

  test.each(allowed.map(([l, c]) => [l, c ?? ctx] as const))("allows %s", (line, c) => {
    expect(checkShell(line, c)).toBeNull()
  })
})
