# EA Projects — REST write shapes

Payloads for writing curated rows to the **EA Projects** list. Hand these to the `sharepoint` agent (it owns cookie auth via `scripts/sharepoint/`, which ships with this skill). Read this before any write. Never change permissions.

- Site: `$SHAREPOINT_SITE_URL`, or `site_url` in `~/.config/ea-projects-curator.json`
- List id: resolved by title, `python3 scripts/sharepoint/resolve.py` (never copied into this file)
- View ids: `python3 scripts/sharepoint/resolve.py --views "Current bets"`
- Auth: helper cookies, ~7h TTL. On 401/403 the human runs `python3 scripts/sharepoint/auth.py "<site>" --refresh` (headed passkey).

## First: get the item entity type (don't hardcode)

```
GET /_api/web/lists(guid'<list id>')?$select=ListItemEntityTypeFullName
```
Use the returned `ListItemEntityTypeFullName` (expected `SP.Data.EA_x0020_PortfolioListItem`, but read it live) as `__metadata.type` below.

## Field value shapes

- **Choice** (`Theme`, `Status`, `EARole`) — plain string, must exactly match an allowed value. `DecisionNeeded`, `Outcome`, `TargetDate` and `Who_x0020_is_x0020_Responsible` were deleted on 2026-10-12: never write or `$select` them, the request fails.
- **Lookup, multi** (`AABItems`) — write the AAB Intake item IDs as `"AABItemsId": {"results": [33, 34]}` in verbose mode; the whole set is replaced, so read the current IDs first and send the union. Not yet verified by a live write: read the field back after the first one.
- **Impact** (`Impact`) — single line of text; the documented impact, financial or not. Omit the key entirely for blank.
- **Hyperlink** (`KeyArtifact`, `ExecutionLink`) — an `SP.FieldUrlValue`:
  ```json
  {"__metadata": {"type": "SP.FieldUrlValue"}, "Url": "https://...", "Description": "ADR-0002"}
  ```
- **Date** (`MilestoneDate`) — ISO 8601. Send **noon UTC** (`2026-07-25T12:00:00Z`) not midnight, so a timezone offset can't roll the displayed date back a day. Omit the key for no date.
- **Text** (`Title`, `NextMilestone`) — plain string.
- **Person, single** (`Sponsor`) — `"SponsorId": <int>`; resolve the person with `POST /_api/web/ensureuser`
  (`{"logonName": "i:0#.f|membership|<email>"}`, verbose headers) → `d.Id`. Names as strings are rejected.

## Create a NEW row

```
POST /_api/web/lists(guid'<list id>')/items
Headers: Content-Type: application/json;odata=verbose | Accept: application/json;odata=verbose | X-RequestDigest: <digest>
```
```json
{
  "__metadata": {"type": "SP.Data.EA_x0020_PortfolioListItem"},
  "Title": "Privileged Access Renewal",
  "Theme": "Platform Foundations",
  "Status": "1. Exploring",
  "EARole": "Builds",
  "Impact": "$478K/yr documented savings",
  "KeyArtifact": {"__metadata": {"type": "SP.FieldUrlValue"}, "Url": "https://.../ADR-0002.aspx", "Description": "ADR-0002 Privileged Access"},
  "ExecutionLink": {"__metadata": {"type": "SP.FieldUrlValue"}, "Url": "https://dev.azure.com/example-org/<living-project>/_workitems/edit/1234", "Description": "ADO epic"},
  "NextMilestone": "Options memo to the CTO",
  "MilestoneDate": "2026-07-25T12:00:00Z"
}
```
Omit any key that's blank (e.g. no documented `Impact` value, no `ExecutionLink`). The response contains the new item `Id` — record it in `curated.json`.

## UPDATE an existing row (changed fields only)

