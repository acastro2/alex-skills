---
name: exa-agent
description: "Run Exa Agent from the CLI with curl and jq for long, multi-step research, list building, enrichment, structured output, continuation, and Exa Connect data sources."
---

# Exa Agent

Use `POST https://api.exa.ai/agent/runs` for work that needs several searches, multi-hop research, list building, or row enrichment.

Use `exa-search` for one-call retrieval, including filtered or advanced search. Use `exa-contents` when the URLs are already known.

This skill uses the official Exa REST API only. Do not use an SDK or MCP.

## Set up authentication

Run this once in the current shell. It uses `EXA_API_KEY` first, then `~/.config/exa/key`. It never prints the key.

```bash
set -euo pipefail

if [[ -n "${EXA_API_KEY:-}" ]]; then
  EXA_KEY="$EXA_API_KEY"
elif [[ -r "$HOME/.config/exa/key" ]]; then
  IFS= read -r EXA_KEY < "$HOME/.config/exa/key" || [[ -n "$EXA_KEY" ]]
else
  printf '%s\n' 'Exa API key not found. Set EXA_API_KEY or create ~/.config/exa/key.' >&2
  exit 1
fi

if [[ -z "$EXA_KEY" ]]; then
  printf '%s\n' 'Exa API key is empty.' >&2
  exit 1
fi

EXA_AGENT_URL="https://api.exa.ai/agent/runs"
```

**WARNING:** Do not use `set -x`. It can print the API key through expanded `curl` headers.

## Create a run

Build request bodies with `jq`. This keeps shell input escaped and produces valid JSON.

```bash
QUERY="Find up to 10 B2B SaaS companies and get monthly visits from Similarweb."

REQUEST="$(jq -n --arg query "$QUERY" '{
  query: $query,
  effort: "auto",
  budget: {maxCostDollars: 5},
  input: {
    data: [{company: "Acme", domain: "acme.example"}],
    exclusion: [{company: "Example Corp"}]
  },
  dataSources: [{provider: "similarweb"}],
  outputSchema: {
    type: "object",
    properties: {
      companies: {
        type: "array",
        maxItems: 10,
        items: {
          type: "object",
          properties: {
            name: {type: "string"},
            domain: {type: "string"},
            monthlyVisits: {type: "number"},
            sourceUrl: {type: "string", format: "uri"}
          },
          required: ["name", "domain", "monthlyVisits", "sourceUrl"]
        }
      }
    },
    required: ["companies"]
  }
}')"

RUN_JSON="$(curl -sS --fail-with-body -X POST "$EXA_AGENT_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EXA_KEY" \
  --data "$REQUEST")"
RUN_ID="$(jq -er '.id' <<<"$RUN_JSON")"
printf 'run_id=%s\n' "$RUN_ID"
```

The create call returns at once unless you request SSE. Save the `agent_run_...` ID.

### Request controls

- `systemPrompt`: Sets source preferences, deduplication rules, and other run behavior.
- `outputSchema`: Returns validated JSON in `output.structured`. Use a top-level object. Put `maxItems` on arrays when cost or result count matters.
- `input.data`: Supplies known rows or entities to enrich.
- `input.exclusion`: Stops the run from returning known or disallowed rows.
- `effort`: Use `minimal`, `low`, `medium`, `high`, `xhigh`, `auto`, or beta `max`. The API default is `auto`. Set it explicitly.
- `budget.maxCostDollars`: A per-run ceiling from `$1` to `$100`. It works only with `auto` or `max`. Do not send it with fixed effort modes.
- `dataSources`: Enables up to five Exa Connect providers. Self-serve provider IDs are `fiber`, `financial_datasets`, `similarweb`, `baselayer`, `affiliate`, `particle`, and `jinko`. Name the provider-specific field in both the query and schema.
- `metadata`: Stores caller tracking fields as string key-value pairs. Do not put secrets in metadata.

Connect data can add separate provider costs. Check `costDollars` after completion.

## Get or poll a run

Get one status snapshot:

```bash
curl -sS --fail-with-body "$EXA_AGENT_URL/$RUN_ID" \
  -H "x-api-key: $EXA_KEY" | jq .
```

Use a bounded poll. This example waits for at most 10 minutes. A local timeout does not cancel the server-side run.

