---
name: agent-creator
description: Create or update OpenCode subagent definitions stored as Markdown files under @agent/. Use when asked to add a new agent, modify an existing agent's prompt/config, or adjust tools/permissions.
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: agent-management
---

# Agent Creator

Create and maintain agent definition files in `@agent/` (backed by `/Users/aamado/.config/opencode/agent/`). Each agent is a single Markdown file with YAML frontmatter that configures tools/permissions plus a prompt body.

## Output target

- New agent: write `@agent/<agent_name>.md`
- Update agent: edit `@agent/<agent_name>.md` in place

Prefer `snake_case` file names to match existing agents.

## Workflow

1. Identify whether this is **create** or **update**.
   - If the user didn’t provide a name, propose a `snake_case` name and confirm.

2. Gather requirements (ask only what’s needed).
   - What the agent does (1–2 sentences)
   - Typical inputs it will receive
   - Required output format (if any)
   - Tools it actually needs (read/write/edit/bash/grep/glob/mermaid)
   - Guardrails: what it must never do

3. Choose minimal permissions.
   - Default to no `bash`.
   - Default to `edit: "deny"` unless the agent must modify files.
   - If the agent needs `edit`, prefer `permission.edit: "ask"` (human-in-the-loop) unless explicitly requested otherwise.
   - If enabling `bash`, restrict it with an allowlist (never broad `"*": "allow"`).
   - Tool enablement is now part of the `permission` block (e.g., `read: "allow"`).

4. Write/update YAML frontmatter.
   - Always include `description` and `mode: subagent`.
   - Add `temperature` only when you need deterministic behavior.

5. Write/update the body prompt.
   - Start with a direct role statement: “You are …”
   - Define responsibilities, constraints, and output format.
   - Include a short checklist when the task is failure-prone.

6. Validate.
   - File exists in `@agent/`
   - Frontmatter parses as YAML
   - Permissions use string values (e.g., `"allow"`, `"deny"`, `"ask"`)

## Agent file template

Use this as a starting point and remove unused parts. Note that the `tools` field is deprecated and merged into `permission`.

```yaml
---
description: <one-sentence description; include when to use>
mode: subagent
# temperature: 0.1  # optional
permission:
  read: "allow"
  glob: "allow"
  grep: "allow"
  write: "deny"
  edit: "deny"
  bash: "deny"
  # mermaid*: "allow" # optional
---
```

### Bash allowlist example

```yaml
permission:
  bash:
    "git status *": "allow"
    "git diff *": "allow"
    "*": "deny"
```

## Update rules

- Preserve what the user didn’t ask to change.
- If the agent’s **role** changes, update the `description` and the first paragraph of the body to match.
- If adding capabilities, tighten permissions to the smallest allowlist that still works.
