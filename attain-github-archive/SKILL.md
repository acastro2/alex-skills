---
name: attain-github-archive
description: Archive GitHub repositories at Attain by transferring them from an active engineering org (Engineering-Attain-Finance, Data-Engineering-Attain-Finance, Risk-Analytics-Attain-Finance, Testing-Attain-Finance) into the dedicated Archive-Attain-Finance org, disabling GitHub Advanced Security and secret scanning to stop billing and noise, archiving the repo, and granting the SRE team read access. Use whenever the user asks to archive, retire, sunset, mothball, decommission, or move a repo out of an active org — single repo or in bulk — or asks how to clean up old/dead repos at Attain. Also use when the user mentions transferring a repo to Archive-Attain-Finance, killing GHAS billing on dead code, disabling secret scanning on the Archive org, auditing already-archived repos for stale scanning, setting org-wide security defaults for new repositories in Archive-Attain-Finance, or any combination of "archive" and a repo or org name at Attain.
---

# Attain GitHub Archive

Workflow for retiring GitHub repos at Attain. Source org is parameterized (any active org). Target is always `Archive-Attain-Finance`. End state per repo: transferred, archived, GHAS fully disabled, SRE team granted `pull`.

## When to use

Triggered by user requests like "archive these repos", "move X to the archive org", "retire this service", "stop paying GHAS on dead repos", "bulk archive engineering repos we don't use". Works for a single repo or a list.

## Preflight

Before any transfer:

1. `gh auth status` — confirm the active account has `admin:org` and `repo` scopes. If missing: `gh auth refresh -s admin:org`.
2. Confirm with the user:
   - Source org (e.g. `Engineering-Attain-Finance`)
   - Repo name(s) — exact spelling
   - Whether to strip direct collaborators automatically or fail loud per repo
3. Verify source repo and target org are reachable:
   ```bash
   gh api "repos/<src>/<repo>" --jq '{full_name, archived, private}'
   gh api "orgs/Archive-Attain-Finance" --jq '.login'
   ```

Never run destructive steps without explicit user confirmation. Transfers are reversible but tedious to undo in bulk.

## Per-repo flow

Order matters. Do everything **before** archiving, because archived repos reject most API mutations (422).

1. **Strip direct collaborators on the source repo.** The Archive org disallows outside collaborators, so transfer fails with 422 if any direct collaborator isn't a member of the Archive org. Record them first, then delete.
2. **Disable security features on the source repo** (GHAS, secret scanning, Dependabot security updates, vulnerability alerts, automated security fixes). GitHub auto-disables most of these on archive, but `automated-security-fixes` persists and continues counting against billing if left on. Doing this pre-transfer avoids the unarchive/re-archive dance.
3. **Transfer** to `Archive-Attain-Finance`. The API returns 202 and the move is async — poll the target until queryable.
4. **Archive** the repo at its new location.
5. **Grant the `sre` team `pull`** on the archived repo.

Use the bundled script `scripts/archive_repo.sh` for a single repo. It does all five steps with logging and confirmation prompts.

```bash
./scripts/archive_repo.sh <source-org> <repo-name>
```

## Bulk flow

Use `scripts/archive_repos_bulk.sh` with a newline-delimited list of repos:

```bash
./scripts/archive_repos_bulk.sh <source-org> repos.txt
```

The script:
- Runs preflight on every repo first and prints a plan
- Asks for confirmation once
- Logs every action (collaborators stripped, security toggles changed, transfer/archive status) to `archive-log-<timestamp>.jsonl`
- Skips repos already archived in the target org (idempotent)
- Continues on per-repo failure and summarizes failures at the end

To list candidate repos from a source org:

```bash
gh api --paginate "orgs/<src>/repos" --jq '.[] | select(.archived | not) | .name' > repos.txt
```

Always have the user review `repos.txt` before running the bulk script.

## Archive org one-time hardening

The Archive org should have all security defaults for new repositories disabled, so anything transferred in starts cold. Check current state:

```bash
gh api "orgs/Archive-Attain-Finance" --jq '{
  advanced_security_enabled_for_new_repositories,
  dependabot_alerts_enabled_for_new_repositories,
  dependabot_security_updates_enabled_for_new_repositories,
  secret_scanning_enabled_for_new_repositories,
  secret_scanning_push_protection_enabled_for_new_repositories,
  secret_scanning_validity_checks_enabled
}'
```

