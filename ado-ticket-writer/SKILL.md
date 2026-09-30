---
name: ado-ticket-writer
description: Write and update Azure DevOps work items using the PARCH-6 template for spec-driven development. Use when creating new work items, updating existing ones from code changes, or converting PRs/branches into properly structured ADO User Stories. Supports traversing git changes to auto-generate ticket content, creating items with clear acceptance criteria, and updating items while preserving existing content. Works with @ado for API operations.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: ticket-management
---

# ADO Work Item Writer

Write spec-driven Azure DevOps work items that capture **what** changed and **why** — derived from actual code changes, not written in isolation.

## Core Principle: Code-First Ticket Writing

**Traditional approach**: Write ticket → Do work → Close ticket
**This skill's approach**: Do work → Analyze changes → Write/update ticket

Tickets should describe actual changes, not speculative requirements. Traverse branches/PRs to understand what was built, then document it properly.

## When to Use

- **Creating items from branches/PRs**: Code exists, needs documentation
- **Updating existing items**: Sync work item with actual implementation
- **Writing spec-driven items**: Clear ACs based on real changes
- **Converting PR descriptions to ADO**: Formalize ad-hoc work
- **Backfilling documentation**: Code merged without proper work items

## Workflow Overview

```
Analyze Changes → Extract Intent → Structure Work Item → Create/Update via @ado
```

---

## Phase 1: Analyze Code Changes

### Git Traversal

Before writing anything, understand what actually changed:

```bash
git log main..HEAD --oneline --no-merges
git diff main..HEAD --stat
git diff main..HEAD
git diff main..HEAD --name-only
```

### Change Analysis Framework

For each commit or logical change group, extract:

| Element | What to Capture | Example |
|---------|----------------|---------|
| **Action** | What was done | "Added", "Fixed", "Refactored", "Removed" |
| **Target** | What was changed | "user authentication", "API rate limiting" |
| **Motivation** | Why it was done | "to support OAuth2", "to prevent abuse" |
| **Impact** | What changes for users | "Users can now login with Google" |

### Commit Message Parsing

Parse conventional commits for structure:

```
feat(auth): add OAuth2 Google provider

- Implements OAuth2 flow for Google
- Adds user profile sync
- Updates login UI with Google button

Fixes: #1234
```

Extract:

- **Type**: feat → Feature
- **Scope**: auth → Authentication service
- **Subject**: add OAuth2 Google provider
- **Body**: Implementation details
- **Footer**: Related ADO IDs

---

## Phase 2: Structure with PARCH-6 Template

Every Story / User Story / Product Backlog Item MUST use the 6-section structure, rendered as HTML for `System.Description`. See `references/ado-template.md` for the complete template with examples.

### Section 1: Constitutional Intent & Success Criteria

**The "North Star" — what success looks like**

```html
<p><strong>Objective:</strong> [One-sentence end-state summary]</p>
<p><strong>Acceptance Criteria (Given/When/Then):</strong></p>
<ul>
  <li>Given [pre], When [action], Then [outcome]</li>
</ul>
```

**Mirror the AC list into `Microsoft.VSTS.Common.AcceptanceCriteria`** as well — that field powers ADO's native AC reporting and the AC pane in the work item editor.

**Rules**:

- Objective must be testable reality, not activity
- ACs must be verifiable without implementation knowledge
- Use Given/When/Then format

### Section 2: Constraints & Guardrails

```html
<p><strong>Critical Non-Actions:</strong></p>
<ul>
  <li>DO NOT: [constraint 1]</li>
</ul>
<p><strong>Security &amp; Compliance:</strong> [requirements]</p>
<p><strong>Timing/SLA:</strong> [constraints]</p>
```

### Section 3: Technical Interface (The Contract)

```html
<p><strong>Configuration &amp; Connectivity:</strong></p>
<ul><li>endpoint, port, env vars</li></ul>
<p><strong>Data Schema &amp; Models:</strong></p>
<pre><code>{ "field": "type" }</code></pre>
<p><strong>API Contracts:</strong></p>
<ul><li><code>POST /api/v1/resource</code></li></ul>
```

