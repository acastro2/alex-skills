---
name: bard
description: >-
  Mine AI-coding session history and scribe meeting transcript notes
  (Scribe/Meetings/Transcripts) and distill them into durable, graph-native notes
  in the personal Obsidian knowledge base at obsidian/Alex/Bard, and copy authored
  deliverable files into the Evidence vault (Evidence/). Use when the user
  runs /bard, asks to capture/record what they've been working on into Obsidian,
  to sweep recent sessions or meetings into the knowledge base, to bootstrap the bard
  hubs, or to turn past decisions/lessons/patterns into notes, and to maintain the
  root-vault `Todo.md` board. On-demand only. Reads sessions via the archeologist agent; writes
  OKF-envelope markdown notes. Never commits, never runs a server, never invents
  provenance.
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
- Root TODO board: `<vault>/Todo.md` (the one living board both Alex and bard edit — see **Root TODO board (`Todo.md`)** below; verified to exist)
- Done archive: `<vault>/Bard/Done Archive.md` (completed items older than ~4 weeks; see **Root TODO board (`Todo.md`)** below)
- Retired board pointer: `<vault>/Bard/TODO.md` (pointer stub only; never treat it as the board)
- Evidence folder: `<vault>/Evidence/` (authored deliverables copied from repos/OneDrive — see **Evidence capture** below)

## Hard constraints (never violate)

- On-demand only. No scheduler, no autonomous run.
- Never `git`, never run a server, never commit. (User does that outside.) The
  read-only `obsidian sync:status` at the end of a sweep is allowed — it queries the
  already-running Obsidian app, it does not start a server. `obsidian reload` is
  BANNED: it hangs and wedges the CLI (see **Vault sync**).
