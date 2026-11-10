# Azure DevOps adapter

Read this before any Azure DevOps write. The core workflow is in `../SKILL.md`; this file holds what only ADO needs. REST detail is in `ado-api-guide.md`, HTML snippets in `html-examples.md`.

## Render

The six sections go in `System.Description` as **HTML**. Mirror the Section 1 ACs into `Microsoft.VSTS.Common.AcceptanceCriteria`: that field powers ADO's native AC reporting. `scripts/html_builder.py` builds the HTML and the JSON Patch.

### Allowed Elements (rendered cleanly)

`<h1>`–`<h6>`, `<p>`, `<strong>`, `<em>`, `<u>`, `<s>`, `<br>`, `<ul>`/`<ol>`/`<li>`, `<a href>`, `<code>`, `<pre>`, `<blockquote>`, `<table>`/`<tr>`/`<td>`, `<img>` (for inline attached images).

### Caveats

- Inline `style=` is mostly stripped — rely on semantic tags
- `<input type=checkbox>` is **not interactive** in descriptions — use a `<ul>` or the AcceptanceCriteria field
- Markdown is NOT rendered in description — convert before sending
- Always escape user content: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`

---

## Pre-flight

Always verify before API calls:

**First resolve the org and the project, never memorize them.** `ORG=$(python3 scripts/resolve_ado.py org)` reads the environment, `az devops configure`, or `~/.config/ado-ticket-writer.json`. `python3 scripts/resolve_ado.py projects` lists the projects that exist right now. New work goes only to a project the user confirms is live; retired projects stay read-only. A stale name files work where nobody looks.

```bash
AUTH=(-u ":$AZURE_DEVOPS_PAT")
BASE="https://dev.azure.com/$ORG/<project>"  # <project> from `resolve_ado.py projects`

# List EVERY work item type in the project, then match each ticket to one (see "Choose the type")
curl -s "${AUTH[@]}" "$BASE/_apis/wit/workitemtypes?api-version=7.1" \
  | jq '.value[] | .name'

# Validate area and iteration
curl -s "${AUTH[@]}" "$BASE/_apis/wit/classificationnodes/areas?api-version=7.1&\$depth=3"
curl -s "${AUTH[@]}" "$BASE/_apis/wit/classificationnodes/iterations?api-version=7.1&\$depth=3"

# For updates, fetch current state + rev
curl -s "${AUTH[@]}" "$BASE/_apis/wit/workitems/1234?api-version=7.1&\$expand=all"
```

**Same checks through the Azure DevOps MCP connector** (when you use the `mcp__claude_ai_Azure_DevOps__*` tools instead of curl):

- Type schema, fields, states: `wit_work_item` with `action: get_type` and the type name. The result is large; read states, required fields and the project's custom fields from the saved file. Field reference names carry the org's own prefix, so never retype one from memory.
- Team area and default iteration: `work` with `action: get_team_settings`.
- Duplicate check before every create: `wit_query` with `action: wiql`, searching the area for the title you are about to use. Run it again before retrying a create that returned an error: the create may have landed.

## Types

Types and states differ per project and drift, so read them: `GET $BASE/_apis/wit/workitemtypes` and `GET $BASE/_apis/wit/workitemtypes/{type}/states`. A type can be valid for the API and hidden on a team's backlog, so check the state list before you move an item.

- **Bug**: set `Microsoft.VSTS.TCM.ReproSteps`.
- **Spike**: read its timebox fields from `get_type`.
- **Changing a type**: update `System.WorkItemType` (it keeps the ID and links), then re-set the state, since states differ per type.

## Fields

**Required fields per JSON Patch op**:

- `/fields/System.Title`
- `/fields/System.Description` (HTML, the six sections)
- `/fields/System.AreaPath` (e.g. `<project>\<area>`; read the area tree, never guess it)
- `/fields/System.IterationPath`

**Recommended**:

- `/fields/Microsoft.VSTS.Common.AcceptanceCriteria` (HTML)
- `/fields/System.Tags` (semicolon-separated)
- `/fields/Microsoft.VSTS.Common.Priority`

## Updates

Always include an optimistic-concurrency `test` op on `/rev`:

```json
[
  {"op": "test", "path": "/rev", "value": 7},
  {"op": "replace", "path": "/fields/System.Description", "value": "<h3>1. ...</h3>"}
]
```

Attach PRs and related items as **link relations**, not inline URLs (see `ado-api-guide.md`).

## Errors

| Error | Resolution |
|-------|------------|
| HTTP 302 → `_signin` | PAT missing/expired in shell. Re-export `AZURE_DEVOPS_PAT` and restart opencode |
| HTTP 401 | PAT lacks `vso.work` / `vso.work_write` scope |
| HTTP 404 | Confirm work item ID and project in ADO UI |
| HTTP 400 invalid patch | Wrong content-type — use `application/json-patch+json` |
| HTTP 412 | `rev` mismatch (concurrent edit) — refetch and retry |
| HTML render issues | Simplify; check tag balance; remove inline styles |
