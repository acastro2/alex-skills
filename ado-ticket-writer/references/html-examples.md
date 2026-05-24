# ADO Work Item HTML Examples

Common HTML patterns for `System.Description` and `Microsoft.VSTS.Common.AcceptanceCriteria`.

ADO renders a constrained subset of HTML — semantic tags work, most inline styles are stripped. Always escape user-provided content (`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`).

---

## Headings

```html
<h1>Top-level (rarely used in descriptions)</h1>
<h2>Section</h2>
<h3>Subsection (preferred for PARCH-6 sections)</h3>
<h4>Sub-subsection</h4>
```

## Text Formatting

```html
<p>Plain paragraph.</p>
<p><strong>Bold</strong>, <em>italic</em>, <u>underline</u>, <s>strikethrough</s>.</p>
<p>Inline <code>monospace</code> for short snippets.</p>
<p>Line break:<br>next line.</p>
```

## Lists

```html
<ul>
  <li>Bullet item</li>
  <li>Another item</li>
</ul>

<ol>
  <li>First step</li>
  <li>Second step</li>
</ol>

<ul>
  <li>Nested:
    <ul>
      <li>Sub-item</li>
    </ul>
  </li>
</ul>
```

## Code Blocks

```html
<pre><code>{
  "field": "type",
  "required": true
}</code></pre>
```

ADO renders `<pre>` in monospace with a light background. There is no syntax highlighting in description fields.

## Links

```html
<p>See the <a href="https://github.com/CuroFinTech/echo/pull/42">related PR</a>.</p>
```

For PRs and other work items, prefer attaching them as **link relations** on the work item (`Hyperlink` or `Related`) instead of inline `<a>` — they show up in the dedicated Links tab.

## Tables

```html
<table>
  <thead>
    <tr><th>Field</th><th>Type</th><th>Notes</th></tr>
  </thead>
  <tbody>
    <tr><td>email</td><td>string</td><td>required</td></tr>
    <tr><td>tier</td><td>enum</td><td>free|pro|ent</td></tr>
  </tbody>
</table>
```

Tables render but the rich-text editor sometimes reformats them. Keep them simple — no merged cells.

## Blockquotes

```html
<blockquote>Quoted context or callout.</blockquote>
```

## Images (inline attachments)

To embed an image, first upload it via the attachments API, then reference the returned URL:

```html
<img src="https://dev.azure.com/CuroFinTech/Tiger/_apis/wit/attachments/{guid}" alt="diagram" />
```

---

## Acceptance Criteria

ADO does **not** render `<input type="checkbox">` interactively in descriptions. Two good patterns:

### Pattern A — Bullet list of Given/When/Then (works in any field)

```html
<ul>
  <li><strong>AC-001:</strong> Given user is logged out, When they click "Sign in with Google", Then OAuth flow initiates</li>
  <li><strong>AC-002:</strong> Given OAuth completes successfully, When user returns, Then profile is synced from Google</li>
</ul>
```

### Pattern B — Use the dedicated AcceptanceCriteria field

Stories/PBIs have a built-in `Microsoft.VSTS.Common.AcceptanceCriteria` field that ADO surfaces in its own pane. Put the same `<ul>` there:

```bash
curl ... -d '[
  {"op":"add","path":"/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
   "value":"<ul><li>Given X, When Y, Then Z</li></ul>"}
]'
```

Use **both**: Section 1 of the description shows ACs inline for context, and the dedicated field powers ADO's AC reporting.

---

## Complete PARCH-6 Description Skeleton

```html
<h3>1. Constitutional Intent &amp; Success Criteria</h3>
<p><em>The "North Star" and testable reality of completed work.</em></p>
<p><strong>Objective:</strong> Users can authenticate via Google OAuth2 and have their profile synced.</p>
<p><strong>Acceptance Criteria (Given/When/Then):</strong></p>
<ul>
  <li><strong>AC-001:</strong> Given user is logged out, When they click "Sign in with Google", Then OAuth flow initiates</li>
  <li><strong>AC-002:</strong> Given OAuth completes, When user returns to app, Then profile is synced from Google</li>
</ul>

<h3>2. Constraints &amp; Guardrails</h3>
<p><em>Operational boundaries. Read before implementation.</em></p>
<p><strong>Critical Non-Actions:</strong></p>
<ul>
  <li>DO NOT: Store Google access tokens in plain text</li>
  <li>DO NOT: Modify existing email/password authentication flow</li>
</ul>
<p><strong>Security &amp; Compliance:</strong> All tokens encrypted at rest (AES-256). PII handling per company policy.</p>
<p><strong>Timing/SLA:</strong> OAuth callback must complete within 5s p95.</p>

<h3>3. Technical Interface (The Contract)</h3>
<p><em>Immutable technical facts for implementation.</em></p>
<p><strong>Configuration &amp; Connectivity:</strong></p>
<ul>
  <li>Callback: <code>POST /auth/google/callback</code></li>
  <li>Env: <code>GOOGLE_CLIENT_ID</code>, <code>GOOGLE_CLIENT_SECRET</code></li>
  <li>Scopes: <code>openid profile email</code></li>
</ul>
<p><strong>Data Schema:</strong></p>
<pre><code>{
  "google_id": "string",
  "email": "string",
  "profile": { "name": "string", "picture": "url" }
}</code></pre>

<h3>4. Logic &amp; Implementation Flow</h3>
<p><em>The execution algorithm for humans.</em></p>
<p><strong>Phase 1 (Preparation):</strong> Register OAuth client in Google Cloud, store credentials in vault.</p>
<p><strong>Phase 2 (Execution):</strong> Implement <code>/auth/google/start</code> redirect, callback handler, token exchange, profile sync.</p>
<p><strong>Phase 3 (Finalization):</strong> Add login button to UI, write integration tests, deploy behind feature flag.</p>

<h3>5. Validation Steps</h3>
<p><em>How to verify the contract was fulfilled.</em></p>
<p><strong>Action:</strong> <code>curl -X POST /auth/google/start</code> and follow redirect.</p>
<p><strong>Expected Result:</strong> Returns valid session cookie; <code>SELECT google_id FROM users</code> shows new row.</p>
<p><strong>Action:</strong> Run <code>npm run test:integration -- auth/google</code></p>
<p><strong>Expected Result:</strong> All tests pass.</p>

<h3>6. Resources &amp; Team Context</h3>
<p><strong>Runbook:</strong> <a href="https://wiki/runbooks/oauth">OAuth incident runbook</a></p>
<p><strong>Infrastructure Source:</strong> <a href="https://github.com/CuroFinTech/echo">echo repo</a></p>
<p><strong>Support Channel:</strong> <a href="https://slack/echo-team">#echo-team</a></p>
<p><strong>Related PRs:</strong> attached as Hyperlink relations on this work item.</p>
```

---

## Building HTML from Python

See `scripts/html_builder.py` for a small builder that emits the structure above from structured Python data.

```python
from html_builder import build_parch6, escape

description_html = build_parch6(
    objective="Users can authenticate via Google OAuth2",
    acceptance_criteria=[
        "Given user is logged out, When they click Google, Then OAuth flow initiates",
    ],
    constraints=["DO NOT: Store tokens in plain text"],
    technical={"Configuration": ["Callback: POST /auth/google/callback"]},
    flow={"Phase 1": "Register client", "Phase 2": "Implement handlers", "Phase 3": "UI + tests"},
    validation=[("Run integration tests", "All pass")],
    resources={"Runbook": "https://wiki/runbooks/oauth"},
)
```
