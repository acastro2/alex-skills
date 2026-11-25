import { expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const script = resolve(dirname(fileURLToPath(import.meta.url)), "../bin/fork-tab");

function tmp(prefix: string): string {
  return mkdtempSync(join(tmpdir(), prefix));
}

// Minimal env: no REX_SESSION, HERDR_ENV, or session IDs leak in from the caller.
function envWithHome(home: string): Record<string, string> {
  return { PATH: process.env.PATH ?? "", HOME: home };
}

function dryRun(cwd: string, home: string) {
  return spawnSync(
    script,
    ["--dry-run", "--tool", "opencode", "--session", "ses_TEST", "--", "try", "plan", "B"],
    { cwd, env: envWithHome(home), encoding: "utf8" },
  );
}

function git(repo: string, home: string, args: string[]) {
  const r = spawnSync("git", ["-c", "user.name=t", "-c", "user.email=t@t", ...args], {
    cwd: repo,
    env: envWithHome(home),
    encoding: "utf8",
  });
  expect(r.status).toBe(0);
}

test("inside a git repo, the dry run plans a worktree under ~/.worktrees/<repo>/, the fork, and the Rex tab", () => {
  const home = tmp("fork-home-");
  const repo = join(tmp("fork-root-"), "fork-proj");
  mkdirSync(repo);
  git(repo, home, ["init", "-q"]);
  git(repo, home, ["commit", "-q", "--allow-empty", "-m", "init"]);

  const r = dryRun(repo, home);
  expect(r.status).toBe(0);

  const lines = r.stdout.split("\n");
  const worktree = `/.worktrees/${basename(repo)}/try-plan-b`;
  expect(lines.some((l) => l.includes("worktree add -b fork/try-plan-b") && l.includes(worktree))).toBe(true);
  // Seen live 2026-11-25: `run --fork` kept the source's location; the fork must move into its worktree.
  expect(lines.some((l) => l.includes("/move") && l.includes(worktree))).toBe(true);
  expect(r.stdout).toContain("opencode api post /api/session/ses_TEST/fork");
  expect(lines.some((l) => /rex window new .*--focus=false/.test(l))).toBe(true);
  expect(existsSync(join(home, ".worktrees"))).toBe(false);
});

test("outside a git repo, the dry run plans no worktree", () => {
  const home = tmp("fork-home-");
  const dir = tmp("fork-plain-");

  const r = dryRun(dir, home);
  expect(r.status).toBe(0);
  expect(r.stdout).not.toContain("worktree add");
  expect(r.stdout).toContain("opencode api post /api/session/ses_TEST/fork");
  expect(r.stdout).toContain("--focus=false");
});
