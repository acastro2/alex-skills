# Evidence capture mechanics

Apply the eligibility and confidentiality rules in
[Evidence capture](../SKILL.md#evidence-capture) before copying.
`Evidence/` and `Bard/` are relative to the vault root, not this reference directory.
The category folders below are inside `Evidence/`.

## Folder layout

`Evidence/` is organized by artifact type, not by topic:
- `Decks/` — .pptx/.pdf presentations
- `ADRs/` — Architecture Decision Records
- `Reports/` — audit/baseline/activity reports (html/docx/pdf)
- `Plans-Proposals/` — plans, proposals, SOWs, remediation plans
- `RFCs/` — RFCs
- `Tech-Briefs/` — tech briefs, opportunity briefs, reference docs
- `Templates/` — templates Alex built
- `Confidential/` — ⚠️ incident-related and internal-sensitive material (see the core confidentiality rules)

## README

Keep `Evidence/README.md` current in place (it is updated alongside `Todo.md` and
`Bard/Done Archive.md`): list each category, note the PII boundary, and flag the
Confidential folder with a do-not-share warning.
