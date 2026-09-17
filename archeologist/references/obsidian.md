# SOURCE D: Obsidian vault (HIGH PRIORITY)

Personal knowledge base. Search alongside Claude Code transcripts and Cortex (Tier 1).

**Path**: `~/Developer/obsidian/Alex/`

Two sub-folders matter most: `Bard/` (distilled decisions, lessons, patterns) and
`Scribe/Meetings/Transcripts/` (one note per meeting since 2026-09-01, written by the
`scribe` skill from Teams transcripts and HiDock call recordings, each with a summary,
decisions, actions, and the verbatim transcript). For "who said", "when did we meet",
or "what was decided in <meeting>" questions, search `Scribe/Meetings/Transcripts/`
BEFORE reaching for Microsoft 365 (the `claude_ai_Microsoft_365` connector, or the `m365`
CLI): it is local, already cleaned, and covers calls Teams
never transcribed. Note filenames start with the meeting date and local time
(`2026-09-02 1500 Architecture Advisory Board.md`).

## Strategy D1: Triage (find matching notes)
```bash
rg -l -i "<kw>" ~/Developer/obsidian/Alex/ 2>/dev/null
```

## Strategy D2: Context search (show surrounding lines)
```bash
KEYWORD="..."
rg -i -C3 "$KEYWORD" ~/Developer/obsidian/Alex/ 2>/dev/null | head -80
```

## Citation format
Cite as: `Obsidian: <relative-path-within-vault>` (e.g. `Obsidian: Bard/grafana-alerting.md`).