### Section 4: Logic & Implementation Flow

```html
<p><strong>Phase 1 (Preparation):</strong> setup steps</p>
<p><strong>Phase 2 (Execution):</strong> core logic steps</p>
<p><strong>Phase 3 (Finalization):</strong> cleanup, verification</p>
```

### Section 5: Validation Steps

```html
<p><strong>Action:</strong> [command or test]</p>
<p><strong>Expected Result:</strong> [success indicator]</p>
```

### Section 6: Resources & Team Context

```html
<p><strong>Runbook:</strong> [link]</p>
<p><strong>Infrastructure Source:</strong> [git link]</p>
<p><strong>Support Channel:</strong> [slack channel]</p>
<p><strong>Related PRs:</strong> [links]</p>
```

Where possible, attach PRs and related work items as **link relations** instead of inline URLs (see `references/ado-api-guide.md`).

---

## Phase 3: Create or Update Work Item

### Pre-flight Checks

Always verify before API calls:

**First resolve the project.** New work goes only to the five living projects: `Software Engineering`, `Information Technology`, `Change Control`, `Incident Response`, `Enterprise Portfolio`. Tiger, Risk Analytics and Marketing are closed to new work — read them for legacy items only.

```bash
AUTH=(-u ":$AZURE_DEVOPS_PAT")
BASE="https://dev.azure.com/CuroFinTech/Software%20Engineering"  # the team's living project

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

- Type schema, fields, states: `wit_work_item` with `action: get_type` and the type name. The result is large; read states, required fields and custom `Curo.*` fields from the saved file.
- Team area and default iteration: `work` with `action: get_team_settings`.
- Duplicate check before every create: `wit_query` with `action: wiql`, searching the area for the title you are about to use. Run it again before retrying a create that returned an error: the create may have landed.

### Choose the type

Never default to the Story type. List the types first, then pick per ticket:

| The ticket is... | Type | Set also |
|---|---|---|
| A timeboxed investigation, exploration, inventory or spike | **Spike** | `Curo.Spike.TimeboxValue` + `Curo.Spike.TimeboxUnit` (e.g. 2, Days); `Curo.Spike.Outcome` when it closes |
| A defect in something that already shipped | **Bug** | `Microsoft.VSTS.TCM.ReproSteps` |
| Planned delivery with a user-visible outcome | **User Story** (or the project's Story equivalent) | AcceptanceCriteria |
| Run-the-business work with no new outcome | **Operational Work**, if the project has it | |
| A change record | **CC** / **ITCC** | follow `attain-change-control` |
| An ask from another team that an IT team fulfills in the same ticket (Information Technology only) | **Request** | the intake fields in "The IT Request" below |

Never mark a spike with a `spike` tag on a Story: use the Spike type. If the type you need is not in the list, say so and ask; do not substitute.

**Known custom sets (verify, they drift):** Software Engineering ships User Story, Bug, Epic, Task, Spike, Operational Work, ITCC, CC and Milestone. Information Technology has at least Epic, Feature, User Story and Spike (checked 2026-09-29). In Information Technology, Spike and User Story have a `Ready` state; Feature only has New/Active/Resolved/Closed and is hidden on the Enterprise Architecture team backlog, so a Feature there cannot be moved to Ready on the board.

Changing the type of an existing item works: update `System.WorkItemType` (it keeps the ID and links), then re-set the state, since states differ per type.

#### The IT Request (Information Technology only)

A `Request` is an internal team-to-team ask that the requested IT team fulfills **in the same ticket**. It does not spawn a child Story, Bug, Spike or Operational Work item by default. It exists only in the `Information Technology` project.

**Not a Request:**

- Non-project Help Desk work: that stays in Ivanti.
- Production change approval: that stays in an `ITCC` for an IT change, or a `CC` for an in-house application change. Link the ITCC to the Request; do not approve inside the Request.
- Work IT plans for itself: a `User Story`, `Spike` or `Operational Work`.

**Intake fields.** Created By is not the requester, and Assigned To is not the requested team, so set the request fields:

| Field | Rule |
|---|---|
| `Curo.IT.Planned` | Always required |
| `Curo.IT.NeededByDate` | Required in New, Ready and In Progress |
| `Curo.IT.RequestUrgentChoice` | Required in New, Ready and In Progress; if Urgent = Yes, `Curo.IT.UrgencyReason` is required too |
| `Curo.IT.Requester`, `Curo.IT.RequestingTeam` | Who asked, and for which team |
| `Curo.IT.DeadlineReason`, `Curo.IT.RequestCategory`, `Curo.IT.RequestServiceCategory`, `Curo.IT.RequestBusinessArea`, `Curo.IT.RequestPurpose` | The context the requested team needs |
| `Curo.IT.RequestPriority` | 1 to 12. The requester describes urgency; the requested team owns queue order |

Identity fields take the person's email, and the person must be a member of the project.

**States:** New → Ready → In Progress → Validating (non-production path) or Pending (production path, through a linked ITCC) → Closed.

**Two checks before it closes:**

1. **Internal validation**: IT confirms the work is done, in `Curo.IT.ValidatedBy`, `Curo.IT.ValidatedDate` and `Curo.IT.ValidationNotes`.
2. **Requester verification**: the requester, or the nominated `Curo.IT.RequestVerifier`, confirms it landed, in `Curo.IT.VerifiedBy`, `Curo.IT.VerifiedDate` and `Curo.IT.VerificationNotes`. Someone may verify on the requester's behalf only with evidence in the notes.

Moving to Validating or Pending with validation evidence and a nominated verifier starts the verification round: the verifier gets a Teams message and an email, then a weekday reminder. The flow closes the Request when it accepts the verification. Closing needs Validated By, Validation Notes, Verified By and Verified Date filled.

Source: the `ado-restructuring` repo, `docs/knowledge/information-technology/request-model.md` and `request-verification.md`. The rules drift, so read those first when in doubt.

### Creating New Work Items

**Title format**: `[SERVICE-NAME] Outcome description`

- **SERVICE-NAME**: Affected service/component, ALL CAPS (`AUTH-SERVICE`, `API-GATEWAY`, `PAYMENT-ENGINE`, `ECHO`)
- **Outcome**: What was achieved (not the activity)
- Keep under 80 chars when possible

**Examples**:

- `[ECHO] Enable OAuth2 Google authentication for users`
- `[API-GATEWAY] Add rate limiting to prevent abuse`
- `[PAYMENT-ENGINE] Fix race condition in transaction processing`

**Bad examples**:

- ~~"Add OAuth2"~~ (no service, no outcome)
- ~~"[Auth] Implement Google login"~~ (lowercase service, describes activity)
- ~~"Authentication Service Changes"~~ (vague)

**Required fields per JSON Patch op**:

- `/fields/System.Title`
- `/fields/System.Description` (HTML, PARCH-6)
- `/fields/System.AreaPath` (e.g. `Software Engineering\Alpha`)
- `/fields/System.IterationPath`

**Recommended**:

- `/fields/Microsoft.VSTS.Common.AcceptanceCriteria` (HTML)
- `/fields/System.Tags` (semicolon-separated)
- `/fields/Microsoft.VSTS.Common.Priority`

### Updating Existing Work Items

**CRITICAL**: Preserve existing content, merge new information. Always include an optimistic-concurrency `test` op on `/rev`:

```json
[
  {"op": "test", "path": "/rev", "value": 7},
  {"op": "replace", "path": "/fields/System.Description", "value": "<h3>1. ...</h3>"}
]
```

**Title/Summary Updates**: When scope or outcome changes significantly, update the title to reflect actual implementation.

**Update strategy by section**:

| Section | Approach |
|---------|----------|
| Section 1 | Append new ACs, update objective if scope changed |
| Section 2 | Add new constraints, keep existing |
| Section 3 | Merge technical details, update schemas |
| Section 4 | Update phases to reflect actual implementation |
| Section 5 | Add new validation steps |
| Section 6 | Append new resources, keep existing |

---

## ADO Description Format (HTML, not Markdown)

`System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria` accept **HTML**. See `references/html-examples.md` for ready-to-paste snippets.

### Allowed Elements (rendered cleanly)

`<h1>`–`<h6>`, `<p>`, `<strong>`, `<em>`, `<u>`, `<s>`, `<br>`, `<ul>`/`<ol>`/`<li>`, `<a href>`, `<code>`, `<pre>`, `<blockquote>`, `<table>`/`<tr>`/`<td>`, `<img>` (for inline attached images).

### Caveats

- Inline `style=` is mostly stripped — rely on semantic tags
- `<input type=checkbox>` is **not interactive** in descriptions — use a `<ul>` or the AcceptanceCriteria field
- Markdown is NOT rendered in description — convert before sending
- Always escape user content: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`

