# Gotchas and rationale

Real failures and behaviors observed during the first end-to-end run. Each one explains *why* the workflow is shaped the way it is.

## 1. Transfer fails with 422 if direct collaborators aren't allowed in target org

`Archive-Attain-Finance` is configured to disallow outside collaborators. If the source repo has any direct collaborator who isn't a member of the Archive org, the transfer call returns:

```
422 Validation Failed
"This repository has collaborators not permitted by Archive-Attain-Finance organization.
To transfer the repository you will need to remove these collaborators, or enable
'Allow repository administrators to invite outside collaborators' in the
Archive-Attain-Finance organization's settings."
```

Note: GitHub's API confusingly calls these "collaborators not permitted" even when they're *direct* collaborators on the source. The error fires whenever any direct collaborator isn't a member of the target org.

**Fix:** strip direct collaborators on the source repo before transfer:
```bash
gh api "repos/<src>/<repo>/collaborators?affiliation=direct" --jq '.[].login'
gh api -X DELETE "repos/<src>/<repo>/collaborators/<user>"
```

Log who was stripped — if access ever needs restoration, it's the only record.

Do NOT solve this by enabling outside collaborators on the Archive org. That defeats the lockdown.

## 2. Transfer is async — poll before archiving

`POST /repos/<src>/<repo>/transfer` returns 202 immediately. The response body still shows the old owner. The repo isn't queryable under the new owner until the move completes — usually 2–10 seconds, occasionally longer for big repos.

Calling `PATCH archived=true` on the new location too early returns 404.

**Fix:** poll `GET /repos/<dst>/<repo>` until 200, then archive:
```bash
for i in {1..30}; do
  gh api "repos/<dst>/<repo>" --silent 2>/dev/null && break
  sleep 2
done
```

## 3. Archived repos reject most PATCH/DELETE calls

Once archived, you can't:
- Modify `security_and_analysis`
- Delete collaborators
- Change team permissions on the repo

API returns 403 or 422. The only "free" mutations are unarchive (`PATCH archived=false`) and a handful of metadata fields.

**Fix:** do all destructive/configuration work *before* archiving. If you discover something needs changing after archival, the dance is:
1. Unarchive (`PATCH archived=false`)
2. Make the change
3. Re-archive (`PATCH archived=true`)

The first run of this workflow on `AdvancedMobilePaymentPinPad` required this dance because automated security fixes wasn't disabled pre-archive. Don't repeat.

## 4. GHAS auto-disable on archive is incomplete

When you archive a repo, GitHub auto-disables most of `security_and_analysis`:
- `advanced_security`
- `secret_scanning` (and all sub-toggles)
- `dependabot_security_updates`

But `automated-security-fixes` (a separate endpoint, `DELETE /repos/<owner>/<repo>/automated-security-fixes`) is NOT auto-disabled. It continues to flag the repo as having Dependabot enabled, which can affect billing/seat counts on some plans.

Similarly, `vulnerability-alerts` is a separate endpoint and should be explicitly disabled for cleanliness, though it's usually auto-off.

**Fix:** explicitly disable both before transfer:
```bash
gh api -X DELETE "repos/<src>/<repo>/automated-security-fixes"
gh api -X DELETE "repos/<src>/<repo>/vulnerability-alerts"
```

Both are idempotent — safe to call even if already off.

## 5. Endpoint return-code inconsistencies

Some GHAS endpoints have inconsistent semantics. Don't trust HTTP status alone — check body where present:

| Endpoint | Enabled | Disabled |
|---|---|---|
| `vulnerability-alerts` | 204 (empty) | 404 (empty) |
| `automated-security-fixes` (older) | 204 (empty) | 404 (empty) |
| `automated-security-fixes` (current) | 200 `{"enabled":true,...}` | 200 `{"enabled":false,...}` |
| `code-scanning/default-setup` | 200 with config | 403 if GHAS off, 404 if never configured |

The newer `automated-security-fixes` returning 200 regardless of state is the trap — always parse the body's `enabled` field.

## 6. Team access drops on transfer; direct collaborators survive

