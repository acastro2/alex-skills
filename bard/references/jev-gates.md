# Typed gates — the `ask_jev` question sets

Reference for **Typed gates** in `SKILL.md`. How to call Jev and read its answers on every
host: [`../../jev/SKILL.md`](../../jev/SKILL.md). Each block here is a copy-paste body.

## Why typed

Every bard judgment was made in prose: keep or drop, which hub, gate, priority, owner, done,
same item. A prose call drifts from sweep to sweep and hides the unsure ones. A typed call
gives the same answer for the same evidence and shows a number for the unsure ones. One call
answers all questions about one item at the same time, so it costs one round trip per item.

## What goes to Jev and what does not

| Jev (judgment) | Code or rule (never Jev) |
|---|---|
| keep or drop a knowledge candidate, its `type` | caps (12 open, 5 this week), spread counts |
| which hub fits | horizon, derived from priority + owner |
| gate: consequence, one next action | file exists, wikilink resolves, Bard note exists |
| priority, owner (who acts next) | dates, ages, the 30-day aging |
| done or still open | ownership split above the marker, hand-edited lines |
| two candidates are the same item | PII exclusions, the confidentiality rules |

Jev never passes a hard rule. A rule, a cap, or Alex's hand edit beats any probability.

## `state` — redacted summary only (Alex, 2026-10-14)

Jev runs on the OpenCode Zen endpoint, outside Attain. Write `state` yourself; never paste
source text into it.

- 2 to 4 lines of your own words about the evidence, plus the candidate action line.
- People by role ("a platform lead", "an application engineer"), never by name.
- No quotes, no mail subjects, no chat or channel names, no URLs, no locators, no ticket or PR
  numbers, no customer data of any kind, no direct identifier from the Attain policy list.
- Name the parts you ask about with backticks: `candidate_action`, `evidence_summary`,
  `completion_signals`.

The redaction has a cost: a rule that says "a **named** person waits" never matches a role.
The questions below say that a role counts. Do not drop that sentence.

## Set T — one task candidate (one call)

```json
{
  "state": "{\"candidate_action\": \"<one imperative step>\", \"evidence_summary\": \"<2-4 redacted lines>\", \"completion_signals\": \"<redacted lines from swept sessions that show it shipped, or none>\"}",
  "questions": {
    "consequence": {"type": "choice",
      "instructions": "Which consequence does `evidence_summary` show if the user never does `candidate_action`? People are described by role, not name; a role counts as a named party.",
      "criteria": {
        "deadline": "a written or implied deadline is missed",
        "someone_waits_on_user": "a person, role, or team is blocked or waiting until the user acts",
        "risk": "production, security, a secret, or a legal or regulatory duty is at risk",
        "promise": "the user promised it to someone",
        "none": "nothing bad happens; it is an offer, an idea, an open question, or hygiene"}},
    "one_action": {"type": "noul",
      "instructions": "Is `candidate_action` a single step the user can finish in one sitting?"},
    "owner": {"type": "choice",
      "instructions": "Who owns the next step of `candidate_action`, given `evidence_summary`?",
      "criteria": {
        "user_owes": "the user must act next; someone waits on the user",
        "user_waits": "someone else must act next; the user waits on them",
        "no_owner": "no one is clearly waiting and no one owes the next step"}},
    "priority": {"type": "choice",
      "instructions": "Which priority fits `candidate_action` given `evidence_summary`? A role counts as a named party.",
      "criteria": {
        "highest": "hard deadline within about 7 days, an exposed secret, production broken, or a legal or regulatory deliverable",
        "high": "a person, role, or team waits on the user, or it blocks a specific PR, ticket, release, or review, or it is tied to a real event",
        "medium": "real work, nobody waits on the user, no deadline",
        "low": "cleanup or hygiene, no consequence if it slips a month",
        "lowest": "someday or maybe, parked with no owner"}},
    "done": {"type": "noul",
      "instructions": "Does `completion_signals` show that `candidate_action` is finished?"}
  }
}
```

Ask Set T for a new candidate, and the `done` question alone for every open board line
during the re-check pass (step 6).

## Set A — is it an ask? (one call, up to 10 messages)

```json
{
  "state": "{\"m1\": \"<one redacted line>\", \"m2\": \"<one redacted line>\"}",
  "questions": {
    "ask_1": {"type": "noul", "instructions": "Does `m1` ask the user to do, answer, decide, or provide something?"},
    "ask_2": {"type": "noul", "instructions": "Does `m2` ask the user to do, answer, decide, or provide something?"}
  }
}
```

## Set R — did Alex's later post answer it? (one call)

```json
{
  "state": "{\"ask\": \"<redacted ask>\", \"reply\": \"<redacted later post by the user in the same chat>\"}",
  "questions": {
    "answered": {"type": "noul", "instructions": "Does `reply` answer or close what `ask` asks for?"}
  }
}
```

`answered` ≥ 0.80 drops the ask; ≤ 0.20 keeps it; between, escalate (see **Unsure → escalate**).

## Set K — one knowledge candidate (one call)

