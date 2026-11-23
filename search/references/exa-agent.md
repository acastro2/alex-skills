# Exa Agent

**The `curl` blocks below are for a host without the Exa MCP**, and for what each API field means. There, set up the key first: see **Exa authentication** in `../SKILL.md`.

Use `POST https://api.exa.ai/agent/runs` when one search is not enough: multi-hop research, list building, and row enrichment. A run is asynchronous. Create it, then poll or stream until it reaches a terminal status.

Use [Exa Search](exa-search.md) for one-call retrieval. Use [Exa Contents](exa-contents.md) when the URLs are already known.

**Every `curl` block below is self-contained.** Shell variables do not survive between tool calls, so each block sets what it needs at the top and reads the key straight from `$EXA_API_KEY`. Run a whole block in one call.

## In Claude Code and OpenCode: use the MCP

Call the Exa MCP tool `agent_run` (the name prefix varies by host). Do not run `curl` there: the Claude Code sandbox blocks `api.exa.ai`. Its parameters match the API fields described below:

| MCP parameter | Use |
| --- | --- |
| `query` | The research objective. Send either `query` or `runId`, not both |
| `effort` | **Always set it.** The MCP defaults to `low`; the API defaults to `auto`. Pick with the effort table below |
| `outputSchema` | JSON Schema for the result. Put `maxItems` on arrays |
| `input.data`, `input.exclusion` | Rows to enrich, and entities to keep out |
| `budget.maxCostDollars`, `budget.maxDurationSeconds` | Caps for `auto` and `ultra` only (duration: `ultra` only) |
| `previousRunId` | Continue a completed run with its context |
| `runId` | Check or keep waiting on a run that is still running. Never start a duplicate run |
| `dataSources`, `systemPrompt` | Exa Connect providers, and extra guidance for the agent |

The MCP tool waits for the run and returns its output. A long run comes back still running: call `agent_run` again with its `runId`. The MCP has no stop call; to stop an `ultra` run early, set `budget.maxDurationSeconds` up front. The checks in **`completed` does not mean correct** below apply to MCP results too.

## Plan the run first

A run costs money and is slow to repeat. Before you create one, write down:

- **Objective:** the question the run answers.
- **Universe:** which entities qualify.
- **Segments:** the partitions to cover (geography, industry, persona, date range).
- **Coverage target:** the count you want, the maximum, and what "good enough" means.
- **Output fields:** the columns you need. These become the `outputSchema`.
- **Evidence:** URL, source title, date, and a confidence or rationale field for fuzzy judgments.
- **Exclusions:** earlier results and disallowed entities, for `input.exclusion`.

Turn relative time ("recent", "last 6 months") into exact dates from today's date before you write the query.

### Agent or a script

- **Discovery is the hard part** (open universe, multi-hop, deciding what to search next): use the Agent.
- **Known rows that fit in one run:** use the Agent with `input.data` (see **Enrich rows you already have**).
- **Too many known rows for one run, same enrichment on each** (hundreds of companies or people): split the rows into batches and send each batch as one run with `input.data`. **Never start one Agent run per row.** A fixed effort bills per request (see **Choosing effort**), so 400 rows at `medium` cost about USD 40 as 400 runs and about USD 2 as 20 runs of 20 rows, before search calls. Start with one batch as a pilot. Do not loop the batches as MCP calls by hand; that burns context. Write a script that sends the batches. The script needs a host that can reach `api.exa.ai` and has `EXA_API_KEY`; the Claude Code sandbox blocks it, so ask the user where to run it. Every row is a paid call: estimate the total cost from the row count and get the user's yes before you run it. The script reads its inputs from a file, uses bounded concurrency and exponential backoff on `429` and `5xx`, checkpoints progress, keeps the raw API error per row, and writes one JSON or CSV file. Then read that file and answer from it.

## Create a run

Build the request body with `jq -n`. It escapes shell input for you and cannot emit invalid JSON.

