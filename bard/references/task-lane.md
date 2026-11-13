# Task lane — what is asked of Alex

Reference for sweep step 3c in `SKILL.md`. The archeologist searches by topic, which finds
knowledge. This lane searches by **who the ask is addressed to**, which finds tasks. Run both.
The `Tested` column says which calls were run for real on 2026-10-14 (Jira rows: 2026-11-12) and what came back.
A row marked **not run** is the documented call shape only: check it on the first live sweep.

Run this lane in the main thread, not inside the archeologist: the archeologist agent has no
Planner, To Do, Todoist, Jira, or `gh` tools. The one exception is the Teams-and-mail paging
on a busy window, which a general background agent can carry (see **Volume** below).

Teams, mail, Jira, and GitHub come from the gather lane first (see `SKILL.md` step 3). The
calls below are the fallback, for a source that gather did not fetch.

## Two cursor kinds

- **Window sources** (Slack, Teams, mail): only items newer than `watermark`.
- **Snapshot sources** (Planner, To Do, Todoist, Jira, GitHub): every item open now, at any age.
  Never apply `watermark` to a snapshot source; the dedupe against the board stops repeats.

## Sources and calls

| Source | Kind | Call (Claude Code) | Busy? | Tested (2026-10-14 unless dated) |
|---|---|---|---|---|
| Slack DMs and group DMs | window | Slack search per open DM: `in:@<person> after:<day before watermark>`; list DMs with the list-my-channels tool (type DMs, group DMs). Read each thread with a hit | yes | run 2026-11-11 through Cursor: DM search (`channel_types: im,mpim`), then `slack_read_channel` per DM; see **Slack** below. Claude Code needs its own Slack sign-in (`/mcp`) |
| Slack threads and channels | window | Slack search `with:@<Alex> after:<day before watermark>` (threads and DMs with Alex), then read each thread | yes | run 2026-11-11 through Cursor, by mention search (`keywords: "<@U…>"`) then `slack_read_thread`; the `with:` search itself **not run** |
| Alex's own Slack posts | filter | Slack search `from:@<Alex> after:<day before watermark>` | — | **not run** as a search; on 2026-11-11 Alex's posts were read inside each DM and thread |
| Teams chats Alex is in | window | `chat_message_search` `query: "*"`, `recipient: <Alex's mail>`, `afterDateTime: <watermark>`; page with `nextOffset` | yes | run: hits; returns **every** message in his chats, not only asks |
| Alex's own Teams posts | filter | `chat_message_search` `query: "*"`, `sender: <Alex's mail>`, same window | — | run: hits |
| Mail to Alex | window | `outlook_email_search` `recipient: <Alex's mail>`, `afterDateTime: <watermark>`; page with `nextOffset` | yes | run: hits, mostly alerts and newsletters |
| Mail with no reply | filter | per kept ask: `outlook_email_search` `sender: <Alex>`, `recipient: <asker>`, `afterDateTime: <ask date>`; a hit means answered | — | **not run** |
| Planner + To Do | snapshot | `tasks_login_status`, then `tasks_assigned_to_me` `include_completed: false` | no | login check run: `none`; `tasks_assigned_to_me` **not run** |
| Todoist | snapshot | `find-tasks-by-date` `startDate: "today"`, `daysCount: 14` (includes overdue) | no | run: 0 |
| Jira assigned | snapshot | `searchJiraIssuesUsingJql`, JQL below | no | run 2026-11-12 with `-7d` for the watermark: 4 of 4 open items matched (every open item had a recent update that day); the `"<watermark>"` string form is **not run** |
| Jira changelog | read | `getJiraIssue` per hit, `expand: "changelog"` | — | run 2026-11-12: one item had a change by another person inside 7 days (checked by hand, not by code) |
| Jira item detail | read | `getJiraIssue`, fields `summary, status, comment` | — | comments **not run** |
| GitHub reviews | snapshot | `gh search prs --review-requested=@me --state=open --owner <org>` per org from step 1 | no | run: 0 in 8 orgs |

Alex's address comes from `get_me`; do not hard-code it in a note or the board.

**Jira JQL.** Alex's own updates touch his items too, so the JQL alone does not show who
changed what; the changelog filter below does. Take open items that changed in the window,
or are due in the next 14 days. Pass the `cloudId` from `getAccessibleAtlassianResources`
(the entry with `read:jira-work`; see `../../ticket-writer/references/jira.md`). Fields: `summary, status, issuetype, duedate, updated`.
`duedate <= 14d` includes overdue items on purpose: an overdue item is still an ask.

