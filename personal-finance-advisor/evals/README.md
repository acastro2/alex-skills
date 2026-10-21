# Evals: personal-finance-advisor

Safe-run rules (repo standard): run each `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read"`, each in its own process group,
and put workspaces under `~/.agents/skill-workspace/alex-skills/`, never in
this repo. Grade yes-or-no expectations in code or with Jev; send only the
unsure ones to an LLM grader.

Cases 1 and 2 assume the private overlay (household rules and account map)
is loaded alongside the skill; the expected outputs say what changes
without it. All prompts are synthetic. Never put real account data, real
balances, or real institution names tied to the household in an eval.