```bash
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-600}"
POLL_SECONDS="${POLL_SECONDS:-4}"
DEADLINE=$((SECONDS + TIMEOUT_SECONDS))

while (( SECONDS < DEADLINE )); do
  RUN_JSON="$(curl -sS --fail-with-body "$EXA_AGENT_URL/$RUN_ID" \
    -H "x-api-key: $EXA_KEY")"
  STATUS="$(jq -er '.status' <<<"$RUN_JSON")"
  printf 'status=%s\n' "$STATUS" >&2

  case "$STATUS" in
    completed)
      jq '{output: .output, usage: .usage, costDollars: .costDollars}' <<<"$RUN_JSON"
      break
      ;;
    failed|cancelled)
      jq '{status, stopReason, error}' <<<"$RUN_JSON" >&2
      exit 1
      ;;
    queued|running)
      sleep "$POLL_SECONDS"
      ;;
    *)
      printf 'Unknown run status: %s\n' "$STATUS" >&2
      exit 1
      ;;
  esac
done

if [[ "${STATUS:-}" != "completed" ]]; then
  printf 'Timed out waiting for %s; the server-side run can still be active.\n' "$RUN_ID" >&2
  exit 124
fi
```

Read `output.text` for prose, `output.structured` for schema output, and `output.grounding` for citations. Do not read output until `status` is `completed`.

## Continue a completed run

`previousRunId` carries context into a new run. It does not poll or reuse the old run ID.

```bash
PREVIOUS_RUN_ID="$RUN_ID"
QUERY="Find five more. Exclude every company already returned."

REQUEST="$(jq -n \
  --arg query "$QUERY" \
  --arg previousRunId "$PREVIOUS_RUN_ID" \
  '{query: $query, previousRunId: $previousRunId, effort: "medium"}')"

RUN_JSON="$(curl -sS --fail-with-body -X POST "$EXA_AGENT_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EXA_KEY" \
  --data "$REQUEST")"
RUN_ID="$(jq -er '.id' <<<"$RUN_JSON")"
printf 'new_run_id=%s\n' "$RUN_ID"
```

The prior run must be completed and belong to the same team. Add `input.exclusion` when exact records must not return again.

## Stream and replay events

Stream a new run until a terminal event:

```bash
REQUEST="$(jq -n '{query: "Research the main causes of sodium-ion battery degradation.", effort: "medium"}')"

curl -sS --fail-with-body -N -X POST "$EXA_AGENT_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -H "x-api-key: $EXA_KEY" \
  --data "$REQUEST"
```

SSE frames contain `id:`, `event:`, and JSON `data:` lines. Ignore `: keep-alive` comments and unknown event names. Save the run ID from `agent_run.created`. Stop on `agent_run.completed`, `agent_run.failed`, or `agent_run.cancelled`. Use the terminal run's `output.grounding` as the final citation set.

List stored events as JSON:

```bash
curl -sS --fail-with-body "$EXA_AGENT_URL/$RUN_ID/events?limit=100" \
  -H "x-api-key: $EXA_KEY" | jq .
```

Follow `nextCursor` while `hasMore` is true. Replay stored events after an event ID as SSE:

```bash
LAST_EVENT_ID="1"
curl -sS --fail-with-body -N "$EXA_AGENT_URL/$RUN_ID/events" \
  -H "Accept: text/event-stream" \
  -H "Last-Event-ID: $LAST_EVENT_ID" \
  -H "x-api-key: $EXA_KEY"
```

Replay returns the events stored at request time, then closes. It does not follow new events from an active run.

## Cancel or delete

Cancel a queued or running run:

```bash
curl -sS --fail-with-body -X POST "$EXA_AGENT_URL/$RUN_ID/cancel" \
  -H "x-api-key: $EXA_KEY" | jq .
```

Delete a stored run from team history:

```bash
curl -sS --fail-with-body -X DELETE "$EXA_AGENT_URL/$RUN_ID" \
  -H "x-api-key: $EXA_KEY" | jq .
```

Cancel an active run before deletion. Deletion is permanent.

## Handle errors

`curl --fail-with-body` returns a nonzero exit code for HTTP errors and keeps the JSON error body. Inspect `.error.code` and `.error.message`. Common codes are:

- `INVALID_OUTPUT_SCHEMA`
- `INVALID_DATA_SOURCE`
- `CONCURRENCY_LIMIT_REACHED`
- `RUN_NOT_FOUND`
- `PREVIOUS_RUN_NOT_FOUND`
- `PREVIOUS_RUN_NOT_COMPLETED`
- `TIMEOUT`

Do not silently replace Agent work with plain search after an Agent API error. Fix the request or report the failure.

## Official references

- https://exa.ai/docs/reference/agent-api-guide
- https://exa.ai/docs/reference/agent-api/create-a-run
- https://exa.ai/docs/reference/agent-api/get-a-run
- https://exa.ai/docs/reference/agent-api/list-run-events
- https://exa.ai/docs/reference/agent-api/cancel-a-run
- https://exa.ai/docs/reference/agent-api/delete-a-run
