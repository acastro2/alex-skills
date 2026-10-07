# Typed gates — the `ask_jev` question sets

Reference for the **Typed gates** section of `SKILL.md`. Every block here is a copy-paste
request body for the `ask_jev` tool. How to call Jev and read its answers, for every host:
[`../../jev/SKILL.md`](../../jev/SKILL.md).

## Why these are typed, not prose

Three calls in this skill are typed judgments made in prose today: the question type
(Phase 1 step 3), which stores get promoted into Tier 1 (Phase 2 step 2), and the confidence
level (Phase 5). A typed answer returns a value **plus a confidence**, so a mixed question
gets the same treatment twice and the confidence call has a second, auditable opinion
attached to it.

**The tier rules in `SKILL.md` stay authoritative.** Promote G for comms questions and I for
shipped-work questions because the rule says so. `ask_jev` adjudicates the **mixed** case,
where two rules point at different source sets, and it never replaces the coverage ledger.

## The four questions

One call, before the stores are touched.

| ID | Type | Answers | Decides |
|---|---|---|---|
| `question_type` | choice | the five types + `Mixed` | Which source set the question wants |
| `promote_comms` | noul | 0–1 | Whether G (mail, Teams, meetings) joins Tier 1 |
| `promote_shipped` | noul | 0–1 | Whether I (PRs, commits, reviews) joins Tier 1 |
| `evidence_strength` | score | LOW / MEDIUM / HIGH | A second opinion on the rubric — never an override |

`evidence_strength` is asked **after** retrieval, on the findings. The other three are asked
before the first store.

## Gate thresholds (defaults — Alex can move them)

| Result | Action |
|---|---|
| `promote_*` ≥ 0.80 | Promote that store into Tier 1 |
| `promote_*` ≤ 0.20 | Leave it in Tier 2 |
| Between | Search it anyway and say in the coverage ledger that the promotion was uncertain |
| `question_type` = `Mixed`, or confidence < 0.80 | Run the **union** of both source sets |
| `evidence_strength` agrees with the rubric | Report the rubric's level |
| `evidence_strength` disagrees | The rubric wins. Report its level and name the disagreement in the rationale |

The `score` answer is a position on the ordered scale, not a label: measured 2026-09-29, the
response returns `1.38` with `legend 0=LOW 1=MEDIUM 2=HIGH` and its own confidence. So 1.38
*leans* MEDIUM. Read the lean, never the nearest integer.

A missed store reads as silence, which is a false claim, so an uncertain promotion is paid
for with one extra query, not with an assumption. The reverse holds for confidence: a model
saying HIGH is not evidence that a file still exists.

## Ready-to-run body — before retrieval

```json
{
  "state": "<the user's question, the entities and dates in it, and any project or topic it maps to>",
  "questions": {
    "question_type": {
      "type": "choice",
      "instructions": "Which single type is this question, or Mixed when it fits more than one?",
      "criteria": {
        "Factual": "A fact that either exists in a store or does not",
        "Temporal": "When something happened, or an order of events",
        "Causal": "Why something happened or what a change led to",
        "Decision-tracking": "Whether a choice was made, and what it was",
        "Error-Solution": "A past failure and the fix that resolved it",
        "Mixed": "Fits two or more of the above"
      }
    },
    "promote_comms": {
      "type": "noul",
      "instructions": "Does answering this need communications evidence: who said or sent something, a meeting, or an agreement reached in chat or mail?"
    },
    "promote_shipped": {
      "type": "noul",
      "instructions": "Does answering this need shipped-work evidence: pull requests, commits, reviews, or activity over a period?"
    }
  }
}
```

## Ready-to-run body — after retrieval

```json
{
  "state": "<the findings: one line per source with its locator and date, plus the current-state checks>",
  "questions": {
    "evidence_strength": {
      "type": "score",
      "instructions": "How strong is this evidence set for answering the question?",
      "criteria": ["LOW", "MEDIUM", "HIGH"]
    }
  }
}
```

## Hard limits

- **`ask_jev` is not a source.** It never returns evidence, never turns a 0-hit store into a
  hit, and never appears in the coverage ledger as a store that was searched.
- **The ledger reports what actually ran.** A suggested source set is not a search. A sweep
  still covers all stores A–I.
- **The rubric owns confidence.** "HONEST CONFIDENCE: if you cannot verify, say so. Do not
  inflate" outranks any model's score.
- **Unavailable Jev:** see [`../../jev/SKILL.md`](../../jev/SKILL.md).
  For this skill, send the question, its entities, and short findings lines, never raw
  transcript text or privileged content.
