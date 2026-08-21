---
name: setup-gcx
description: >
  Sets up gcx for self-hosted Grafana OSS: installation, token-based login,
  context selection, organization namespaces, datasource defaults, on-premise
  environment overrides, TLS, and connection troubleshooting. Use when
  installing gcx, connecting gcx to a self-hosted Grafana instance, or when gcx
  commands fail with auth, connectivity, context, or namespace errors.
---

# Set up gcx for self-hosted Grafana OSS

Use a named context for each Grafana environment. gcx stores the Grafana
connection in a named stack and binds the context to that stack.

For all supported on-premise fields and context patterns, see
[configuration.md](references/configuration.md).

## 1. Install gcx

Check for an existing installation:

```bash
gcx --version
```

If gcx is not installed, build it from source. This requires
[git](https://git-scm.com/) and a recent [Go](https://go.dev/) toolchain:

```bash
tmp=$(mktemp -d) && git clone --depth 1 https://github.com/grafana/gcx.git "$tmp" && (cd "$tmp" && go install ./cmd/gcx) && rm -rf "$tmp"
```

Verify the installation:

```bash
gcx --version
```

## 2. Log in with a service account token

Create a service account in Grafana. Give it only the role that its gcx work
needs. Use its token to create and select a context:

```bash
read -rsp "Grafana service account token: " GRAFANA_TOKEN; echo
gcx login onprem --server https://grafana.example.com \
  --token "$GRAFANA_TOKEN" --org-id 1 --yes
unset GRAFANA_TOKEN
```

Replace `onprem`, the server URL, and the organization ID. The default Grafana
organization ID is usually `1`.

Do not put a real token directly in a command that shell history records.

### Manual context setup

Use this path when the stack and context must be created one field at a time:

```bash
read -rsp "Grafana service account token: " GRAFANA_TOKEN; echo
gcx config set stacks.onprem.grafana.server https://grafana.example.com
gcx config set stacks.onprem.grafana.token "$GRAFANA_TOKEN"
unset GRAFANA_TOKEN
gcx config set stacks.onprem.grafana.org-id 1
gcx config set contexts.onprem.stack onprem
gcx config use-context onprem
```

The token takes precedence if the same stack also has a username and password.

## 3. Check the context and connection

```bash
gcx config current-context
gcx config view
gcx config check
```

`gcx config view` redacts secrets by default. Never request unredacted output,
print the config file, or copy stored credentials into logs or chat.

For self-hosted Grafana, `grafana.org-id` supplies the API namespace. An org ID
of `1` maps to `org-1`. Set the numeric organization ID when gcx reports a
missing namespace:

```bash
gcx config set stacks.onprem.grafana.org-id 1
gcx config check
```

## 4. Set default datasources

List datasource UIDs:

```bash
gcx datasources list -o json
```

Set the defaults on the context:

```bash
gcx config set contexts.onprem.datasources.prometheus <prometheus-uid>
gcx config set contexts.onprem.datasources.loki <loki-uid>
```

Commands that support `-d` can then use the matching context default.

## 5. Use more than one environment

Create one stack and context per environment. Select one permanently or for one
command:

```bash
gcx config use-context staging
gcx --context production resources get dashboards
```

Inspect the selected context before a write operation:

```bash
gcx config current-context
gcx config check
```

## 6. Use environment overrides

Environment variables override fields on the selected context at runtime. They
do not change the config file.

| Variable | Runtime override |
|---|---|
| `GRAFANA_SERVER` | Grafana server URL |
| `GRAFANA_TOKEN` | Service account token |
| `GRAFANA_USER` | Basic-auth username |
| `GRAFANA_PASSWORD` | Basic-auth password |
| `GRAFANA_ORG_ID` | Numeric Grafana organization ID |
| `GRAFANA_TLS_CERT_FILE` | mTLS client certificate file |
| `GRAFANA_TLS_KEY_FILE` | mTLS client key file |
| `GRAFANA_TLS_CA_FILE` | Custom CA bundle file |

Select the context before gcx applies these values. Use `--context` for one
command when the current context is not the required target:

```bash
GRAFANA_SERVER=https://grafana.example.com \
GRAFANA_TOKEN="$GRAFANA_TOKEN" \
GRAFANA_ORG_ID=1 \
gcx --context onprem resources get dashboards -o json
```

To select one explicit config file:

```bash
gcx --config /path/to/config.yaml resources get dashboards
# or
export GCX_CONFIG=/path/to/config.yaml
```

Review a repository `.gcx.yaml` before use. Select it explicitly with
`--config .gcx.yaml` or `GCX_CONFIG=.gcx.yaml`. Do not let a repository file
choose a credential destination without review.

## 7. Configure TLS when required

Prefer a trusted custom CA in production:

```bash
gcx config set stacks.onprem.grafana.tls.ca-data <base64-encoded-pem>
```

For mTLS, use the file-based environment overrides shown above or the supported
TLS fields in [configuration.md](references/configuration.md#tls).

Use certificate verification bypass only for local development:

```bash
gcx config set stacks.onprem.grafana.tls.insecure-skip-verify true
```

## Troubleshooting

### Wrong or empty context

```bash
gcx config current-context
gcx config view
gcx config set current-context <context-name>
gcx config check
```

An environment override applies only after gcx selects a context.

### Missing namespace

Set the organization ID on the stack used by the active context:

```bash
gcx config set stacks.<name>.grafana.org-id 1
gcx config check
```

Confirm that the active context points to `<name>` with the redacted
`gcx config view` output.

### 401 Unauthorized

Replace an invalid or expired token:

```bash
read -rsp "Grafana service account token: " GRAFANA_TOKEN; echo
gcx config set stacks.<name>.grafana.token "$GRAFANA_TOKEN"
unset GRAFANA_TOKEN
gcx config check
```

Check for a stale `GRAFANA_TOKEN` override. Runtime environment values take
precedence over stored context values.

### 403 Forbidden

The token is valid but its service account lacks permission. Assign the minimum
Grafana role required for the command. Use Viewer for read-only work. Use
Editor or Admin only when the operation requires it.

### Connection refused or timeout

1. Check the redacted configuration with `gcx config view`.
2. Test the endpoint from the same machine:

   ```bash
   curl -I https://grafana.example.com/api/health
   ```

3. Check DNS, firewall, reverse proxy, and VPN access.
4. Check whether `GRAFANA_SERVER` points to a different host.

### TLS certificate error

Use the correct CA bundle or client certificate. Do not bypass certificate
validation in production. If a development bypass is necessary, limit it to
the affected stack and remove it after the test:

```bash
gcx config unset stacks.<name>.grafana.tls.insecure-skip-verify
```
