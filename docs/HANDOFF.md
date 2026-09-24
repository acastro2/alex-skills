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
- Known wrong record to revisit: `2026-09-01 1339 Architecture 1 on 1 - Steve Rake.md` — its
  summary (written 2026-09-03) assigns actions to Steve that the labels now put on speaker 1
  (Alex), e.g. the AWS pen-test invite. The labels are the better evidence; the summary needs a
  rewrite, not a patch.
- Uncommitted: the diarization build, the hint step, plus the SKILL.md policy edit. The working
  tree is Alex's.
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

1. Alex: review the rewritten notes (especially the 6 newly promoted Sep 1–4 ones) and commit.
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
