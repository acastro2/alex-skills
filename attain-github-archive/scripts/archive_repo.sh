#!/usr/bin/env bash
# Archive a single repo: strip direct collaborators, disable GHAS, transfer to
# Archive-Attain-Finance, archive, grant SRE team read.
#
# Usage: ./archive_repo.sh <source-org> <repo-name>

set -euo pipefail

SRC_OWNER="${1:-}"
REPO="${2:-}"
DST_OWNER="Archive-Attain-Finance"
SRE_TEAM="sre"

if [[ -z "$SRC_OWNER" || -z "$REPO" ]]; then
  echo "Usage: $0 <source-org> <repo-name>" >&2
  exit 2
fi

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

log "Preflight: source repo"
gh api "repos/${SRC_OWNER}/${REPO}" --jq '{full_name, archived, private}' \
  || { echo "Cannot access ${SRC_OWNER}/${REPO}"; exit 1; }

log "Preflight: target org"
gh api "orgs/${DST_OWNER}" --jq '.login' >/dev/null \
  || { echo "Cannot access ${DST_OWNER}"; exit 1; }

# Idempotency: if already in target and archived, exit clean
if gh api "repos/${DST_OWNER}/${REPO}" --silent 2>/dev/null; then
  archived=$(gh api "repos/${DST_OWNER}/${REPO}" --jq '.archived')
  if [[ "$archived" == "true" ]]; then
    log "Already at ${DST_OWNER}/${REPO} and archived. Nothing to do."
    exit 0
  fi
  log "Already at ${DST_OWNER}/${REPO} but not archived. Continuing from archive step."
  SKIP_TRANSFER=1
else
  SKIP_TRANSFER=0
fi

read -r -p "Proceed with archival of ${SRC_OWNER}/${REPO} -> ${DST_OWNER}/${REPO}? [y/N] " confirm
[[ "$confirm" == "y" ]] || { log "Aborted."; exit 0; }

if [[ "$SKIP_TRANSFER" == "0" ]]; then
  log "Listing direct collaborators (will be stripped)"
  collaborators=$(gh api "repos/${SRC_OWNER}/${REPO}/collaborators?affiliation=direct" --jq '.[].login' || true)
  if [[ -n "$collaborators" ]]; then
    echo "$collaborators" | while read -r user; do
      log "Removing direct collaborator: ${user}"
      gh api -X DELETE "repos/${SRC_OWNER}/${REPO}/collaborators/${user}"
    done
  else
    log "No direct collaborators."
  fi

  log "Disabling security features on source (pre-transfer to avoid unarchive dance)"
  # security_and_analysis: idempotent, safe to set all to disabled
  gh api -X PATCH "repos/${SRC_OWNER}/${REPO}" \
    -F security_and_analysis[advanced_security][status]=disabled \
    -F security_and_analysis[secret_scanning][status]=disabled \
    -F security_and_analysis[secret_scanning_push_protection][status]=disabled \
    >/dev/null || log "  (some security_and_analysis fields may not be settable; continuing)"

  # Separate endpoints — see references/gotchas.md
  gh api -X DELETE "repos/${SRC_OWNER}/${REPO}/automated-security-fixes" 2>/dev/null && log "  automated-security-fixes disabled" || log "  automated-security-fixes already off or N/A"
  gh api -X DELETE "repos/${SRC_OWNER}/${REPO}/vulnerability-alerts" 2>/dev/null && log "  vulnerability-alerts disabled" || log "  vulnerability-alerts already off or N/A"

  log "Transferring ${SRC_OWNER}/${REPO} -> ${DST_OWNER}"
  gh api -X POST "repos/${SRC_OWNER}/${REPO}/transfer" -f new_owner="${DST_OWNER}" >/dev/null

  log "Polling for transfer to settle"
  for i in {1..30}; do
    if gh api "repos/${DST_OWNER}/${REPO}" --silent 2>/dev/null; then
      log "  settled (attempt ${i})"
      break
    fi
    sleep 2
    if [[ $i -eq 30 ]]; then
      log "Transfer did not settle in 60s. Check GitHub UI."
      exit 1
    fi
  done
fi

log "Archiving ${DST_OWNER}/${REPO}"
gh api -X PATCH "repos/${DST_OWNER}/${REPO}" -F archived=true --jq '.archived' >/dev/null

log "Granting ${SRE_TEAM} team pull access"
gh api -X PUT "orgs/${DST_OWNER}/teams/${SRE_TEAM}/repos/${DST_OWNER}/${REPO}" \
  -f permission="pull" >/dev/null

log "Verifying final state"
gh api "repos/${DST_OWNER}/${REPO}" --jq '{full_name, archived, security_and_analysis}'
gh api "repos/${DST_OWNER}/${REPO}/teams" --jq '.[] | {slug, permission}'

log "Done: ${DST_OWNER}/${REPO}"
