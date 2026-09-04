---
name: signing-in-to-aws
description: >-
  Gets AWS credentials for CLI/SDK access through an existing IAM Identity Center
  profile (`aws sso login`) or `aws login` when no SSO profile applies. Activates for
  local AWS authentication, missing or expired credentials, caller verification,
  profile selection, or setup requests. Triggers: "set up AWS", "configure AWS",
  "aws login", "aws sso login", "get credentials", "authenticate", "session expired",
  "token expired", "no credentials", or AccessDeniedException with no valid caller.
version: 2
---

# Sign In: Get CLI/SDK Credentials

Help developers use the credential flow already configured on the machine. Prefer an existing IAM Identity Center profile with `aws sso login --profile <profile>`. Use `aws login` only when no established SSO profile fits the task. Both flows provide short-term credentials; neither belongs in CI.

**Important:**
- Run `aws --version`, profile discovery, login, and identity checks in the user's local shell, not through MCP or API tools.
- Ask for confirmation before any interactive login command. State the exact profile or session that the command will use, then wait.
- Do not guess a profile when more than one account can match the request.

## Prerequisites

Check the installed version first:

```bash
aws --version
```

Existing IAM Identity Center profiles use `aws sso login`. The generic `aws login` command requires **AWS CLI version 2.32.0 or later**.

If the CLI is missing, point the user to the [AWS CLI installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and stop. If `aws login` is the selected flow and the CLI is below 2.32.0, ask whether to update it. Do not block an established `aws sso login` workflow only because `aws login` is unavailable.

## Flow

### Lead with the selected flow

Name the remediation before you run checks:

- Existing SSO profile: `aws sso login --profile <profile>`.
- Named SSO session: `aws sso login --sso-session <session>`.
- No established SSO profile: `aws login` or `aws login --profile <name>`, if supported.

### Precondition checks

Run these in the local shell before asking for login confirmation:

1. `aws --version`: confirm the CLI exists.
2. `aws configure list-profiles`: discover configured profiles. Do not construct a profile name from an account ID.
3. For a likely profile, inspect `aws configure get sso_session --profile <profile>` and `aws configure get sso_start_url --profile <profile>`. Either setting proves the profile uses IAM Identity Center.
4. Run `aws sts get-caller-identity --profile <profile> --query '[Account,Arn]' --output text` when a profile is selected. Use the unqualified command only when the user explicitly wants the default profile.
   - **Succeeds:** Show the caller and ask whether it is the intended target.
   - **Fails with an expired SSO token:** Use `aws sso login --profile <profile>`.
   - **Fails with no configured SSO profile:** Consider `aws login`.
   - **Fails with `AccessDeniedException` after identity succeeds:** This is authorization, not authentication. Do not repeat login.
5. If the active credential source is a long-term `AKIA` access key, explain the risk and recommend the approved short-term SSO or login flow.

### Confirm and run the login

State the exact command and ask for confirmation. After approval, run one of:

```bash
# Choose exactly one approved flow.
aws sso login --profile "$PROFILE"
# aws sso login --sso-session "$SSO_SESSION"
# aws login --profile "$PROFILE"
```

Use plain `aws login` only when the user wants the default profile and no established SSO profile should be preserved.

### Verify

After login, rerun `aws sts get-caller-identity` with the same profile and show the caller. For later commands, keep the profile explicit with `--profile` or command-scoped `AWS_PROFILE=<profile>`.

## Handling Errors

### "command not found" or version too old

If the CLI is missing, direct the user to the [AWS CLI installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). If `aws login` is the selected flow and the CLI is below 2.32.0, update it. Do not reject a working SSO-capable CLI only because it is below the separate `aws login` minimum.

### Browser doesn't open

For generic `aws login`, suggest `aws login --remote`, which provides a URL and code for cross-device authentication. For IAM Identity Center, keep the configured SSO flow and use its device authorization path instead of changing credential methods.

### Permission error after generic `aws login`

The IAM identity needs the `SignInLocalDevelopmentAccess` managed policy attached to the user, role, or group. Root users do not need it. Tell the user to ask their administrator to add it, or attach it themselves if they have IAM permissions. This policy is not the fix for an IAM Identity Center profile; SSO permissions come from its assigned permission set.

### GovCloud or China regions

`aws login` is not available in AWS GovCloud (US) or AWS China regions. Do not mention this exception proactively — only relevant if the user explicitly states they are in one of these partitions.

## Existing `aws sso login` Workflows

Prefer an existing IAM Identity Center profile over starting a new generic `aws login` flow, even when the user only says that the session expired. This is a workflow choice, not AWS CLI precedence: command-line options and credential or configuration environment variables can override profile settings. Clear unintended overrides before testing the profile.

- Use `aws sso login --profile <profile>` for profiles in `~/.aws/config` that contain `sso_session` or `sso_start_url`.
- If SSO login fails, troubleshoot the selected profile: expired session, revoked authorization, cached token, or Identity Center configuration change.
- Do not delete SSO cache files without explaining the effect and getting confirmation.

## Fallback to `aws configure`

Do NOT mention `aws configure` in your initial response or include it as a table row alongside `aws login`. Only offer it as an alternative if:

1. The user explicitly declines `aws login` or asks for alternatives
2. The user states they are in GovCloud or China regions (where `aws login` is unavailable)

When offering it, explain that long-term access keys are less secure: they persist on disk as plaintext, never expire automatically, and grant indefinite access if leaked.

## When NOT to Use This Skill

- User is setting up CI/CD credentials: use an IAM role or OIDC federation, not an interactive login

## Key Points

- Preserve configured SSO profiles. Do not replace working organization access with a new generic login.
- Verify the caller after every login and before every state-changing command.
- Do not front-load troubleshooting. Keep the initial response simple and address errors only if they occur.
- `aws login` works with root users, IAM users, and IAM federation when no established SSO flow applies.

## Additional Resources

- [Sign in through the AWS CLI](https://docs.aws.amazon.com/signin/latest/userguide/command-line-sign-in.html)
- [Installing or updating the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [SignInLocalDevelopmentAccess managed policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SignInLocalDevelopmentAccess.html)
- [IAM security best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
