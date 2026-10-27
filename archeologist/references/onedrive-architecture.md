# SOURCE F: OneDrive Architecture (SECONDARY)

Formal architecture documents: ADRs, Solution Architecture Docs (SAD), Security Improvement
Plans (SIP), tech briefs, GenAI policy, and templates.

**Path**: discovered, never hardcoded. The mount folder carries the tenant name, which differs per person and changes when the tenant is renamed, so resolve it once per session:

```bash
ARCH_DIR=$(ls -d "$HOME"/Library/CloudStorage/OneDrive-*/"Architecture - Documents" 2>/dev/null | head -1)
[ -n "$ARCH_DIR" ] || ARCH_DIR=$(ls -d "$HOME"/OneDrive*/OneDrive*/"Architecture - Documents" 2>/dev/null | head -1)
[ -n "$ARCH_DIR" ] || ARCH_DIR=$(ls -d "$HOME"/OneDrive*/"Architecture - Documents" 2>/dev/null | head -1)
[ -n "$ARCH_DIR" ] || echo "No OneDrive Architecture folder; list $HOME/Library/CloudStorage" >&2
```
(The `Architecture-Architects Internal - Documents/` folder is a mirror; skip it to avoid dupes.)

## Strategy F1: Search markdown/text files (fast)
```bash
# ARCH_DIR comes from the discovery block above; rerun it if this is a new shell
[ -n "$ARCH_DIR" ] || { echo "Set ARCH_DIR first (see Path above)" >&2; return 1 2>/dev/null || exit 1; }
rg -l -i "$KEYWORD" "$ARCH_DIR" 2>/dev/null
```

## Strategy F2: Search .docx files (extract text on the fly)
```bash
# ARCH_DIR comes from the discovery block above; rerun it if this is a new shell
[ -n "$ARCH_DIR" ] || { echo "Set ARCH_DIR first (see Path above)" >&2; return 1 2>/dev/null || exit 1; }
find "$ARCH_DIR" -name '*.docx' -exec sh -c \
  'textutil -convert txt -stdout "$1" 2>/dev/null | grep -qi "$2" && echo "$1"' _ {} "$KEYWORD" \;
```

## Strategy F3: Read a .docx file
```bash
textutil -convert txt -stdout "$FILE"
```

## Known document patterns
- `ADR-XXXX-kebab-title.docx` (Architecture Decision Records)
- `SAD-*.docx` (Solution Architecture Documents)
- `SIP-*.docx` (Security Improvement Plans)
- Tech briefs: `<topic>-tech-brief.{docx,md}` pairs
- GenAI policy: `*GenAI Policy*.docx`, `*-genai-standard.md`
- Templates: `ADR_Template.docx`, `Solution-Architecture-Document-Template.docx`

## Citation format
Cite as: `OneDrive/Architecture: <filename>` (e.g. `OneDrive/Architecture: ADR-0003-Data-Warehouse-Platform-Strategy.docx`).
