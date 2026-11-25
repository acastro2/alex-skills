# Phase 8 prune report (2026-11-25)

OpenCode only, default model `cursor/claude-haiku-5-5`. Raw JSON: `/tmp/opencode/prune/<rule>.run{1,2}.json`.
Scenarios: `~/.agents/skills/harness/evals/scenarios/`.

| rule | scenario | on (r1, r2) | off (r1, r2) | fired on? (r1, r2) | verdict |
|---|---|---|---|---|---|
| egress | egress.json | 0.97 | 0.07 | yes (1) | keep (clear effect; no re-run needed) |
| routing-hint | routing-hint.json | 0.97, 0.95 | 0.95, 0.94 | yes, yes | candidate-to-remove (agent already routes to archeologist without the hint) |
| inject-ui | inject-ui.json | 0.53, 0.33 | 0.54, 0.65 | yes, NO | candidate-to-remove (no gain; noisy; r2 rule did not fire) |
| inject-coding | coding-worker.json | 0.18, 0.05 | 0.02, 0.02 | yes, NO | inconclusive: both arms fail the expectation (agent never loads `coding`), so the rule does not work either |
| inject-links | links.json | 0.57, 0.67 | 0.69, 0.60 | NO, NO | inconclusive: rule never fired in the eval; check why (tool name or push detection) before judging |
| nudge-wrapup | none | n/a | n/a | n/a | not run: fires only for a worker session (`ev.parentSession`) past its time budget. A standalone `opencode run` has no parent, so the moment cannot happen |
| compact-state | none | n/a | n/a | n/a | not run: needs a forced compaction, not possible in an eval run |

Notes
- `changes` threshold is |on-off| >= 0.3. Only egress passes.
- Run 2 re-ran every rule with |on-off| < 0.3 in run 1 (noise check). inject-ui run 2 had a delta of -0.32 in the wrong direction (off better), so it is noise, not a benefit.
- Scenarios added: `egress.json`, `inject-ui.json`, `routing-hint.json`. Existing: `coding-worker.json`, `links.json`.
- Follow-ups for the parent: (1) inject-links and inject-coding/inject-ui fired 0 in some "on" runs: check the OpenCode tool.after path in the eval env. (2) Do not remove rules on this data alone: Haiku, one scenario, two runs each.
