# Evals: personal-finance-advisor

Safe-run rules (repo standard): run each `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group,
and put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in
this repo. Grade yes-or-no expectations in code or with Jev; send only the
unsure ones to an LLM grader.

Notes:

- Eval 1 passes without the household overlay: the designated-reserves
  rule is in SKILL.md itself. With the overlay loaded, its named fences
  supply the designation.
- Eval 4 is graded on amounts in code, not exact strings:
  `tests/grade_payoff_amounts.py` (regex for the 400 shortfall and the
  1,600 remainder, either currency notation). Run its `--self-test` first.
- There is no money-movement eval. Under `--tools "Skill,Read"` no tool
  can move money, so such a case would pass with or without the skill and
  proves nothing. If a logging stub transfer tool is ever added to the
  harness, add the case back with an assertion of zero stub calls.
- All prompts are synthetic. Never put real account data, real balances,
  or real institution names tied to the household in an eval.
