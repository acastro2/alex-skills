# Azure DevOps REST API Guide

Quick reference for common Azure DevOps work item API operations against `https://dev.azure.com/CuroFinTech/Tiger`.

## Authentication

All requests use Basic Auth with empty username and a Personal Access Token:

```bash
AUTH=(-u ":$AZURE_DEVOPS_EXT_PAT")
BASE="https://dev.azure.com/CuroFinTech/Tiger"
```

Required PAT scopes: `vso.work` (read) and `vso.work_write` (create/update).

If a request returns HTTP 302 redirecting to `vssps.visualstudio.com/_signin`, the PAT is missing or expired in the current shell.

## Common Operations

### Get Work Item

```bash
curl -s "${AUTH[@]}" \
  "$BASE/_apis/wit/workitems/1234?api-version=7.1&\$expand=all" | jq '.'
```

`$expand` accepts: `none` (default), `relations`, `fields`, `links`, `all`. You can also restrict fields:

```bash
curl -s "${AUTH[@]}" \
  "$BASE/_apis/wit/workitems/1234?api-version=7.1&fields=System.Id,System.Title,System.State"
```

**Useful jq paths**:

- `.id` — work item ID
- `.rev` — current revision (needed for safe updates)
- `.fields["System.Title"]`
- `.fields["System.Description"]` — HTML
- `.fields["System.State"]` (e.g. New, Active, Resolved, Closed)
- `.fields["System.WorkItemType"]`
- `.fields["System.AssignedTo"].displayName`
- `.fields["System.AreaPath"]`
- `.fields["System.IterationPath"]`
- `.fields["System.Tags"]` — semicolon-separated string
- `.fields["Microsoft.VSTS.Common.AcceptanceCriteria"]`
- `._links.html.href` — user-facing URL

### Batch Get

```bash
curl -s "${AUTH[@]}" \
  "$BASE/_apis/wit/workitems?ids=1,2,3&api-version=7.1&fields=System.Id,System.Title,System.State" \
  | jq '.value[]'
```

Up to 200 IDs per call.

### Search via WIQL

WIQL (Work Item Query Language) is ADO's SQL-like query syntax. POST a query, get back IDs only, then hydrate.

```bash
QUERY='{"query":"SELECT [System.Id],[System.Title],[System.State] FROM WorkItems WHERE [System.TeamProject]=@project AND [System.WorkItemType]=\"User Story\" AND [State] <> \"Closed\" ORDER BY [System.ChangedDate] DESC"}'

curl -s "${AUTH[@]}" -X POST -H "Content-Type: application/json" \
  "$BASE/Echo/_apis/wit/wiql?api-version=7.1&\$top=20" \
  -d "$QUERY" | jq '.workItems[].id'
```

`@project` and `@me` are server-side macros. `@currentIteration('[Tiger]\Echo')` gives the current sprint of a team.

WIQL gotchas:

- String literals use double quotes inside JSON (escape them)
- Use `[Field.Reference.Name]` in brackets
- Date/time literals: `'2024-01-01T00:00:00Z'`
- Tag membership: `[System.Tags] CONTAINS 'auth'`
- Returns max 20,000 IDs; use `$top` to limit

### Get Comments (Discussion)

```bash
curl -s "${AUTH[@]}" \
  "$BASE/_apis/wit/workItems/1234/comments?api-version=7.1-preview.4" \
  | jq '.comments[] | {createdBy: .createdBy.displayName, createdDate, text}'
```

### Create Work Item

Pre-flight: list available work item types so you pick one that exists in this project's process template.

```bash
curl -s "${AUTH[@]}" \
  "$BASE/_apis/wit/workitemtypes?api-version=7.1" | jq '.value[].name'
# Agile  → "User Story", "Bug", "Task", "Epic", "Feature"
# Scrum  → "Product Backlog Item", "Bug", "Task", "Epic", "Feature"
# Basic  → "Issue", "Epic", "Task"
```

Then POST a JSON Patch document. **Note the literal `$` before the type name in the URL** — URL-encode spaces as `%20`:

```bash
TYPE="User%20Story"
curl -s "${AUTH[@]}" -X POST -H "Content-Type: application/json-patch+json" \
  "$BASE/_apis/wit/workitems/\$$TYPE?api-version=7.1" \
  -d '[
    {"op":"add","path":"/fields/System.Title","value":"[ECHO] Enable OAuth2 Google login"},
    {"op":"add","path":"/fields/System.Description","value":"<h3>1. Constitutional Intent</h3><p>...</p>"},
    {"op":"add","path":"/fields/Microsoft.VSTS.Common.AcceptanceCriteria","value":"<ul><li>Given user is logged out, When they click Google, Then OAuth flow starts</li></ul>"},
    {"op":"add","path":"/fields/System.AreaPath","value":"Tiger\\Echo"},
    {"op":"add","path":"/fields/System.IterationPath","value":"Tiger"},
    {"op":"add","path":"/fields/System.Tags","value":"auth; oauth2"}
  ]'
```

Optional query flags:

- `bypassRules=true` — skip work item rules (requires admin scope)
- `suppressNotifications=true` — don't email watchers
- `validateOnly=true` — dry run, returns what would happen