```bash
QUERY="Find AI infrastructure companies that raised a Series A or B in the last 6 months."

REQUEST="$(jq -n --arg query "$QUERY" '{
  query: $query,
  effort: "auto",
  systemPrompt: "Prefer official company sources. Do not return duplicates.",
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
            round: {type: "string"},
            sourceUrl: {type: "string", format: "uri"}
          },
          required: ["name", "round", "sourceUrl"]
        }
      }
    },
    required: ["companies"]
  }
}')"

RUN_JSON="$(curl -sS --fail-with-body -X POST "https://api.exa.ai/agent/runs" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EXA_API_KEY" \
  --data "$REQUEST")"

RUN_ID="$(jq -er '.id' <<<"$RUN_JSON")"
printf 'run_id=%s\n' "$RUN_ID"
```

The create call returns at once unless you ask for SSE. Save the `agent_run_...` ID — without it you must fall back to listing runs.

### Enrich rows you already have

`input.data` and `input.exclusion` do different jobs, so keep them apart in your head. `input.data` gives the agent the rows to work on. `input.exclusion` names entities it must not return. Use `data` for enrichment and `exclusion` for de-duplication across runs.

```bash
REQUEST="$(jq -n '{
  query: "For each company, find one current executive and cite a source.",
  effort: "medium",
  input: {
    data: [
      {company: "Apple", domain: "apple.com"},
      {company: "Microsoft", domain: "microsoft.com"}
    ],
    exclusion: [{company: "Apple", person: "Tim Cook"}]
  }
}')"

curl -sS --fail-with-body -X POST "https://api.exa.ai/agent/runs" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EXA_API_KEY" \
  --data "$REQUEST" | jq -r '.id'
```

### Request controls

- `systemPrompt`: Source preferences, novelty rules, and duplication rules. Behaviour guidance, not the question.
- `outputSchema`: Validated JSON in `output.structured`. Use a top-level object. Supports JSON Schema draft-07, 2019-09, and 2020-12 through `$schema`, plus the `phone` format. Put `maxItems` on arrays so the worst-case cost is predictable.
- `input.data` / `input.exclusion`: Rows to process, and entities to keep out.
- `effort`: `minimal`, `low`, `medium`, `high`, `xhigh`, `auto`, or `max`. The default is `auto`. Set it on purpose — see the table below.
- `budget.maxCostDollars`: Per-run ceiling, `$1` to `$100`. It applies only to the metered efforts: `auto`, `ultra`, and `max`. Sending it with a fixed effort does nothing. Defaults are `$5` for `auto` and `$20` for `max`, so only set it when you want a different cap.
- `dataSources`: Up to five Exa Connect providers. Self-serve IDs are `fiber`, `financial_datasets`, `similarweb`, `baselayer`, `affiliate`, `particle`, and `jinko`. Name the provider in the query *and* in the schema field description (`"description": "from Similarweb"`) or the agent will not call it.
- `metadata`: String key-value pairs for your own tracking.

### Choosing effort

Fixed efforts cost a flat price per request. `auto` and `max` are metered against their cap.

| effort | price | use it for |
| --- | --- | --- |
| `minimal` | $0.012 | one or two fields, very narrow lookup |
| `low` | $0.025 | simple lookups, shallow schema |
| `medium` | $0.10 | the default for standard single-entity research |
| `high` | $0.50 | larger schemas, stricter completeness |
| `xhigh` | $1.00 | complex schemas, many fields, hard verification |
| `auto` | metered, $5 cap | list building and any task whose scope you cannot predict |
| `max` | metered, $20 cap | beta — biggest list builds and deepest multi-source research |

Search calls add `$0.005` each, contact enrichment adds `$0.02` per email and `$0.07` per phone number, and Connect providers bill per call. Read the real number from `costDollars` after the run.

### Ultra

`ultra` (released 2026-09-24, Exa changelog) is the highest effort, for large list building, deep multi-source research, and criteria that are hard to verify. It is metered at standard Agent rates up to a default cap of USD 20 per run (`budget.maxCostDollars` changes it). Set `budget.maxDurationSeconds`, from 300 to 10800 (5 minutes to 3 hours), and the run wraps up with what it found by then. To end a run early and keep its results so far, call `POST https://api.exa.ai/agent/runs/{id}/stop`. Use `ultra` only when the user asks for maximum completeness, because a run can take hours.

