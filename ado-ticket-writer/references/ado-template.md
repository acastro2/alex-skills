# PARCH-6 Template for Azure DevOps Stories

Complete template for writing spec-driven ADO work items. All Story / User Story / Product Backlog Item descriptions MUST contain these 6 sections, rendered as **HTML** in the `System.Description` field. Mirror Section 1's ACs into `Microsoft.VSTS.Common.AcceptanceCriteria` for native ADO AC reporting.

See `html-examples.md` for the HTML rendering of every section below.

---

## Section 1: Constitutional Intent & Success Criteria

**The "North Star" and testable reality of completed work.**

### Objective

[One-sentence end-state summary describing what success looks like]

**Good**: "Users can authenticate via Google OAuth2 and sync their profile data"
**Bad**: "Implement OAuth2 authentication" (describes activity, not outcome)

### Acceptance Criteria (Given/When/Then format)

**AC-001**: [Brief description]

- **Given**: [Pre-conditions/state]
- **When**: [Action taken]
- **Then**: [Expected outcome]

**AC-002**: [Next criteria]

- **Given**: [Pre-conditions]
- **When**: [Action]
- **Then**: [Outcome]

### Success Metrics

- [Measurable metric 1]
- [Measurable metric 2]

---

## Section 2: Constraints & Guardrails

**Operational boundaries. Read before implementation.**

### Critical Non-Actions

- **DO NOT**: [Constraint that must not be violated]
- **DO NOT**: [Another critical constraint]
- **DO NOT**: [Third constraint if applicable]

### Security & Compliance

- [Security requirement]
- [Compliance requirement]
- [Data handling requirement]

### Timing/SLA Constraints

- [Time-based constraint]
- [Performance requirement]
- [Availability requirement]

---

## Section 3: Technical Interface (The Contract)

**Immutable technical facts for implementation.**

### Configuration & Connectivity

- **Endpoint**: [URL/endpoint]
- **Port**: [Port number]
- **Environment Variables**: [Required env vars]
- **Dependencies**: [External services needed]

### Data Schema & Models

**Input Schema**:

```json
{
  "field_name": {
    "type": "string|number|boolean|object|array",
    "required": true|false,
    "description": "Field description"
  }
}
```

**Output Schema**:

```json
{
  "response_field": {
    "type": "string|number|boolean|object|array",
    "description": "Response field description"
  }
}
```

### API Contracts

**Endpoint**: `METHOD /path/to/endpoint`

**Request**:

```json
{
  "example": "request body"
}
```

**Response** (200 OK):

```json
{
  "example": "response body"
}
```

**Error Responses**:

- 400 Bad Request: [When this occurs]
- 401 Unauthorized: [When this occurs]
- 500 Internal Error: [When this occurs]

---

## Section 4: Logic & Implementation Flow

**The execution algorithm for humans.**

### Phase 1: Preparation

1. [Setup step 1]
2. [Setup step 2]
3. [Setup step 3]

### Phase 2: Execution

1. [Core logic step 1]
2. [Core logic step 2]
3. [Core logic step 3]

### Phase 3: Finalization

1. [Cleanup step 1]
2. [Verification step 2]
3. [Completion step 3]

### State Transitions

```
[Initial State] → [Action] → [Intermediate State] → [Action] → [Final State]
```

### Error Handling

- **Scenario**: [Error condition]
  - **Detection**: [How to detect]
  - **Response**: [How to handle]
  - **Recovery**: [How to recover]

---

## Section 5: Validation Steps

**How to verify the contract was fulfilled.**

### Automated Tests

**Unit Tests**:

```bash
# Command to run unit tests
npm test -- --grep "OAuth2"
```

**Integration Tests**:

```bash
# Command to run integration tests
npm run test:integration
```

### Manual Verification

**Test Case 1**: [Description]

- **Action**: [Step-by-step manual test]
- **Expected Result**: [What should happen]
- **Success Criteria**: [How to confirm success]

**Test Case 2**: [Description]

- **Action**: [Steps]
- **Expected Result**: [Outcome]
- **Success Criteria**: [Confirmation]

### Monitoring Checks

- [Metric to monitor]
- [Log entry to verify]
- [Alert to confirm]

---

## Section 6: Resources & Team Context

**Links and references for the team.**

### Documentation

- **Runbook**: [Link to operational runbook]
- **Design Doc**: [Link to design documentation]
- **API Documentation**: [Link to API docs]

### Code & Infrastructure

- **Infrastructure Source**: [Git repository link]
- **Related PRs**:
  - [PR #1](link)
  - [PR #2](link)
- **Related Tickets**:
  - [TICKET-123](link)
  - [TICKET-124](link)

### Team & Support

- **Support Channel**: [#slack-channel](link)
- **Team**: [Team name]
- **Stakeholders**: [List of stakeholders]

### External References

- [External documentation link]
- [Third-party service docs]
- [Relevant blog posts/articles]

---

## Examples by Ticket Type

### Feature Addition Example

**Section 1**: "Users can export their data as CSV from the dashboard"

**Section 3**:

- Endpoint: `GET /api/v1/users/{id}/export`
- Response: CSV file download

**Section 4**:

- Phase 1: Query user data from database
- Phase 2: Transform to CSV format
- Phase 3: Stream response to client

### Bug Fix Example

**Section 1**: "Payment processing handles timeout errors gracefully"

**Section 2**:

- DO NOT: Change existing payment success flow
- DO NOT: Modify database schema

**Section 4**:

- Phase 1: Detect timeout in payment gateway
- Phase 2: Retry with exponential backoff (max 3 attempts)
- Phase 3: Return user-friendly error if all retries fail

### Refactoring Example

**Section 1**: "Authentication service uses clean architecture pattern"

**Section 2**:

- DO NOT: Change public API contracts
- DO NOT: Modify database schema
- DO NOT: Alter authentication behavior

**Section 4**:

- Phase 1: Extract business logic to use cases
- Phase 2: Move data access to repositories
- Phase 3: Update dependency injection