- Write ONLY inside `Bard/` and `Evidence/`, with the root vault `Todo.md` as the
  named board exception. Never edit a hub or an existing knowledge note during a sweep
  (note→hub direction means hubs never need rewriting). `Todo.md`,
  `Bard/Done Archive.md`, and `Evidence/README.md` are the only existing files bard
  updates in place. `Bard/Done Archive.md` is inside the existing `Bard/` scope; no
  additional write-scope exception is needed. On `Todo.md`, bard edits ONLY from the
  `<!-- BARD:START -->` marker down: never edit, reorder, or read as task input anything
  above it, and never add frontmatter to that file. The retired `Bard/TODO.md` is a
  pointer stub only; bard never writes it. Knowledge notes and hubs stay
  append-only/never-touched.
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
4. On approval, scaffold:
   - one minimal hub note per approved hub (see `references/obsidian-setup.md`),
   - `Bard.base` (copy from `references/obsidian-setup.md`),
   - the BARD List block in the root `<vault>/Todo.md` (template in
     `references/obsidian-setup.md`). Use the two-level `## Open` structure: a derived
     horizon heading, then a fixed-map topic heading. Insert new items at the top of
     their topic group, using the short open and Done-line formats. Keep only the last ~4 weeks
     in `## Done`; roll older items to `<vault>/Bard/Done Archive.md`, never delete
     them. If `<!-- BARD:START -->` is already present, leave the block alone;
     otherwise append the whole block at the end of the file,
   - create `<vault>/Bard/Done Archive.md` from the archive template if it is absent,
     so the `[[Done Archive]]` board link resolves,
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
     - Pi: `~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl` — the filename
       timestamp is the session start (UTC ISO). Pi dir names start with `--`, so
       glob with a `./` prefix or absolute paths: bare `--...` paths are parsed as
       options by `head`/`jq`/`ls`/`find` and silently return nothing. The record
       shape is NOT the same as Claude Code's: a Pi turn is
       `{"type":"message","message":{"role":"user","content":[{"type":"text","text":...}]}}`,
       so the selector is `select(.type=="message" and .message.role=="user")` and the
       text is under `.message.content[]`. A jq filter written against the Claude Code
       shape returns an empty string per line, which looks exactly like "this session
       had no user messages" — verify with `jq -r '.type' <file> | sort | uniq -c`
       before concluding a session is empty.
     - opencode (legacy, first/`full` sweep only): `session.time_archived`.
     - **scribe meeting notes** (since 2026-09-03): `<vault>/Scribe/Meetings/Transcripts/*.md`,
       one note per meeting written by the `scribe` skill (Teams transcripts and HiDock
       call recordings). Frontmatter `date` is the meeting start (UTC ISO): sweep notes
       with `date` newer than `watermark`. They are the meeting-side twin of the coding
       sessions: same STEP 1-5, same quote rule. Read the whole note; `## Summary`,
       `## Decisions`, `## Actions` are scribe's digest, `## Transcript` is the verbatim
       source and the only thing you may quote. Provenance is the note path
       (`Obsidian: Scribe/Meetings/Transcripts/<file>`) plus the frontmatter
       `provenance` block; never invent more. HiDock notes have no speaker labels
       (`speakers: []`): never attribute a line to a person unless the transcript names
       them. `## Actions` lines owned by Alex are board candidates for `Todo.md`; the
       others are context, not tasks. scribe writes everything, including standups and
       1:1s: the half-life filter in STEP 1 is where the noise dies, so expect to drop
       most of them.
     Optionally rank/cluster the candidates with the **archeologist skill** (spawn a
     `delegate`/`scout` subagent with skill `archeologist` — there is no archeologist
     *agent* in pi) — but treat its output as a LEAD, not as quotable content. For
     small windows, skip it: inline reading is faster.
   - **Read raw** the candidate transcripts directly (Read/Bash on the `.jsonl` /
     SQLite, per the patterns in the archeologist skill) so STEP 1–5 operate on real
     text and quotes are verbatim. Two pitfalls: sessions can span the watermark —
     filter entries by per-message timestamps (CC/Pi `.timestamp`, Cortex
     `user_sent_time`), don't trust session-start alone; and a sweep will rediscover
     its own prior bard sessions (first user message = this skill's text) — skip
     them as mechanics, and expect Cortex sidecar files (`*.history.jsonl`) to be
     JSONL, one object per line, not a JSON array.
   - **AI attention pass** — before distillation, explicitly scan every candidate for
     durable AI work even when AI was not the session's main topic: model or tool
     choices, agents, skills, prompts, evals, context or memory, governance, security,
     cost, adoption, and measured outcomes or failures. Do not rely only on the session
     title or repo name to surface it.
4. Run the **Generation prompt** (below) over the raw material.
5. Write the resulting notes into `Bard/` (respecting dedupe — update or skip,
   never duplicate; never touch hubs/existing notes).
6. **Update the root TODO board** (`<vault>/Todo.md`) — see **Root TODO board
   (`Todo.md`)**. Use one Edit pass over the existing file. Preserve everything above
   `<!-- BARD:START -->`; if the marker is absent, append the whole BARD List block at
   the END of the file. Dedupe against every existing board line, open and done. Derive
   each new item's horizon from the rules below, place it under its fixed-map topic
   heading, and insert it at the top of that topic group. Use the short open-line format
   with no topic emoji on open lines. Re-check every open item against the swept sessions;
   auto-complete clearly finished items, restore its topic emoji, move it to the top of
   flat `## Done`, and append the ISO date. Roll `## Done` entries older than ~4 weeks
   to `<vault>/Bard/Done Archive.md`; move them, never delete them. This is one of the
   existing files bard edits in place.
7. **Capture evidence files** — when the sweep's file scan surfaces authored
   deliverables not yet in `Evidence/`, copy them per **Evidence capture** (see
   below). Update `Evidence/README.md` to match. This is another existing file
   bard edits in place.
8. Update `.bard-state.json`: set `last_run` = now (ISO), `watermark` = the newest
   session-start timestamp swept this run. It must be a **real session-start you
   actually swept**, copied from the index — never a rounded day boundary. A watermark
   of `...T00:00:00Z` re-sweeps that whole day on the next run (seen on 2026-09-04,
   where the prior run left `2026-09-03T00:00:00Z`). **Then read the file back and
   confirm.** Alex's zsh has `noclobber` set, so a plain `> state.json` fails with
   `file exists` and leaves the OLD watermark in place — the sweep looks successful and
   the next one redoes everything. Write it with `>|`, a heredoc into `python3`, or the
   Write tool, and `cat` it afterwards.
9. **Sync the vault** — Obsidian watches the filesystem, so on-disk writes are picked
   up on their own. Run ONLY `obsidian sync:status vault=Alex` (see **Vault sync**
   below) and report the status line. Do NOT run `obsidian reload`: it prints
   `Reloading...` and never returns, and it leaves the CLI wedged so the `sync:status`
   after it times out too (verified 2026-09-03 by scribe, again 2026-09-04 by bard).
10. **Report**: per note `created | updated | skipped` + reason, plus any
   `bard/unreviewed` flags raised (notes that found no fitting hub), a one-line
   summary of TODO-board changes (N added by horizon and topic, M marked done, R rolled
   over to `Done Archive.md`), a line for evidence files copied (N added, and any PII
   files deliberately excluded), and the vault sync status. Alex reviews in Obsidian
   via the `Bard.base` dashboard + health view.

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

**AI gets special attention.** Treat durable AI decisions, lessons, patterns,
artifacts, and impact as high-value candidates. Look for model or tool choices,
agents, skills, prompts, evals, context or memory, governance, security, cost,
adoption, and measured outcomes or failures. AI relevance raises review priority;
it does not override the half-life filter. DROP routine model use, generated
boilerplate, and AI chatter with no reusable insight.

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

## Root TODO board (`Todo.md`)

`<vault>/Todo.md` is the root-vault operational board. The exact filename is `Todo.md`
(capital T only), not `TODO.md`. It is Alex's file, seeded from swept sessions. Alex
curates; bard is the scribe. It has no frontmatter and is not a knowledge note.

**Ownership split is a hard rule.** Everything above the
`<!-- BARD:START -->` marker belongs to Alex. bard never edits it, reorders it, or
reads it as task input. bard edits ONLY from the marker down and never adds frontmatter
to this file. If the marker is absent, bard appends the whole block at the END of the
file — never at the top. The retired `Bard/TODO.md` is a pointer stub only; it is not
the board.

The block below the marker has this structure:

```markdown
<!-- BARD:START — bard owns everything below this line. Alex owns everything above. -->

# BARD List

_Seeded by `/bard` from swept sessions. Newest first in each topic group. Alex curates, bard is the scribe. The priority emoji at line end is Obsidian Tasks syntax._

## Open

### 🔥 This week
#### 📊 Grafana
- [ ] Send Tyler the alerting done message `(01a025e2)` ⏫
#### 🔐 Security
- [ ] Rotate the Snowflake SCIM token `(8bf834c5)` 🔺

### 📅 This month
#### 🏛️ Enterprise Architecture
- [ ] Fix the 5 overdue EA milestones `(da41d7ea)` 🔼

### ⏳ Waiting on others
#### ☁️ AWS
- [ ] Bucket-policy owner repoints aws:SourceVpce `(aa2f6ad0)` 🔼

### 🧊 Someday
#### 🔐 Security
- [ ] Scope the org-wide Firemon decommission `(f1fd2740)` 🔽

## Done

_Last ~4 weeks. Older rolls to [[Done Archive]]._

- [x] 🏛️ Published the 08-19 AAB recap `(da41d7ea)` ⏫ ✅ 2026-08-21
```

### Line format and parser constraint

Open lines are exactly:

```text
- [ ] <short imperative description> `(<session id>)` <priority emoji>
```

Done lines are exactly:

```text
- [x] <topic emoji> <short description> `(<session id>)` <priority emoji> ✅ YYYY-MM-DD
```

Descriptions are short imperatives. Target 80 characters or fewer; hard cap 90. Drop
detail — the session id is the record. The breadcrumb is the session id only, backticked.
It has no `session ` prefix, repo, or ` · ` separator. The `####` heading carries the
topic emoji, so open lines have no topic emoji. The priority emoji is the last token on
an open line. On a done line, the priority emoji and `✅ YYYY-MM-DD` are the last two
fields. The installed Obsidian Tasks plugin (v8.3.0) parses trailing fields with
`$`-anchored regexes in a loop. Any text after the priority emoji stops it parsing. Put
the breadcrumb before the priority, never after it. Every line carries exactly one
priority emoji.

### Priority

Use Obsidian Tasks native symbols:

| emoji | level | when |
|---|---|---|
| 🔺 | Highest | a hard deadline within ~7 days **whether or not a date string appears** ("needs it today", "2.1 days before retention", "before Friday's freeze"); an exposed credential or secret; production broken; a legal, regulatory, or counsel deliverable |
| ⏫ | High | a **named person or team is waiting on you** (Jeremy, Tyler, counsel, CAB, the DBAs); OR it blocks a specific PR, ticket, or someone else's work; OR it is tied to a real-world event — townhall, forum, review, release — even with no written date |
| 🔼 | Medium | real work, nobody named is waiting, no deadline |
| 🔽 | Low | cleanup or hygiene, no consequence if it slips a month |
| ⏬ | Lowest | someday/maybe, parked with no owner |

Grade from the EVIDENCE, not the wording. A deadline counts even when it is implied
rather than written as a date. A person counts when they are named anywhere in the
thread, not only when the session proves they are blocked.

**Spread check — both directions.** A one-sided cap fails: capping only the top drains
everything into 🔼, which is just as useless as marking everything ⏫. After grading,
check the distribution against these targets and re-grade before writing if it misses:

| priority | target share of open items |
|---|---|
| 🔺 | 5–12% |
| ⏫ | 15–25% |
| 🔼 | 45–65% |
| 🔽 + ⏬ | the remainder |

**⏫ must never be 0.** Zero high means the bar was read as demanding proof no real
board ever has. Report the final distribution in the sweep report.

**Count the spread in Python, never with `grep -o`.** BSD `grep -o '🔺\|⏫\|🔼'` does not
alternate correctly over these multi-byte symbols: on 2026-09-04 it reported all 115
open items as ⏫, and only the implausibility of a 100% result caught it. A subtly wrong
count would have "confirmed" a bad board. Read the file, take the LAST priority symbol
on each `- [ ]` line, and tally with `collections.Counter`.

**Re-grading moves the item.** Horizon is derived from priority, so demoting ⏫→🔼 to
land inside the band also moves that line out of `🔥 This week` into `📅 This month`
(or into `⏳ Waiting on others` if the next action turned out to be someone else's).
Do the spread pass BEFORE placing lines, or re-place every line you re-graded.

### Topic emoji

Fixed map. Reuse these symbols. Never invent a new one:

`☁️` AWS / cloud · `❄️` Snowflake · `🏗️` Terraform / IaC · `📊` Grafana /
observability · `🔐` security / access / credentials · `🏛️` enterprise architecture /
governance / docs · `🎫` Azure DevOps / process · `🐙` GitHub · `🧪` testing / QA · `🤖`
AI / agents / skills · `👥` people / hiring / comms · `💰` cost / licensing · `🗄️`
databases / SQL Server · `📦` anything else.

### Horizon derivation and seeding

Horizon is DERIVED, never guessed from prose. The fixed horizon set and order are:
`### 🔥 This week`, `### 📅 This month`, `### ⏳ Waiting on others`, `### 🧊 Someday`.
Test `⏳ Waiting on others` FIRST — ownership beats priority.

| horizon | rule |
|---|---|
| 🔥 This week | priority 🔺 or ⏫ AND the next action is Alex's |
| 📅 This month | priority 🔼 AND the next action is Alex's |
| ⏳ Waiting on others | the next action belongs to someone else, at any priority |
| 🧊 Someday | priority 🔽 or ⏬, or parked with no owner |

Topic sub-headings use the fixed topic-emoji map, written as `#### <emoji> <name>`
(e.g. `#### ❄️ Snowflake`). Order them in fixed map order for predictable scanning,
not by size. Omit any heading with zero items — horizon and topic alike. The board never
shows an empty section.

Use high recall. Seed everything bard seeds today: Alex's commitments, unanswered
"want me to X?" offers, `PARKED`/`DRAFTED`/gated items, open questions, and handoffs.
Never invent a task. If the session did not defer it, it does not go on the board.

### Ordering, completion, and curation

A new item goes at the TOP of its `####` topic group, never appended at the bottom. Create
horizon and topic headings only when they contain an item. Keep both heading levels in
fixed order. `## Done` stays flat; insert a newly completed item at the top of `## Done`.
On every sweep, bard re-checks every open item against the swept sessions. When a session
clearly shows an item finished — for example, a merged PR, applied change, shipped report,
or sent message — bard checks the box, restores the topic emoji from its `####` heading,
appends `✅ <ISO date>`, and MOVES the line to the top of `## Done`. This is mandatory,
not best effort.

`## Done` holds only the last ~4 weeks. Anything older rolls over to
`<vault>/Bard/Done Archive.md`; pruning now means moving, not deleting. The archive is
never deleted or shortened. It has frontmatter `type: board`, `# Done Archive`, and
`## YYYY-MM` month sections, newest month first, with newest items first inside each
month. Archive lines use the same flat Done format. The verified `Bard.base` filter uses
`file.inFolder("Bard")` and excludes `type == "board"`, so the archive stays out of the
base by type; that folder filter excludes the root `<vault>/Todo.md`, not the archive.
A future full retrospective rebuild writes its finished-work haul into `Done Archive.md`,
never into `Todo.md`. The roll-over/prune step never deletes archive content.

bard adds items, marks done, and rolls over old `## Done` entries. It never deletes an
open item Alex has not actioned. Secrets, PII, and regulated specifics stay off the board,
the same as notes.

### Alex edits this board by hand — re-read it immediately before writing

`Todo.md` is a live file Alex works in Obsidian between sweeps. He ticks items off
himself, adds his own, and edits text. **Never write the board from state read earlier in
the run.** Re-read it as the last step before the write, and diff against what the sweep
started with.

- An item Alex checked himself is a REAL completion. Keep his `✅ <date>` and move it to
  `## Done`. Never revert it to `- [ ]`, and never restamp it with a different date.
- An item Alex added by hand stays, even with no breadcrumb and no priority emoji. Grade
  and file it, do not delete it for failing the format.
- An item Alex edited keeps his wording.

This is a data-loss class, not a style rule: a sweep that trusts stale state silently
erases work Alex already did.

### Bulk clear ("the board is mostly done, start fresh")

When Alex asks to clear the board, archive it — do not mark it done.

- Items he actually checked keep their real `✅` date and file under `## YYYY-MM`.
- Everything else moves to `Bard/Done Archive.md` under a
  `## Cleared <ISO date> — bulk, not individually verified (N items)` section, staying
  `- [ ]` with NO `✅` date, topic emoji restored to the line, grouped by topic.
- Say plainly in that section that the items were not checked one by one, and that the
  session id is the record for re-opening any of them.

**"Mostly done" is not done.** Stamping a completion date bard did not observe writes
false provenance into the knowledge base and destroys the difference between real
completed work and a bulk clear. Same rule as never inventing provenance.

## Evidence capture

Alongside the knowledge sweep, copy **authored deliverable files** into `<vault>/Evidence/`
when a swept session or the sweep's file scan surfaces them. This is Alex's personal work
record — the artifacts that back up the knowledge notes (decks, ADRs, reports, plans).

### What qualifies (copy when it makes sense)

Authored deliverables Alex produced or co-authored, from local repos or OneDrive
(Architecture - Documents and the OneDrive root). Copy ONLY when:
- it's a **deliverable** (deck, ADR/SAD/SIP/RFC, report, plan/proposal, SOW, tech brief,
  template), and
- Alex authored/co-authored it (swept session, git authorship, or file metadata shows
  him as the creator), and
- it's not already in `Evidence/` (dedupe by filename — copy = ADD only, never overwrite
  an existing copy, never move/delete the source).

