---
name: cf-cli
description: Use the cf CLI, Cloudflare's unified technical-preview CLI (`npm i -g cf`, `npx cf`) that exposes Cloudflare API operations Wrangler does not have commands for. Covers the agent discovery protocol (`cf cli search`, `<cmd> --help`, `cf schema`), token and OAuth-profile auth, JSON-by-default output, `--dry-run` on mutations, and known beta gaps and plan gates. Use when a Cloudflare task has no Wrangler command, when you need to inspect or call a raw Cloudflare API operation from the shell, or when setting up cf auth on this machine.
---

# cf CLI

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

`cf` is the technical preview of the unified Cloudflare CLI: one consistent command surface over Cloudflare's ~3,000 API operations, built for agents as much as humans. It is early and covers a subset of products, so treat it as the escape hatch for everything Wrangler does not do.

Division of labour: Wrangler still owns Worker dev and deploy. `cf` owns the rest of the account (DNS, tokens, R2, Containers, AI Gateway, and so on).

## Discovery protocol

Every `cf` run prints a "STOP: AGENT COMMAND DISCOVERY" banner. It is guidance, not an error. Follow it:

1. Search by intent, never guess names:

   ```
   cf cli search "deploy a container application"
   ```

   Returns exactly five JSON matches with `command` and `summary`. Refine the wording rather than repeating a similar search.

2. Read the chosen command's flags:

   ```
   cf containers applications create --help
   ```

3. Inspect the exact API request it makes, replacing the leading `cf` with `cf schema`:

   ```
   cf schema containers applications list
   ```

   Returns `operationId`, `httpMethod`, `path`, `pathParams`, `queryParams`, `requestBodyFields`.

Do not chain nested `--help` calls to explore the tree, and keep search queries anonymous: describe the action and resource type only. Never put names, emails, domains, account or resource IDs, or tokens in a `cf cli search` query.

## Conventions (enforced by Cloudflare)

- `get`, never `info`.
- `--force`, never `--skip-confirmations`.
- JSON is the default output. This beta has no `--json` flag; passing it makes the command print its help instead of running.
- `--dry-run` on mutating commands validates and shows the change without applying it. Use it before any create, edit, or delete.
- Global flags: `-q/--quiet`, `-z/--zone` (ID or domain, overrides `CLOUDFLARE_ZONE_ID`), `--profile`, `-m/--mode`, `--local`, `--persist-to`.
- Bare command groups print their subcommands as help. `cf workers scripts` has only `search`, so read the group output before assuming a `list` exists.

## Authentication

Two paths:

**API token via environment (preferred for scripts and agents).** `cf` reads `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. If `~/.config/hookme/account.env` exists it keeps them as `TF_VAR_*`, so map them with this skill's own script; if it does not, export the two names yourself:

```
. scripts/cf-env.sh
cf auth whoami
```

`scripts/cf-env.sh` reads `~/.config/hookme/account.env` (override with `CF_ENV_FILE`) and exports only those two names. Without a token, wrangler falls back to an OAuth login that points at a different Cloudflare account.

**OAuth profiles (interactive, directory-bound).** `cf auth login`, `cf auth create <name>`, `cf auth activate <name> [dir]`, `cf auth list`, `cf auth whoami`, `cf auth logout`. The OAuth login is a different Cloudflare account from the company token, so do not use it to reach the company account.

A `401` whose hint says "Try running: cf auth login" is usually not an auth problem. Read the API error body first: it often names a plan or permission gate.

## Gotchas

- Plan gates surface as API errors, not clean messages. Example: Containers returns `401 Unauthorized: You do not have access to Cloudflare Containers. Deploying containers requires the Workers Paid plan.`
- Beta coverage is partial. Search first; if nothing matches, the operation may exist in the REST API but not yet in `cf`.
- `cf cli telemetry` configures anonymous usage telemetry.
- Local Explorer mirrors local simulated resources (KV, R2, D1, Durable Objects, Workflows) at `/cdn-cgi/explorer/api` while running Wrangler or the Vite plugin; `--local` with `--persist-to` points `cf` at that local simulation instead of the API.

## Worked examples

```
# Find the command for a task
cf cli search "set a secret for a worker"

# Learn its flags, then the exact API request
cf workers secrets update --help
cf schema workers secrets update

# Read-only check that auth and account are right
cf auth whoami

# Preview a mutation before applying it
cf <group> <resource> create --dry-run ...
```
