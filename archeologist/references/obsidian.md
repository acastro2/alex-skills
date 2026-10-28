# SOURCE D: Obsidian vault (HIGH PRIORITY)

Personal knowledge base. Search it alongside Claude Code transcripts and Cortex (Tier 1).
This file is also the setup guide: follow **Retrofit** to build the same vault, and every
command below works on it.

## Vault root

```bash
VAULT="${OBSIDIAN_VAULT:-$(obsidian vault 2>/dev/null | awk '$1=="path"{print $2}')}"
```

`bard` and `scribe` find the vault the same way: `$OBSIDIAN_VAULT` first, then the vault the
`obsidian` CLI reports. Never hard-code the path. If both are empty, ask the user for the path.

## Layout

The vault has two kinds of folders. People write the numbered zones. Agents write the
managed collections. The vault's own `AGENTS.md` is the contract: it lists the zones, the
filing rules, and the frontmatter `type` values. Read it before you write to the vault.

| Folder | Written by | What it holds | Search it for |
| --- | --- | --- | --- |
| `Bard/` | `bard` skill | One note per lesson or decision, titled as a full sentence. Topic hubs (`type: hub`), `Bard Index.md`, `Bard.base`, `.bard-state.json`. | Decisions, fixes, "why did we", "how did we". Search first. |
| `Scribe/Meetings/Transcripts/` | `scribe` skill | One note per meeting: summary, decisions, actions, verbatim transcript. Filename `YYYY-MM-DD HHMM <title>.md`, local time. `Scribe/Glossary.md` holds term fixes. | "Who said", "when did we meet", "what was decided in <meeting>". |
| `Evidence/` | `bard` skill | Copies of authored deliverables: ADRs, RFCs, SOWs, tech briefs, decks, reports, templates, `Confidential/`. Mostly docx, pptx, xlsx, pdf. `README.md` indexes it and records what was left out. | The formal record: what was proposed, decided, or shipped on paper. |
| `Hermes/` | Wolfie agent | Agent memory, research, tasks, decisions. | Only when the question names Wolfie or CareerOS. |
| `00 Inbox/` to `40 Writing/` | The owner | Captures, work notes, personal notes, knowledge, writing. | Context that no agent recorded. |
| `90 Archive/` | The owner, once | Frozen notes. | Old context. Treat it as stale and say so in the briefing. |
| `Todo.md` | Owner above `<!-- BARD:START`, `bard` below | The one task board. | Open work and who waits on it. |

`rg` skips hidden folders by default, so `.obsidian/`, `.claude/`, and `.copilot/` (plugin
and agent config) stay out of results.

## Retrofit

To build the same setup on another machine:

1. **Tools.** Install `rg`, `uv`, and `pdftotext` (`brew install ripgrep uv poppler`), and
   the Xcode command line tools for `swiftc` (`xcode-select --install`).
   Install Obsidian and its `obsidian` CLI; the check is that `obsidian vault` prints the
   vault path. Turn on the core plugins Bases, Properties, and Sync: the `bard` views need
   Bases and Properties. The community plugins Tasks, Iconize, Admonition, and Charts are in
   use but optional; nothing here depends on them.
2. **Vault root.** Set `OBSIDIAN_VAULT` in your shell profile, or let the CLI report it.
3. **Contract.** Put an `AGENTS.md` at the vault root. It names the zones, the managed
   folders that agents own (people never hand-edit them), the filing rules, and the
   required frontmatter `type`.
4. **Writers.** Run `/bard bootstrap`. It proposes a topic hub list for you to approve,
   then scaffolds `Bard/`, the hubs, `Bard.base`, and the board block in `Todo.md` (see
   `bard/references/obsidian-setup.md`).
   Run `scribe` to create `Scribe/`. `bard` creates `Evidence/` the first time it copies a
   deliverable.
5. **Evidence boundary.** Copy authored work only. Never copy third-party personal data
   or live credentials into the vault: record that work as a `Bard` note instead.
   `Evidence/README.md` lists what was left out and why.
6. **Check.** Run D1 below with a word that you know is inside a `.docx` in `Evidence/`.
   If it returns nothing, the `--pre` flags or `uv` are missing.

## Office and PDF files

Plain `rg` cannot read docx, pptx, xlsx, or pdf. A docx is a zip file, so its text is
compressed and every search misses it. Always pass the `--pre` flags below.
`scripts/office2txt` turns each such file into text (markitdown through `uvx` for Office,
`pdftotext` for PDF) and caches the text in `~/.cache/archeologist/text`, keyed on the file
path and modification time. The first search after a file changes is slow (about 10
seconds for a few hundred files). Later searches take under a second.

A PDF made only of images has no text layer. When `pdftotext` returns almost nothing,
`office2txt` falls back to macOS Vision OCR (`scripts/ocr_pdf.swift`). The first time,
it compiles that file with `swiftc` into `~/.cache/archeologist/bin/ocr_pdf`. It is compiled
because the sandbox kills `swift <file>` scripts. Measured: 13 slides in 3.5 seconds.

## Search order

| Question | Search first | Then |
| --- | --- | --- |
| Decision, fix, lesson | `Bard/` | `Evidence/`, then the zones |
| Meeting, who said, when | `Scribe/Meetings/Transcripts/` | Microsoft 365 (`claude_ai_Microsoft_365` connector or the `m365` CLI) |
| Formal document, proposal, ADR | `Evidence/` | `Bard/` for the reasoning behind it |
| Anything else | The whole vault | |

Search `Scribe/` before Microsoft 365: it is local, already cleaned, and covers calls that
Teams never transcribed.

## Strategy D1: Triage (find matching notes)
```bash
PRE=(--pre ~/.agents/skills/archeologist/scripts/office2txt --pre-glob '*.{docx,pptx,xlsx,pdf}')
SKIP=(-g '!**/credentials/**' -g '!**/secrets/**')
rg -l -i "${PRE[@]}" "${SKIP[@]}" "<kw>" "$VAULT" 2>/dev/null
```

`SKIP` keeps credential folders out of results, so a briefing never quotes a secret. To
search one folder, put it after `$VAULT`, for example `"$VAULT/Bard"`.

## Strategy D2: Context search (show surrounding lines)
```bash
KEYWORD="..."
rg -i -C3 "${PRE[@]}" "${SKIP[@]}" "$KEYWORD" "$VAULT" 2>/dev/null | head -80
```

## Strategy D3: Read one Office or PDF file in full
```bash
~/.agents/skills/archeologist/scripts/office2txt "<path-to-file>"
```

## Citation format
Cite as: `Obsidian: <relative-path-within-vault>` (e.g. `Obsidian: Bard/grafana-alerting.md`).
