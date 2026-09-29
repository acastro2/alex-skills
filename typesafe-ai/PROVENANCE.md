# Provenance

Third-party skill, vendored. Do not hand-edit `SKILL.md` or `LICENSE.txt`.

| Field | Value |
| --- | --- |
| Source | https://github.com/typesafe-ai/skills |
| Upstream path | `skills/typesafe-ai/` |
| Pinned commit | `65a39f393687675ce170e6094757de20370365b9` — v0.5.7, 2026-09-12 |
| Vendored | 2026-09-29 |
| License | MIT — see `LICENSE.txt` |
| `SKILL.md` sha256 | `71ea90d7906c6554c4f4c460ef7361b2d26f59116ccdae986dc6d997b9389f52` |

Two changes to the upstream copy, both deliberate:

1. Upstream `LICENSE` is renamed `LICENSE.txt` to match this repo's skill anatomy.
2. Upstream `.claude-plugin/` and `README.md` are not vendored. This repo serves the skill to OpenCode, Pi, and Claude Code through `~/.agents/skills`.

To update: fetch the same two files at the new commit, check the `SKILL.md` sha256, then run `python3 scripts/validate_skill_graph.py`.
