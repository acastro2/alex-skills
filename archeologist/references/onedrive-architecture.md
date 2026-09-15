# SOURCE F: OneDrive Architecture (SECONDARY)

Formal architecture documents: ADRs, Solution Architecture Docs (SAD), Security Improvement
Plans (SIP), tech briefs, GenAI policy, and templates.

**Path**: `~/Library/CloudStorage/OneDrive-Attainfinance.com/Architecture - Documents/`
(verified 2026-08-10 — the old `~/OneDrive - Attainfinance.com/...` path does not exist on this machine;
fallback: `~/OneDrive/OneDrive - Attainfinance.com/...`)
(The `Architecture-Architects Internal - Documents/` folder is a mirror; skip it to avoid dupes.)

## Strategy F1: Search markdown/text files (fast)
```bash
ARCH_DIR="$HOME/Library/CloudStorage/OneDrive-Attainfinance.com/Architecture - Documents"
# fallback if the above doesn't exist:
[ -d "$ARCH_DIR" ] || ARCH_DIR="$HOME/OneDrive/OneDrive - Attainfinance.com/Architecture - Documents"
rg -l -i "$KEYWORD" "$ARCH_DIR" 2>/dev/null
```

## Strategy F2: Search .docx files (extract text on the fly)
```bash
ARCH_DIR="$HOME/Library/CloudStorage/OneDrive-Attainfinance.com/Architecture - Documents"
# fallback if the above doesn't exist:
[ -d "$ARCH_DIR" ] || ARCH_DIR="$HOME/OneDrive/OneDrive - Attainfinance.com/Architecture - Documents"
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
- GenAI policy: `Attain GenAI Policy.docx`, `attain-genai-standard.md`
- Templates: `ADR_Template.docx`, `Solution-Architecture-Document-Template.docx`

## Citation format
Cite as: `OneDrive/Architecture: <filename>` (e.g. `OneDrive/Architecture: ADR-0003-Data-Warehouse-Platform-Strategy.docx`).
