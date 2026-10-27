# Task lane — what is asked of Alex

Reference for sweep step 3c in `SKILL.md`. The archeologist searches by topic, which finds
knowledge. This lane searches by **who the ask is addressed to**, which finds tasks. Run both.
The `Tested` column says which calls were run for real on 2026-10-14 and what came back.
A row marked **not run** is the documented call shape only: check it on the first live sweep.

Run this lane in the main thread, not inside the archeologist: the archeologist agent has no
Planner, To Do, Todoist, ADO, or `gh` tools. The one exception is the Teams-and-mail paging
on a busy window, which a general background agent can carry (see **Volume** below).

## Two cursor kinds

- **Window sources** (Teams, mail): only items newer than `watermark`.
- **Snapshot sources** (Planner, To Do, Todoist, ADO, GitHub): every item open now, at any age.
  Never apply `watermark` to a snapshot source; the dedupe against the board stops repeats.

## Sources and calls

| Source | Kind | Call (Claude Code) | Busy? | Tested 2026-10-14 |
|---|---|---|---|---|
| Teams chats Alex is in | window | `chat_message_search` `query: "*"`, `recipient: <Alex's mail>`, `afterDateTime: <watermark>`; page with `nextOffset` | yes | run: hits; returns **every** message in his chats, not only asks |
| Alex's own Teams posts | filter | `chat_message_search` `query: "*"`, `sender: <Alex's mail>`, same window | — | run: hits |
| Mail to Alex | window | `outlook_email_search` `recipient: <Alex's mail>`, `afterDateTime: <watermark>`; page with `nextOffset` | yes | run: hits, mostly alerts and newsletters |
| Mail with no reply | filter | per kept ask: `outlook_email_search` `sender: <Alex>`, `recipient: <asker>`, `afterDateTime: <ask date>`; a hit means answered | — | **not run** |
| Planner + To Do | snapshot | `tasks_login_status`, then `tasks_assigned_to_me` `include_completed: false` | no | login check run: `none`; `tasks_assigned_to_me` **not run** |
| Todoist | snapshot | `find-tasks-by-date` `startDate: "today"`, `daysCount: 14` (includes overdue) | no | run: 0 |
| ADO assigned | snapshot | `wit_query` `action: "wiql"`, `project:` from `resolve_ado.py projects`, WIQL below | no | run: 4 of 42 open |
| ADO item detail | read | `wit_work_item` per hit | — | **not run** |
| GitHub reviews | snapshot | `gh search prs --review-requested=@me --state=open --owner <org>` per org from step 1 | no | run: 0 in 8 orgs |

Alex's address comes from `get_me`; do not hard-code it in a note or the board.

**ADO WIQL.** 42 items are open on a normal day and most are long-lived stories. A plain
"changed since watermark" filter still returned all 42 on 2026-10-14, because Alex's own
curator run touches them every week. Take only items **someone else** changed in the window,
or items due in the next 14 days. This returned 4 of 42 (pass `timePrecision: true` so the
watermark time counts):

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [Microsoft.VSTS.Scheduling.TargetDate]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] NOT IN ('Closed','Done','Removed','Resolved','Completed')
  AND (([System.ChangedDate] >= '<watermark>' AND [System.ChangedBy] <> @Me)
       OR ([Microsoft.VSTS.Scheduling.TargetDate] >= @Today AND [Microsoft.VSTS.Scheduling.TargetDate] <= @Today + 14))
