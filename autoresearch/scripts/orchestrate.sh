#!/usr/bin/env bash
# orchestrate.sh — the autoresearch safety gate.
#
#   screen-cmd <shell-string>  → "ok" exit 0 | "refuse" exit 1 safety gate
#
# Run before any derived or persisted shell command is executed. Prints "ok"
# to allow, "refuse" to block. Pure and CI-usable via exit codes.
set -uo pipefail

# ---------------------------------------------------------------------------
# screen-cmd: safety gate for shell strings before execution.
# Prints "ok" / "refuse". Anchored DB-host allowlist: only localhost,
# 127.0.0.1, or a plain hostname (no dots) with a _test or _ci dbname suffix.
# Bare substring "test" inside words like "latest" or "precision" must NOT qualify.
# ---------------------------------------------------------------------------
screen-cmd() {
  local cmd="${1:?usage: screen-cmd <shell-string>}"

  # rm with recursive AND force, in any flag arrangement: bundled (-rf/-Rf/-fr),
  # separate (-r -f), or long (--recursive --force). Both flags must be present.
  # The optional path prefix catches path-qualified invocations (/bin/rm, ./rm,
  # /usr/local/bin/rm) that a bare command-name anchor would miss.
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])([^[:space:]]*/)?rm([[:space:]]|$)'; then
    local rm_rec=0 rm_force=0
    printf '%s' "$cmd" | grep -qE -- '(^|[[:space:]])-[a-zA-Z]*[rR]|--recursive' && rm_rec=1
    printf '%s' "$cmd" | grep -qE -- '(^|[[:space:]])-[a-zA-Z]*[fF]|--force'     && rm_force=1
    if [[ "$rm_rec" -eq 1 && "$rm_force" -eq 1 ]]; then
      echo "refuse"; return 1
    fi
  fi

  # curl/wget piped to an interpreter (sh/bash/zsh/dash/fish/ksh/python/perl/ruby/
  # node/php), including a path-qualified one (| /bin/bash). Enumerated interpreters
  # rather than "refuse any curl pipe" so a legitimate derived predicate that pipes
  # curl output to a parser (jq/grep/awk) is not falsely refused.
  if printf '%s' "$cmd" | grep -qE '(curl|wget)[^|]*\|[[:space:]]*([^[:space:]]*/)?(sh|bash|zsh|dash|fish|ksh|python[0-9.]*|perl|ruby|node|php)([[:space:]]|$)'; then
    echo "refuse"; return 1
  fi

  # curl/wget routed through xargs into an interpreter. The xargs wrapper sidesteps the
  # direct pipe matcher above, so a remote payload still reaches a shell.
  if printf '%s' "$cmd" | grep -qE '(curl|wget)[^|]*\|.*xargs.*[[:space:]]([^[:space:]]*/)?(sh|bash|zsh|dash|ksh|python[0-9.]*|perl|ruby|node|php)([[:space:]]|$)'; then
    echo "refuse"; return 1
  fi

  # Output piped to netcat exfiltrates data off-host.
  if printf '%s' "$cmd" | grep -qE '\|[[:space:]]*([^[:space:]]*/)?(nc|ncat|netcat)([[:space:]]|$)'; then
    echo "refuse"; return 1
  fi

  # Raw block-device write — dd target or shell redirect onto a disk device wipes it.
  # Scoped to real device families (incl. SD/eMMC mmcblk, mdadm md, device-mapper dm-)
  # so dd/redirect to /dev/null or a regular file stays ok.
  if printf '%s' "$cmd" | grep -qE '(of=|>[[:space:]]*)/dev/(sd|hd|vd|nvme|disk|mapper|loop|xvd|mmcblk|md|dm-)'; then
    echo "refuse"; return 1
  fi

  # Filesystem format destroys everything on a partition. Optional path prefix catches a
  # path-qualified invocation (/sbin/mkfs.ext4) that a bare-name anchor would miss.
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])([^[:space:]]*/)?(mkfs|mke2fs)'; then
    echo "refuse"; return 1
  fi

  # find ... -delete mass-removes matched files. Both tokens required so a plain find
  # search (no -delete) is not refused; optional path prefix catches /usr/bin/find.
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])([^[:space:]]*/)?find([[:space:]]|$)' \
     && printf '%s' "$cmd" | grep -qE '[[:space:]]-delete([[:space:]]|$)'; then
    echo "refuse"; return 1
  fi

  # shred overwrites then unlinks — irrecoverable.
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])([^[:space:]]*/)?shred([[:space:]]|$)'; then
    echo "refuse"; return 1
  fi

  # truncate to zero size destroys file contents in place. Non-zero sizes are allowed.
  # Optional path prefix catches /usr/bin/truncate; size matcher covers -s 0, -s0,
  # --size 0, and --size=0.
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])([^[:space:]]*/)?truncate([[:space:]]|$)' \
     && printf '%s' "$cmd" | grep -qE '(-s[[:space:]]*0|--size[[:space:]]*=?[[:space:]]*0)([[:space:]]|$)'; then
    echo "refuse"; return 1
  fi

  # Recursive chmod to a zero mode locks an entire tree out of access. Scoped to the
  # zero lock-out (000/00/0 octal short forms) so ordinary recursive permission changes
  # are not refused; optional path prefix catches /bin/chmod.
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])([^[:space:]]*/)?chmod([[:space:]]|$)' \
     && printf '%s' "$cmd" | grep -qE '(-R|--recursive)([[:space:]]|$)' \
     && printf '%s' "$cmd" | grep -qE '(^|[[:space:]])(000|00|0)([[:space:]]|$)'; then
    echo "refuse"; return 1
  fi

  # Fork bomb pattern
  if printf '%s' "$cmd" | grep -qF ':(){ :|:'; then
    echo "refuse"; return 1
  fi
  if printf '%s' "$cmd" | grep -qE ':\(\)\{'; then
    echo "refuse"; return 1
  fi

  # AWS credential patterns (key IDs start with AKIA, secret keys are 40-char base64)
  if printf '%s' "$cmd" | grep -qE 'AKIA[0-9A-Z]{16}'; then
    echo "refuse"; return 1
  fi

  # PASSWORD= credential pattern
  if printf '%s' "$cmd" | grep -qE 'PASSWORD[[:space:]]*='; then
    echo "refuse"; return 1
  fi

  # Private key headers — pattern starts with dashes so pass -- to avoid flag misparse
  if printf '%s' "$cmd" | grep -qE -- 'BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY'; then
    echo "refuse"; return 1
  fi

  # Database URL safety: extract host and dbname from postgres:// or postgresql:// URIs
  # Pattern: postgres(ql)://user:pass@HOST/DBNAME or postgres(ql)://HOST/DBNAME
  if printf '%s' "$cmd" | grep -qE 'postgres(ql)?://'; then
    # Extract the host portion (after @ or after ://)
    local db_host db_name
    db_host=$(printf '%s' "$cmd" \
      | grep -oE 'postgres(ql)?://[^[:space:]]+' \
      | sed -E 's|postgres(ql)?://([^@]+@)?([^/:]+)[:/].*|\3|')
    db_name=$(printf '%s' "$cmd" \
      | grep -oE 'postgres(ql)?://[^[:space:]]+' \
      | sed -E 's|postgres(ql)?://[^/]*/([^?[:space:]]+).*|\2|')

    # Allowed hosts: localhost, 127.0.0.1, or a single-label hostname (no dots = container)
    local host_ok=0
    if [[ "$db_host" == "localhost" || "$db_host" == "127.0.0.1" ]]; then
      host_ok=1
    elif printf '%s' "$db_host" | grep -qvE '\.'; then
      # No dots = plain container hostname → allowed
      host_ok=1
    fi

    if [[ "$host_ok" -eq 0 ]]; then
      # Non-allowlisted host: dbname must end with _test or _ci (anchored suffix, not substring)
      if printf '%s' "$db_name" | grep -qE '_test$|_ci$'; then
        echo "ok"; return 0
      fi
      echo "refuse"; return 1
    fi
  fi

  echo "ok"; return 0
}

case "${1:-}" in
  screen-cmd) shift; screen-cmd "$@" ;;
  *) echo "usage: $0 screen-cmd <shell-string>" >&2; exit 64 ;;
esac