```bash
curl -sS --fail-with-body -X POST "https://api.exa.ai/agent/runs" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EXA_API_KEY" \
  --data "$(jq -n '{query: "...", effort: "ultra", budget: {maxCostDollars: 20, maxDurationSeconds: 3600}}')" | jq -r '.id'
```

The `max` effort below predates `ultra`. Exa's API reference still documents it, but the MCP `agent_run` tool lists only `ultra`, so prefer `ultra`.

`max` is public beta and needs an extra header, so it fails as a plain `effort` value:

```bash
curl -sS --fail-with-body -X POST "https://api.exa.ai/agent/runs" \
  -H "Content-Type: application/json" \
  -H "Exa-Beta: agent-max-effort-2026-07-27" \
  -H "x-api-key: $EXA_API_KEY" \
  --data "$(jq -n '{query: "...", effort: "max"}')"
```

The beta token is dated and Exa can change it. If a `max` run returns `INVALID_REQUEST`, check the current token in the Agent overview docs before debugging anything else.

## Poll a run

This block creates a run and waits for it. Change `QUERY` and `EFFORT`, or replace the create step with a known `RUN_ID`. The result is saved to `$OUT_DIR/<run id>.json`; set `OUT_DIR` to the session scratchpad when the host gives one, because `/tmp` is shared and kept after the session.

```bash
QUERY="Research the main causes of sodium-ion battery degradation."
EFFORT="medium"
TIMEOUT_SECONDS=600
POLL_SECONDS=4

RUN_ID="$(curl -sS --fail-with-body -X POST "https://api.exa.ai/agent/runs" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EXA_API_KEY" \
  --data "$(jq -n --arg q "$QUERY" --arg e "$EFFORT" '{query: $q, effort: $e}')" \
  | jq -er '.id')"
printf 'run_id=%s\n' "$RUN_ID" >&2

DEADLINE=$((SECONDS + TIMEOUT_SECONDS))
STATUS="queued"

while (( SECONDS < DEADLINE )); do
  RUN_JSON="$(curl -sS --fail-with-body "https://api.exa.ai/agent/runs/$RUN_ID" \
    -H "x-api-key: $EXA_API_KEY")"
  STATUS="$(jq -er '.status' <<<"$RUN_JSON")"
  printf 'status=%s\n' "$STATUS" >&2

  case "$STATUS" in
    completed)
      jq '{stopReason, output, usage, costDollars}' <<<"$RUN_JSON" > "${OUT_DIR:-${TMPDIR:-/tmp}}/$RUN_ID.json"
      jq '{stopReason, costDollars: .costDollars.total}' <<<"$RUN_JSON"
      break
      ;;
    failed|cancelled)
      jq '{status, stopReason, error}' <<<"$RUN_JSON" >&2
      break
      ;;
    *)
      sleep "$POLL_SECONDS"
      ;;
  esac
done

if [ "$STATUS" != "completed" ]; then
  printf 'Run %s did not complete locally. The server-side run can still be active.\n' "$RUN_ID" >&2
fi
```

A local timeout does not cancel the run. The server gives every run one hour before it times out on its own.

### `completed` does not mean correct

This is the trap that quietly corrupts downstream work. Two things can go wrong while `status` is still `completed`:

- **The agent returns `null` for anything it could not evidence, even for fields your schema marks `required`.** `stopReason: schema_satisfied` means the output matched the *shape* with those nulls allowed. It does not mean your schema validated. Treat every field as nullable and drop the records that are missing what you need.
- **`stopReason: budget_reached` also lands as `completed`.** You get a short list that looks finished.

So check the stop reason and the nulls before you use the output:

```bash
RUN_ID="agent_run_..."
RUN_JSON="$(curl -sS --fail-with-body "https://api.exa.ai/agent/runs/$RUN_ID" \
  -H "x-api-key: $EXA_API_KEY")"

jq -r '
  "stopReason=\(.stopReason)",
  (if .stopReason == "budget_reached"
   then "WARNING: hit the spend cap - the result set is probably short"
   else empty end),
  ([.output.structured | paths(. == null) | map(tostring) | join(".")] as $n
   | if ($n | length) > 0
     then "WARNING: null fields: \($n | join(", "))"
     else "no null fields" end)
' <<<"$RUN_JSON"
```