Response includes `.id`, `.rev`, and `._links.html.href` — return the html href to the user.

### Update Work Item

Always read first to capture `rev`, then PATCH with a `test` op for optimistic concurrency:

```bash
REV=$(curl -s "${AUTH[@]}" "$BASE/_apis/wit/workitems/1234?api-version=7.1" | jq '.rev')

curl -s "${AUTH[@]}" -X PATCH -H "Content-Type: application/json-patch+json" \
  "$BASE/_apis/wit/workitems/1234?api-version=7.1" \
  -d "[
    {\"op\":\"test\",\"path\":\"/rev\",\"value\":$REV},
    {\"op\":\"replace\",\"path\":\"/fields/System.Title\",\"value\":\"Updated title\"},
    {\"op\":\"replace\",\"path\":\"/fields/System.Description\",\"value\":\"<h3>1. ...</h3>\"}
  ]"
```

If HTTP 412, refetch and retry — someone else updated the item.

### JSON Patch Op Reference

| op | use |
|----|-----|
| `add` | Set a field value. For string fields acts like replace. For `/relations/-` appends a relation. |
| `replace` | Replace existing field value. Fails if field not present (use `add`). |
| `remove` | Remove a field or `/relations/{idx}`. |
| `test` | Assert a value (used with `/rev` for concurrency). |
| `move`, `copy` | Rarely used for work items. |

### Add Discussion Comment

Prefer the dedicated comments endpoint:

```bash
curl -s "${AUTH[@]}" -X POST -H "Content-Type: application/json" \
  "$BASE/_apis/wit/workItems/1234/comments?api-version=7.1-preview.4" \
  -d '{"text":"<p>Comment body in HTML</p>"}'
```

Alternative (older, also adds to history):

```bash
curl -s "${AUTH[@]}" -X PATCH -H "Content-Type: application/json-patch+json" \
  "$BASE/_apis/wit/workitems/1234?api-version=7.1" \
  -d '[{"op":"add","path":"/fields/System.History","value":"<p>Comment body</p>"}]'
```

### Link to PR or Related Work Item

```bash
# Related work item
curl -s "${AUTH[@]}" -X PATCH -H "Content-Type: application/json-patch+json" \
  "$BASE/_apis/wit/workitems/1234?api-version=7.1" \
  -d '[{
    "op":"add","path":"/relations/-",
    "value":{
      "rel":"System.LinkTypes.Related",
      "url":"https://dev.azure.com/CuroFinTech/Tiger/_apis/wit/workItems/5678",
      "attributes":{"comment":"related to"}
    }
  }]'

# Parent (Story under Feature)
# rel: System.LinkTypes.Hierarchy-Reverse  (this item's parent)
# rel: System.LinkTypes.Hierarchy-Forward  (this item's child)

# External hyperlink (e.g. GitHub PR)
curl -s "${AUTH[@]}" -X PATCH -H "Content-Type: application/json-patch+json" \
  "$BASE/_apis/wit/workitems/1234?api-version=7.1" \
  -d '[{"op":"add","path":"/relations/-","value":{"rel":"Hyperlink","url":"https://github.com/org/repo/pull/42"}}]'
```

Common `rel` values:

- `System.LinkTypes.Related`
- `System.LinkTypes.Hierarchy-Forward` / `Hierarchy-Reverse`
- `System.LinkTypes.Dependency-Forward` / `Dependency-Reverse`
- `Hyperlink`
- `AttachedFile`
- `ArtifactLink` (for build/PR/branch links — needs special vstfs URLs)

### List Areas and Iterations

```bash
curl -s "${AUTH[@]}" \
  "$BASE/_apis/wit/classificationnodes/areas?api-version=7.1&\$depth=3" \
  | jq '.. | objects | select(.path?) | {name, path}'

curl -s "${AUTH[@]}" \
  "$BASE/_apis/wit/classificationnodes/iterations?api-version=7.1&\$depth=3"
```

Area/iteration values for fields use **backslash separators**, e.g. `Tiger\Echo` (in JSON: `"Tiger\\Echo"`).

### Team Settings (default area + current iteration)

```bash
curl -s "${AUTH[@]}" \
  "$BASE/Echo/_apis/work/teamsettings?api-version=7.1" | jq '.'
```

### Stored Queries

If a user shares a query URL `.../_queries/query/{guid}`, run it server-side:

```bash
curl -s "${AUTH[@]}" -X POST -H "Content-Type: application/json" \
  "$BASE/_apis/wit/wiql/{guid}?api-version=7.1"
```

## Error Reference

| HTTP | Meaning | Fix |
|------|---------|-----|
| 200/201 | Success | — |
| 302 → `_signin` | PAT missing/expired | Re-export `AZURE_DEVOPS_EXT_PAT` |
| 401 | PAT lacks scope | Regenerate with `vso.work_write` |
| 403 | Project permission denied | Check user is in project |
| 404 | Wrong ID, wrong project, or item deleted | Verify in ADO UI |
| 400 invalid patch | Wrong content-type or body | Use `application/json-patch+json`, body must be JSON array |
| 400 field required | Missing required field for type | Refetch type schema |
| 412 | `rev` test failed | Refetch and retry |