### Folder layout

`Evidence/` is organized by artifact type, not by topic:
- `Decks/` — .pptx/.pdf presentations
- `ADRs/` — Architecture Decision Records
- `Reports/` — audit/baseline/activity reports (html/docx/pdf)
- `Plans-Proposals/` — plans, proposals, SOWs, remediation plans
- `RFCs/` — RFCs
- `Tech-Briefs/` — tech briefs, opportunity briefs, reference docs
- `Templates/` — templates Alex built
- `Confidential/` — ⚠️ incident-related and internal-sensitive material (see below)

### Confidentiality (hard rule, same as notes)

- **Never copy consumer-PII datafiles** (loan documents, consumer-count datafiles,
  candidate resumes, watchlist extracts, any file whose content is third-party personal
  data) into the vault at all — record the work as a Bard note instead. This is a hard
  line, not a judgment call: a personal-sync vault is not a place for other people's data.
- Incident-related / internal-sensitive deliverables (incident briefings, security
  incident summaries, PII access reviews, legal hold notices, exec-only updates) go into
  `Evidence/Confidential/` and get flagged in `Evidence/README.md`. The CURO/Attain
  matter is **"an incident," never "a breach"** — never reframe, never widen audience.
- Nothing confidential ever goes to Exa or any public web tool (same boundary as notes).

