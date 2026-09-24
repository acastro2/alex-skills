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
- Names without biometrics: `scribe/scripts/hint_speakers.py` hedges a label
  (`speaker 1 (likely Alexandre Castro)`) when the transcript's own text identifies it and the
  name is a calendar attendee. Applied to the vault: 3 of 22 labelled notes named (Rec85, Rec87,
  Rec96); the rest had no usable evidence. Conflicting evidence (Rec96's speaker 3, addressed as
  both Brock and Greg) deliberately yields nothing.
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
3. Optional backlog: the Sep 1–18 HiDock notes still carry no labels; the same backfill applies.

## Blockers

None.

## Pointers (do not rediscover)

- Rollback material for today: `~/.scribe/backup/2026-09-24/` (old JSONs, old notes, retired
  policy files). MP3s are deleted as always; the device still holds every recording Sep 1–24.
- Spec + evidence: `.scratch/scribe-diarization/spec.md`; tickets `issues/01..05`.
- Headline numbers: 72-min call diarized in 1.96 s, 198 MB model, 8-speaker cap; the diarizer
  download needs `HF_HUB_DISABLE_XET=1` once.
- Session: `ses_f2b19eaa6ffeGBIQnPXt6q27xw`
