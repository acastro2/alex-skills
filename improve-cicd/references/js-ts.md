# JavaScript and TypeScript

Default tools for the budgets in `improve-cicd`. Checked 2026-11-24 against Bun 1.4.5 (released 2026-11-19). Check each command against the installed version before you use it.

| Job | Command | Notes |
| --- | --- | --- |
| Install | `bun install --frozen-lockfile` | Fails if `bun.lock` and `package.json` disagree. Bun migrates `pnpm-lock.yaml` when no `bun.lock` exists ([lockfile](https://bun.sh/docs/pm/lockfile.md)) |
| Lint | `bun lint` | **Canary only** in Bun 1.4.5 ([PR #46438](https://github.com/oven-sh/bun/pull/46438)). Pin the exact canary build. It reads the existing `.oxlintrc.json` and ESLint configs; `--type-aware` uses types from `bun check` ([docs](https://bun.sh/docs/lint.md)). On stable Bun, use `bunx oxlint .` |
| Format | `bun fmt --check` | Since Bun 1.4.4: a Prettier-compatible formatter, writes nothing with `--check`. Reads Prettier and oxfmt configs. `bun format` is not this command ([v1.4.4](https://bun.sh/blog/bun-v1.4.4)) |
| Typecheck | `bun check` | Since Bun 1.4.3: a port of typescript-go 7.0.2 that reads `tsconfig.json` and emits nothing. 3.0–6.4× faster than `tsc` 7.0.2 on Bun's own runs ([v1.4.3](https://bun.sh/blog/bun-v1.4.3)) |
| Tests | `bun test --isolate=modules --randomize` | Test files keep their `vitest` imports: `import { test, expect } from "vitest"` works under `bun test`, but `vitest/node` and `vitest/config` do not ([writing tests](https://bun.sh/docs/test/writing-tests.md)) |
| Shard | `bun test --shard=2/4 --parallel` | 1-based index. `--timings` balances by recorded time ([v1.3.13](https://bun.sh/blog/bun-v1.3.13.md)) |
| Replay an order | `bun test --seed 123456` | Implies `--randomize`; the seed is printed on every random run ([test](https://bun.sh/docs/test.md)) |
| Coverage | `bun test --coverage --coverage-reporter=text --coverage-reporter=lcov` | Set `coverageThreshold` in `bunfig.toml` to fail CI; keep the `text` reporter, because an lcov-only run does not enforce the threshold ([coverage](https://bun.sh/docs/test/code-coverage)) |

## Isolation

- `--isolate=modules` gives each file a fresh module graph in one process. `--isolate` also gives each file a new global. `--parallel` runs files in worker processes and implies full `--isolate` ([parallel](https://bun.sh/docs/test/parallel.md)).
- **Measure `--parallel` against the single process.** It wins when files spend time in I/O or real work. For many fast files that import the same large graph, one process is faster, and Bun prints the timing after every run.
- Random order finds shared state. It does not fix it: reset state after every file.

## What to delete

Delete npm, yarn, pnpm, Prettier, ESLint, oxlint, Vitest, and Jest once bun covers them. Before each removal, run old and new side by side and list what the new one misses:

- **ESLint:** Oxlint covers more than 800 rules, not every plugin ([migrate](https://oxc.rs/docs/guide/usage/linter/migrate-from-eslint)). Keep ESLint only for a rule nothing else has.
- **Prettier:** compare the formatted diff on the whole repo first. Prettier plugins are not supported by oxfmt, and Bun's formatter ports Prettier but plugins still need a check.
- **Vitest:** list every `vitest/*` import and config feature the suite uses.

## TypeScript 7 without Bun

TypeScript 7.0 shipped 2026-07-08: the native port is the `typescript` package and its binary is `tsc`, not `tsgo`. It is 8–12× faster than TypeScript 6 in Microsoft's builds; `--checkers N` sets the worker count (default 4). It has no stable programmatic API yet, so tools that embed the compiler may still need TypeScript 6 ([TypeScript 7.0](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/)).

```bash
npx tsc --noEmit --checkers 8
```

## Test selection

No built-in "tests the diff can reach" command was verified for `bun test`. Build the list from the import graph (or the monorepo tool's affected command), list the inputs that rerun everything, and prove it goes red on a hidden change, as the skill says.
