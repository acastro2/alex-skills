# Jira adapter

Read this before any Jira write. The core workflow is in `../SKILL.md`. This file holds what only Jira needs. It uses the Atlassian MCP connector and nothing else.

Why this file is careful: the write path was proven once, on one throwaway issue (2026-11-13). Treat every UNVERIFIED line as a question to check on the first real call.

## Tools and hosts

Tools are `mcp__claude_ai_Atlassian__<name>` in Claude Code. OpenCode has no Atlassian connector. In OpenCode, hand the Jira steps to the `ask-claude` agent and use its answer.

## Run status

- Read calls RUN on 2026-11-12: `getAccessibleAtlassianResources`, `getVisibleJiraProjects`, `getJiraProjectIssueTypesMetadata`, `searchJiraIssuesUsingJql`, `getJiraIssue` (with `expand: "changelog"`).
- Write calls RUN on 2026-11-13, on one throwaway Task: `createJiraIssue`, `editJiraIssue`, `addCommentToJiraIssue`, `getTransitionsForJiraIssue`, `transitionJiraIssue` (to Done). Also `getJiraIssueTypeMetaWithFields` and `getJiraIssueRemoteIssueLinks` (returns `[]` when there are no links).
- Still NOT RUN: `createIssueLink`, setting `parent`, changing `issuetype`.

## Resolve first, never memorize

Never write a cloudId, site name, or project key into any file. They go stale, and this repo is public. Examples use `PROJ-123` and `<site>.atlassian.net`.

- **Site.** `getAccessibleAtlassianResources` returns the site twice, one entry per product. Use the entry whose `scopes` include `read:jira-work` and `write:jira-work`. Its `id` is the `cloudId`. Resolve it every run.
- **Project.** Derive it from a known issue key, or call `getVisibleJiraProjects` with `searchString`. NEVER call it unfiltered: 50 projects returned 230K characters. Alex confirms the project before a create.
- **Types.** `getJiraProjectIssueTypesMetadata` with `projectIdOrKey` lists the project's types. Names differ per project: `Sub-task`, `Sub-Task` and `Subtask` all exist on the site. A `Spike` type is rare. If the type you need is missing, ask. Do not substitute.
- **Fields per type.** `getJiraIssueTypeMetaWithFields` with `issueTypeId`. Pass `requiredFieldsOnly: false` to see all fields.

## Render

The six sections go in the description as Markdown `##` headings. Use `contentFormat: "markdown"` on `createJiraIssue` and `editJiraIssue`. `"adf"` also works. The description limit is 32000 characters (tool schema).

Read back with `responseContentFormat: "markdown"`.

Measured 2026-11-13: headings, bold, inline code and a pipe table survive a write and a Markdown read-back. Lists come back with `*` for `-`, and a nested list gains blank lines; the content is the same. Sending the read-back text again in an edit did not drift. Still read the item back after each write.

### Acceptance criteria and repro steps

Jira has no native field for either. Look in the type's field metadata for a custom field with that name. If one exists, mirror the Section 1 ACs (or the repro steps) into it by the `customfield_` id you read live. Never hardcode a `customfield_` id. If none exists, the ACs live only in Section 1.

### Other fields

Other fields go in `additional_fields`:

```json
{"labels": ["a", "b"], "priority": {"name": "..."}, "components": [{"name": "..."}]}
```

Read the allowed priority and component values from the field metadata first. The metadata can leave out a field the site still sets: on 2026-11-13 a Task's create metadata had no priority field, and the new issue got the site's default priority. Check the created issue, not only the metadata.

## Create

1. Resolve the site, project, and type (above). Alex confirms the project.
2. Duplicate check: `searchJiraIssuesUsingJql` in the project with `summary ~ "\"<title words>\""` (the inner quotes make it a phrase). Run 2026-11-13: 0 hits before the create, 1 hit after. Run the same check again before you retry a failed create, because the create may have landed.
3. `createJiraIssue` with the title, the six sections, and `additional_fields`.
4. Read the item back and check the render. Return the item URL (`https://<site>.atlassian.net/browse/PROJ-123`).

Parent: `createJiraIssue` has a `parent` parameter. The schema says "for subtasks". Setting an epic as the parent of a story is UNVERIFIED. Read the field metadata first.

## Update

1. `getJiraIssue` with fields `description`, `updated`, and any AC custom field. Merge with the update table in `../SKILL.md`. Do not overwrite.
2. `editJiraIssue` has no revision guard. Re-read `updated` right before the edit. If it changed since your read, merge again.

Type change: UNVERIFIED through the MCP. If `editJiraIssue` rejects `issuetype`, ask Alex to use Move in the Jira UI.

## State

Call `getTransitionsForJiraIssue`, then `transitionJiraIssue` with the transition id. Never set status as a field. Transition ids differ per project workflow, so never reuse one. `hasScreen: false` means the transition needs no fields.

## Links and comments

- **Issue links.** `createIssueLink` with a type name from `getIssueLinkTypes`. Direction, from the tool schema: for "A is blocked by B", `inwardIssue` = B and `outwardIssue` = A.
- **PR links.** No MCP tool writes a remote link. Put the issue key (`PROJ-123`) in the branch name, a commit message, or the PR title. The site's GitHub integration links it, if the site has one. Then check with `getJiraIssueRemoteIssueLinks` or `getTeamworkGraphContext`. If no link shows, keep the PR URL in Section 6 and tell Alex.
- **Comments.** `addCommentToJiraIssue`.

## Connector note

The claude.ai Atlassian connector on this machine uses the deprecated `/v1/mcp` endpoint. It is removed on 2027-03-01. Fix: remove and re-add the connector. A custom connector uses `https://mcp.atlassian.com/v2/mcp`.

## Errors

No Jira errors yet (the 2026-11-13 write test had none). Record the first real ones here, with the call, the message, and the fix.
