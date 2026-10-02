# HANDOFF — Jev typed gates in ea-projects-curator + archeologist

Updated: 2026-10-01 CDT

## 2026-10-01 — scribe runs in parallel (uncommitted)

- Scope chosen by Alex: the two real bottlenecks (transcription pool + per-meeting summary
  subagents), not source-overlap; that lane stays unbuilt.
- `scribe/scripts/hidock_batch.sh` is now a pool: up to `jobs` `transcribe.py` runs at once
  (arg 3, default 3, capped at 4), the MLX env builds once before the pool, a failed file keeps
  its MP3 and the script exits 1. Measured on real audio: the same 6 recordings took 112 s
  serial vs 66 s 3-wide; that night's live serial run was 246 s end to end. Per-file wall grows
  ~1.4x under the pool.
- `scribe/SKILL.md` + `references/hidock.md`: in a batch, one subagent per meeting runs steps
  1–3 (label naming + summary file); the session keeps glossary, `write_note.py`, state, sync.
  Subagent rules: this session's model only, no web tools, only the two meeting files; naming
  now says to rename every occurrence (`turns[].speaker` and `speakers`).
- Proof for the skill text: OpenCode demo, two fixture meetings, two `general` subagents in
  parallel (sessions `ses_f058378c5ffeV7wLOcUIxMUG9E`, `ses_f058378c6ffex5Kmu3M8Nxxltk`);
  parent wrote both notes; naming rules held (Bruno Costa from his self-intro, ambiguous "Ana"
  and a "Yeah." label left unnamed). Demo workspace was `$TMPDIR/opencode/scribe-parallel-demo/`.
- `scribe/tests/test_hidock_batch.py` added (pool concurrency, failure handling, jobs clamp):
  red against the old script, green after. Scribe suite 81 passed; validator PASS.
- Not yet run: a live `/scribe` with the pool on a real batch — do that next.

## 2026-10-01 — bard goes daily: cursor fixes in bard + scribe (uncommitted)

- Alex is moving `/bard` from weekly to daily (scribe is already daily, curator stays weekly).
  The curator does not read bard output, so there is no coupling to break (`grep -ri bard
  ea-projects-curator/` returns nothing).
- Fixes for daily cadence, text-only (no script change):
  - `bard/SKILL.md`: scribe notes are selected by a `scribe_seen` path set in
    `.bard-state.json`, not by meeting `date` (a late note fell behind `watermark` and was
    lost) and not by mtime (vault sync can rewrite it). Absent set → seed with notes dated
    > 7 days before `watermark`. Pi/Cortex also select by file mtime, so sessions that span
    the watermark are not missed. Comms-zero rule is now per working day; weekend-only windows exempt.
  - `scribe/SKILL.md` + `references/hidock.md`: per-source cursors `teams_last_run` /
    `hidock_last_run` (fallback `last_run`). A cursor moves only when its source finished.
    Teams window = 48 h before its cursor; `no-transcript`/new `not-ready` skips inside it are retried.
