# gcx configuration for self-hosted Grafana OSS

gcx uses named stacks and contexts. A stack holds one Grafana connection. A
context points to a stack and can hold default datasource UIDs. One context is
current. Use `--context <name>` to select another context for one command.

Use `gcx config view` for a redacted view and `gcx config check` for validation
and a live connection check. Never request unredacted output or read the config
file directly.

## Config file selection

`--config <path>` or `GCX_CONFIG` selects one explicit file and bypasses normal
layering. Otherwise, gcx loads existing files from lower to higher priority:

| Priority | Source |
|---|---|
| 3 | System config: `$XDG_CONFIG_DIRS/gcx/config.yaml` or platform equivalent |
| 2 | User config: `$HOME/.config/gcx/config.yaml`, then platform fallback |
| 1 | Repository config: `.gcx.yaml` in the current directory |

If no file exists, gcx creates one at the standard location with a `default`
context.

Same-named stacks are atomic. A higher-priority source replaces the complete
stack. Context references and datasource defaults can merge. Review a
repository config before selecting it because it can change the server and TLS
settings used with runtime credentials.

```bash
gcx --config /path/to/config.yaml config check
# or
GCX_CONFIG=/path/to/config.yaml gcx config check
```

## Supported config paths

Use `gcx config set <path> <value>`. Missing stack and context entries are
created automatically. Paths are absolute from a top-level section. They do
not resolve relative to the current context.

### Grafana connection

| Path | Purpose |
|---|---|
| `stacks.<name>.grafana.server` | Grafana server URL |
| `stacks.<name>.grafana.token` | Service account token |
| `stacks.<name>.grafana.user` | Basic-auth username |
| `stacks.<name>.grafana.password` | Basic-auth password |
| `stacks.<name>.grafana.org-id` | Numeric organization ID |

The token takes precedence over username and password.

### Context and datasource defaults

| Path | Purpose |
|---|---|
| `contexts.<name>.stack` | Stack used by this context |
| `contexts.<name>.datasources.<kind>` | Default datasource UID for a kind such as `prometheus` or `loki` |
| `current-context` | Active context name |

Example:

```bash
read -rsp "Grafana service account token: " GRAFANA_TOKEN; echo
gcx config set stacks.production.grafana.server https://grafana.example.com
gcx config set stacks.production.grafana.token "$GRAFANA_TOKEN"
unset GRAFANA_TOKEN
gcx config set stacks.production.grafana.org-id 1
gcx config set contexts.production.stack production
gcx config set contexts.production.datasources.prometheus <uid>
gcx config use-context production
gcx config check
```

Remove a field or entry with `gcx config unset`:

```bash
gcx config unset contexts.old
gcx config unset stacks.old
gcx config unset stacks.production.grafana.password
```

## Token-based login

Use `gcx login` to create or update a context, save a service account token,
and select the context:

```bash
read -rsp "Grafana service account token: " GRAFANA_TOKEN; echo
gcx login production --server https://grafana.example.com \
  --token "$GRAFANA_TOKEN" --org-id 1 --yes
unset GRAFANA_TOKEN
gcx config check
```

Do not put the token value directly in shell history. For automation, inject it
from the platform secret store.

## Organization namespace

The self-hosted API namespace comes from `grafana.org-id`. Organization ID `N`
maps to namespace `org-N`. The default Grafana organization is usually `1`, but
confirm the target organization's numeric ID before a write operation.

```bash
gcx config set stacks.production.grafana.org-id 1
gcx config check
```

If gcx reports a missing namespace, check all three items:

1. `gcx config current-context` shows the intended context.
2. The context points to the intended stack in redacted `gcx config view`
   output.
3. That stack has a non-zero `grafana.org-id`.

## Context management

```bash
# Redacted inspection
gcx config view

# Show the active context
gcx config current-context

# Change the active context
gcx config use-context production

# Select a context for one command
gcx --context staging resources get dashboards
```

Before write operations, run:

```bash
gcx config current-context
gcx config check
```

## Environment variables

