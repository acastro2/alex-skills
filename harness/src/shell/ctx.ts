// The real-world ShellCtx for a cwd: repo root, branch, allowlist roots and the git
// tracked-or-ignored test. Shared by guard-lite, the adapters' failure mode and the core.
import { homedir, tmpdir } from "node:os"
import type { ShellCtx } from "./rules"

function git(args: string[], cwd: string): { ok: boolean; out: string } {
  try {
    const r = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "ignore" })
    return { ok: r.exitCode === 0, out: r.stdout.toString().trim() }
  } catch {
    return { ok: false, out: "" }
  }
}

export const DESTRUCTIVE = ["recursive-delete", "merge-in-shell", "destructive-git"] as const

export function shellCtx(cwd: string, only?: readonly string[]): ShellCtx {
  const home = process.env.HOME || homedir()
  const top = git(["rev-parse", "--show-toplevel"], cwd)
  const repoRoot = top.ok && top.out ? top.out : null
  const branch = git(["symbolic-ref", "--short", "-q", "HEAD"], cwd)
  const roots = [tmpdir(), "/tmp", `${home}/.agents/skill-workspace`]
  if (process.env.TMPDIR) roots.push(process.env.TMPDIR)
  return {
    cwd,
    home,
    repoRoot,
    allowRoots: roots,
    branch: branch.ok && branch.out ? branch.out : undefined,
    isTrackedOrIgnored: (p) =>
      !!repoRoot && (git(["ls-files", "--error-unmatch", "--", p], repoRoot).ok || git(["check-ignore", "-q", "--", p], repoRoot).ok),
    only,
  }
}
