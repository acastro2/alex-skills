# Provenance — peekaboo skill

Pinned snapshot, not live current-source guidance.

| Field | Value |
|---|---|
| Upstream | https://github.com/openclaw/Peekaboo |
| Path | `skills/peekaboo/SKILL.md` |
| Release | v4.9.8 |
| Commit | `70dbc4183f390a5a72d5dc01d8a77eb672217070` |
| Copied | 2026-11-13 |
| CLI installed | peekaboo 4.9.8 (`brew install openclaw/tap/peekaboo`) |
| Upstream license | MIT |

`SKILL.md` is the upstream file plus two local edits:

1. The description ends with "Not for reading page content, DOM, forms, or tabs; use a browser skill for those." It keeps the router from sending page reads here.
2. The `## Asking` block after the title, which every skill in this repo carries.

Do not make other edits here; send behaviour corrections upstream. To refresh, copy
`skills/peekaboo/SKILL.md` from the new release, re-apply the two edits, and update this
table. Keep the pinned release equal to the installed CLI (`peekaboo --version`).

Upstream considers `skills/peekaboo/SKILL.md` in the Peekaboo repository the
canonical owner of Peekaboo command behaviour. A frozen copy must not be
presented as live current-source guidance.

Alternative to this snapshot: symlink to a Peekaboo checkout so updating the
checkout updates the skill. Not used here because no checkout exists on this
machine.
