#!/usr/bin/env bash
# Bulk archive: takes a source org and a newline-delimited repos file.
# Runs preflight on every repo, shows a plan, asks once for confirmation,
# then executes per-repo with JSONL logging.
#
# Usage: ./archive_repos_bulk.sh <source-org> <repos-file>

set -uo pipefail  # intentionally NOT -e: we want to continue past per-repo failures

SRC_OWNER="${1:-}"
REPOS_FILE="${2:-}"
DST_OWNER="Archive-Attain-Finance"
SRE_TEAM="sre"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SINGLE="${SCRIPT_DIR}/archive_repo.sh"

LOG="archive-log-$(date +%Y%m%d-%H%M%S).jsonl"

if [[ -z "$SRC_OWNER" || -z "$REPOS_FILE" ]]; then
  echo "Usage: $0 <source-org> <repos-file>" >&2
  exit 2
fi

if [[ ! -f "$REPOS_FILE" ]]; then
  echo "Repos file not found: $REPOS_FILE" >&2
  exit 2
fi

log_event() {
  # log_event <repo> <status> <message>
  printf '{"ts":"%s","repo":"%s","status":"%s","message":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "${3//\"/\\\"}" >> "$LOG"
}

echo "==> Preflight: validating ${REPOS_FILE} against ${SRC_OWNER}"
plan=()
skip=()
missing=()
while IFS= read -r repo; do
  [[ -z "$repo" || "$repo" =~ ^# ]] && continue
  if gh api "repos/${DST_OWNER}/${repo}" --silent 2>/dev/null; then
    arch=$(gh api "repos/${DST_OWNER}/${repo}" --jq '.archived')
    if [[ "$arch" == "true" ]]; then
      skip+=("$repo")
      continue
    fi
  fi
  if gh api "repos/${SRC_OWNER}/${repo}" --silent 2>/dev/null; then
    plan+=("$repo")
  else
    missing+=("$repo")
  fi
done < "$REPOS_FILE"

echo ""
echo "Plan:"
echo "  Will archive (${#plan[@]}): ${plan[*]:-none}"
echo "  Already archived, skipping (${#skip[@]}): ${skip[*]:-none}"
echo "  Not found in ${SRC_OWNER} (${#missing[@]}): ${missing[*]:-none}"
echo ""
echo "Log file: ${LOG}"
echo ""

if [[ ${#plan[@]} -eq 0 ]]; then
  echo "Nothing to do."
  exit 0
fi

read -r -p "Proceed with ${#plan[@]} repo(s)? [y/N] " confirm
[[ "$confirm" == "y" ]] || { echo "Aborted."; exit 0; }

failed=()
succeeded=()
for repo in "${plan[@]}"; do
  echo ""
  echo "================================================================"
  echo "==> ${repo}"
  echo "================================================================"
  log_event "$repo" "start" "beginning archival"

  # Pipe 'y' to auto-confirm the per-repo prompt since we already confirmed in bulk.
  if echo "y" | "$SINGLE" "$SRC_OWNER" "$repo"; then
    succeeded+=("$repo")
    log_event "$repo" "success" "archived and granted SRE pull"
  else
    failed+=("$repo")
    log_event "$repo" "failure" "see stderr above"
  fi
done

echo ""
echo "================================================================"
echo "Summary"
echo "================================================================"
echo "  Succeeded (${#succeeded[@]}): ${succeeded[*]:-none}"
echo "  Failed    (${#failed[@]}): ${failed[*]:-none}"
echo "  Log: ${LOG}"

[[ ${#failed[@]} -eq 0 ]]
