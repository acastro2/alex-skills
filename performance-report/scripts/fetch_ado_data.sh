#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <display_name> <since_date_YYYY-MM-DD> <output_dir>" >&2
  exit 1
fi

DISPLAY_NAME="$1"
SINCE_DATE="$2"
OUTPUT_DIR="$3"

if [[ -z "${AZURE_DEVOPS_PAT:-}" ]]; then
  echo "Error: AZURE_DEVOPS_PAT environment variable is not set." >&2
  echo "Generate a PAT at https://dev.azure.com/CuroFinTech/_usersSettings/tokens" >&2
  exit 1
fi

BASE_URL="https://dev.azure.com/CuroFinTech/Tiger"
API_VERSION="7.1"
AUTH=("-u" ":${AZURE_DEVOPS_PAT}")

mkdir -p "$OUTPUT_DIR"

# ── 1. WIQL query for closed User Stories ──

WIQL_QUERY="SELECT [System.Id] FROM WorkItems \
WHERE [System.WorkItemType] = 'User Story' \
AND [System.State] = 'Closed' \
AND [System.AssignedTo] CONTAINS '${DISPLAY_NAME}' \
AND [System.ChangedDate] >= '${SINCE_DATE}' \
ORDER BY [System.ChangedDate] DESC"

WIQL_BODY=$(jq -n --arg q "$WIQL_QUERY" '{query: $q}')

HTTP_CODE=$(curl -s -o /tmp/ado_wiql_response.json -w "%{http_code}" \
  "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d "$WIQL_BODY" \
  "${BASE_URL}/_apis/wit/wiql?api-version=${API_VERSION}")

if [[ "$HTTP_CODE" == "302" ]]; then
  echo "Error: Got HTTP 302 (redirect to login). Your PAT is missing or expired." >&2
  exit 1
fi

if [[ "$HTTP_CODE" == "401" || "$HTTP_CODE" == "403" ]]; then
  echo "Error: HTTP ${HTTP_CODE} - authentication/authorization failed. Check your PAT and permissions." >&2
  exit 1
fi

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "Error: WIQL query returned HTTP ${HTTP_CODE}" >&2
  cat /tmp/ado_wiql_response.json >&2
  exit 1
fi

# Extract work item IDs
IDS=$(jq -r '[.workItems[].id]' /tmp/ado_wiql_response.json)
ID_COUNT=$(echo "$IDS" | jq 'length')

if [[ "$ID_COUNT" -eq 0 ]]; then
  echo "Warning: No closed User Stories found for '${DISPLAY_NAME}' since ${SINCE_DATE}." >&2
  echo "This could be valid (new hire, different display name, etc.)." >&2
  echo "[]" > "${OUTPUT_DIR}/ado_items.json"
  exit 0
fi

echo "Found ${ID_COUNT} closed User Stories for '${DISPLAY_NAME}' since ${SINCE_DATE}"

# ── 2. Batch fetch work item details (200 max per batch) ──

FIELDS='["System.Id","System.Title","System.State","Microsoft.VSTS.Scheduling.StoryPoints","System.AreaPath","System.CreatedDate","System.ChangedDate","System.Description","Microsoft.VSTS.Common.AcceptanceCriteria","System.Tags"]'
ALL_ITEMS="[]"

BATCH_SIZE=200
OFFSET=0

while [[ $OFFSET -lt $ID_COUNT ]]; do
  BATCH_IDS=$(echo "$IDS" | jq ".[$OFFSET:$((OFFSET + BATCH_SIZE))]")

  BATCH_BODY=$(jq -n --argjson ids "$BATCH_IDS" --argjson fields "$FIELDS" \
    '{ids: $ids, fields: $fields}')

  HTTP_CODE=$(curl -s -o /tmp/ado_batch_response.json -w "%{http_code}" \
    "${AUTH[@]}" \
    -H "Content-Type: application/json" \
    -d "$BATCH_BODY" \
    "${BASE_URL}/_apis/wit/workitemsbatch?api-version=${API_VERSION}")

  if [[ "$HTTP_CODE" != "200" ]]; then
    echo "Error: Batch fetch returned HTTP ${HTTP_CODE} (offset ${OFFSET})" >&2
    cat /tmp/ado_batch_response.json >&2
    exit 1
  fi

  ALL_ITEMS=$(jq -s '.[0] + .[1]' \
    <(echo "$ALL_ITEMS") \
    <(jq '[.value[]]' /tmp/ado_batch_response.json))

  OFFSET=$((OFFSET + BATCH_SIZE))
done

# ── 3. Transform to clean JSON ──

echo "$ALL_ITEMS" | jq '[.[] | {
  id: .fields["System.Id"],
  title: .fields["System.Title"],
  state: .fields["System.State"],
  storyPoints: (.fields["Microsoft.VSTS.Scheduling.StoryPoints"] // null),
  areaPath: .fields["System.AreaPath"],
  createdDate: .fields["System.CreatedDate"],
  changedDate: .fields["System.ChangedDate"],
  hasDescription: ((.fields["System.Description"] // "") | length > 0),
  hasAcceptanceCriteria: ((.fields["Microsoft.VSTS.Common.AcceptanceCriteria"] // "") | length > 0),
  tags: (.fields["System.Tags"] // "")
}]' > "${OUTPUT_DIR}/ado_items.json"

# ── 4. Summary ──

FINAL_COUNT=$(jq 'length' "${OUTPUT_DIR}/ado_items.json")
echo ""
echo "=== ADO Summary ==="
echo "Total items: ${FINAL_COUNT}"
echo ""
echo "Area path distribution:"
jq -r 'group_by(.areaPath) | .[] | "  \(.[0].areaPath): \(length)"' "${OUTPUT_DIR}/ado_items.json"
echo ""
echo "State distribution:"
jq -r 'group_by(.state) | .[] | "  \(.[0].state): \(length)"' "${OUTPUT_DIR}/ado_items.json"
echo ""
echo "Output: ${OUTPUT_DIR}/ado_items.json"
