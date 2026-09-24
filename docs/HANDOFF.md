# HANDOFF — scribe speaker diarization

Updated: 2026-09-24 15:50 CDT

## Current state

- Build done: tickets 01–04 complete and verified; ticket 05 (phase-2 spike) decided with a
  real experiment. All tests pass (69). Nothing committed — the working tree is Alex's to
  review and commit.
- PR review 2026-09-24: 0 blockers; follow-ups fixed same day — uncached offline model now
  `skipped` with a hint, warning when spans label no turn, natural speaker-label sort,
  spec/doc reconciliations.
- Artifacts: spec `.scratch/scribe-diarization/spec.md`; tickets
  `.scratch/scribe-diarization/issues/01..05` (all items ticked); phase-2 decision
  `.scratch/scribe-diarization/phase2-decision.md`.
- Acceptance (real audio, real pipeline): AAB 284/294 turns labelled, 8 speakers; 1:1
  70/72, 2 speakers; presenter spot-check matches the prototype; Alex long-turns 90%,
  Greg long-turns 81% at turn resolution (prototype span resolution: 88/90); short
  backchannels still collapse to the dominant label. Vault untouched; audio deleted.
- Phase-2 experiment: same-voice 0.58–0.82, cross-voice 0.03–0.20, margin +0.569 with
  clean slices; mixed-speech slices collapse to +0.055.

## Decisions

- Phase 1 shipped in code: anonymous speaker labels on HiDock notes via mlx-audio +
  `mlx-community/Nemotron-3-Diarization`; graceful degradation (`skipped`/`failed`).
- Phase 2 protocol fixed by experiment; implementation not started.

## Top 3 next actions

1. Alex: run `/pr-reviewer` over the diff, then commit.
2. When wanted: build phase 2 from `.scratch/scribe-diarization/phase2-decision.md`.
3. Backlog: the device still holds Sep 1–23 recordings; first real `/scribe` run exercises
   the new path end to end.

## Blockers

None.

## Pointers (do not rediscover)

- Spec with all evidence and caveats: `.scratch/scribe-diarization/spec.md`
- QC artifacts (throwaway): `/private/var/folders/jj/bnbv9l314fvfd3mx1z_fzd0m0000gn/T/opencode/scribe-diar-smoke/`
  (`full.json`, `rec51.json`, `qc3.py`, `anchors_rec51.py`; temp dir may be cleaned)
- Headline numbers: 1.96 s / 72-min call; 198 MB model; 8-speaker cap; `HF_HUB_DISABLE_XET=1`
  needed once for the download; short backchannels weak, substantive turns 88–96%.
- Device still holds Rec94 (AAB) and Rec51 (1:1) if re-tests are needed.
- Session with the full conversation: `ses_f2b19eaa6ffeGBIQnPXt6q27xw`