Any field returning `true` should be flipped to `false`:

```bash
gh api -X PATCH "orgs/Archive-Attain-Finance" --input - <<'EOF'
{
  "advanced_security_enabled_for_new_repositories": false,
  "dependabot_alerts_enabled_for_new_repositories": false,
  "dependabot_security_updates_enabled_for_new_repositories": false,
  "secret_scanning_enabled_for_new_repositories": false,
  "secret_scanning_push_protection_enabled_for_new_repositories": false,
  "secret_scanning_validity_checks_enabled": false
}
EOF
```

This only affects *future* repos transferred or created in the org. Existing repos keep whatever they had when transferred — fix those separately (see next section).

## Audit and remediate already-archived repos

Older archives may still have GHAS or secret scanning enabled because they predated this workflow or were transferred before the org defaults were tightened. Find them:

```bash
gh api "orgs/Archive-Attain-Finance/repos?per_page=100&type=all" --paginate --jq '.[] | select(
  .security_and_analysis.advanced_security.status == "enabled" or
  .security_and_analysis.secret_scanning.status == "enabled" or
  .security_and_analysis.secret_scanning_push_protection.status == "enabled"
) | .name'
```

For each repo returned, disable scanning via stdin JSON (square brackets in `-F` flags get glob-expanded by zsh — use `--input -`):

```bash
gh api -X PATCH "repos/Archive-Attain-Finance/<repo>" --input - <<'EOF'
{
  "security_and_analysis": {
    "advanced_security": {"status": "disabled"},
    "secret_scanning": {"status": "disabled"},
    "secret_scanning_push_protection": {"status": "disabled"}
  }
}
EOF
```

This works on archived repos — the `security_and_analysis` PATCH is one of the few mutations GitHub still accepts post-archive (counter to gotcha #3, which applies to most other fields).

## SRE team setup (one-time per archive org)

If the `sre` team doesn't exist in `Archive-Attain-Finance` yet, mirror it from a source org:

```bash
# read source team
gh api "orgs/<src>/teams/sre" --jq '{description, privacy}'
gh api --paginate "orgs/<src>/teams/sre/members" --jq '.[].login'

# create in archive
gh api -X POST "orgs/Archive-Attain-Finance/teams" \
  -f name="SRE" -f description="<copy from source>" -f privacy="closed"

# add each member as maintainer
gh api -X PUT "orgs/Archive-Attain-Finance/teams/sre/memberships/<user>" -f role="maintainer"
```

Membership returns `state: active` immediately if the user is already an enterprise member (typical at Attain via SSO/SCIM); otherwise `pending` until they accept the invite. Either way the workflow proceeds — team grants apply on acceptance.

## Verification

After each archive, confirm:

```bash
gh api "repos/Archive-Attain-Finance/<repo>" \
  --jq '{archived, security_and_analysis, full_name}'
gh api "repos/Archive-Attain-Finance/<repo>/teams" \
  --jq '.[] | {slug, permission}'
```

Expected: `archived: true`, all `security_and_analysis` toggles `disabled`, SRE team with `pull`.

## Gotchas and rationale

Several non-obvious behaviors caused real failures the first time we ran this. They're documented in `references/gotchas.md`. Read that file when:
- A transfer returns 422 with an unexpected error
- The team membership endpoint returns 404 or scope errors
- Security feature endpoints behave inconsistently (200 with body vs 204 vs 404)
- The user asks why the script does step X before step Y

## What this skill does *not* do

- It does not delete repos. Archival is reversible; deletion isn't. If the user asks to delete, push back and confirm.
- It does not handle renames during transfer. The repo keeps its original name. If the user wants a rename (e.g. `archived-<year>-` prefix), they need to ask explicitly — it's a separate API call after transfer.
- It does not strip webhooks, deploy keys, or Actions secrets. Archived repos can't run workflows or fire webhooks anyway, so this is cosmetic. If the user wants a deep clean, add steps before transfer.
- It does not commit anything or push to git. Per Attain's AGENTS.md, commits are manual.