### README

Keep `Evidence/README.md` current in place (it is updated alongside `Todo.md` and
`Bard/Done Archive.md`): list each category, note the PII boundary, and flag the
Confidential folder with a do-not-share warning.

## Vault sync

bard writes files straight to disk, outside the Obsidian app. Obsidian watches the
filesystem, so it picks those writes up on its own; the only thing left is to confirm
Obsidian Sync flushed them, via the `obsidian` CLI (installed at
`/usr/local/bin/obsidian`; the vault is named `Alex`):

```bash
obsidian sync:status vault=Alex   # expect "status: synced"
```

- **Never run `obsidian reload`.** It prints `Reloading...` and never returns. Worse, it
  wedges the CLI: a `sync:status` issued after it also times out, so the sweep ends with
  no sync confirmation at all. Verified 2026-09-03 (scribe) and again 2026-09-04 (bard).
  It is not needed — the filesystem watcher already indexes on-disk writes.
- Wrap the call in a 20 s timeout (macOS has no `timeout` binary; use `python3 -c` with
  `subprocess.run(..., timeout=20)`). A timeout means Obsidian is not running: say so
  and skip sync, never try to launch it.
- There is **no explicit "push now" command** — Obsidian Sync flushes automatically.
  `sync:status` returning `synced` is the confirmation; if it shows pending/syncing,
  report that rather than claiming it's done.
- Never use `sync off` / `reload` / `restart` / destructive `sync:restore` in a sweep.
  Only `sync:status` (read-only) is part of the flow.

See `references/obsidian-setup.md` for the root `Todo.md`, `Bard.base`, hub-note
template, and the one-time graph-color-group setup.
