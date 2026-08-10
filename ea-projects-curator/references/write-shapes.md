# EA Projects — REST write shapes

Payloads for writing curated rows to the **EA Projects** list. Hand these to the `sharepoint` agent (it owns cookie auth via `~/.claude/scripts/sharepoint/`). Read this before any write. Never change permissions.

- Site: `https://attainfinance.sharepoint.com/sites/Architecture`
- List GUID: `d2c0a30a-dab4-40a7-bc63-7268736473f2`
- Auth: helper cookies, ~7h TTL. On 401/403 the human runs `python3 ~/.claude/scripts/sharepoint/auth.py "<site>" --refresh` (headed passkey).

## First: get the item entity type (don't hardcode)

```
GET /_api/web/lists(guid'd2c0a30a-dab4-40a7-bc63-7268736473f2')?$select=ListItemEntityTypeFullName
```
Use the returned `ListItemEntityTypeFullName` (expected `SP.Data.EA_x0020_PortfolioListItem`, but read it live) as `__metadata.type` below.

## Field value shapes

- **Choice** (`Theme`, `Status`, `DecisionNeeded`) — plain string, must exactly match an allowed value.
- **Impact** (`Impact`) — single line of text; the documented impact, financial or not. Omit the key entirely for blank.
- **Hyperlink** (`KeyArtifact`, `ExecutionLink`) — an `SP.FieldUrlValue`:
  ```json
  {"__metadata": {"type": "SP.FieldUrlValue"}, "Url": "https://...", "Description": "ADR-0002"}
  ```
- **Date** (`MilestoneDate`) — ISO 8601. Send **noon UTC** (`2026-07-25T12:00:00Z`) not midnight, so a timezone offset can't roll the displayed date back a day. Omit the key for no date.
- **Text** (`Title`, `NextMilestone`) — plain string.

## Create a NEW row

```
POST /_api/web/lists(guid'd2c0a30a-dab4-40a7-bc63-7268736473f2')/items
Headers: Content-Type: application/json;odata=verbose | Accept: application/json;odata=verbose | X-RequestDigest: <digest>
```
```json
{
  "__metadata": {"type": "SP.Data.EA_x0020_PortfolioListItem"},
  "Title": "Privileged Access Renewal",
  "Theme": "Platform Foundations",
  "Status": "3. Decision-Ready",
  "DecisionNeeded": "CTO",
  "Impact": "$478K/yr documented savings",
  "KeyArtifact": {"__metadata": {"type": "SP.FieldUrlValue"}, "Url": "https://.../ADR-0002.aspx", "Description": "ADR-0002 Privileged Access"},
  "ExecutionLink": {"__metadata": {"type": "SP.FieldUrlValue"}, "Url": "https://dev.azure.com/CuroFinTech/Tiger/...", "Description": "ADO epic"},
  "NextMilestone": "Options memo to the CTO",
  "MilestoneDate": "2026-07-25T12:00:00Z"
}
```
Omit any key that's blank (e.g. no documented `ImpactUSD`, no `ExecutionLink`). The response contains the new item `Id` — record it in `curated.json`.

## UPDATE an existing row (changed fields only)

```
POST /_api/web/lists(guid'd2c0a30a-dab4-40a7-bc63-7268736473f2')/items(<itemId>)
Headers: ...odata=verbose | X-RequestDigest: <digest> | X-HTTP-Method: MERGE | If-Match: *
```
```json
{
  "__metadata": {"type": "SP.Data.EA_x0020_PortfolioListItem"},
  "Status": "4. In Progress",
  "DecisionNeeded": "None",
  "NextMilestone": "Rollout to first team",
  "MilestoneDate": "2026-08-08T12:00:00Z"
}
```
Send only the fields that changed. `If-Match: *` overwrites regardless of etag (fine for a single-owner board); use the real etag if you want optimistic concurrency. A successful MERGE returns `204 No Content`.

## Comments on an item (narrative layer)

Modern list-item comments API. Same cookie auth; POST needs `X-RequestDigest`.

**Read existing comments first** (idempotency + pick up replies others left):

```
GET /_api/web/lists(guid'd2c0a30a-dab4-40a7-bc63-7268736473f2')/items(<itemId>)/Comments
Headers: Accept: application/json;odata=nometadata
```
Response `value[]`: each has `id`, `text`, `author.email`, `createdDate`, `isReply`. Newest first.

**Post a comment** (plain text only — no @-mentions, no HTML):

```
POST /_api/web/lists(guid'd2c0a30a-dab4-40a7-bc63-7268736473f2')/items(<itemId>)/Comments
Headers: Content-Type: application/json;odata=nometadata | Accept: application/json;odata=nometadata | X-RequestDigest: <digest>
```
> **Use `nometadata` here, NOT `odata=verbose`** (verified 2026-08-03). The comments endpoint takes a bare `{"text": ...}` body with no `__metadata`, so verbose mode rejects it with `400 InvalidClientQueryException: "An entry without a type name was found, but no expected type was specified."` Item MERGE/create above still needs verbose.

