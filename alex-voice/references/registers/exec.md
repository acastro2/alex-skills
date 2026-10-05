# Exec (briefs, board artifacts, leadership decisions)

Decision Architect mode. The reader decides, they do not learn. Exec is not a message: the "cut to two thirds" rule does not apply. Keep it tight by cutting adjectives and implementation detail, never the consequence.

Why this shape: in a blind test (2026-10-05), Alex picked briefs that spell out the cost of waiting, why now, and what the numbers mean over tighter briefs that listed only the facts, 4 of 4.

## Rules

- Lead with the decision needed and the recommendation, with the reason in the same sentence: "Approve, because the server costs $90,000 a year and only 3 reports still depend on it." Context after, never before.
- Say why now: the date or event that forces the decision, and what happens if nobody decides.
- Quantify the cost of waiting: "Each month of delay costs about $7,500." If it cannot be measured, say what gets worse.
- Interpret the numbers for the reader: give the change, not just the two values ("Incidents fell from 14 to 6, a 57% drop"), then one sentence on what it means ("the gains are not locked in until both items close").
- Never invent a fact, plan, number, or decision the user did not give. A reason or a tip must follow from the facts you have. If the doc needs something you do not know (a rollback plan, an owner, a date), write "[to confirm]" in its place. Arithmetic on given numbers is fine ($90,000 a year is about $7,500 a month).
- Portfolio altitude: outcome, business impact, owner, deadline. Name a technology only when the decision is about technology.
- Two or three options at most, one marked recommended, trade-offs in one table (cost, risk, outcome).
- Actions are numbered, each with an owner and a date.
- A status update still gets a recommendation ("Keep the current plan"), even when no decision is needed.
- Every substantive claim traces to a source. End with a source line ("Source for all figures: [link]") and name what is unverified. No source, say "unverified" or drop the claim.
- When it goes by email or Teams, the subject line carries the headline: "Platform reliability: incidents down 57%, two items left".
- No hedging, no advocacy campaign, no anecdotes, no second-person intimacy, no "I think". State the case and stop.

## Red flags

- A brief that lists facts but never says what happens if nobody acts.
- Two numbers with no change or meaning next to them.
- Implementation detail answering a portfolio question.
- A next step without owner and date.
- A paragraph a VP could not forward to the CEO unchanged.

## Register samples

Synthetic, modeled on the real patterns. No internal names, facts, or decisions.

> **Decision:** Retire the legacy reporting server. **Recommendation:** Approve, because it costs $90,000 a year and only 3 reports still depend on it. The replacements are built and tested, so nothing is left to build before the switch. Each month of delay costs about $7,500. Data Engineering owns the retirement and finishes by November 30. Decision needed by October 20.
>
> Source for all figures: [link].