```json
{
  "state": "{\"candidate\": \"<2-4 redacted lines: what happened and why it matters>\", \"hubs\": [\"<hub titles>\"]}",
  "questions": {
    "kind": {"type": "choice",
      "instructions": "Which kind of durable knowledge is `candidate`? Pick drop when you cannot say in one line why it will matter in six months.",
      "criteria": {
        "decision": "a choice with a lasting reason",
        "lesson": "something broke and what to do differently",
        "pattern": "a reusable technique",
        "artifact": "a tool or approach worth remembering",
        "impact": "an outcome that mattered",
        "drop": "routine fix, transient debugging, one-off lookup, status chatter"}},
    "hub": {"type": "choice",
      "instructions": "Which hub in `hubs` does `candidate` belong under?",
      "criteria": {"<each hub title>": "<its scope in a few words>", "none": "no hub fits"}}
  }
}
```

## Set D — same item (one call, up to 5 pairs)

Pre-filter in code first: same ADO id, PR, or session id is a match without Jev. Only the
text-only pairs go to Jev, and only the 5 nearest candidates (same topic emoji first). Jev is
weak at finding one row in a long list (curator evals, 2026-10-12), so never send the whole
board.

```json
{
  "state": "{\"new\": \"<candidate line>\", \"existing_1\": \"<board line>\", \"existing_2\": \"<board line>\"}",
  "questions": {
    "same_1": {"type": "noul", "instructions": "Do `new` and `existing_1` ask for the same next step?"},
    "same_2": {"type": "noul", "instructions": "Do `new` and `existing_2` ask for the same next step?"}
  }
}
```

## Bands

| Answer | Act |
|---|---|
| `ask_*` ≥ 0.80 | an ask: go on to Set R; ≤ 0.20 drop |
| `consequence` P(none) ≤ 0.20 | gate rule 1 passes |
| `consequence` P(none) ≥ 0.80 | gate fails: backlog |
| `one_action` ≥ 0.80 | gate rule 2 passes; ≤ 0.20 split it, or backlog the project line |
| `owner` = `user_waits`, confidence ≥ 0.80 | `⏳ Waiting on others` |
| `priority` confidence ≥ 0.80 | `highest` 🔺 · `high` ⏫ · `medium` 🔼 · `low` 🔽 · `lowest` ⏬ |
| `done` ≥ **0.90** | auto-complete (a move Alex may not see, so the bar is higher) |
| `done` 0.20–0.90 | escalate; the model completes it only on explicit completion evidence |
| `kind` ≠ `drop`, confidence ≥ 0.80 | write the note with that `type` |
| `hub` confidence < 0.80 | escalate; the model picks the hub |
| `hub` = `none` at 0.80 or more, or the model finds no hub | omit `up`, tag `bard/unreviewed` (STEP 4) |
| `same_*` ≥ 0.80 | dedupe; ≤ 0.20 a new item; between, escalate |
| anything else between the bands | escalate |

## Unsure → escalate (Alex, 2026-10-14)

Every Jev answer between the bands goes to the model running the sweep. No exceptions, no
default answer, no "keep it and see". The model:

1. Reads the **full evidence**, not the redacted `state`: the raw message, thread, session,
   or work item. It stays inside this session; nothing new goes to Jev or outside Attain.
2. Decides with the same rule the question encodes (board rules, STEP 1, STEP 4).
3. Writes one report line: `Jev unsure (0.xx) → model: <answer> — <one-line why>`.

For a move Alex may not see (auto-complete to `## Done`), the model completes the item only
when the evidence shows it finished. When the model is unsure too, the item stays open and
the report asks Alex. Escalation never overrides a hard rule, a cap, or a hand edit.

In the sweep report, give each board change its number and band: "CAB approval: waits on
user 0.98, over 0.80: ⏫".

## Known-answer checks (2026-10-14, `jev-1.13`)

| Case | Expected | Jev |
|---|---|---|
| A change waits at the CAB stage for the user's approval | someone waits on user | `someone_waits_on_user` 0.98 |
| An external newsletter, nobody asked anything | none | `none` 1.00 |
| The user waits for a platform lead to approve a SAD | user waits (the ⏫ direction trap) | `user_waits` 1.00 |
| Same CAB case, old Noul "is there a consequence?" with roles | yes | **0.12, wrong** — the reason Set T uses a Choice and says a role counts |
| Full Set T on the CAB case | waits on user, one step, user owes, ⏫, open | 0.99 · 0.91 · 0.98 · `high` 0.99 · done 0.02 |
| SAD case, a later session shows it merged | user waits, done | `user_waits` 1.00 · done 0.92 · `high` 0.85 (forum date, a real event) |
| Set K: ADO filter lesson | lesson, Azure DevOps hub | `lesson` 0.96 · `Azure DevOps` 1.00 |
| Set A: 5 real Teams messages, redacted | 2 asks, 2 not, 1 unclear | 0.89 · 0.97 ask; 0.14 · 0.11 not; 0.33 unsure |

Re-run these after you change any question text. Note on the SAD row: `high` comes from the
forum date, not from the platform lead. The board's direction test still applies: Alex
waiting on someone never makes an item ⏫ by itself; a deadline or event can.

## Jev unavailable

No `ask_jev` tool and no `jev` CLI, no key, or a network block: say so once in the report,
decide every call in prose with the board rules, and mark the report "Jev unavailable". Never
write an answer Jev did not give.