---

## Complete Workflow Example

### Scenario: PR exists, need to create ADO work item

1. **Analyze the PR/branch**:

   ```bash
   git log main..HEAD --oneline
   # a1b2c3d Add Google OAuth2 provider
   # e4f5g6h Update login UI with Google button
   # i7j8k9l Add user profile sync
   ```

2. **Extract intent**:
   - Action: Add OAuth2 authentication
   - Target: Google provider
   - Motivation: Enable Google login
   - Impact: Users authenticate with Google

3. **Structure PARCH-6**:
   - Section 1: Objective = "Users can authenticate via Google OAuth2"
   - Section 2: Constraints = "DO NOT: Store Google tokens in plain text"
   - Section 3: Interface = OAuth2 endpoints, callback URLs
   - Section 4: Flow = Initiate → Google auth → Callback → Profile sync
   - Section 5: Validation = Test login flow, verify profile data
   - Section 6: Resources = PR link, OAuth docs

4. **Render to HTML**, build JSON Patch, POST via @ado

5. **Link the PR** as a `Hyperlink` relation on the work item, and update the PR description with the work item URL

---

## Common Patterns

### Pattern: Bug Fix

From `fix(api): resolve race condition in payment processing`:

- **Type**: `Bug` (use `Microsoft.VSTS.TCM.ReproSteps` for the repro)
- **Section 1**: Objective = "Payment processing handles concurrent requests without race conditions"
- **Section 4**: Phase 1 identify → Phase 2 atomic ops → Phase 3 concurrency tests

