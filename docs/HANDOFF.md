# HANDOFF — Jev typed gates in ea-projects-curator + archeologist

Updated: 2026-09-29 11:14 CDT

## Current state

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

1. Review and commit the four changed files (Alex commits; `jev-routing/SKILL.md` is staged
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
