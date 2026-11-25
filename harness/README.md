# harness

Rules in code, not prose: hooks for Claude Code and a plugin for OpenCode that call one core. Spec: `../docs/specs/harness-evolution.md`. UI spec: `../docs/specs/harness-office.md`.

| Path | Holds |
| --- | --- |
| `src/types.ts` | `HarnessEvent` and `Decision`, the one interface |
| `src/core.ts` | `decide(event)`: runs the policies in order |
| `src/shell/` | shell command parser and the shell and path rules |
| `src/ledger/` | SQLite storage, migrations, journal, rule registry, authority |
| `src/adapters/` | `claude.ts` (command hook entry) and the OpenCode plugin |
| `src/install.ts` | writes both tools' config from `src/manifest.ts` |
| `guard-lite.ts` | the destructive rules alone, for when the core fails |

Run the tests with `bun test` from this folder.

Merges land through the `merge_pr` tool after a fresh passkey tap on the page, or `MERGE-OK <pr>` as the first line of a prompt.