ORDER BY [System.ChangedDate] DESC
```

Then read each hit (`wit_work_item`) for the title and latest comment before you judge it.

**`ChangedBy <> @Me` still lets noise through.** On 2026-10-14 every non-canary hit was
noise: two changes by `Azure Boards` (automation, not a person) and two where a colleague
only re-ranked the backlog (`StackRank` was the only changed field). Drop both in code
before Jev: skip a hit whose `System.ChangedBy` display name is `Azure Boards`, and for the
rest read the last revision (`list_revisions`) and skip it when `Microsoft.VSTS.Common.StackRank`
is the only field that changed. Also skip any item titled `[CANARY] … DO NOT APPROVE`.

**GitHub orgs.** `gh api user/orgs --jq '.[].login'` lists them; pick the work orgs from that list, one per call. A parent company name is not an org and fails, so never guess one.

**Planner and To Do sign-in.** When `tasks_login_status` returns `none`, write
`unavailable — not signed in` in the ledger and tell Alex to sign in (`tasks_login_begin`
gives a device code). Never start the login yourself in a sweep.

## Filter in code first, Jev second

Drop these in code, before any Jev call. They are rules, not judgments:

- Mail from outside `example.com`, except system senders that carry approvals
  (`IT-Alerts@`, `azuredevops@microsoft.com`). Newsletters and conference mail die here.
- Alex's own messages (he is the sender), and duplicate notices for the same item (the same
  change control arrives once from ADO and twice from IT-Alerts: keep one per item id).
- Monitoring cards (`[FIRING:`) unless a person in the same thread asks Alex to act.
- Approval-queue notices (CAB / "needs CAB Manager", CSM approval, SailPoint review) and
  meeting invites or "please join" asks. They are operational work Alex does in the tool,
  the CAB meeting, or the calendar, never board items (Alex, 2026-10-14; see
  [todo-board.md](todo-board.md) → intake gate). Count them in the ledger only.
- A request to approve a PR that Alex authored. Check the author with `gh pr view <n> -R
  <org/repo> --json author` first: Alex cannot approve his own PR, so the ask is
  backwards (2026-10-14: a contractor's "can you approve this for me" pointed at Alex's own
  PR, and Set A scored it 0.97). Report it to Alex as unclear instead of filing it.

Then two typed screens, in this order, before Set T (all in [jev-gates.md](jev-gates.md)):

1. **Is it an ask? (Set A).** The `recipient` filter returns every message in every chat Alex
   is in: a normal day is dozens of messages, and most are chatter. Write one redacted line
   per message and send up to 10 per call. ≥ 0.80 is an ask; ≤ 0.20 drop; between, escalate to the
   model, which reads the thread and decides (jev-gates.md, **Unsure → escalate**). Tested on 5 real messages: two asks 0.89 and 0.97, an offer 0.14, chatter
   0.11, a PR-policy complaint 0.33 (unsure, as it should be).
2. **Did Alex already answer it? (Set R).** For Teams, take Alex's own posts (row above) in
   the same `chatId` after the ask's `createdDateTime`. No later post → still open. A later
   post → send both redacted lines to Set R; ≥ 0.80 drop it as answered. Tested 2026-10-14:
   Alex posted in the same chat 9 minutes after an ask, so the match works; Set R itself was
   not run on that pair. For mail, use the "Mail with no reply" row.

Only an ask that is still open becomes a `candidate_action` for Set T.

## Manager and skip-level chats: read in full, every sweep

`chat_message_search` returns a `summary` cut at about 250 characters, and a Set A screen
over a cut summary misses the ask in the second half. On 2026-10-14 that hid most of what
Jeremy (Alex's manager) and Rick (CTO) asked across two days: an Enterprise-plan push, a
.NET question, an AI use-case gap read, a BCP investment ask, a session Alex promised to
join. Alex runs bard almost daily, so each sweep must close its own day.

For the 1:1 chats with Jeremy and Rick, and any group chat with both: call `read_resource`
on the chat URI (`teams:///chats/<id>/messages`). It returns the latest 50 messages with
full bodies; page back with `chat_message_search` plus `beforeDateTime` until you pass the
watermark. Run Set A on full bodies, never on summaries. Treat every question from them
that Alex has not answered in the same chat as an open ask.

## Asks the recipient filter cannot see

Some asks never arrive as a message to Alex: an `@alex` to-do written into SharePoint
meeting notes, or a commitment Alex types in a group meeting chat. On 2026-10-14 the
archeologist's SharePoint and channel lanes found three risk-register to-dos assigned to
Alex and two commitments he made in chats, all missed by the `recipient` searches. Take
every ask or commitment in the archeologist's briefing through Set T as well, with the
`(sharepoint:…)` or `(teams:…)` breadcrumb.

## What was not verified

- **Channel @mentions.** Channel posts have no recipients, so the `recipient` filter skips
  them. A keyword search for Alex's name matched almost everything (KQL is loose), so it is
  not a mention detector. Channels reach bard only through the archeologist's topic search.
- **Unanswered invites.** The calendar search returns `showAs: tentative` for many standing
  meetings; it is not proof that Alex did not answer. Use the calendar only for event dates
  that set a deadline ("before Tuesday's forum"), never as a task source of its own.

## Other hosts

In OpenCode or Pi there is no Planner, To Do, or Todoist tool: write `unavailable — no tool on
this host`. Claude Code can lack them too: on 2026-10-14 neither `tasks_login_status` nor a
Todoist tool was in the session's tool list. Check the list (ToolSearch) before you write
the ledger line, and use the same wording when they are absent.

## Volume

On 2026-10-14 the `recipient` filter returned 662 Teams messages and Alex's own posts
returned about 778 over two working days. Paging both and running Set A and Set R on that
volume fills the main thread. Give the Teams-and-mail part to one background agent with
this file and `jev-gates.md` as its brief, and keep ADO, GitHub and Planner in the main
thread. The agent returns the ledger, the open asks with their numbers, and the answered
asks. Mail and Teams use the `m365` CLI (`../m365/SKILL.md`); ADO uses the `ado` agent.

## Coverage ledger

One line per source, in the archeologist's three states (`unavailable — <reason>`,
`searched, N hits`, `not searched — <why>`). A 0 from Teams or mail on a window with a working
day is a coverage failure (SKILL.md step 3). A 0 from Planner, Todoist, or GitHub can be real.