- **First live `/scribe` run with the new cursors: 2026-10-02 02:42Z.** Both cursors fell back to
  `last_run` and now exist in `.scribe-state.json`. Window Sep 29 14:51Z → now; 2 Teams notes + 6
  HiDock notes written; Rec25 skipped as `teams-covers` (Teams window matched to seconds, but the
  calendar had 4 events at 09:00, so the strict "one event" test failed: Alex's call). Not yet done:
  `Bard/.bard-state.json` has no `scribe_seen` until the next `/bard`; Obsidian was not running, so
  no sync check. The two Teams VTT files were hand-copied from inline payloads (cue counts 323/114
  are the only check). Teams retries: only the 4 non-standup `no-transcript` skips were re-read.
- Verified: validator PASS (37), `pytest scribe/tests ea-projects-curator/tests scripts/tests`
  141 passed (needs `--with pyusb --with pyyaml`), pre-commit pass. Not yet run live:
  first daily `/scribe` + `/bard` will seed `scribe_seen` and the cursors — check both state
  files after that run.

## 2026-10-01 — AI Program theme tie-break

- Added "AI wins the tie" to `ea-projects-curator/SKILL.md` (Field mapping › Theme; Coherence
  check) and to the `theme` gate in `references/jev-gates.md` (also "seven" → "eight" themes).
  Why: the AI Program view filters on `Theme` only, so an AI row tagged Security/Platform was
  invisible there. Live Jev check: triage agent → AI Program 1.0; Privileged Access Renewal →
  Security Hardening 0.97. Validator + pre-commit pass.
- **Live check done 2026-10-01 (cookie refreshed):** 47 rows, 18 AI Program; no clear AI row
  under another theme. Only open question: row 46 "Engineering Intelligence Service
  Identities" (Governance) — AI Program if Engineering Intelligence is an AI/agent system;
  Alex to confirm. Jev on row text alone: 0.17 (no local docs found to settle it).
- **Blind Jev run done 2026-10-01** (Alex's call; run in OpenCode, where the Claude Code
  classifier does not apply). All 47 rows, gates `status`/`decision_needed`/`theme`, state =
  row text only (no person fields, no current labels): 85/141 cells agree, 12 high-confidence
  disagreements, 77 cells < 0.80. `theme` is the confident gate on row text; most `status`
  flips are thin evidence (closure/outcome not in `state`). Report `.scratch/jev-board/report.md`
  (+ `results.json`, `run.py`). Read-only; every move goes through the review table. OpenCode
  Zen vendor approval stays open for Security.
- **Jev findings applied 2026-10-01** (Alex approved all 12 by line). 8 written and
  GET-verified: Theme rows 1 (→Security Hardening), 27/30 (→Governance), 28/45 (→Platform
  Foundations); Status (his column) row 4 5→4, row 33 1→4; DecisionNeeded row 37 →Process
  Owner. 4 held: row 15 stays AI Program (repo is an ML stack; row text carries no AI
  signal), row 22 stays None (board agreed 16 Sep; Jev graded stale text), row 26 superseded
  row, row 43 Closed is immutable. `curated.json` written; each hold sits in `open_items`.
- **Open decision for Alex:** whether to add more Jev questions (impact kind, outcome at close)
  and dedupe the criteria into `jev-gates.md`; recap/intake classification kept off Jev on
  purpose (transcript content to an external endpoint).

## Current state (2026-09-29)

- **Shipped this session (uncommitted):** `ask_jev` typed gates wired into two skills. Both
  edits are additive — a `## Typed gates — ask_jev` section in each `SKILL.md`, a short
  cross-reference where the gate fires, and one new reference file per skill:
  - `ea-projects-curator/SKILL.md` + `ea-projects-curator/references/jev-gates.md` —
    gates the five candidate judgments (`row_qualifies` noul, `status`, `decision_needed`,
    `theme`, `dedupe`) and routes low-confidence results to the review table as
    `Needs you? yes` lines. Reference file carries the ready-to-run request body.
  - `archeologist/SKILL.md` + `archeologist/references/jev-gates.md` — gates the mixed
    question type, the G/I tier promotions, and `evidence_strength`.
- **Why typed:** the same judgments ran in prose every run, so labels could drift; a typed
  answer carries a confidence, so uncertain calls become questions instead of labels.
- **Design rules the edits enforce:** Jev never passes a hard gate (exclusion screen,
  `not_doing`, the three invariants); the archeologist's confidence rubric outranks a Jev
  score; `Status` stays Alex's column; `state` sent to Jev is a short summary, never a raw
  transcript, credential, or privileged text; an unavailable `ask_jev` is reported, never faked.
- **Verified 2026-09-29:** `scripts/validate_skill_graph.py` PASS (37 skills); Codex
  `quick_validate.py` valid for both; `pytest scripts/tests ea-projects-curator/tests` 63
  passed; `pre-commit run --files` all hooks pass; four live `jev` calls with the exact new
  bodies (curator 5 answers, `dedupe` 0.99; archeologist `question_type` Mixed 0.53 →
  union of source sets, `evidence_strength` 1.38 lean with the rubric overriding to LOW); both
  archeologist behavioural evals re-run, 13/13 expectations pass, briefings in
  `~/.agents/skill-workspace/alex-skills/archeologist/2026-09-29-jev-gates/`.
- **Not done:** bard and scribe were deliberately left alone (bard is lower stakes and feeds
  the curator; scribe's rules are already deterministic). No new agents: the earlier decision
  "no router agent, call `ask_jev` directly" holds, and Jev is its own model so no lane is pinned.

## Top 3 next actions

1. Review and commit the changed files (Alex commits; these now include the 2026-10-01 scribe
   parallel work — `scribe/scripts/hidock_batch.sh`, `scribe/tests/test_hidock_batch.py`,
   `scribe/SKILL.md`, `scribe/references/hidock.md`; `jev-routing/SKILL.md` is staged
   as added but deleted on disk — the leftover of the earlier revert, decide what to do with it).
2. Run a real curator `--maintain` week with the gates on, then move the thresholds
   (0.80 / 0.20 defaults) only if the review table shows they are wrong.
3. If wanted, wire the same gate into `bard` (intake gate, `type`, priority).

## Blockers

- The three questions from the earlier Jev session are still unanswered and still block the
  corpus/shortlist/EA-intake work (not this work): what "EA intake" means in Alex's words,
  which corpus to classify, and what produces the shortlist. `ea-projects-curator` does not
  need them — its corpus is the board itself.

## Pointers (do not rediscover)

- Stuck session, read-only diagnosis: `ses_f12264570ffeHIM8tJj2BWDNfG` — every turn since
  2026-09-29 10:47 fails with `OpenAI Chat assistant messages only support text, reasoning,
  and tool-call content for now` (protocol lowering, not the provider). Untested workaround:
  switch it back to `claude-code/claude-opus-5-5` or `muse-spark-1.3-contributor`.
- Jev wiring: `~/.local/bin/jev`, `~/.local/bin/jev-mcp` (MCP server `jev`, tool `ask_jev`),
  registered in `~/.config/opencode/opencode.jsonc` and `~/.claude.json`. Endpoint
  `https://opencode.ai/zen/v1/systemone`, model `jev-1.13-free`.
- The `score` answer is a float on the ordered scale with a `legend` — read the lean, not the
  nearest integer (recorded in `archeologist/references/jev-gates.md`).

## Prior workstream — scribe speaker diarization (2026-09-24, unchanged)

State: Phase 1 shipped and in use; "nothing is held and nothing is withheld" policy live;
Phase 2 voiceprinting rejected, not deferred. Its own next actions were: review the rewritten
notes (the 6 newly promoted Sep 1–4 ones), name labels on request from Alex's own statement,
and optionally re-transcribe the Sep 8–18 HiDock notes. Full detail: git history of this file,
`ses_f2b19eaa6ffeGBIQnPXt6q27xw`, and `.scratch/scribe-diarization/`.
