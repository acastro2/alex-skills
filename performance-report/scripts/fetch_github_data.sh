#!/usr/bin/env bash
set -euo pipefail

ORGS=(
  "Engineering-Attain-Finance"
  "Data-Engineering-Attain-Finance"
  "Risk-Analytics-Attain-Finance"
  "Testing-Attain-Finance"
)

# --- Validation ---

if ! command -v gh &>/dev/null; then
  echo "ERROR: 'gh' CLI is not installed. Install from https://cli.github.com" >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "ERROR: 'jq' is not installed." >&2
  exit 1
fi

if ! gh auth status &>/dev/null; then
  echo "ERROR: Not authenticated. Run 'gh auth login' first." >&2
  exit 1
fi

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <email> <since_date_YYYY-MM-DD> <output_dir>" >&2
  exit 1
fi

EMAIL="$1"
SINCE="$2"
OUTPUT_DIR="$3"

mkdir -p "$OUTPUT_DIR"

# --- Step 1: Resolve GitHub username from email ---

resolve_username() {
  local email="$1"

  # Try direct email search first
  local login
  login=$(gh search users "$email" --json login --jq '.[0].login // empty' 2>/dev/null || true)
  if [[ -n "$login" ]]; then
    echo "$login"
    return
  fi

  # Fallback: derive a probable display name from the email local part,
  # then scan org members for a case-insensitive match.
  # e.g. "pavankantipudi@..." -> search for "pavan kantipudi"
  local local_part="${email%%@*}"
  # Insert spaces before uppercase letters, then lowercase everything
  local search_name
  search_name=$(echo "$local_part" | sed 's/\([a-z]\)\([A-Z]\)/\1 \2/g; s/[._-]/ /g' | tr '[:upper:]' '[:lower:]')

  echo "  Direct search failed. Scanning org members for name matching '$search_name'..." >&2

  for org in "${ORGS[@]}"; do
    local members
    members=$(gh api "/orgs/$org/members" --paginate --jq '.[].login' 2>/dev/null || true)
    [[ -z "$members" ]] && continue

    while IFS= read -r member; do
      local name
      name=$(gh api "/users/$member" --jq '.name // ""' 2>/dev/null || true)
      local name_lower
      name_lower=$(echo "$name" | tr '[:upper:]' '[:lower:]')

      if [[ -n "$name_lower" && "$name_lower" == *"$search_name"* ]]; then
        echo "$member"
        return
      fi
      sleep 0.3
    done <<< "$members"
  done
}

echo "==> Resolving GitHub username for '$EMAIL'..."
USERNAME=$(resolve_username "$EMAIL")

if [[ -z "$USERNAME" ]]; then
  echo "ERROR: Could not resolve a GitHub username for '$EMAIL'." >&2
  exit 1
fi

echo "$USERNAME" > "$OUTPUT_DIR/github_username.txt"
echo "    Found: $USERNAME"

# --- Step 2: Fetch merged PRs authored ---

echo "==> Fetching authored PRs (merged since $SINCE)..."

authored_all="[]"
orgs_with_authored=()

for org in "${ORGS[@]}"; do
  prs=$(gh search prs \
    --author="$USERNAME" \
    --org="$org" \
    --merged \
    --created=">=$SINCE" \
    --json number,title,repository,closedAt,url \
    --limit 200 2>/dev/null || echo "[]")

  count=$(echo "$prs" | jq 'length')
  if [[ "$count" -eq 0 ]]; then
    echo "    WARN: No authored PRs in $org" >&2
  else
    echo "    $org: $count PRs"
    orgs_with_authored+=("$org")
  fi

  authored_all=$(echo "$authored_all" "$prs" | jq -s '.[0] + .[1]')
  sleep 2
done

# Enrich each PR with LOC stats
echo "    Fetching LOC for $(echo "$authored_all" | jq 'length') PRs..."
enriched="[]"

for row in $(echo "$authored_all" | jq -r -c '.[]'); do
  repo_full=$(echo "$row" | jq -r '.repository.nameWithOwner // (.repository.owner + "/" + .repository.name)' 2>/dev/null || true)
  pr_number=$(echo "$row" | jq -r '.number')

  loc=$(gh api "repos/$repo_full/pulls/$pr_number" \
    --jq '{additions,deletions,changedFiles}' 2>/dev/null || echo '{"additions":0,"deletions":0,"changedFiles":0}')

  merged=$(echo "$row" "$loc" | jq -s '.[0] * .[1]')
  enriched=$(echo "$enriched" "[$merged]" | jq -s '.[0] + .[1]')
  sleep 1
done

echo "$enriched" | jq '.' > "$OUTPUT_DIR/prs_authored.json"

# --- Step 3: Fetch PRs reviewed ---

echo "==> Fetching reviewed PRs (since $SINCE)..."

reviewed_all="[]"
orgs_with_reviewed=()

for org in "${ORGS[@]}"; do
  prs=$(gh search prs \
    --reviewed-by="$USERNAME" \
    --org="$org" \
    --created=">=$SINCE" \
    --json number,title,repository,closedAt,url \
    --limit 200 2>/dev/null || echo "[]")

  count=$(echo "$prs" | jq 'length')
  if [[ "$count" -eq 0 ]]; then
    echo "    WARN: No reviewed PRs in $org" >&2
  else
    echo "    $org: $count PRs"
    orgs_with_reviewed+=("$org")
  fi

  reviewed_all=$(echo "$reviewed_all" "$prs" | jq -s '.[0] + .[1]')
  sleep 2
done

# Deduplicate by URL (same PR reviewed multiple times)
reviewed_all=$(echo "$reviewed_all" | jq '[group_by(.url)[] | .[0]]')

echo "$reviewed_all" | jq '.' > "$OUTPUT_DIR/prs_reviewed.json"

# --- Step 4: Summary ---

authored_count=$(jq 'length' "$OUTPUT_DIR/prs_authored.json")
reviewed_count=$(jq 'length' "$OUTPUT_DIR/prs_reviewed.json")

active_orgs=$(printf '%s\n' "${orgs_with_authored[@]}" "${orgs_with_reviewed[@]}" | sort -u | paste -sd', ' -)

echo ""
echo "=== Summary ==="
echo "  Username:      $USERNAME"
echo "  Authored PRs:  $authored_count"
echo "  Reviewed PRs:  $reviewed_count"
echo "  Active orgs:   ${active_orgs:-none}"
echo "  Output:        $OUTPUT_DIR/"
