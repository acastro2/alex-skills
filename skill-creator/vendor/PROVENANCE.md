# Vendored upstream sources

Pinned copies of the two upstream skill-creator skills. `skill-creator/SKILL.md`
routes work to one of them. Do not edit these files.

| Source | Origin | Commit | Commit date | License |
| --- | --- | --- | --- | --- |
| Codex | `https://github.com/openai/skills.git` — `skills/.system/skill-creator/` | `49f948faa9258a0c61caceaf225e179651397431` | 2026-06-23 | Apache-2.0 |
| Claude | `https://github.com/anthropics/skills.git` — `skills/skill-creator/` | `34040c9c568585f6929bedeaad110ad08f079624` | 2026-09-10 | Apache-2.0 |

Each vendored directory keeps the upstream `LICENSE.txt`. The upstream
repositories also carry their own third-party notices; only the two
skill-creator directories are copied here.

## Why the entry file is named `CREATOR.md`

Upstream names it `SKILL.md`. OpenCode discovers **any** file named exactly
`SKILL.md` at any depth under a skill source, with dot-directories and symlinks
included. A vendored `SKILL.md` would therefore register another skill.
Renaming the vendored entry file keeps it a plain resource file.

## Refresh

`vendor/` is copied, not a submodule. To move to a newer upstream commit,
re-copy both directories, rename the new `SKILL.md` to `CREATOR.md`, drop any
`__pycache__`, update this table, and check that
`find skill-creator -name SKILL.md` still returns only the wrapper.