```json
{"text": "Verification evidence gathered; on track for the 07-25 options memo."}
```
201 returns the created comment (record `createdDate` + text in `curated.json` under the row's `comments` array).

Gotchas:
- Comments are **org-visible** like the row — the full exclusion screen applies to `text`.
- **Append-only policy**: never DELETE or edit comments, a correction is a new comment. (The API allows `DELETE .../Comments(<id>)` on your own — don't use it.)
- If the endpoint 404s or errors with comments disabled, the list has `CommentsDisabled=true` — report it, don't try to flip the setting.
- `@`-mention markup (`<a data-sp-mention-user-id=...>`) exists but sends email notifications — never emit it.

## Find an item Id for matching (idempotency)

```
GET /_api/web/lists(guid'...')/items?$select=Id,Title,KeyArtifact,Status,DecisionNeeded,Impact,NextMilestone,MilestoneDate&$top=100
```
Match a candidate to an existing row by `Title` similarity + `KeyArtifact` Url. Match → UPDATE that `Id`; no match → CREATE.

---

# AAB Intake — REST read/write shapes

Second list Alex curates alongside EA Projects — the Architecture Advisory Board forum queue. Same site, same cookie auth. **Read-only checks power the Weekly AAB control; any field write still goes through the review table.**

- List GUID: `80c68e54-eadf-4cf3-946a-3c0e432056a5`
- Entity type: `SP.Data.AAB_x0020_IntakeListItem` (expected — read it live before every write)
- Fields used by the weekly control: `Title`, `Status` (`New` / `Triaged` / `Scheduled` / `Decided` / `Parked` / `Deflected`), `Scheduledfor` (DateTime with `Format="DateOnly"`), `Outcomenotes` (Note/text), `Modified`
- Site timezone: Central Time (US and Canada), verified 2026-08-10. Read `RegionalSettings/TimeZone` each run and use DST-aware UTC bounds for America/Chicago calendar dates.

## Read: metadata and timezone

```
GET /_api/web/lists(guid'80c68e54-eadf-4cf3-946a-3c0e432056a5')?$select=ListItemEntityTypeFullName
GET /_api/web/RegionalSettings?$select=TimeZone/Id,TimeZone/Description&$expand=TimeZone
```
If the site timezone no longer maps to America/Chicago, mark date-based checks UNVERIFIED rather than guessing.

## Read: intake items for session selection and close-out check

```
GET /_api/web/lists(guid'80c68e54-eadf-4cf3-946a-3c0e432056a5')/items?$select=Id,Title,Status,Scheduledfor,Outcomenotes,Modified&$top=100&$orderby=Scheduledfor desc
```
Use this to find the latest due session and every item scheduled for that exact site-local session date. Treat a date scheduled for today as due only when the exact-date recap or same-day outcome data shows the session happened; otherwise verify the previous session and report today as upcoming/UNVERIFIED.

## Read: every stale scheduled item

Replace `<today-start-utc>` with site-local midnight converted to UTC, including the current DST offset.

```
GET /_api/web/lists(guid'80c68e54-eadf-4cf3-946a-3c0e432056a5')/items?$select=Id,Title,Status,Scheduledfor,Outcomenotes,Modified&$filter=Status eq 'Scheduled' and Scheduledfor lt datetime'<today-start-utc>'&$orderby=Scheduledfor asc
```
This dedicated query catches past-dated `Scheduled` rows that both normal views hide. Follow `d.__next` until absent; never treat the first page as the full result.

## Read: next calendar week's schedule

Replace both placeholders with the DST-aware UTC instants for next Monday and the following Monday in America/Chicago.

```
GET /_api/web/lists(guid'80c68e54-eadf-4cf3-946a-3c0e432056a5')/items?$select=Id,Title,Status,Scheduledfor&$filter=Status eq 'Scheduled' and Scheduledfor ge datetime'<next-monday-utc>' and Scheduledfor lt datetime'<following-monday-utc>'&$orderby=Scheduledfor asc
```
No returned item after all pages are read means ALERT: Alex must schedule the forum or confirm there is no session.

## Read: published recap evidence

```
GET /_api/web/GetFolderByServerRelativeUrl('/sites/Architecture/SitePages/Recaps')/Files?$select=Name,ServerRelativeUrl,TimeLastModified,ListItemAllFields/Id,ListItemAllFields/PromotedState,ListItemAllFields/FirstPublishedDate,ListItemAllFields/Modified,ListItemAllFields/OData__ModerationStatus&$expand=ListItemAllFields&$orderby=Name desc&$top=20
```
Match the exact file name `<session-date>-AAB-Recap.aspx`. PASS only when `PromotedState=2`, `OData__ModerationStatus=0`, and `FirstPublishedDate` is present. A missing file, a draft, or a file that is not promoted News is an ALERT; a failed live read is UNVERIFIED.

## MERGE: apply approved intake field changes (Status / Outcomenotes / Scheduledfor only)

```
POST /_api/web/lists(guid'80c68e54-eadf-4cf3-946a-3c0e432056a5')/items(<itemId>)
Headers: Content-Type: application/json;odata=verbose | Accept: application/json;odata=verbose | X-RequestDigest: <digest> | X-HTTP-Method: MERGE | If-Match: *
```
```json
{
  "__metadata": {"type": "SP.Data.AAB_x0020_IntakeListItem"},
  "Status": "Decided",
  "Outcomenotes": "Approved for pilot; Security to confirm scope by 08-20."
}
```
Send only the fields Alex approved in the review table — never invent `Outcomenotes` text or a `Scheduledfor` date. For a `Scheduledfor` write, use noon UTC (`2026-08-19T12:00:00Z`) to avoid a timezone rollback. A successful MERGE returns `204 No Content`; **verify with a follow-up GET** on the changed fields before reporting the write as done.
