# EA Projects — REST write shapes

Payloads for writing curated rows to the **EA Projects** list. Hand these to the `sharepoint` agent (it owns cookie auth via `~/.claude/scripts/sharepoint/`). Read this before any write. Never change permissions.

- Site: `https://attainfinance.sharepoint.com/sites/Architecture`
- List GUID: `d2c0a30a-dab4-40a7-bc63-7268736473f2`
- Auth: helper cookies, ~7h TTL. On 401/403 the human runs `python3 ~/.claude/scripts/sharepoint/auth.py "<site>" --refresh` (headed passkey).

## First: get the item entity type (don't hardcode)

```
GET /_api/web/lists(guid'd2c0a30a-dab4-40a7-bc63-7268736473f2')?$select=ListItemEntityTypeFullName
```
Use the returned `ListItemEntityTypeFullName` (expected `SP.Data.EA_x0020_PortfolioListListItem`, but read it live) as `__metadata.type` below.

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
  "__metadata": {"type": "SP.Data.EA_x0020_PortfolioListListItem"},
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
  "__metadata": {"type": "SP.Data.EA_x0020_PortfolioListListItem"},
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
Headers: Content-Type: application/json;odata=verbose | Accept: application/json;odata=verbose | X-RequestDigest: <digest>
```
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