The four stop reasons are `schema_satisfied`, `budget_reached`, `error`, and `cancelled`.

### Check coverage before you report

A completed run is not an exhaustive one. Before you answer:

1. Compare the row count with the coverage target.
2. Check that each segment has rows.
3. Remove duplicate entities.
4. Check the evidence in `output.grounding` (see **Read the citations**). Fetch a source URL only for a claim you will repeat: each fetch is a paid call.
5. List the gaps.

If the output is sparse, continue with `previousRunId`, put the earlier results in `input.exclusion`, or split the universe into one run per segment and merge the results yourself.

Say "best-effort discovery" or "not exhaustive", and say where coverage is strong and where it is weak. Say "complete" or "all" only when the universe is bounded, every segment was searched, and steps 1 to 5 passed.

## Read the citations

`output.grounding` is what makes an Agent run worth its price, so do not stop at `output.text`. Each entry is `{field, citations, confidence}`, where `field` is a path into the output such as `structured.companies[0].sourceUrl` and `confidence` is `low`, `medium`, `high`, or absent.

Flatten it into one line per citation:

```bash
RUN_ID="agent_run_..."
curl -sS --fail-with-body "https://api.exa.ai/agent/runs/$RUN_ID" \
  -H "x-api-key: $EXA_API_KEY" \
| jq -r '.output.grounding[]
    | .field as $field
    | (.confidence // "unrated") as $conf
    | .citations[]
    | [$field, $conf, .url, (.title // "")] | @tsv'
```

Two follow-ups that matter when you report the result. The second one only sees fields that hold a value, because `paths(scalars)` skips nulls — pair it with the null check above to cover the whole output.

```bash
# Fields the model itself rates as weak - verify these before quoting them.
jq -r '[.output.grounding[] | select(.confidence == "low") | .field] | unique[]' <<<"$RUN_JSON"

# Structured fields with no citation at all.
jq -r '
  ([.output.structured | paths(scalars) | map(tostring) | join(".")] | map("structured." + .)) as $fields
  | ([.output.grounding[].field]) as $grounded
  | $fields - $grounded | .[]
' <<<"$RUN_JSON"
```

## Continue a completed run

`previousRunId` carries context into a **new** run with its own ID. It does not reuse or resume the old run.

```bash
PREVIOUS_RUN_ID="agent_run_..."

curl -sS --fail-with-body -X POST "https://api.exa.ai/agent/runs" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $EXA_API_KEY" \
  --data "$(jq -n --arg p "$PREVIOUS_RUN_ID" '{
    query: "Find five more. Exclude every company already returned.",
    previousRunId: $p,
    effort: "medium"
  }')" | jq -r '.id'
```

The prior run must be `completed` and belong to the same team. Context carry-over is a hint, not a guarantee, so add `input.exclusion` when specific records must not come back.

## Stream events

Streaming holds the create request open and avoids polling. This block prints progress to stderr and the final result to stdout:

```bash
curl -sS --fail-with-body -N -X POST "https://api.exa.ai/agent/runs" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -H "x-api-key: $EXA_API_KEY" \
  --data "$(jq -n '{query: "Find five recently launched tools for evaluating AI agents.", effort: "medium"}')" \
| while IFS= read -r line; do
    case "$line" in
      event:*)
        EVENT="${line#event:}"
        EVENT="${EVENT# }"
        ;;
      data:*)
        DATA="${line#data:}"
        DATA="${DATA# }"
        case "$EVENT" in
          agent_run.created)
            jq -r '"run_id=" + .id' <<<"$DATA" >&2
            ;;
          agent_run.completed)
            jq '{stopReason, output, costDollars}' <<<"$DATA"
            break
            ;;
          agent_run.failed|agent_run.cancelled)
            jq '{status, error}' <<<"$DATA" >&2
            break
            ;;
        esac
        ;;
    esac
  done
```

Save the run ID from `agent_run.created` — that is your only handle if the stream drops.

Ignoring unknown event names is not optional politeness, it is required. The documented enum has five names, but a real run also emits `agent_run.search_trace`, `agent_run.output_item.added`, `agent_run.output_item.done`, `agent_run.function_call_arguments.done`, `agent_run.source.added`, and `agent_run.source.truncated`. Ignore `: keep-alive` comment lines too. Only `agent_run.completed`, `agent_run.failed`, and `agent_run.cancelled` are terminal.