```text
assignee = currentUser() AND statusCategory != Done AND (updated >= "<watermark>" OR duedate <= 14d) ORDER BY updated DESC
```

The watermark string is `yyyy-MM-dd HH:mm` in the Jira profile time zone.

Then read each hit with `getJiraIssue` and `expand: "changelog"`. Each `changelog.histories[]`
entry has `author.accountId`, `created`, and `items[]` (`field`, `fromString`, `toString`).
Alex's account id comes from `atlassianUserInfo` (`<Alex's account id>`); never write it in a
file. Keep a hit when some history entry after the watermark has an `author.accountId` that is
not Alex's, or when its due date is in the window. Drop the rest in code before Jev.

Do not use a JQL `updatedBy` clause: it returned 0 with no positive case, so its meaning is
unproven.

**Noise filters.** Automation actors and rank-only changes may exist in Jira too. Check on
the first live sweep and record what you find here. Skip any item titled
`[CANARY] … DO NOT APPROVE`.

**GitHub orgs.** `gh api user/orgs --jq '.[].login'` lists them; pick the work orgs from that list, one per call. A parent company name is not an org and fails, so never guess one.

**Planner and To Do sign-in.** When `tasks_login_status` returns `none`, write
`unavailable — not signed in` in the ledger and tell Alex to sign in (`tasks_login_begin`
gives a device code). Never start the login yourself in a sweep.

## Filter in code first, Jev second

Drop these in code, before any Jev call. They are rules, not judgments:

- Mail from outside `example.com`, except system senders that carry approvals
  (`IT-Alerts@`). Newsletters and conference mail die here.
- Alex's own messages (he is the sender), and duplicate notices for the same item (the same
  change control can arrive from more than one sender: keep one per item id).
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

## Slack

Slack is the busiest comms store at Alex's current job, so run it first. Use archeologist
[Source J](../../archeologist/references/slack.md) for access per host: OpenCode reaches Slack
natively through its own `slack_*` tools. Search with `slack_search_public_and_private` (modifiers
go in `filters`), then read each hit with `slack_read_thread` (`Channel` id + `Message_ts` from
the result). Quote the tool's own markdown result verbatim.

- **Dates:** `after:` leaves out the date you type, so search from the day before the
  watermark day and drop older messages in code by their timestamp.
- **No `to:` modifier exists.** An ask to Alex is a DM, a group DM, a thread he is in
  (`with:`), or a mention. Mentions have no documented modifier: search Alex's `@` handle
  as a query term and verify on the first live run that it finds mentions.
- **Read the whole thread** before Set A and Set R. Search returns a snippet, and the answer
  to an ask is often a reply further down. Set R uses Alex's own posts in the same thread
  or DM after the ask, the same way as Teams.
- Breadcrumb on the board: `(slack:YYYY-MM-DD)`, the message date, like `(teams:…)`.
- **Method that worked (2026-11-11):** get Alex's user id with `slack_search_users`; search DMs
  (`channel_types: im,mpim`) and mentions (`keywords: "<@U…>"`) only to find the conversations;
  then read each DM in full with `slack_read_channel` and each mentioned thread with
  `slack_read_thread`. Alex answers fast, so most items are his own commitments ("will do",
  "I will write an ADR"), not unanswered pings: read his posts, not only theirs. Booking or
  attending a sync is meeting work (todo-board.md), so list it in the report only.

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

In OpenCode there is no Planner, To Do, Todoist, or Atlassian (Jira) tool: write `unavailable — no tool on
this host`. Claude Code can lack them too: on 2026-10-14 neither `tasks_login_status` nor a
Todoist tool was in the session's tool list. Check the list (ToolSearch) before you write
the ledger line, and use the same wording when they are absent.

## Volume

On 2026-10-14 the `recipient` filter returned 662 Teams messages and Alex's own posts
returned about 778 over two working days. Paging both and running Set A and Set R on that
volume fills the main thread. Give the Teams-and-mail part to one background agent with
this file and `jev-gates.md` as its brief, and keep Jira, GitHub and Planner in the main
thread. A busy Slack window can go to a second background agent the same way. The agent returns the ledger, the open asks with their numbers, and the answered
asks. Mail and Teams use the `m365` CLI (`../m365/SKILL.md`); Jira uses the Atlassian MCP (`searchJiraIssuesUsingJql`, `getJiraIssue`) in the main thread.

## Coverage ledger

One line per source, in the archeologist's three states (`unavailable — <reason>`,
`searched, N hits`, `not searched — <why>`). A 0 from Slack, Teams or mail on a window with a working
day is a coverage failure (SKILL.md step 3). A 0 from Planner, Todoist, or GitHub can be real.
