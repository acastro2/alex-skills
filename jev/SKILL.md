---
name: jev
description: "Send your own judgment calls to Jev, TypeSafe's decision model, through the ask_jev tool (or the jev CLI in Pi), and get typed answers with probabilities instead of deciding in prose. Use whenever you would otherwise classify, route, gate, score against a rubric, pick one option from a fixed set, check whether a statement is true of a document, decide if two items are the same thing, or grade an output against expectations, such as skill eval grading. Use it most when the same judgment repeats across many items or runs, when you need a number to branch on, or when the call should be auditable. Not for generating text, math, counting, or comparing dates."
---

# Jev

Jev is a System One model: you send `state` (the evidence) and typed questions, and it returns typed answers with probabilities. It does not write text, call tools, or reason in steps. Use it for the judgments you would otherwise make in prose, so the same evidence gets the same answer next time and an uncertain call shows up as a number instead of hiding in a paragraph.

## When to send a judgment to Jev

Use it when the answer is one of these:

- **A choice from a fixed set**: a route, a category, a status, which skill, which existing record matches (`choice`).
- **Yes or no about the evidence**: does the output flag X, does the doc state Y, does this qualify (`noul`, the probability of yes).
- **A position on a rubric**: severity, quality, risk, evidence strength (`score`).

It pays most when the same judgment runs on many items (grading every eval expectation, labeling every board row), when you need a number to set a threshold on, or when someone will audit the call later.

Keep it out of: generating or rewriting text, arithmetic, counting (words, items, occurrences), comparing dates, exact lookups, and anything a regex or parser can decide. Do those in code or yourself; Jev's own known-limits page lists them as weak spots.

## How to call it

| Host | Path |
| --- | --- |
| Claude Code, OpenCode | The `ask_jev` MCP tool (server `jev`): `{"state": "...", "questions": {...}}` |
| Pi, or when the MCP is missing | `jev -` with the same JSON on stdin; add `--raw` for the API's JSON |

Question shapes:

```json
{"type": "noul",   "instructions": "Does `review` say the email gives no reason for the delay?"}
{"type": "choice", "instructions": "Which severity does `review` give the call offer?",
 "criteria": {"Blocker": "listed under Blockers", "Should-fix": "listed under Should-fix", "Not mentioned": "not in the review"}}
{"type": "score",  "instructions": "How strong is this evidence set for the question?", "criteria": ["LOW", "MEDIUM", "HIGH"]}
```

The default model is `jev-1.13-free` on the OpenCode Zen endpoint. `jev --model jev-1.13` uses the paid model.

## Write questions Jev can answer

- **One judgment per question**, stated exactly. Jev reads instructions literally: when you catch yourself explaining what you meant, that explanation belongs in the instruction or the criteria.
- **Ask in the positive.** Negations and double negatives are a known weak spot. To check "the call offer is not a Blocker", ask a Choice for its severity, not a Noul for "is it below Blocker?". Measured 2026-10-07: on the same short state, the negated Noul gave an unsure 0.39, the Choice gave `Blocker` at confidence 1.
- **Name the part of `state`** the question is about, with backticked paths such as `review` or `ticket.messages[0].text`. Use JSON `state` when the evidence has several parts.
- **Send only what the questions need.** Accuracy drops as unrelated detail grows. Filter first.
- **Give every Choice a way out** ("None", "Not mentioned", "new") when nothing may fit, and define every option in the criteria.
- **Batch independent questions over the same state in one call.** They run in parallel and cannot see each other's answers, so do not write a question that depends on another. Ask a second call only when the first answer changes what evidence you send.
- **For a high-stakes Choice, reorder the options and ask again.** Jev can lean toward the first option; the answer should not change.

## Read the answers

- **Noul**: `noul` is the probability of yes. There is no separate confidence: a value near 0.5 is the model saying it is unsure.
- **Choice**: the answer, a probability per option, and `confidence` from 0 to 1 (how concentrated the probabilities are).
- **Score**: a position on the ordered levels, such as `1.38` on `0=LOW 1=MEDIUM 2=HIGH`, plus confidence. Read the lean (1.38 leans MEDIUM), never the nearest integer, and never use the number for arithmetic between levels.

Set thresholds by what a wrong answer costs. Default bands, which a calling skill may move on purpose (never per run):

| Answer | Act |
| --- | --- |
| Noul at 0.80 or more, or Choice confidence at 0.80 or more | Act on it |
| Noul at 0.20 or less | Act on "no" |
| Noul between 0.20 and 0.80, or Choice confidence below 0.80 | Unsure: decide it yourself with the evidence, or ask the user, and say Jev was unsure |

For an action that is hard to undo, raise the bar (0.90 or more) or always confirm with the user.

When you report a Jev answer, give the number and name the band you applied ("0.86, over the 0.80 bar: billing"), so the reader can see how close the call was.

## Hard rules

- **Jev never passes a hard gate.** A rule, a policy, an exclusion list, or a user decision outranks any probability. Jev judges fit; rules judge what is allowed.
- **Jev is not a source.** It judges the evidence you send; it adds no facts. Never cite it as evidence that something exists or happened.
- **Never invent a Jev answer.** If `ask_jev` and the CLI are unavailable (no server, no key, blocked network), say so and decide as you would without it. Report only answers from calls that ran.
- **Typed output guarantees the shape, not the truth.** Test a new question set on a few cases with known answers before you trust it at scale.

## References

- [Eval grading with Jev](references/eval-grading.md): one Noul per expectation, with an LLM grader only for the unsure middle.
- TypeSafe docs index: https://docs.typesafe.ai/llms.txt. Known limits of the current model: https://docs.typesafe.ai/model-jaggedness/jev-1.13.md. Read these with the `search` skill before you design a large question set.
