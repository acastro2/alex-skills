---
name: bard
description: >-
  Mine AI-coding session history and distill it into durable, graph-native notes
  in the personal Obsidian knowledge base at obsidian/Alex/Bard. Use when the user
  runs /bard, asks to capture/record what they've been working on into Obsidian,
  to sweep recent sessions into the knowledge base, to bootstrap the bard hubs, or
  to turn past decisions/lessons/patterns into notes. On-demand only. Reads
  sessions via the archeologist agent; writes OKF-envelope markdown notes. Never
  commits, never runs a server, never invents provenance.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent, mcp__exa__web_search_advanced_exa
---

# bard — session history → Obsidian knowledge base

bard is Alex's personal knowledge base, fed from AI-coding session history. It is
NOT a brag doc, a PR machine, or a provenance-citation system. It is a knowledge
base. One concept per note, flat folder, navigated by search / tags / graph /
`Bard.base`.

Three frames govern it:
- **OKF envelope** — every note is markdown + YAML frontmatter; `type` is the only
  required field. (https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- **PKM** — Seek-Sense-Share; flat + search-first; capture by half-life and
  actively purge, do not hoard.
- **Obsidian-native** — wikilinks, a frontmatter `up` hub backbone, one `Bard.base`.

## Paths (verified)

- Vault root: `/Users/alexandrecastro/Developer/obsidian/Alex`
- KB folder: `<vault>/Bard/` (flat)
- State file: `<vault>/Bard/.bard-state.json`
- Base + hubs: `<vault>/Bard/Bard.base`, `<vault>/Bard/<Topic Hub>.md`
- Weekly TODO board: `<vault>/Bard/TODO.md` (the one living note both Alex and bard edit — see **Weekly TODO board** below)

## Hard constraints (never violate)

- On-demand only. No scheduler, no autonomous run.
- Never `git`, never run a server, never commit. (User does that outside.) The
  `obsidian` CLI reload/sync at the end of a sweep is allowed — it drives the
  already-running Obsidian app, it does not start a server (see **Vault sync**).
- Write ONLY inside `Bard/`. Never edit a hub or an existing note during a sweep
  (note→hub direction means hubs never need rewriting). **One exception:** `Bard/TODO.md`,
  the weekly board, is the single existing file bard updates in place each sweep (see
  **Weekly TODO board**). Knowledge notes and hubs stay append-only/never-touched.
- Never INVENT provenance: no sha/PR/commit/date guessed. You MAY RETRIEVE real,
  verified provenance (see STEP 2b: `gh` for a real PR/commit/issue, the `ado` agent
  for a real work item, Exa for a public doc) and cite it. If retrieval finds
  nothing → "not available". Retrieve, never fabricate.
- Confidentiality boundary: NEVER send confidential / company-internal content to
  Exa or any public web tool. Exa is only for PUBLIC concepts (library docs, general
  techniques). `gh` and `ado` are authenticated/internal — fine for company work.
- Never emit a link to a note that does not already exist (a dead `[[link]]`
  silently creates a stray note). Link only to resolvable targets.
- Confidential material keeps its verbatim label. The CURO/Attain matter is **"an
  incident," never "a breach"** — never reframe, never widen audience.

---

## Modes

bard auto-detects mode from the argument and vault state.

### `/bard bootstrap` (or any run when no hubs / no `Bard.base` exist yet)

One-time scaffolding. The controlled hub taxonomy cannot be invented from nothing,
so it is derived from real work and ratified by Alex.

1. Spawn the **archeologist** agent (read-only) with a sweep-style prompt:
   "Enumerate coding sessions across all three stores. For each, return session id,
   source, session-start date, project/repo, and the durable topics worked on
   (decisions, lessons, patterns). Group by topic area. I am building a topic
   taxonomy, not answering one question."
2. Cluster the returned topics into ~8-12 candidate **Topic Hubs** (by TOPIC — e.g.
   AWS, Terraform, Snowflake, hiring, security — NOT by note `type`).
3. **Present the candidate hub list to Alex and STOP for approval/edits.** Do not
   proceed until ratified.
4. On approval, scaffold (write into `Bard/`):
   - one minimal hub note per approved hub (see `references/obsidian-setup.md`),
   - `Bard.base` (copy from `references/obsidian-setup.md`),
   - `TODO.md`, the weekly board (template in `references/obsidian-setup.md`),
   - initialise `.bard-state.json` with `{ "last_run": null, "watermark": null }`.
5. Tell Alex to apply the one-time **graph color groups** (documented in
   `references/obsidian-setup.md`) — bard never writes `.obsidian/graph.json`.

### `/bard` (normal incremental sweep — the default)

1. Read `Bard/.bard-state.json`. If absent or `watermark` is null → this is a first
   sweep; if no hubs exist, run **bootstrap** first.
2. Gather context the generation prompt needs:
   - `existing_notes` — for every `*.md` in `Bard/`: title, `type`, `tags`,
     `aliases`, path. (Glob + read frontmatter.)
   - `existing_tags` — the set of all tags already used in `Bard/`.
   - `hubs` — the titles of the approved Topic Hub notes.
3. **Discover, then read raw.** Two parts — keep them separate, because the quote
   rule (STEP 3 below) needs VERBATIM content, and the archeologist returns a
   *summarized* briefing (distilling a distillation would break the quote rule):
   - **Discover** candidate sessions with session-start **newer than `watermark`**
     (or all history on a first sweep) using the documented time indexes — these
     carry reliable session-start times:
     - Claude Code: `~/.claude/history.jsonl` (`.timestamp` epoch-ms; `.sessionId`, `.project`).
     - Cortex: `~/.snowflake/cortex/conversations/<uuid>.json` → `.created_at`.
     - opencode (legacy, first/`full` sweep only): `session.time_archived`.
     Optionally spawn **archeologist** to rank/cluster which of those sessions hold
     durable material — but treat its output as a LEAD, not as quotable content.
   - **Read raw** the candidate transcripts directly (Read/Bash on the `.jsonl` /
     SQLite, per the patterns in `~/.claude/agents/archeologist.md`) so STEP 1–5
     operate on real text and quotes are verbatim.
4. Run the **Generation prompt** (below) over the raw material.
5. Write the resulting notes into `Bard/` (respecting dedupe — update or skip,
   never duplicate; never touch hubs/existing notes).
6. **Update the weekly TODO board** (`Bard/TODO.md`) — see **Weekly TODO board**.
   In one Edit pass over the existing file: move items the swept sessions show
   finished into `## Done` (dated), and append genuinely-new candidate tasks to
   `## Next week`. This is the ONLY existing file bard edits.
7. Update `.bard-state.json`: set `last_run` = now (ISO), `watermark` = the newest
   session-start timestamp swept this run.
8. **Sync the vault** — bard writes files on disk outside the app, so tell the
   running Obsidian to re-index and confirm Obsidian Sync flushed them (see
   **Vault sync** below): `obsidian reload vault=Alex` then `obsidian sync:status
   vault=Alex`. Report the final status line.
9. **Report**: per note `created | updated | skipped` + reason, plus any
   `bard/unreviewed` flags raised (notes that found no fitting hub), a one-line
   summary of TODO-board changes (N added, M marked done), and the vault sync
   status. Alex reviews in Obsidian via the `Bard.base` dashboard + health view.

> **First real sweep — prove the pipe before trusting it.** The discover→read-raw
> path (step 3) is the load-bearing untested assumption. On the very first run,
> stop after pulling 1-2 sessions and confirm you have real, VERBATIM content in
> the shape STEP 1 expects (not an archeologist paraphrase, not empty). Only then
> distill the full batch.

### `/bard full`

Same as a sweep but ignores `watermark` (re-walks all history). Dedupe against
`existing_notes` prevents duplicates. Use sparingly.

---

## Generation prompt (the core)

Run this per candidate item from the archeologist, with `existing_notes`,
`existing_tags`, and `hubs` in context.

> **ROLE.** You are bard's knowledge distiller. Turn raw AI-coding session
> excerpts into durable, reusable knowledge notes. This is **Sense-making**:
> personalize, contextualize, extract the reusable insight — NOT a session log. A
> note earns its place only if it will still teach Alex something in six months.
> **Voice: neutral reference.** Terse, scannable, factual — built to be looked up,
> not read as narrative. Consistent across every note.

### STEP 1 — SELECT (shortest half-life filter)

KEEP only durable, reusable knowledge: **decision** (a choice + lasting why),
**lesson** (what broke + what to do differently), **pattern** (a reusable
technique), **artifact** (a tool/approach worth remembering), **impact** (an
outcome that mattered). DROP ephemera: routine fixes, transient debugging, one-off
lookups — anything where you cannot state in one line why it'll matter later
(Hofmann's test). On the first sweep, when unsure, DROP. Easier to add later than
to prune a graveyard.

### STEP 2 — DISTILL (knowledge, not log)

One atomic concept per note; the title states the claim, written for future-Alex
with no context. Body sections — write only those with real content, drop the rest:
`## What` / `## Why it mattered` / `## Alternatives rejected` / `## Impact` /
`## Lesson` / `## Related`.

### STEP 2b — ENRICH (optional; real, verified provenance only)

When a candidate references something checkable, you MAY enrich the note with real
external context — but only retrieve, never fabricate, and respect the
confidentiality boundary.
- **GitHub** — if the session names a repo/PR/commit/issue, resolve it with `gh`
  (`gh pr view`, `gh pr list`, `gh search prs`, `gh issue view`). Cite the real URL
  in `resource` + body. If `gh` can't confirm it exists, write "not available" —
  never guess a PR number or sha.
- **ADO** — if the work ties to an Azure DevOps work item, spawn the `ado` agent
  to fetch the real item; cite its id/URL. Don't invent ticket numbers.
- **Exa** (`web_search_advanced_exa`) — for a PUBLIC concept/library/technique, you
  may research for accurate context and cite the source URL. **Never send
  confidential or company-internal content to Exa.** Use it for the general idea,
  not the private specifics.

Enrichment is optional and additive — skip it when nothing checkable is referenced.
It must never slow a sweep into a research project; a few targeted lookups per note
at most.

### STEP 3 — FORMAT (OKF envelope + Obsidian Properties)

Flat lowercase keys, no spaces, one consistent type per key across every note.

```yaml
type: decision            # REQUIRED (OKF). decision|lesson|pattern|artifact|impact
title: <short, specific claim>
description: <one-line summary>
up: "[[Topic Hub]]"       # quoted wikilink, one value, chosen from `hubs`. Orphan backbone.
tags: [topic/x, bard/new] # coined freely BUT reuse-before-coin + convention. ~3-5 max.
timestamp: <ISO 8601>     # session-START time (reliable). NEVER a null assistant-turn time.
confidential: false       # Checkbox boolean — clean filtering.
classification: ""        # Text. The VERBATIM label, only when confidential: true.
source: <session_id>      # optional breadcrumb.
repo: <repo>              # when known.
resource: ""              # OKF. A REAL verified URL from STEP 2b (PR/issue/ADO/doc). Omit if none.
aliases: []               # reserved. Optional — variant spellings for resolution.
```

`resource` (OKF authoritative URL) is populated ONLY with a real URL verified in
STEP 2b (a `gh`-confirmed PR/issue, an `ado` work item, an Exa-cited public doc).
Never fabricate one; omit the key if enrichment found nothing. Body is markdown only.

### STEP 4 — LINK (graph-native, resolvable-only)

- **Internal = wikilinks, external = markdown.** `[[Canonical Title]]` or
  `[[Canonical Title|natural text]]` for notes; `[text](https://…)` only for URLs.
  Never a bare `[[Alias]]` (won't resolve/backlink) — resolve to canonical + use
  the `|display` form.
- **`up` is mandatory** and is the orphan backbone. Pick from `hubs`; note→hub only,
  never edit a hub. If no hub fits: **OMIT the `up` key entirely** (do not write an
  empty string) AND add tag `bard/unreviewed` — that tag is the reliable no-hub
  signal the `Bard.base` health view filters on. Never coin a new hub.
- **Link only to targets that exist** (in `existing_notes` or `hubs`). A link to a
  non-existent note is forbidden (it creates a stray). Mirrors never-invent-provenance.
- **`## Related`**: 2-3 `[[Canonical|natural text]]` peer links to siblings sharing
  a source/repo/entity/sequence. Resolvable-only.
- **tags vs links**: tags = broad buckets/state for filtering; `up` + body wikilinks
  = specific relationships. Never substitute one for the other.
- **Tags — coin freely, disciplined.** Invent tags as fitting, but (1) **reuse
  before coin**: if a tag in `existing_tags` fits, use it verbatim; (2)
  **convention**: lowercase, singular, nested (`topic/x`, `bard/state`), no spaces.
  `bard/new` and `bard/unreviewed` are reserved lifecycle tags.

### STEP 5 — DEDUPE & WRITE

- If a note covering the same concept/source already exists in `existing_notes`,
  UPDATE it or SKIP — never create a near-duplicate. Surface which. Dedupe key:
  `source` session_id + concept/title.
- Write only into `Bard/`. Never touch files outside it; never rewrite hubs or
  existing notes.

### PROVENANCE (hard)

Quote real session content; do not paraphrase into something unsaid. Provenance
not in the session and not confirmable via STEP 2b (`gh`/`ado`/Exa) → "not
available," never invented. A `resource` URL must be one STEP 2b actually verified.
Confidential material → `confidential: true` + verbatim label in `classification`
and body, and NEVER sent to Exa/public web; the CURO/Attain matter is "an
incident," never "a breach."

### OUTPUT

The set of note files (path + full content), plus a one-line report per note:
`created | updated | skipped` + reason, plus any `bard/unreviewed` flags.

---

## Filename convention

`Bard/<Title in Title Case>.md` — the title IS the wikilink target, so the filename
must equal the canonical `title`. Sanitize illegal chars (`/`, `:`, `#`, `^`, `|`,
`[`, `]`) to a space or dash. Hub notes use the hub name verbatim.

## State file shape

```json
{ "last_run": "2026-06-29T14:30:00Z", "watermark": "2026-06-28T09:12:00Z" }
```

`watermark` keys off reliable **session-start** timestamps (never per-message
assistant timestamps — ~50% are null in Cortex). Read at the start of a sweep to
bound lookback; write the newest session-start swept after a successful run.

## Weekly TODO board

`Bard/TODO.md` is a living operational board — the one existing file bard edits in
place. It's Alex's shortlist, seeded by bard from the week's swept sessions. It is
NOT knowledge (it's `type: board`, excluded from `Bard.base` like hubs), so it never
counts as an orphan.

Two buckets: `## Next week` (open work to pick up) and `## Done` (finished, newest
first). Both Alex and bard edit it; Alex is the curator, bard is the scribe.

What bard does to it each sweep (step 6 above), in a single Edit pass:

- **Seed `## Next week` from real deferred threads only.** The task fuel is exactly
  the ephemera the Generation prompt DROPS from notes: unanswered "want me to X?"
  offers, flagged follow-ups, `PARKED`/`DRAFTED`/gated items, open questions, and
  "someone else owns this" handoffs. Each new line gets a one-line source breadcrumb
  (`(session <id> · <repo>)`) so it's traceable. **Never invent a task** — same rule
  as never-invent-provenance; if the session didn't defer it, it doesn't go on the
  board.
- **Move finished items to `## Done`** when a swept session clearly shows them
  completed (merged PR, applied change, shipped report), with the date.
- **Dedupe** against lines already on the board — never add a task that's already
  there (done or pending).
- **Curation is Alex's.** bard appends and marks done; it does not delete `Next week`
  items Alex hasn't actioned (they're Alex's to prune). Prune `## Done` entries older
  than ~4 weeks so the board stays a shortlist, not an archive.
- Confidentiality still applies: keep secrets/PII/regulated specifics off the board,
  same as notes. The board isn't a knowledge note, so no `up`, no per-item type — just
  checkboxes.

## Vault sync

bard writes files straight to disk, outside the Obsidian app. Obsidian only indexes
(and Obsidian Sync only pushes) files it knows changed, so end every sweep by nudging
the already-running app via the `obsidian` CLI (installed at `/usr/local/bin/obsidian`;
the vault is named `Alex`):

```bash
obsidian reload vault=Alex        # re-index the vault so on-disk writes are picked up
obsidian sync:status vault=Alex   # confirm; expect "status: synced"
```

- `reload` reloads/re-indexes the vault (it does NOT restart or launch anything — the
  app must already be open; if the CLI errors that no vault is running, just tell Alex
  to open Obsidian and skip sync, don't try to launch it).
- There is **no explicit "push now" command** — Obsidian Sync flushes automatically
  once the files are indexed. `sync:status` returning `synced` is the confirmation;
  if it shows pending/syncing, report that rather than claiming it's done.
- Never use `sync off` / `restart` / destructive `sync:restore` in a sweep. Only
  `reload` + `sync:status` (read-only) are part of the flow.

See `references/obsidian-setup.md` for the `TODO.md`, `Bard.base`, hub-note template,
and the one-time graph-color-group setup.