Transferring a repo doesn't carry over teams from the source org (they don't exist in the target). So:
- All team-based access vanishes
- Direct collaborators carry over (which is why #1 fires)
- The person doing the transfer is auto-added as admin

At Attain, where access is normally team-managed, this means the bulk of dev team access disappears automatically — desired outcome for an archive. The SRE team grant in step 5 is what gives ongoing read access to the SRE folks who manage the archive org.

## 7. Membership check requires `user` scope

`GET /orgs/<org>/memberships/<user>` returns 404 both when the user isn't a member *and* when the token lacks `user` scope. The error message lies — it claims you need `user` scope, but adds the 404 case anyway, making the two indistinguishable.

**Fix:** don't bother checking membership. `PUT /orgs/<org>/teams/<team>/memberships/<user>` is idempotent — it adds the user if missing (auto-invite), no-ops if present. Check the response's `state` field (`active` vs `pending`) to know which happened.

## 8. Existing local clones keep working after transfer

GitHub auto-redirects the old `<src>/<repo>` URL to the new `<dst>/<repo>` for git operations. Anyone with a local clone keeps working for fetch/pull. Once the repo is archived, write operations fail regardless of URL, but reads still work via the redirect.

Not a problem, just FYI when users ask "do I need to tell everyone to re-clone?"

## 9. zsh expands `gh api -F security_and_analysis[...][...]=...` as a glob

When passing nested `security_and_analysis` fields via repeated `-F` flags on zsh (the default Attain shell), the square brackets get treated as a glob pattern and the command fails before `gh` ever sees the arguments:

```
zsh:3: no matches found: security_and_analysis[advanced_security][status]=disabled
```

Quoting the whole flag works (`-F 'security_and_analysis[advanced_security][status]=disabled'`) but is brittle and unreadable. Prefer stdin JSON, which is also clearer for nested config:

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

Same pattern applies to org-level PATCH calls.

## 10. `security_and_analysis` PATCH is allowed on archived repos

Gotcha #3 says archived repos reject most PATCH/DELETE calls. The `security_and_analysis` field is a documented exception — GitHub accepts disable mutations on archived repos so you can clean up scanning state retroactively without the unarchive/re-archive dance.

The dance is still required for *other* fields (collaborators, team perms, etc.). Only `security_and_analysis` and the archive flag itself are post-archive-safe in practice.

This makes the "audit and remediate already-archived repos" workflow in SKILL.md possible — you don't need to unarchive 8 old repos to disable their scanning.

## 11. Org-level scanning defaults are separate from per-repo state

Disabling GHAS/secret scanning on every existing repo in the Archive org doesn't stop *new* transfers from arriving with scanning enabled — GitHub applies the org's `*_enabled_for_new_repositories` defaults to incoming transfers. If those defaults are `true`, every new archive needs manual cleanup.

The right pattern is: flip the org defaults once (SKILL.md "Archive org one-time hardening"), then the per-repo cleanup only ever applies to legacy archives.

Counter-intuitively, archiving a repo does NOT re-evaluate the org defaults — it just freezes whatever was there. So the org-default flip is a forward-looking fix, not a retroactive one.

## Enforced code security configurations override repo-level toggles

Observed 2026-09-03 on `Curo-AstroUS-OLD` and `Attain-MWAA` after transfer from `Data-Engineering-Attain-Finance`.

- Both repos arrived carrying the enterprise-level **Attain Security Configuration** (id 257718, `enforcement: enforced`, secret scanning on).
- `PATCH repos/<repo>` with `security_and_analysis.secret_scanning.status = disabled` returned 200 with `disabled` in the body, and the value reverted to `enabled` within about 20 seconds. The unarchive, disable, re-archive dance had no effect for the same reason.
- The Archive org's own defaults (`secret_scanning_enabled_for_new_repositories: false`) do not apply to transferred repos. They only cover repos created in the org.
- Fix: `POST orgs/Archive-Attain-Finance/code-security/configurations/266618/attach` with `{"scope":"selected","selected_repository_ids":[<id>]}`. Works on archived repos. Scanning read `disabled` and the org's open generic alerts dropped from 13 to 0 within 30 seconds.
- The same mechanism explains repos in active orgs with scanning or AI detection mysteriously off: they were sitting on the unenforced global "GitHub recommended" configuration instead of the enterprise one. Attaching 257718 fixed 16 Engineering repos the same day.
