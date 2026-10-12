# Typed gates — the `ask_jev` question sets

Reference for the **Typed gates** section of `SKILL.md`. Everything here is a copy-paste
request body for the `ask_jev` tool. How to call Jev and read its answers, for every host:
[`../../jev/SKILL.md`](../../jev/SKILL.md).

## Why these are typed, not prose

The same judgments run on every candidate every week: does it qualify, which stage
(`Status`), which `Theme`, which `EARole`. (Decisions live in AAB Intake, not on the board.) In prose they drift — the same evidence can get a
different label next run, and the board then disagrees with itself. A typed answer returns a
value **plus a confidence**, so a stable label is cheap and the uncertain calls are visible
instead of buried in a paragraph.

`ask_jev` is a judgment, never a gate. The exclusion screen, `not_doing`, and "never invent"
stay rules; see the hard limits in `SKILL.md`.

## The five questions

One call per candidate. `state` carries the clustered evidence **and** the matched live row
when there is one, because Jev sees only what is in `state` — and the questions in one call
cannot see each other.

| ID | Type | Answers | Decides |
|---|---|---|---|
| `row_qualifies` | noul | 0–1 | Inclusion: delivery or influence not attendance, initiative scale, owner-of-record |
| `status` | choice | the four active stages (`5. Stopped` is never inferred) | The proposed stage line (Alex's column — a proposal only) |
| `theme` | choice | the five theme values | `Theme`; AI wins the tie, so AI rows show in the AI Program view |
| `ea_role` | choice | `Builds` / `Influences` / `Runs` | `EARole`: whether EA builds it, influences it, or runs it |
| `dedupe` | choice | the current row titles + `new` | NEW vs UPDATE, the "one row = one initiative" test |

## Gate thresholds (defaults — Alex can move them)

| Result | Action |
|---|---|
| `row_qualifies` ≥ 0.80 | Propose the row |
| `row_qualifies` ≤ 0.20 | Screened out; record the reason in the report's screened-out list |
| Between | a **Needs you** line — the evidence does not settle it |
| `choice` confidence ≥ 0.80 | Recommend that value |
| `choice` confidence < 0.80 | Still propose, but as a **Needs you** line whose `Why` line carries the Jev confidence and the runner-up |
| `dedupe` picks an existing row with confidence ≥ 0.80 | Emit an UPDATE of that row, never a new row |

A low-confidence result that stops a proposal goes on `curated.json` `open_items`, so the
next run re-asks instead of re-guessing. Do not add new ledger keys; the Connections pass `ideas` key is the one exception.

## Ready-to-run body

```json
{
  "state": "<clustered evidence + the matched live row, if any>",
  "questions": {
    "row_qualifies": {
      "type": "noul",
      "instructions": "Does this qualify as an EA Projects board row under all four tests: delivery rather than attendance, initiative scale, owner-of-record, and org-shareable?"
    },
    "status": {
      "type": "choice",
      "instructions": "Which stage best describes where this initiative stands today, from the evidence in the state?",
      "criteria": {
        "1. Exploring": "still being looked into: research, conversations, options or an RFC; no decision yet to build or adopt it",
        "2. Committed": "the decision to do it is made, but building, piloting or rollout has not started",
        "3. Delivering": "building, piloting, configuring or rolling out is under way",
        "4. Delivered": "the outcome is live and the work is finished"
      }
    },
    "theme": {
      "type": "choice",
      "instructions": "Which single theme is the current centre of gravity of this initiative? Exception: if the work delivers an AI agent, model, or assistant, or a control on AI use or AI spend, answer AI Program even when the domain is security, ops, or governance.",
      "criteria": {
        "Security Hardening": "Access, hardening, privileged access, vulnerability work, when no AI agent or model is the deliverable",
        "Platform Foundations": "Core platform, networking, identity, tooling and observability foundations, when no AI agent or model is the deliverable",
        "AI Program": "Delivers an AI agent, model, or assistant, AI tooling or platform, or a control on AI use or AI spend. Wins any tie with another theme",
        "Governance": "Policy, standards, review process, decision rights, and how the technology team hires and organises",
        "Business Initiatives": "EA supporting a business move"
      }
    },
    "ea_role": {
      "type": "choice",
      "instructions": "What is Enterprise Architecture's role in this initiative, from the evidence in the state? For an initiative that has not started building yet, judge who is planned to do the hands-on work.",
      "criteria": {
        "Builds": "EA does the hands-on work: EA people author the code, configuration, pipelines, infrastructure or agents, or run the pilot themselves",
        "Influences": "Another team builds or rolls it out; EA advises, reviews, decides through the AAB, or sets the standard or the document the team follows",
        "Runs": "Recurring keep-the-lights-on work EA operates, such as the Architecture Advisory Board forum or EA operations, with no end state"
      }
    },
    "dedupe": {
      "type": "choice",
      "instructions": "Does this evidence belong to an existing board row, or is it a new initiative?",
      "criteria": {
        "Privileged Access Renewal": "existing row title, one entry per live row",
        "Observability Platform": "existing row title, one entry per live row",
        "new": "No existing row covers this body of work"
      }
    }
  }
}
```

Build the `dedupe` criteria from the live list read, one entry per existing row title, plus
`new`. Never judge dedupe from memory of the list.

## Connections pass questions

One call per candidate idea, after the review is built
([connections-pass.md](connections-pass.md)). `state` carries the idea, the connection it claims,
and a short summary of each cited source. Jev sees only `state`, so put the evidence there, not a
pointer to it.

| ID | Type | Answers | Decides |
|---|---|---|---|
| `evidence_supports` | noul | 0–1 | Does the cited evidence support the connection, with no facts from outside `state`? |
| `non_obvious` | noul | 0–1 | Would Alex miss this from a glance at the board, AAB Intake and the EA epics, each on its own? |
| `actionable` | noul | 0–1 | Is there a concrete step Alex can take this week? |
| `same_idea` | choice | earlier idea texts from the ledger + `new` | Only when you are unsure whether an idea repeats a ledger idea |

Thresholds: any of the three nouls at or below 0.20 drops the idea, with the reason in the
filtered-out list. Every other idea is shown with its three numbers; ideas with all three at or
above 0.80 come first. `same_idea` follows the `dedupe` rule: an earlier idea at 0.80 or more is a
repeat, so a Dropped match never comes back and a Parked match comes back only on new evidence.

```json
{
  "state": "<the idea, the connection it claims, and a short summary of each cited source>",
  "questions": {
    "evidence_supports": {
      "type": "noul",
      "instructions": "Does the evidence in the state support the connection this idea claims, without relying on any fact that is not in the state?"
    },
    "non_obvious": {
      "type": "noul",
      "instructions": "Would an enterprise architect likely miss this connection by glancing at the EA Projects board, the AAB Intake list and the EA epics one at a time? Answer yes only if seeing it needs two or more sources put together."
    },
    "actionable": {
      "type": "noul",
      "instructions": "Is there a concrete next step the architect can take this week, such as a message to an owner, a link between two items, an AAB item, or a row change?"
    }
  }
}
```

## Not a Jev question

- **`Title` wording** — voice and brevity, not classification. Follow the field mapping.
- **Anything on the exclusion screen** — privileged, vendor-sensitive, scope-claiming, HR.
  These are hard gates; a probability must never admit a row a rule excludes.
- **`not_doing`** — a declined initiative stays declined. Never re-propose, never re-ask.
- **Whether to write** — the review decides that, always.
- **Whether an idea is true** — Jev grades fit against the evidence in `state`; checking that each cited source is real and was read this run is your job, before the call.

## Privacy

For this skill, send a short summary: the initiative, its artifacts, and the row. Never paste a
raw transcript or privileged text. The exclusion screen applies to the request too.
