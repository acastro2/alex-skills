# SOURCE E: Developer repos - docs only (SECONDARY)

Documentation files (.md) across all local project folders. Does NOT search source code,
configs, or other file types.

**Path**: `~/Developer/`

Search this in the secondary sweep (after transcripts + Cortex + Obsidian). Restrict to
markdown files only.

## Strategy E1: Broad triage (.md files only)
```bash
KEYWORD="..."
rg -l -i -g '*.md' --glob '!.git' --glob '!node_modules' \
  "$KEYWORD" ~/Developer/ 2>/dev/null | head -30
```

## Strategy E2: Scoped search (when topic maps to a known project)
```bash
rg -l -i -g '*.md' "$KEYWORD" ~/Developer/<project-dir>/ 2>/dev/null
```

## Strategy E3: Architecture docs fast-path (CONTEXT.md, ADRs, READMEs)
```bash
find ~/Developer -maxdepth 4 \( -name 'CONTEXT.md' -o -name 'ADR*' -o -name 'README*' \) \
  -exec rg -li "$KEYWORD" {} + 2>/dev/null
```

## Strategy E4: Read a file for full context
Use `read` tool on the matching file path.

## Citation format
Cite as: `Developer: <repo-name>/<relative-path>:<line>` (e.g. `Developer: grafana-improvements/CONTEXT.md:42`).
