# HANDOFF — scribe speaker diarization + no-withholding policy

Updated: 2026-09-24 17:00 CDT

## Current state

- Phase 1 is shipped **and now in use**: 22 HiDock recordings re-transcribed with speaker labels
  and their notes re-rendered — the 15 Sep 21–23 notes, the 6 recordings previously held on
  HR/personal grounds (Sep 1–4), and today's Rec96 (`Tech Ops Leader Meeting`).
- Policy change (Alex, 2026-09-24): **nothing is held and nothing is withheld.** The HR-data
  segment withholding rule is removed from `scribe/SKILL.md`; the 6 recordings previously
  skipped as `tier1`/personal now have full notes and their `skipped` entries are gone.
- The two `.trimmed.json` files are retired to
  `~/.scribe/backup/2026-09-24/retired-policy-files/`; no trimmed copies are produced any more.
- Names without biometrics: the skill tells the agent to name speaker labels from the transcript
  text itself — a self-introduction, someone being addressed, or an exchange that settles it —
  hedged as `speaker 1 (likely Alexandre Castro)` with the quote recorded in provenance. There is
  no script and no enrollment. Applied to the vault on 2026-09-24: **16 of 22 labelled notes
  named**; the rest gave no usable evidence. A label the text does not settle stays `speaker N`.
- Eval of the naming step (2026-09-24, ground truth = the Teams note for the same meeting, 3
  meetings with 6-8 speakers, re-transcribed with diarization): across 7 agent runs it emitted 22
  names — 17 exactly right, 1 wrong, 1 imprecise, 3 on truth too thin to verify. Roughly half the
  labels with available truth stay anonymous. Two instruction fixes came out of it: a bare
  acknowledgement ("Yeah.") is not evidence of being addressed, and a first name shared by
  several attendees names nobody. Repeatable case: `scribe/evals/evals.json` eval 5 with
  `tests/fixtures/transcript_hidock_naming.json`.
- Rec07 summary fixed 2026-09-24 after the labels disagreed with it: the Anova/Vault design, the
  pen-test invite and Matt's break-glass access are Alex's, the CSO offer was Alex's news to
  Steve, and the SANS course is not approved. Owners now follow the labels.
- `bard/SKILL.md` updated for the new note shape: the false "HiDock notes have no speaker
  labels" line is replaced by the hedged-label rule, and people/HR material is explicitly
  distilled like any other durable knowledge into the `People` hub (Alex, 2026-09-24).
- Committed and pushed by Alex on 2026-09-24: `f80eb88` (diarization), `b085f4e` (edge cases and
  tests), `a9555e6` (speaker hinting), `83ac605` (naming process; the hint script removed).
- Verified limit: re-transcribing is not text-stable — 11 of 15 re-runs were byte-identical, 4
  differed by 1–115 words. Recorded in `scribe/SKILL.md` → Known limits.
- Diarization misses seen in the wild: Rec82 (63-min, three attendees) returned a single label;
  Rec88 hit the 8-speaker cap.

## Decisions

- Phase 1: anonymous labels on HiDock notes (mlx-audio + `mlx-community/Nemotron-3-Diarization`).
- No HR withholding and no holding anywhere; every recording becomes a full note, 2026-09-24.
- Phase 2 (voiceprint → names) is **rejected**, not deferred: biometric consent, volunteers-only
  coverage, and Teams already names the multi-person calls. See
  `.scratch/scribe-diarization/phase2-decision.md`.

## Top 3 next actions

1. Review the rewritten notes, especially the 6 newly promoted Sep 1–4 ones.
2. If you want names on a HiDock call, tell me which label was whom and I will re-render that
   note with them — Alex's own statement, never a tone guess.
3. Optional backlog: the Sep 8–18 HiDock notes still carry no speaker labels; the same
   transcribe-and-name pass applies. Also revisit the Rec07 summary noted above.

## Blockers

None.

## Pointers (do not rediscover)

- Rollback material for today: `~/.scribe/backup/2026-09-24/` (old JSONs, old notes, retired
  policy files). MP3s are deleted as always; the device still holds every recording Sep 1–24.
- Spec + evidence: `.scratch/scribe-diarization/spec.md`; tickets `issues/01..05`.
- Headline numbers: 72-min call diarized in 1.96 s, 198 MB model, 8-speaker cap; the diarizer
  download needs `HF_HUB_DISABLE_XET=1` once.
- Session: `ses_f2b19eaa6ffeGBIQnPXt6q27xw`
