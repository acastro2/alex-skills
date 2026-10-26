#!/bin/sh
# Put the Cloudflare token where `cf` and wrangler look for it.
#
# The credentials file stores Terraform-style names; `cf` and wrangler read different ones.
# Getting this wrong is quiet: without a token, wrangler falls back to an OAuth login that
# points at a different Cloudflare account.
#
#   . scripts/cf-env.sh                  # uses ~/.config/hookme/account.env
#   CF_ENV_FILE=/path/to/env . scripts/cf-env.sh
#
# Reads only the two keys below; every other line in the file is ignored.
set -eu

ENV_FILE="${CF_ENV_FILE:-$HOME/.config/hookme/account.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "cf-env: $ENV_FILE not found; export CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID yourself" >&2
  return 1 2>/dev/null || exit 1
fi

while IFS='=' read -r key value; do
  value=$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//')
  case "$key" in
    TF_VAR_cloudflare_api_token) CLOUDFLARE_API_TOKEN="$value" ;;
    TF_VAR_cloudflare_account_id) CLOUDFLARE_ACCOUNT_ID="$value" ;;
  esac
done < "$ENV_FILE"

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] || [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  echo "cf-env: $ENV_FILE has no TF_VAR_cloudflare_api_token or TF_VAR_cloudflare_account_id" >&2
  return 1 2>/dev/null || exit 1
fi

export CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID
