# Eval grading with Jev

Most skill eval expectations are yes-or-no claims about an output ("Flags the SQL interpolation as a Blocker"). Grade them as one Noul each, all in one call per output. You get a calibrated probability per expectation in about a second, and only the unsure ones need an LLM grader. Why: an LLM grader reads the whole output once per run and returns prose verdicts that drift between runs; Jev gives the same number for the same evidence and shows which verdicts are close calls.

Measured 2026-10-07 on a `reviewer` eval output: six expectations in one call, 862 input tokens. The four the output met scored 0.82 to 0.99. The two it failed (a call offer ranked as a Blocker, a claim that a check passed when no tools ran) scored 0.04 and 0.05, which matched the human grading.

## 1. Split the expectations

| Expectation kind | Grade it with |
| --- | --- |
| Countable or exact: word count, number of findings, a string or line number present, a file exists, valid JSON | Code (`wc`, `grep`, `jq`, a parser). Jev does not count. |
| A size comparison: "much shorter", "longer than", "under 150 words" | Code: measure both sides. Measured 2026-10-07: Jev passed a rewrite as "much shorter" at 0.84 when it was about the same length as the original. |
| Exact words: a verdict that must say "Fix first" or "Rethink", a named label | Code (`grep`). Jev gave 0.78 to an output that had neither word. |
| A tool call or effort setting in a transcript, or anything about what the run did (which tools ran, whether it could have looked a fact up) | Code over the transcript's tool-use events. The output alone cannot show it: if you grade from the output, pass the facts in their own `state` field (such as `tools_run`), or skip the expectation and say so |
| A judgment about what the output says or does | Jev Noul |
| A category: which severity, which route, which tool | Jev Choice |

## 2. Build the request

- `state`: the output under test, as JSON with named parts when you need more than the output: `{"task": "...", "output": "...", "tools_run": ["..."]}`. Add only the context a question needs. A fact the output cannot show by itself (which tools actually ran, what the fixture contains) goes in its own field, so a question can point at it.
- One question per expectation. Use the expectation's index as the ID (`e1`, `e2`), so results map back to `evals.json`.
- Rewrite each expectation as a literal, positive question about a named part of `state`:
  - "Flags the CSV endpoint as unrequested scope" becomes "Does `output` say the CSV endpoint was not asked for?"
  - "Does not claim a check passed unless it ran it" becomes "`tools_run` lists the tools that ran. Is it true that `output` makes no claim that a script, test, or check passed?"
  - "Does not rank the call offer as a Blocker" becomes a Choice: "Which severity does `output` give the call offer?" with `Blocker`, `Should-fix`, `Nice-to-have`, `Not mentioned`.
- **Negated expectations** ("does not claim", "does not ask", "never"): ask the positive question and invert the answer in code. "Does not ask for facts it could look up" becomes "Does `output` ask the user for a fact that is in `state` or could be looked up?", and a high probability means the expectation fails.
- **Define severity options by meaning, not by label.** Outputs use their own headings ("Major gaps", "Minor", "Critical"). Write each criterion so any heading maps to it: `Blocker`: "in the most severe group, must be fixed before it ships (Blocker, Critical, Major)"; `Should-fix`: "in a middle group (Should-fix, Significant)"; `Nice-to-have`: "in the least severe group (Nice-to-have, Minor, Nit)"; `Not mentioned`.

## 3. Decide pass or fail

| Result | Verdict |
| --- | --- |
| Noul at 0.80 or more, or the Choice picks the expected option at confidence 0.80 or more | Pass |
| Noul at 0.20 or less, or the Choice picks another option at confidence 0.80 or more | Fail |
| Anything between | Unsure: send only these expectations to the LLM grader (`skill-creator/vendor/claude/agents/grader.md`), with the output |

Record the probability in the evidence so a reader sees how close each call was.

## 4. Write grading.json

Use the skill-creator schema (`skill-creator/vendor/claude/references/schemas.md`, section `grading.json`), so the viewer and the benchmark scripts read it unchanged:

```json
{
  "expectations": [
    {"text": "Flags that no reason for the delay is given", "passed": true,
     "evidence": "jev noul 0.98 (jev-1.13-free, 2026-10-07)"},
    {"text": "Has at most one grill question", "passed": false,
     "evidence": "code: 2 lines start with a question marker"}
  ],
  "summary": {"passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5}
}
```

## Before you trust it on a new eval set

Measured 2026-10-07 on 10 `reviewer` outputs (76 verdicts): 61 of 62 firm verdicts matched the reference grades, 11 landed in the unsure middle. The middle clustered on expectations about the run ("asks a question it could look up") and on missing items ("marks it not verified"): grade those from the transcript or with the LLM grader.

Grade two or three outputs whose answers you already know. If a question disagrees with the known answer, rewrite the question (more literal, positive, pointed at a named field) before you blame the output. Keep the Jev request bodies next to the run, so a later reader can re-ask the same questions.