### Pattern: Feature Addition

- **Section 3**: Document new endpoint, request/response schemas
- **Section 4**: Backend → Frontend → E2E

### Pattern: Refactoring

- **Section 1**: Objective = "[Service] codebase follows clean architecture principles"
- **Section 2**: "DO NOT: Change external API contracts"
- **Section 4**: Refactoring strategy + migration path

---

## Error Handling

| Error | Resolution |
|-------|------------|
| HTTP 302 → `_signin` | PAT missing/expired in shell. Re-export `AZURE_DEVOPS_PAT` and restart opencode |
| HTTP 401 | PAT lacks `vso.work` / `vso.work_write` scope |
| HTTP 404 | Confirm work item ID and project in ADO UI |
| HTTP 400 invalid patch | Wrong content-type — use `application/json-patch+json` |
| HTTP 412 | `rev` mismatch (concurrent edit) — refetch and retry |
| HTML render issues | Simplify; check tag balance; remove inline styles |

---

## Resources

### Reference Files

- `references/ado-template.md` — Complete PARCH-6 template (HTML) with examples
- `references/ado-api-guide.md` — ADO REST API details and curl examples
- `references/html-examples.md` — Common HTML snippets for descriptions

### Scripts

- `scripts/git_change_analyzer.py` — Analyze git changes and extract intent
- `scripts/html_builder.py` — Build PARCH-6 HTML from structured content

---

## Integration with @ado

This skill works alongside the `@ado` agent for API operations:

1. Use this skill to **structure content** and **analyze changes**
2. Use `@ado` to **fetch**, **create**, and **update** work items
3. This skill provides the **template** and **workflow**
4. `@ado` provides the **API execution**

When both are available, prefer this skill for ticket writing tasks — it owns the PARCH-6 structure and code-first workflow.
