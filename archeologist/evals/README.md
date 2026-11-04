# Archeologist behavioural evals

Two cases that assert the **Phase 5 output contract**: summary and references first,
references itemised with a locator and timestamp, a verbatim excerpt for any source the
reader cannot reach, sensitive content returned rather than withheld, and unreachable
stores named instead of reported as empty.

They do **not** test retrieval quality against live stores. Both fixtures simulate the
stores, so the suite is deterministic and touches nothing real.

## Cases

- Case 1: summary and references lead; each source carries a locator and a timestamp; the
  M365 item carries a verbatim excerpt because the reader has no connector for it.
- Case 2: a privileged mail item is returned with its verbatim classification label rather
  than withheld, and Teams is reported unreachable rather than as zero results.

## Running

Give the executor the whole `archeologist/` skill directory and that case's fixture, in a
fresh context. It writes `briefing.md` to a scratch output directory. Grade that file
against the case's `expectations` in `evals/evals.json`.

Where to run it, and what it cannot tell you:

- The fixture is graded on **shape**, not on whether the archeologist searched well. A
  briefing can satisfy every expectation here and still miss the right session in a real
  store.
- **Trigger behaviour is unmeasured.** Nothing here tests whether a host selects this
  skill.
- Results table: **not yet run.** Do not cite this suite as evidence until it has.

## Results

Run 2026-09-16, OpenCode, model DeepSeek V4.1 Flash, one fresh `general` subagent per case.
**With-skill only. Baseline was not run**, so there is no delta. Both briefings were written
to `.skill-workspace/archeologist/2026-09-16-run1/case-N/briefing.md`.

| case | with-skill | baseline | delta | verdict |
|---|---:|---:|---:|---|
| 1 | 7/7 | — | — | — |
| 2 | 6/6 | — | — | — |

Total 13/13.

Both briefings led with the finding summary, itemised their references before any
narrative, and carried a verbatim excerpt for the M365 item the reader could not query.
Case 2 quoted the `Privileged - Attorney Work Product` mail and preserved its label, which
is the behaviour the contract now requires: retrieval returns, the caller filters. Case 2
also reported Teams as `NO DATA` with the connector error, and named Pi, Developer,
OneDrive and opencode as unsourced coverage gaps rather than silence.

These results say nothing about retrieval quality against real stores — see the limits
above.

Run 2026-09-24 (re-run after Source J, Claude web, was added to the skill), OpenCode, model
DeepSeek V4.1 Flash, one fresh `general` subagent per case. **With-skill only. Baseline was
not run**; no delta is claimed. Briefings:
`~/.agents/skill-workspace/alex-skills/archeologist/2026-09-24-run2/case-N/briefing.md`.

| case | with-skill | baseline | delta | verdict |
|---|---:|---:|---:|---|
| 1 | 7/7 | — | — | — |
| 2 | 6/6 | — | — | — |

Total 13/13.

Same contract behaviour as the first run: both coverage ledgers enumerate the stores they
audited and mark out-of-scope stores `not searched — <why>` instead of omitting them.

Run 2026-10-28 (re-run after Source D gained the `--pre` extractor for docx, pptx, xlsx, and
pdf), Claude Code `claude -p`, model Sonnet, `--strict-mcp-config --tools "Skill,Read"`, one
process per case. **With-skill only. Baseline was not run**; no delta is claimed. Briefings:
`~/.agents/skill-workspace/alex-skills/archeologist/2026-10-28-run3/case-N/briefing.md`.

| case | with-skill | baseline | delta | verdict |
|---|---:|---:|---:|---|
| 1 | 7/7 | — | — | — |
| 2 | 6/6 | — | — | — |

Total 13/13. Graded inline: Jev returned HTTP 401. One call was close: case 2 puts a
two-line why-it-matters note and a diagram between the finding and the references. The
narrative (`Primary Context`) still follows the references, so it passes. Re-checked with Jev once its key was fixed (same day): yes-probability 0.66, in the unsure band, so the pass stays a judgment call. These cases do
not touch Source D, so they show no regression in the output contract only. The Evidence
search itself was checked live: an `archeologist` run found a fact that exists only inside
an Evidence docx.

## Trigger card

Safe-run rules (repo standard): run every `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group, and
put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in this
repo.

Run: `python3 scripts/trigger_eval.py --skill archeologist` (7 cases, 3 runs
each, 21 runs). This is the suite the limits above call unmeasured.

What it covers: five real asks must load `archeologist`; two near-misses must
load the neighbour instead (`bard` for writing notes, `scribe` for a
transcript). The card exists because archeologist is read-only and returns a
briefing, while its neighbours write and pull.

No Microsoft 365 or git access is needed. Under `--tools "Skill,Read"` the body
cannot search anything, and this card only measures which skill the router
picks. Prompts are synthetic: no real colleagues, sessions, or PR numbers.

This card was first run on 2026-11-03: 7/7.