```
POST /_api/web/lists(guid'<list id>')/items(<itemId>)
Headers: ...odata=verbose | X-RequestDigest: <digest> | X-HTTP-Method: MERGE | If-Match: *
```
```json
{
  "__metadata": {"type": "SP.Data.EA_x0020_PortfolioListItem"},
  "Status": "3. Delivering",
  "NextMilestone": "Rollout to first team",
  "MilestoneDate": "2026-08-08T12:00:00Z"
}
```
Send only changed fields. `If-Match: *` overwrites regardless of etag (fine for a single-owner board; use the real etag for optimistic concurrency). A successful MERGE returns `204 No Content`.

## Comments on an item (narrative layer)

Modern list-item comments API. Same cookie auth; POST needs `X-RequestDigest`.

**Read existing comments first** (idempotency + pick up replies others left):

```
GET /_api/web/lists(guid'<list id>')/items(<itemId>)/Comments
Headers: Accept: application/json;odata=nometadata
```
Response `value[]`: each has `id`, `text`, `author.email`, `createdDate`, `isReply`. Newest first.

**Post a comment** (plain text only — no @-mentions, no HTML):

```
POST /_api/web/lists(guid'<list id>')/items(<itemId>)/Comments
Headers: Content-Type: application/json;odata=nometadata | Accept: application/json;odata=nometadata | X-RequestDigest: <digest>
```
> **Use `nometadata` here, NOT `odata=verbose`** (verified 2026-08-03). The endpoint takes a bare `{"text": ...}` body with no `__metadata`; verbose mode rejects it with `400 InvalidClientQueryException: "An entry without a type name was found, but no expected type was specified."` Item MERGE/create still needs verbose.