Environment variables patch the selected context at load time. They do not
change the config file. Context selection happens before these overrides.

| Variable | Selected-stack override | Type |
|---|---|---|
| `GRAFANA_SERVER` | `grafana.server` | string |
| `GRAFANA_TOKEN` | `grafana.token` | string |
| `GRAFANA_USER` | `grafana.user` | string |
| `GRAFANA_PASSWORD` | `grafana.password` | string |
| `GRAFANA_ORG_ID` | `grafana.org-id` | integer |
| `GRAFANA_TLS_CERT_FILE` | `grafana.tls.cert-file` | string |
| `GRAFANA_TLS_KEY_FILE` | `grafana.tls.key-file` | string |
| `GRAFANA_TLS_CA_FILE` | `grafana.tls.ca-file` | string |

Token authentication takes precedence over basic authentication when both are
present.

```bash
GRAFANA_SERVER=https://grafana.example.com \
GRAFANA_TOKEN="$GRAFANA_TOKEN" \
GRAFANA_ORG_ID=1 \
gcx --context production resources get dashboards -o json
```

Check for stale environment values when gcx connects to the wrong server or a
new stored token still returns 401.

## TLS

| Path | Purpose |
|---|---|
| `stacks.<name>.grafana.tls.insecure-skip-verify` | Disable server certificate validation |
| `stacks.<name>.grafana.tls.ca-data` | Base64-encoded custom CA bundle |
| `stacks.<name>.grafana.tls.cert-data` | Base64-encoded mTLS client certificate |
| `stacks.<name>.grafana.tls.key-data` | Base64-encoded mTLS client key |

Prefer a trusted custom CA:

```bash
gcx config set stacks.production.grafana.tls.ca-data <base64-encoded-pem>
```

Use file-based environment overrides when an external secret manager supplies
mTLS files. A repository config cannot authorize an external client key. Select
and review the repository config explicitly before combining it with runtime
credentials.

Use certificate validation bypass only for local development:

```bash
gcx config set stacks.local.grafana.tls.insecure-skip-verify true
gcx config unset stacks.local.grafana.tls.insecure-skip-verify
```

## Datasource defaults

Find datasource UIDs:

```bash
gcx datasources list -o json
```

Set defaults on each context that needs them:

```bash
gcx config set contexts.production.datasources.prometheus <prometheus-uid>
gcx config set contexts.production.datasources.loki <loki-uid>
```

## Security rules

- Use one service account per automation boundary.
- Give the account the minimum required role.
- Inject automation tokens from a secret store.
- Do not put tokens or passwords directly in shell history.
- Use only the redacted `gcx config view` output.
- Do not print, copy, or inspect the config file directly.
- Do not log environment variables that contain credentials.
- Review repository config before it can select a server or TLS setting.
- Do not disable TLS certificate validation in production.

## Troubleshooting

### `gcx config check` reports an empty context

```bash
gcx config current-context
gcx config view
gcx config set current-context <context-name>
gcx config check
```

### 401 Unauthorized

Replace the token and check for an environment override:

```bash
read -rsp "Grafana service account token: " GRAFANA_TOKEN; echo
gcx config set stacks.<name>.grafana.token "$GRAFANA_TOKEN"
unset GRAFANA_TOKEN
gcx config check
```

A stale `GRAFANA_TOKEN` overrides the stored token.

### 403 Forbidden

The token is valid, but the service account lacks the required role. Assign the
minimum Viewer, Editor, or Admin role required for the operation.

### Missing namespace

```bash
gcx config set stacks.<name>.grafana.org-id 1
gcx config check
```

Confirm that the selected context uses that stack and that the numeric ID is
for the intended Grafana organization.

### Connection refused or timeout

```bash
gcx config view
curl -I https://grafana.example.com/api/health
```

Check the server URL, `GRAFANA_SERVER`, DNS, firewall, reverse proxy, and VPN.
Run the test from the same machine that runs gcx.

### TLS error

Supply the correct CA bundle and, when required, the matching mTLS certificate
and key. Do not disable certificate validation in production.
