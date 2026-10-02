# Typed gates — the `ask_jev` question sets

Reference for the **Typed gates** section of `SKILL.md`. Everything here is a copy-paste
request body for the `ask_jev` tool (MCP server `jev`, `~/.local/bin/jev-mcp`, backed by
`~/.local/bin/jev`).

## Why these are typed, not prose

The same four judgments run on every candidate every week: does it qualify, which `Status`,
which `DecisionNeeded`, which `Theme`. In prose they drift — the same evidence can get a
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
| `row_qualifies` | noul | 0–1 | Inclusion: delivery not attendance, initiative scale, owner-of-record |
| `status` | choice | the six lifecycle values | The proposed `Status` line (Alex's column — a proposal only) |
| `decision_needed` | choice | `None` / `CTO` / `Advisory Board` / `Business Owner` / `Process Owner` | Who the pending decision belongs to |
| `theme` | choice | the eight theme values | `Theme`; AI wins the tie, so AI rows show in the AI Program view |
| `dedupe` | choice | the current row titles + `new` | NEW vs UPDATE, the "one row = one initiative" test |

## Gate thresholds (defaults — Alex can move them)

| Result | Action |
|---|---|
| `row_qualifies` ≥ 0.80 | Propose the row |
| `row_qualifies` ≤ 0.20 | Screened out; record the reason in the report's screened-out list |
| Between | `Needs you? yes` line — the evidence does not settle it |
| `choice` confidence ≥ 0.80 | Recommend that value |
| `choice` confidence < 0.80 | Still propose, but the line is `Needs you? yes` and the `Why` cell carries the Jev confidence and the runner-up |
| `dedupe` picks an existing row with confidence ≥ 0.80 | Emit an UPDATE of that row, never a new row |

A low-confidence result that stops a proposal goes on `curated.json` `open_items`, so the
next run re-asks instead of re-guessing. Do not add new ledger keys.

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
      "instructions": "Which lifecycle status fits this initiative right now, from the evidence in the state?",
      "criteria": {
        "1. Proposed": "Problem stated, idea only",
        "2. In Analysis": "Problem justifies analysis and work is underway",
        "3. Decision-Ready": "A decision-maker could act on a costed or documented options analysis",
        "4. In Progress": "The named owner has said yes and delivery started",
        "5. Verifying": "The change is live, the outcome is not yet checked",
        "6. Closed": "Outcome documented against the promise"
      }
    },
    "decision_needed": {
      "type": "choice",
      "instructions": "Who must make the pending decision before this work can move? Answer None when EA itself decides.",
      "criteria": {
        "None": "No external decision pending; EA decides",
        "CTO": "The decision is genuinely the CTO's",
        "Advisory Board": "Belongs to the Architecture Advisory Board forum",
        "Business Owner": "The P&L or budget holder must decide",
        "Process Owner": "Whoever owns the process being changed"
      }
    },
    "theme": {
      "type": "choice",
      "instructions": "Which single theme is the current centre of gravity of this initiative? Exception: if the work delivers an AI agent, model, or assistant, or a control on AI use or AI spend, answer AI Program even when the domain is security, ops, or governance.",
      "criteria": {
        "Security Hardening": "Access, hardening, privileged access, vulnerability work, when no AI agent or model is the deliverable",
        "Platform Foundations": "Core platform, networking, identity, tooling foundations, when no AI agent or model is the deliverable",
        "AI Program": "Delivers an AI agent, model, or assistant, AI tooling or platform, or a control on AI use or AI spend. Wins any tie with another theme",
        "Governance": "Policy, standards, review process, decision rights",
        "Observability": "Telemetry, logging, metrics, profiling, alerting",
        "Tech Recruiting": "Hiring and capability build-out for technology",
        "Modernization Enablement": "EA advising work another team owns",
        "Business Initiatives": "EA supporting a business move"
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

## Not a Jev question

- **`Title` wording** — voice and brevity, not classification. Follow the field mapping.
- **Anything on the exclusion screen** — privileged, vendor-sensitive, scope-claiming, HR.
  These are hard gates; a probability must never admit a row a rule excludes.
- **`not_doing`** — a declined initiative stays declined. Never re-propose, never re-ask.
- **Whether to write** — the review table decides that, always.

## Privacy

`state` leaves the machine for the OpenCode Zen endpoint. Send a short summary: the
initiative, its artifacts, and the row. Never paste a raw transcript, a credential, or
privileged text. The exclusion screen applies to the request too.