```json
{"text": "Verification evidence gathered; on track for the 07-25 options memo."}
```
201 returns the created comment (record `createdDate` + text in `curated.json` under the row's `comments` array).

Gotchas:
- Comments are **org-visible**: the full exclusion screen applies to `text`.
- **Append-only**: never DELETE or edit a comment; a correction is a new comment, even though the API allows deleting your own.
- A 404 or comments-disabled error means `CommentsDisabled=true` — report it, don't flip the setting.
- `@`-mention markup sends email notifications — never emit it.

## Find an item Id for matching (idempotency)

```
GET /_api/web/lists(guid'...')/items?$select=Id,Title,KeyArtifact,Status,AABItemsId,Impact,NextMilestone,MilestoneDate&$top=100
```
Match a candidate to an existing row by `Title` similarity + `KeyArtifact` Url. Match → UPDATE that `Id`; no match → CREATE.

---

# AAB Intake — REST read/write shapes

Second list Alex curates alongside EA Projects — the Architecture Advisory Board forum queue. Same site, same cookie auth. **Read-only checks power the Weekly AAB control; any field write still goes through the review table.**

- List GUID: `<AAB Intake list id>`
- Entity type: `SP.Data.AAB_x0020_IntakeListItem` (expected — read it live before every write)
- Fields used by the weekly control: `Title`, `Status` (`New` / `Triaged` / `Scheduled` / `Decided` / `Parked` / `Deflected`), `Scheduledfor` (DateTime with `Format="DateOnly"`), `Outcomenotes` (Note/text), `Modified`
- Site timezone: Central Time (US and Canada), verified 2026-08-10. Read `RegionalSettings/TimeZone` each run and use DST-aware UTC bounds for America/Chicago calendar dates.

## Read: metadata and timezone

```
GET /_api/web/lists(guid'<AAB Intake list id>')?$select=ListItemEntityTypeFullName
GET /_api/web/RegionalSettings?$select=TimeZone/Id,TimeZone/Description&$expand=TimeZone
```
If the site timezone no longer maps to America/Chicago, mark date-based checks UNVERIFIED rather than guessing.

## Read: intake items for session selection and close-out check

```
GET /_api/web/lists(guid'<AAB Intake list id>')/items?$select=Id,Title,Status,Scheduledfor,Outcomenotes,Modified&$top=100&$orderby=Scheduledfor desc
```
Use this to find the latest due session and its items. Treat a session dated today as due only when the exact-date recap or same-day outcome shows it happened; otherwise verify the previous session and report today upcoming/UNVERIFIED.

## Read: every stale scheduled item

Replace `<today-start-utc>` with site-local midnight converted to UTC, including the current DST offset.

```
GET /_api/web/lists(guid'<AAB Intake list id>')/items?$select=Id,Title,Status,Scheduledfor,Outcomenotes,Modified&$filter=Status eq 'Scheduled' and Scheduledfor lt datetime'<today-start-utc>'&$orderby=Scheduledfor asc
```
This catches past-dated `Scheduled` rows the normal views hide. Follow `d.__next` until absent; never treat the first page as the full result.

## Read: next calendar week's schedule

Replace both placeholders with the DST-aware UTC instants for next Monday and the following Monday in America/Chicago.

```
GET /_api/web/lists(guid'<AAB Intake list id>')/items?$select=Id,Title,Status,Scheduledfor&$filter=Status eq 'Scheduled' and Scheduledfor ge datetime'<next-monday-utc>' and Scheduledfor lt datetime'<following-monday-utc>'&$orderby=Scheduledfor asc
```
No item after all pages are read means ALERT: Alex must schedule the forum or confirm there is none.

## Read: published recap evidence

```
GET /_api/web/GetFolderByServerRelativeUrl('/sites/Architecture/SitePages/Recaps')/Files?$select=Name,ServerRelativeUrl,TimeLastModified,ListItemAllFields/Id,ListItemAllFields/PromotedState,ListItemAllFields/FirstPublishedDate,ListItemAllFields/Modified,ListItemAllFields/OData__ModerationStatus&$expand=ListItemAllFields&$orderby=Name desc&$top=20
```
Match the exact file name `<session-date>-AAB-Recap.aspx`. PASS only when `PromotedState=2`, `OData__ModerationStatus=0`, and `FirstPublishedDate` is present. A missing file, a draft, or a file that is not promoted News is an ALERT; a failed live read is UNVERIFIED.

## MERGE: apply approved intake field changes (Status / Outcomenotes / Scheduledfor only)

```
POST /_api/web/lists(guid'<AAB Intake list id>')/items(<itemId>)
Headers: Content-Type: application/json;odata=verbose | Accept: application/json;odata=verbose | X-RequestDigest: <digest> | X-HTTP-Method: MERGE | If-Match: *
```
```json
{
  "__metadata": {"type": "SP.Data.AAB_x0020_IntakeListItem"},
  "Status": "Decided",
  "Outcomenotes": "Approved for pilot; Security to confirm scope by 08-20."
}
```
Send only fields Alex approved — never invent `Outcomenotes` or a `Scheduledfor` date. For `Scheduledfor`, use noon UTC to avoid a timezone rollback. A successful MERGE returns `204 No Content`; **verify with a follow-up GET** before reporting the write as done.

---

# ADO — REST read/write shapes (EA areas)

Payloads for the [Weekly ADO control](../SKILL.md#weekly-ado-control--what-ea-does). Every write is an approved `W#` line. Never change permissions, areas, iterations, or process rules, and never delete a work item.

- Org: `https://dev.azure.com/example-org`. Project: `Information Technology`.
- Auth: Basic with an empty user and the `AZURE_DEVOPS_PAT` environment variable. Never print the token.
- Writes use `PATCH` / `POST` with `Content-Type: application/json-patch+json`, except comments (plain `application/json`).
- **Dry-run first.** Add `validateOnly=true` to any work item PATCH or create: ADO runs every process rule and saves nothing. Verified 2026-10-09 (the epic's links and Current Status were unchanged after the calls, and no probe item was created). Use it to catch a rule refusal before you put the line in front of Alex.

## Process rules the dry-run will enforce (verified 2026-10-09)

| Move | Required, or the write is refused |
|---|---|
| Epic `New` → `Active` | `Curo.ArchitectureReviewApprovedDate` and `Curo.ArchitectureReviewApprovedBy` (a person from the field's allowed list). This is the AAB gate in ADO. Take both values from a `Decided` AAB Intake item or Alex's own words, never from a guess |
| Epic `New` → `Closed` | Refused. States move one step at a time: `New` → `Active` → `Resolved` → `Closed` |
| Story to `In Progress` | `System.AssignedTo`, `System.Description`, `Microsoft.VSTS.Scheduling.StoryPoints` |
| Story to `Closed` | `Curo.IT.ValidationNotes` (the evidence, for example the merged PR) and `Curo.IT.ValidatedBy` (a person from the field's allowed list) |
| Story created in `New` | Title and area are enough |

A missing-item story that is already done needs validation evidence and a validator on its `W#` line. If the evidence or the person is missing, propose it in `New` and put the gap on `open_items`.

## Read an item with its links

```
GET /_apis/wit/workitems/<id>?$expand=relations&api-version=7.1
```
A row link shows as `relations[]` with `rel: "Hyperlink"` (verified on work item 256368). The parent is `rel: "System.LinkTypes.Hierarchy-Reverse"`; `System.Parent` also carries the parent id.

## Link an epic to its EA Projects row

```
PATCH /_apis/wit/workitems/<epicId>?api-version=7.1
```
```json
[{"op": "add", "path": "/relations/-",
  "value": {"rel": "Hyperlink",
            "url": "https://example.sharepoint.com/sites/Architecture/Lists/EA%20Portfolio/DispForm.aspx?ID=<rowId>",
            "attributes": {"comment": "EA Projects row"}}}]
```
Read the relations first: an epic that already has a row link (a Hyperlink whose URL contains `/Lists/EA%20Portfolio/DispForm.aspx`) gets no second one. Other hyperlinks do not count.

## Set a parent epic

```json
[{"op": "add", "path": "/relations/-",
  "value": {"rel": "System.LinkTypes.Hierarchy-Reverse",
            "url": "https://dev.azure.com/example-org/_apis/wit/workItems/<epicId>"}}]
```
An item can have only one parent; the write fails if it already has one.

## Set Current Status or State

```json
[{"op": "add", "path": "/fields/Curo.CurrentStatus", "value": "On Track"}]
```
`System.State` uses the same shape, one step at a time, and only on items assigned to Alex.

## Create a missing item

```
POST /Platform%20Project/_apis/wit/workitems/$User%20Story?api-version=7.1
```
```json
[{"op": "add", "path": "/fields/System.Title", "value": "<outcome-first title>"},
 {"op": "add", "path": "/fields/System.AreaPath", "value": "Information Technology\\Enterprise Architecture"},
 {"op": "add", "path": "/fields/System.AssignedTo", "value": "<who did the work>"},
 {"op": "add", "path": "/relations/-",
  "value": {"rel": "System.LinkTypes.Hierarchy-Reverse",
            "url": "https://dev.azure.com/example-org/_apis/wit/workItems/<epicId>"}}]
```
Use `$Spike` or `$Request` for those types. Create in `New`, then walk the states with the required fields above. Record the new id in the ledger `ado` key with `created_by_curator: true` and its evidence.

## Weekly epic update comment

**Read first** (idempotency, and replies other people left):

```
GET /Platform%20Project/_apis/wit/workItems/<epicId>/comments?api-version=7.1-preview.4&$top=10&order=desc
```

**Post** (the same call the ado-restructuring repo's incident-response seed script uses):

```
POST /Platform%20Project/_apis/wit/workItems/<epicId>/comments?api-version=7.1-preview.4
Content-Type: application/json
```
```json
{"text": "<div><b>Done this week:</b> ...</div><div><b>Next:</b> ...</div>"}
```

Gotchas:
- The text renders as **HTML**: one `<div>` per line, `<b>` for the labels, and escape `&`, `<` and `>` in the content. A bare newline collapses.
- **No @-mentions**: a mention notifies the person, and that is a human's call.
- **Append-only**: never edit or delete a comment; a correction is a new comment.
- Comments are readable by the whole org: the full exclusion screen applies.
- The response returns the created comment; read it back, then record its date and text in the ledger `ado.<id>.updates`.
