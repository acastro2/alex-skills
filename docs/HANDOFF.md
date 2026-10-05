# HANDOFF — Jev typed gates in ea-projects-curator + archeologist

Updated: 2026-10-05 CDT

## 2026-10-02 — alex-voice rebuild v2, from a much bigger corpus (in progress)

- Ask: drafts "resemble Alex but don't pass by him to himself". Done means a blind lineup
  (real held-out Alex vs skill output, same context) where Alex picks the fakes at chance.
- Diagnosis so far: old corpus was lopsided (200k words of prompts to AI vs ~1k chat, ~300 email);
  core rules push "I think"/"right?" into every register, but real chat and email have ~0 "I think".
- Private corpus (never in this repo): `~/Developer/obsidian/Alex/40 Writing/Voice/corpus/`
  — `email-train.jsonl` (333, automated mail removed), `spoken-train.md` (24 Teams meetings, 70k words),
  `typed.jsonl` (264k words), `holdout/` (68 emails, 8 meetings) reserved for the lineup.
  HiDock transcripts were left out: speaker labels are only "likely Alex" and were wrong in a spot check.
- Teams harvest (chats, then channel posts) runs from a scratchpad script that reads through the
  `m365` CLI token (GET only). It writes `teams-chat.jsonl` and `teams-channel.jsonl` into the corpus folder.
  If the files are missing, rerun the harvest.
- Workflow `alex-voice-analysis` (run `wf_b5b800a9-8f8`) covers email and meetings: triage, then
  6 lenses, then 2 skeptics per claim, then synthesis into the vault note
  `40 Writing/Voice/Voice rebuild 2026-10 findings.md`.
- Email/meetings run done: 161 claims, 112 survived both skeptics. Triage found 79 of 333 emails
  AI-assisted (removed). Findings + 15 open questions in the vault note above.
- Chat harvested: `chat-train.jsonl` (29.9k msgs, 251k words), `holdout/chat.jsonl` (3.4k). Chat run
  `wf_f1e51bb7-0c4` writes `Voice rebuild 2026-10 findings - chat.md`. Channel harvest still running.
- Alex decided (2026-10-04/05): own typing only; frames follow size; lol/swearing mirror the thread;
  chat asks for recipient + last messages; checker seam = CLI; lowercase "i" blocks, short-line period
  warns; AI-tell words block in spoken too; lineup = real vs new only; NEVER offer a call (async).
- SKILL.md core rewritten by hand (caricature trap, marker budget, blockers vs warnings). Snapshot of the
  old skill: `~/.agents/skill-workspace/alex-skills/alex-voice-workspace/snapshot-2026-10-04/`.
- Rewrite workflow `wf_6908f7b5-5e9`: lanes for chat.md, comms.md, spoken.md, fingerprint, checker+tests,
  private exemplars (stratified random, train only), evals; two skeptics + fixer per lane.
- Rewrite landed: 78 checker tests green (call offers now BLOCK, test-first), 22 samples pass, skill
  graph PASS. Exemplar note rebuilt from stratified random train samples. Evals: 21 in evals.json (local).
- Lineup workflow `wf_1a7dff3b-a8b` writes `40 Writing/Voice/Voice lineup 2026-10.md` + `(key).md`:
  chat first-message replies (holdout split per message, so bursts untested), emails, channel posts;
  spoken left out (ASR artifacts make it unfair). DONE: 75 pairs (chat 30, email 29, posts 16); one
  personal email removed. Pre-mark stats: fakes run longer than real (chat median 8 vs 4 words, email
  20 vs 14), email fakes end on a period more (10 vs 4), post fakes have no "!" (real 5 of 16).
- skill-creator review done 2026-10-05: quick_validate PASS; eval iteration-3 (21 evals, new vs Sept
  snapshot, baseline used a partial reconstruction of the Sept exemplars because the lane overwrote the
  original note): 94.3% vs 58.6% mean pass rate. Eval 10 (ask for missing chat context) failed, rule
  reworded in SKILL.md + chat.md, re-run 3/3 pass (`iteration-3b/`). Review page: `iteration-3/review.html`.
  Evals were written from the same findings, so they confirm rule-following, not voice; the lineup does.
