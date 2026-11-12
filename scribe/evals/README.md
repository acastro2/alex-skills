# Evals: scribe

Safe-run rules (repo standard): every `claude -p` run uses `--strict-mcp-config --tools "Skill,Read"`
in its own process group, so it can read fixtures but cannot run a script, reach M365, touch the
HiDock or Voice Memos, or write the vault. Workspaces live under
`~/.agents/skill-workspace/alex-skills/scribe/`, never in this repo.

- The cases test scribe's judgment calls (which memo to skip, which speaker gets a name, what
  counts as a decision, which cursor moves), with the script and connector outputs given as
  synthetic fixtures in `files/`. Names, ids and meetings are made up.
- Baseline: the prompt without the leading `/scribe`, plus `--disallowedTools Skill(scribe)` and a
  Read deny on both scribe folders. A typed `/scribe` loads the skill as a slash command, which the
  Skill deny does not block: iteration-1's first baseline read `references/voicememos.md`. Check
  `timing.json` → `skills_loaded`, and the transcript for "Skill execution blocked", after a run.
- Checks are `code` (regex over the reply) or `jev` (one Noul each, `invert` for negated ones).
  Read every miss and every UNSURE by hand; record the verdict and reason in the iteration's
  `overrides.json`.
- Run, then grade: `python3 tests/eval_run.py <iteration>` (`--configs`, `--runs`), then
  `python3 tests/eval_grade.py <iteration>`, then from `skill-creator/vendor/claude`:
  `python3 -m scripts.aggregate_benchmark <iteration> --skill-name scribe` and
  `python3 eval-viewer/generate_review.py <iteration> --skill-name scribe --benchmark <iteration>/benchmark.json --static <iteration>/review.html`.
  The aggregate's header text ("3 runs each", model placeholder) is the template's; the real run
  count and model are in each `timing.json` and `eval_run.py`.
