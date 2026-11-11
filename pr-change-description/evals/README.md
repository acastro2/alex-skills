# Evals: pr-change-description

Safe-run rules (repo standard): run each `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group,
and put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in
this repo. Grade yes-or-no expectations in code or with Jev; send only the
unsure ones to an LLM grader.

Notes:

- Prompts write the fixture folder as `{FIXTURES}`; the runner copies `files/` to `<iteration>/fixtures/` and fills it in.
- The skill gathers facts with `git` and posts with `gh`. Under
  `--tools "Skill,Read"` neither runs, so each case gives the command
  outputs as fixture files in `files/<case>/`. The runs cannot post or
  touch a real PR. The publish and render-check steps (section 3) are not
  tested here; the evals check only that a run does not claim them.
- Baseline: the same prompt with `--disallowedTools "Skill(pr-change-description)"`.
  The baseline keeps the Skill tool, so it can still load `alex-voice`, as the
  real host does. Checked 2026-11-11: the deny rule returns "Skill execution
  blocked by permission rules".
- Expectations start with `[code]` (counted or matched in code) or `[jev]`
  (one Noul each). "Every number of 11 or more appears in the fixtures" is a
  code check: it lists each number in the body that no fixture contains.
- All fixtures are synthetic. The PR numbers, hashes, tickets and incidents
  are made up and must stay internally consistent: the shortstat lines match
  the line-count tables and the diff excerpts.
- The tooling lives in `../tests/`. Run, then grade:
  `python3 tests/run_iteration.py <workspace>/iteration-N`, then
  `MERMAID_DIR=<dir> python3 tests/grade_code.py <workspace>/iteration-N`, then
  `python3 tests/grade_jev.py <workspace>/iteration-N`. `MERMAID_DIR` is a temp dir
  with `mermaid_parse.mjs` and `npm install mermaid@11.4.1 jsdom@25.0.1`.
  The runner writes `<case>/<config>/run-1/`, the layout `aggregate_benchmark` reads.
- The number check also flags correct derived numbers (1501 - 558 = 943, or a
  status code the diff leaves out of a set). Check each flag by hand and record
  the verdict with its reason in `overrides.json` in the iteration folder.
- Iteration 1 (2026-11-11) found that Opus wrote a zero-width space before each
  Mermaid fence. That breaks the fence on GitHub, so every case with diagrams
  now has a parse check.
