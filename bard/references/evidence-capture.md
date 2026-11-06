# Evidence capture mechanics

Apply the eligibility and confidentiality rules in
[Evidence capture](../SKILL.md#evidence-capture) before copying.
`Evidence/` and `Bard/` are relative to the vault root, not this reference directory.

## Folder layout

`Evidence/` is organized by artifact type, not by topic:

| Folder | `doc_type` | Holds |
|---|---|---|
| `ADRs/` | adr | Architecture Decision Records |
| `RFCs/` | rfc | RFCs |
| `SADs/` | sad | Solution Architecture Documents |
| `SOWs/` | sow | Statements of work |
| `Standards/` | standard | Standards and policies |
| `Runbooks/` | runbook | Runbooks, procedures, playbooks |
| `Plans-Proposals/` | plan | Plans, proposals, remediation plans |
| `Tech-Briefs/` | brief | Tech briefs, opportunity briefs, reference docs |
| `Reports/` | report | Audit, baseline and activity reports |
| `Decks/` | deck | Presentations, newsletters, emails |
| `Templates/` | template | Templates and checklists |
| `Notes/` | note | Memos, prep, handoffs |
| `Confidential/` | any | ⚠️ Incident and internal-sensitive material (see the core confidentiality rules) |
| `Sources/Architecture/` | any | Raw mirror of the Architecture SharePoint site |
| `Sources/Architecture-Private/` | any | Raw mirror of the internal architecture library |
| `Sources/Developer/` | any | Curated copies of `~/Developer`, one `_digest.md` per folder |

Do not move or rename files inside `Sources/`. Their internal links depend on the paths.

## Catalog

`Evidence/catalog.jsonl` is the machine index. It has one JSON object per eligible
Markdown document. `CATALOG.md` is the rendered table view. `catalog.meta.json` holds
the row count and generation time. `catalog.schema.json` is the JSON Schema.

After adding or updating documents, rebuild and check:

```
python3 ~/.agents/skills/bard/scripts/evidence_catalog.py build --vault <vault>
python3 ~/.agents/skills/bard/scripts/evidence_catalog.py check --vault <vault>
```

Never edit `catalog.jsonl`, `catalog.meta.json` or `CATALOG.md` by hand.

Rules:

- A type-folder copy is `canonical: true`. A `Sources/` copy of the same document is
  `canonical: false` with `duplicate_of` pointing at the curated path. Agents should
  read canonical rows by default.
- `date` is the document date, never the copy date. Use `date_precision` and
  `date_source` to show how it was found. Do not use filesystem mtime.
- `original` records the source path or URL only when it is known. If the path does
  not exist, keep the string and mark `source_status: missing`; never rewrite history.
- `related` holds vault-resolvable links. Topic-hub links are deterministic. Link a
  specific Bard note or Scribe transcript only when a hard key matches: exact title,
  session ID, GitHub pull-request URL, or an existing transcript path.
- `needs_tag: true` means the row has no explicit topic. The Developer digests carry
  this flag because they are folder indexes, not topic notes.

## README

Keep `Evidence/README.md` current in place (it is updated alongside `Todo.md` and
`Bard/Done Archive.md`): list each category, note the PII boundary, and flag the
Confidential folder with a do-not-share warning.
