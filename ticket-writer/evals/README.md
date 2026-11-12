# Evals: ticket-writer

Safe-run rules (repo standard): run each `claude -p` eval with
`--strict-mcp-config --tools "Skill,Read" --model claude-opus-5-5`, each in its
own process group (`start_new_session=True`), and put workspaces under
`~/.agents/skill-workspace/alex-skills/ticket-writer/`, never in this repo.
Grade yes-or-no expectations in code or with Jev; send only the unsure ones to
an LLM grader. After a run, check that none of your `claude -p` is left:
`pgrep -fl 'claude -p'`.

Notes:

- No run can reach Jira. `--tools "Skill,Read"` removes Bash, and
  `--strict-mcp-config` removes the Atlassian connector. So each prompt says
  "there is no shell or Jira access", points at fixture files, and asks for the
  MCP calls the run would make (a) and the issue title and body (b). The evals
  grade the plan, not a real write. The real write calls stay NOT RUN, as
  `references/jira.md` says.
- Prompts write the fixture folder as `{FIXTURES}`; the runner copies `files/`
  to `<iteration>/fixtures/` and fills it in.
- Baseline (config `without_skill`): the same prompt with
  `--disallowedTools "Skill(ticket-writer)" "Read(//<home>/.agents/skills/ticket-writer/**)" "Read(//<home>/.claude/skills/ticket-writer/**)"`.
  The baseline keeps the Skill tool, so it can still load `alex-voice`.
  Checked 2026-11-12: the Skill deny returns "Skill execution blocked by
  permission rules". The Skill deny alone is not enough: in iteration-1 the
  denied baseline then read `SKILL.md` and `references/jira.md` with the Read
  tool. So the baseline also denies Read on the skill folder, at both paths
  (`~/.claude/skills/ticket-writer` is a symlink to the repo folder). Checked:
  both paths return "File is in a directory that is denied by your permission
  settings", and `jev/SKILL.md` stays readable. The runner records
  `skills_called`, `blocked` and `ticket_writer_loaded` in each run's
  `timing.json`. Check from the transcripts that no baseline run got the skill
  text, and that each with_skill run loaded it.
- The runner gives each run a neutral working directory (`<iteration>/cwd/<hex>`).
  Why: the run folder name holds the config, and in the first pass a baseline
  run read it from its cwd and said it was a baseline. Use `--configs
  without_skill` (or `with_skill`) to rerun one config.
- Expectations start with `[code]` (matched in code) or `[jev]` (one Noul
  each). Negated expectations are asked as a positive question and inverted in
  `grade_jev.py`. Code checks that look for a forbidden call (`createJiraIssue`
  in an update, `remotelink`) ignore lines with a negation word ("do not call
  createJiraIssue"). Check each such verdict by hand and record a correction in
  `overrides.json` in the iteration folder:
  `{"<case>/<config>/run-<k>": {"e3": {"passed": true, "reason": "..."}}}`.
- All fixtures are synthetic: project key `PROJ`, site `<site>.atlassian.net`,
  made-up people, `example-org` for the repo. The two Jira metadata shapes
  (`issue-types.json`, `story-fields.json`) follow the REST createmeta shape and
  were not captured from a live call. Never put a real site, key or person here.
- Cases: `create-story` (full create with an AC custom field), `update-merge`
  (merge into an existing item), `missing-type` (no Spike type: ask, do not fake),
  `pr-link` (no MCP tool writes a remote link).

## Run and grade

```
W=~/.agents/skill-workspace/alex-skills/ticket-writer/iteration-1
python3 tests/run_iteration.py $W --runs 1        # add --configs without_skill to rerun the baseline only
python3 tests/grade_code.py $W
python3 tests/grade_jev.py $W
```

The runner writes `<case>/<config>/run-1/`, the layout `aggregate_benchmark`
reads (`outputs/answer.md`, `transcript.jsonl`, `timing.json`). `grade_jev.py`
calls the `jev` CLI (`~/.local/bin/jev --raw <request.json>`), keeps each
request and reply as `jev_request.json` and `jev_response.json`, and writes
`grading.json`. A verdict between 0.20 and 0.80 is `null` in `grading.json`
and counts as not passed; list those and send them to the LLM grader.

## Trigger evals

`trigger-evals.json` holds 12 queries (6 should trigger, 6 near misses) in the
format `skill-creator/vendor/claude/scripts/run_eval.py` reads:
`[{"query": "...", "should_trigger": true}]`.

Do not run `run_eval.py` itself. It starts `claude -p` with no
`--strict-mcp-config`, no `--tools` and no process group, and it writes a temp
command file under `<repo>/.claude/commands`. So a near miss such as
"transition PROJ-9 to Done" would run with the live Atlassian connector. Its
trigger test also looks for a made-up `ticket-writer-skill-<uuid>` name, so a
call to the real `ticket-writer` would not count.

Use `tests/run_triggers.py` instead:

```
python3 tests/run_triggers.py ~/.agents/skill-workspace/alex-skills/ticket-writer/triggers-1 --runs 2
```

Each query is one `claude -p` (`--strict-mcp-config --tools "Skill,Read"
--model claude-opus-5-5`), in its own process group, in a neutral cwd under the
output folder, with a 180 s timeout. It tests the live skill through the
`~/.claude/skills` symlink. Triggered = a Skill call whose skill is
`ticket-writer`. It also records Reads of ticket-writer paths and any tool other
than Skill or Read (`other_tools`; none is possible under `--tools`). Output:
`results.json` (per query: runs, triggered, pass; plus precision and recall at run
level) and every transcript. A should-trigger query passes at a rate of 0.5 or
more; a near miss passes below 0.5. Before a full run, check the runner on one
should-trigger and one near-miss query with `--runs 1 --indices 0,10`.

## Known weak spots in the evals

- The `mirrors` code check (`Mirrors the ACs into customfield_10234`) accepts
  `Given`, `AC-0n` or "acceptance criteria" within 300 characters after
  `customfield_10234`. A placeholder such as `"<the AC block below>"` passes. Both
  configs pass it, so it does not separate with_skill from without_skill. Read the
  call arguments by hand when it matters.
- Case 1 changed after iteration 1. Iteration 1 named the project in the prompt
  ("... in PROJ ..."), and the with_skill run took that as the project
  confirmation. From iteration 2 the prompt names no project key, so "Asks Alex to
  confirm the project" tests the real step. The fixtures are unchanged:
  `issue-types.json` holds no project key, and the `[jev]` question text still says
  "(PROJ)".