Treat `agent_run.source.added` as a live preview, not a citation list — the terminal run's `output.grounding` is authoritative. Events that belong to the same research step share a `callId`, and some search traces arrive after the source they describe, so group by `callId` rather than by arrival order.

### Replay stored events

```bash
RUN_ID="agent_run_..."

# As paginated JSON. Follow nextCursor while hasMore is true.
curl -sS --fail-with-body "https://api.exa.ai/agent/runs/$RUN_ID/events?limit=100" \
  -H "x-api-key: $EXA_API_KEY" | jq '{hasMore, nextCursor, events: [.data[] | {id, event}]}'

# As SSE, skipping events you already handled.
curl -sS --fail-with-body -N "https://api.exa.ai/agent/runs/$RUN_ID/events" \
  -H "Accept: text/event-stream" \
  -H "Last-Event-ID: 12" \
  -H "x-api-key: $EXA_API_KEY"
```

Replay sends the events stored at request time and then closes. It does not follow a live run.

## List, cancel, delete

```bash
# Recover a lost run ID.
curl -sS --fail-with-body "https://api.exa.ai/agent/runs?limit=10" \
  -H "x-api-key: $EXA_API_KEY" \
| jq -r '.data[] | [.id, .status, .createdAt, (.request.query // "")] | @tsv'

RUN_ID="agent_run_..."

# Cancel a queued or running run.
curl -sS --fail-with-body -X POST "https://api.exa.ai/agent/runs/$RUN_ID/cancel" \
  -H "x-api-key: $EXA_API_KEY" | jq '{id, status, stopReason}'

# Delete a stored run. Cancel it first if it is still active. Deletion is permanent.
curl -sS --fail-with-body -X DELETE "https://api.exa.ai/agent/runs/$RUN_ID" \
  -H "x-api-key: $EXA_API_KEY" | jq .
```

## Handle errors

`curl --fail-with-body` gives a nonzero exit code on an HTTP error and still prints the JSON body, so you can read `.error.type`, `.error.code`, and `.error.message`. The codes are:

`INVALID_REQUEST`, `TEAM_NOT_FOUND`, `RUN_NOT_FOUND`, `PREVIOUS_RUN_NOT_FOUND`, `PREVIOUS_RUN_NOT_COMPLETED`, `CONCURRENCY_LIMIT_REACHED`, `INVALID_OUTPUT_SCHEMA`, `INVALID_DATA_SOURCE`, `TIMEOUT`, `SERVER_ERROR`.

`CONCURRENCY_LIMIT_REACHED` is the common one: your Agent concurrency limit is one fifth of your account QPS, which is **two active runs** on a default pay-as-you-go account. Wait for a run to finish rather than retrying in a tight loop.

Do not quietly swap Agent work for a plain search after an Agent error. Fix the request or report the failure — a single search answers a different question and the caller cannot tell.

## Zero Data Retention teams

If ZDR is enabled for the team, three things in this skill stop working: `previousRunId` is rejected, events are not stored so replay returns nothing, and a create call with `dataSources` returns `400`. Consume ZDR output from the live SSE stream, or poll within ten minutes of completion — after that the result is deleted.

## Official references

- https://exa.ai/docs/reference/agent-api/overview
- https://exa.ai/docs/reference/agent-api-guide
- https://exa.ai/docs/reference/agent-api/create-a-run
- https://exa.ai/docs/reference/agent-api/get-a-run
- https://exa.ai/docs/reference/agent-api/list-runs
- https://exa.ai/docs/reference/agent-api/list-run-events
- https://exa.ai/docs/reference/agent-api/cancel-a-run
- https://exa.ai/docs/reference/agent-api/delete-a-run
- https://exa.ai/docs/reference/agent-api/connect/overview

_**Plan the run first**, **Agent or a script**, and **Check coverage before you report** adapt the `exa-agent` skill in exa-labs/exa-mcp-server (MIT) at `81d687e` (2026-11-21), the source of the `exa@claude-plugins-official` plugin._