- Alex reviewed `iteration-3/review.html` on 2026-10-05: "its fine", no feedback to apply.
- Round 2 (Alex asked to cover the untested registers): chat re-harvested with full chat keys into
  `corpus/chat-full-2026-10-05.jsonl` (38k msgs, 406 chats). Workflow `wf_9666a978-316` builds
  `Voice lineup 2026-10 round 2.md` + key: 30 chat bursts (only post-Oct-3 or holdout messages),
  15 spoken turns (clean verbatim, Alex's call), 10 blog paragraphs (no 6-gram overlap with skill files),
  and a docs/exec PREFERENCE test (new vs old skill; Alex's call, no provable hand-typed docs exist).
- Round 2 built: 61 items (30 bursts, 15 spoken, 6 blog after dropping 4 AI-looking 2024 paragraphs,
  6 docs + 4 exec preference). New harvest had 12% duplicate rows (chat list reordered mid-paging);
  first harvest had 0, so findings stand. Pre-mark stats, both rounds: fakes ~30-60% longer than real
  (bursts 18.5 vs 14 words, spoken 74 vs 52, blog 90 vs 57). New skill docs/exec ~half the old length.
- Blog calibration risk: selector flagged the 2024 Senior Engineer parts as partly AI-assisted
  (em dashes, "Hey there!"). alex-blogger.md treats them as hand-written; needs Alex's call.
- Alex (2026-10-05): 2024 blog posts were AI-assisted but stay as the anchor (noted in alex-blogger.md);
  plan = he marks only round 1's 30 chat items; I fix length and build a fresh round 3.
- Length fix: SKILL.md core rule 3 is now "Say only what you were given, then cut"; checker warns on
  chat > 40 words, comms > 60, blog paragraph > 120 (TDD, 84 tests green).
- Alex marked (2026-10-05, export pasted in chat): email 9/20 caught (45%, at chance), posts 4/6,
  blog 3/6, spoken 1/1; chat (35) and spoken (9) NOT marked yet. Docs/exec preference: he picked the
  SEPTEMBER drafts 10/10 ("would sign"). Merged, not reverted: docs.md/exec.md now keep the old why,
  next-mistake tips, reader question, scope sections, cost of waiting, number meaning, source line,
  plus the new tightness and no chat markers. Core rule 3 now cuts messages only. Docs/exec checker
  bands provisional, fitted on his 10 picks (86 tests green). Email: "Hi," + "Thank you," on EVERY
  email (his rule, overrides the size-gated data); comms.md, SKILL.md, fingerprint, evals 2/8/14/15/20 updated.
- Short lineup (`Voice lineup 2026-10 short.html`, 10 chat + 5 spoken, marks in ~/Downloads): chat 6/10
  caught, spoken 4/5. All identity marks so far: 27/48 = 56% (one-sided p=0.24 vs chance) -> passes
  overall. Weak spot: spoken 5/6 caught (p=0.11, n small); real turns carry more fillers ("you know",
  "so", "yeah") than fakes, which the spoken register avoids on purpose for scripts. Open: Alex's call.
- DONE 2026-10-05: all six it4 failures fixed. Rule fixes: chat asks only when recipient or the answered
  message is missing; length warnings must be acted on; long chat status cut to 40 words before switching
  to comms; docs opener = specific benefit, tips only from given facts, no list repeating a diagram;
  spoken pre-handover check (because, for example, short sentences). Eval fixes: 14 (frame not counted),
  3 (source line may end an exec brief), 10 and 16 (test substance, not template wording; re-graded
  inline with quoted evidence). Iteration-5: 290/293 (99.0%) over 28 runs, 7 fixed evals run twice.
  Only blog evals 4 and 6 still miss 3 checks ("I tried" beat, 2-to-5-sentence paragraphs, "you");
  pre-existing since it3, old skill misses them too, and Alex's lineup scored blog at chance (3/6).
  86 tests, validate_skill_graph, quick_validate all PASS. Not committed (pre-commit not run).
- Round 3 workflow `wf_7113c18f-530`: fresh items (holdout, post-Oct-3 bursts, train-not-exemplar email
  fill since no new human mail exists), returns real vs fake median words per group before handover. Not committed yet (needs pre-commit, then a branch commit when he asks). Next: score his picks vs the key, turn each "why" into a rule,
  rerun the lineup. Likely first fix: shorter defaults in chat and email.
- Then the blind lineup: fresh subagents loading only the skill, given prev/context + a content brief,
  30+ items per register from `holdout/`. DONE = Alex picks fakes at chance, not tests green.

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
