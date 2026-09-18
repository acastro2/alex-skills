---
name: agent-creator
description: Create or update OpenCode subagent definitions in ~/.config/opencode/agents/. Use when asked to add an agent, change its role or prompt, or adjust its permissions.
license: MIT
compatibility: opencode
disable-model-invocation: true
metadata:
  audience: maintainers
  workflow: agent-management
---

# Agent Creator

Maintain Markdown agent definitions in `~/.config/opencode/agents/`. YAML frontmatter selects the model, mode, and permissions. The body defines the role.

## Output target

- New agent: write `~/.config/opencode/agents/<agent_name>.md`.
- Update agent: edit its existing file in place.

Prefer `snake_case` file names to match existing agents.

## Workflow

1. Load the OpenCode skill and consult the V2 agents and permissions docs. Read the existing definition, project instructions, and global permissions in `~/.config/opencode/opencode.jsonc`.
2. Recover the role, inputs, and expected result from the request. Ask only for missing decisions. Classify by the work: changing remote tickets or SharePoint pages makes an agent a writer, even if it rarely edits local files.
3. Apply the shared permission policy below.
4. Keep the description and first paragraph consistent with the role. Give the agent responsibility for routine work and scoped verification. Return missing decisions and actual blockers to the parent. Keep user-required review or publication steps explicit.
5. Validate the YAML and inspect the running server's resolved rules with `opencode api get /api/agent/<agent_id>`. Verify shell inheritance, edit behavior, delegation, and the global deny/ask rules. A rule count alone proves none of these.

## Shared permission policy

- All agents inherit global shell, read, and directory permissions. Keep shell rules in the global configuration; omit agent-level shell allowlists, wildcard defaults, and copied git/Vault rules. Agent rules run last, so even a local `shell: ask` can weaken a global deny.
- Writers add only a `subagent` deny. Examples: ADO, SharePoint, blog writing, GitHub issue creation, and implementation workers.
- Read-only agents add an `edit` deny and a `subagent` deny. Their body limits shell and remote operations to inspection. `edit: deny` controls the edit tools; it does not make shell commands read-only.
- Workers return blockers to their parent rather than launching more workers.
- Reuse the existing format for small edits. New definitions use native V2 `permissions` rules. Keep each definition in one format; supported legacy `permission` blocks need no migration just for style.
- Check `~/.config/opencode/cli.json` before promising an approval prompt. `session.permissions: autoaccept` accepts requests automatically; `prompt` shows them. Change this user-wide setting only when requested.

## Agent file template

Writer template; preserve any existing model selection when updating:

```yaml
---
description: <one-sentence description; include when to use>
mode: subagent
permissions:
  - action: subagent
    resource: "*"
    effect: deny
---
```

For a read-only agent, add this rule and state the inspection-only role in the body:

```yaml
  - action: edit
    resource: "*"
    effect: deny
```

## Update rules

- Preserve what the user didn’t ask to change.
- If the agent’s **role** changes, update the `description` and the first paragraph of the body to match.
- Verify a routine shell command is allowed, global blocked commands stay blocked, and global approval-required commands stay `ask`. Inspect the resolved policy without executing destructive commands.
