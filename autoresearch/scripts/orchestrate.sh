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
  # A control byte (other than tab and newline) can confuse the readers below, and a
  # backslash before a newline joins two lines into one word (r\<newline>m is rm).
  # Both are refused as a whole kind.
  if printf '%s' "$cmd" | tr -d '\t\n' | LC_ALL=C grep -q '[[:cntrl:]]' \
    || [[ "$cmd" == *\\$'\n'* ]]; then
    echo "refuse"; return 1
  fi
  # The shell drops quotes and backslashes before it runs a name, so 'rm' and \rm are rm.
  local bare=${cmd//[\"\'\\]/}
  # $IFS and brace lists ({rm,-rf,/}) turn into spaces when bash runs them.
  bare=${bare//\$\{IFS\}/ }
  bare=${bare//\$IFS/ }
  bare=${bare//[\{\},]/ }

  # This check cannot expand variables, substitutions or brace lists, and each one can
  # build a name (${X}m, $X, r``m, `printf rm`, $'\x72m', r{m,}). So it refuses the whole
  # kind: any backtick, and any $ outside single quotes unless a closing double quote, a
  # space or the line end follows it (grep "ok$" is fine). A brace list outside quotes is
  # refused too. The scan below reads quotes the way bash does: a backslash escapes the
  # next character, and a single quote inside double quotes is just a character.
  # $"..." is a quoted string to bash, so it is marked like a backtick and refused.
  # Each quoted part is also kept (joined by \002) so a script passed to a nested shell
  # can be checked on its own.
  local scan live unquoted parts
  scan=$(printf '%s' "$cmd" | awk -v sq="'" -v dq='"' -v bs='\\' 'BEGIN { RS = "\001" } {
    q = ""; a = ""; b = ""; part = ""; parts = ""
    for (i = 1; i <= length($0); i++) {
      c = substr($0, i, 1)
      if (q == sq) { if (c == sq) { q = ""; a = a c; b = b c; parts = parts part "\002"; part = "" } else part = part c; continue }
      if (c == bs) { i++; a = a "_"; if (q == "") b = b "_"; else part = part c substr($0, i, 1); continue }
      if (q == dq) { a = a c; if (c == dq) { q = ""; b = b c; parts = parts part "\002"; part = "" } else part = part c; continue }
      if (c == "$" && substr($0, i + 1, 1) == dq) a = a "`"
      if (c == sq || c == dq) q = c
      a = a c; b = b c
    }
    printf "%s\001%s\001%s", a, b, parts part
  }')
  live=${scan%%$'\001'*}
  unquoted=${scan#*$'\001'}
  parts=${unquoted#*$'\001'}
  unquoted=${unquoted%%$'\001'*}
  if printf '%s' "$live" | grep -qE '`|\$[^"[:space:]]' \
    || printf '%s' "$unquoted" | grep -qE '\{[^[:space:]{}]*(,|\.\.)[^[:space:]{}]*\}'; then
    echo "refuse"; return 1
  fi

  # A glob in a command name (r?, /bin/r[m], sudo r*) can match any program, so a glob
  # in the first word of a command, after assignments, reserved words, flags and
  # numbers, is refused. After a launcher, every later word is checked, because an
  # option value (sudo -u root) can come before the name. Globs in arguments
  # (ls *.txt) and the test commands [ and [[ stay fine.
  # Every line is read, and a redirect target (>x, 2>/dev/null) is dropped first so it
  # cannot stand in for the command name.
  if printf '%s' "$unquoted" | awk '{
    line = $0; gsub(/[0-9]*[<>]+[&|]?[[:space:]]*[^[:space:];&|(){}<>]*/, " ", line)
    n = split(line, segs, /[;&|(){}<>]/)
    for (s = 1; s <= n; s++) {
      w = split(segs[s], words, /[[:space:]]+/)
      launched = 0
      for (k = 1; k <= w; k++) {
        x = words[k]
        if (x == "" || x ~ /^[A-Za-z_][A-Za-z0-9_]*=/ || x ~ /^-/ || x ~ /^[0-9]+$/) continue
        if (x ~ /^(if|then|else|elif|do|while|until|!)$/) continue
        y = x; sub(/^[^[:space:]]*[\/]/, "", y)
        if (y ~ /^(sudo|doas|env|exec|command|builtin|nohup|time|nice|ionice|timeout|xargs|stdbuf|chrt|taskset|eval)$/) { launched = 1; continue }
        if (x == "[" || x == "[[") break
        if (x ~ /[*?[]/) found = 1
        if (!launched) break
      }
    }
  }
  END { exit !found }'; then
    echo "refuse"; return 1
  fi

  # A shell or eval runs its quoted script as a new command, so each quoted part is
  # screened on its own too: bash -c 'X=rm; $X -rf /' and eval 'r? -rf /' are seen.
  # The outer shell drops the backslash in \$ and \`, so the inner script sees a live
  # expansion; those are refused outright when a nested shell is present.
  if printf '%s' "$bare" | grep -qE '(^|[[:space:];&|(){`<>])([^[:space:];&|(){`<>]*/)?(eval|sh|bash|zsh|dash|ksh|fish|source|su)([[:space:];&|()<>]|$)' \
    || printf '%s' "$bare" | grep -qE '(^|[;&|(){`])[[:space:]]*\.[[:space:]]'; then
    if [[ "$cmd" == *'\$'* || "$cmd" == *'\`'* ]]; then echo "refuse"; return 1; fi
    local part
    while IFS= read -r -d $'\002' part; do
      [[ -n "${part//[[:space:]]/}" ]] || continue
      screen-cmd "$part" >/dev/null || { echo "refuse"; return 1; }
    done <<< "$parts"$'\002'
  fi

  # env -S splits one argument into a new command line that the matchers cannot read.
  if printf '%s' "$bare" | grep -qE '(^|[[:space:];&|(){`<>])([^[:space:];&|(){`<>]*/)?env([[:space:]]+[^[:space:];&|()<>]+)*[[:space:]]+(-[a-zA-Z]*S|--split-string)'; then
    echo "refuse"; return 1
  fi

  # Each command matcher below starts at a space, ; & | ( ) { ` $ < or >, so `true;rm -rf /`
  # and `$(rm -rf ~)` are seen too. Flags are read from $bare, so rm "-rf" / is too.
  # rm with recursive AND force, in any flag arrangement: bundled (-rf/-Rf/-fr),
  # separate (-r -f), or long (--recursive --force). Both flags must be present.
  # The optional path prefix catches path-qualified invocations (/bin/rm, ./rm,
  # /usr/local/bin/rm) that a bare command-name anchor would miss.
  if printf '%s' "$bare" | grep -qE '(^|[[:space:];&|(){`\\$<>])([^[:space:];&|(){`<>]*/)?rm([[:space:];&|()<>]|$)'; then
    local rm_rec=0 rm_force=0
    printf '%s' "$bare" | grep -qE -- '(^|[[:space:]])-[a-zA-Z]*[rR]|(^|[[:space:]])--r(e(c(u(r(s(i(ve?)?)?)?)?)?)?)?([^[:alnum:]_-]|$)' && rm_rec=1
    printf '%s' "$bare" | grep -qE -- '(^|[[:space:]])-[a-zA-Z]*[fF]|(^|[[:space:]])--f(o(r(ce?)?)?)?([^[:alnum:]_-]|$)'     && rm_force=1
    if [[ "$rm_rec" -eq 1 && "$rm_force" -eq 1 ]]; then
      echo "refuse"; return 1
    fi
  fi

  # curl/wget piped to an interpreter (sh/bash/zsh/dash/fish/ksh/python/perl/ruby/
  # node/php), including a path-qualified one (| /bin/bash). Enumerated interpreters
  # rather than "refuse any curl pipe" so a legitimate derived predicate that pipes
  # curl output to a parser (jq/grep/awk) is not falsely refused.
  if printf '%s' "$bare" | grep -qE '(curl|wget)[^|]*\|[[:space:]]*([^[:space:]]*/)?(sh|bash|zsh|dash|fish|ksh|python[0-9.]*|perl|ruby|node|php)([[:space:];&|()<>]|$)'; then
    echo "refuse"; return 1
  fi

  # curl/wget piped through a launcher (sudo, env, exec, ...) into an interpreter.
  if printf '%s' "$bare" | grep -qE '(curl|wget)[^|]*\|[[:space:]]*(sudo|doas|env|exec|command|nohup|time)([[:space:]]+[^[:space:]|]+)*[[:space:]]+([^[:space:]]*/)?(sh|bash|zsh|dash|fish|ksh|python[0-9.]*|perl|ruby|node|php)([[:space:];&|()<>]|$)'; then
    echo "refuse"; return 1
  fi

  # A remote payload run without a pipe: bash <(curl ...), source <(curl ...),
  # bash -c "$(curl ...)", eval "$(curl ...)".
  if printf '%s' "$bare" | grep -qE '((sh|bash|zsh|dash|fish|ksh|python[0-9.]*|perl|ruby|node|php)|source|\.)[[:space:]]+(<[[:space:]]*)?<\([[:space:]]*(curl|wget)'; then
    echo "refuse"; return 1
  fi
  if printf '%s' "$bare" | grep -qE '((sh|bash|zsh|dash|fish|ksh|python[0-9.]*|perl|ruby|node|php)([[:space:]]+([^[:space:];&|]|[<>]&|&>)+)*[[:space:]]+-[a-zA-Z]*c[a-zA-Z]*|eval)[[:space:]]+["'"'"']?(\$\(|`)[[:space:]]*(curl|wget)'; then
    echo "refuse"; return 1
  fi

  # curl/wget routed through xargs into an interpreter. The xargs wrapper sidesteps the
  # direct pipe matcher above, so a remote payload still reaches a shell.
  if printf '%s' "$bare" | grep -qE '(curl|wget)[^|]*\|.*xargs.*[[:space:]]([^[:space:]]*/)?(sh|bash|zsh|dash|ksh|python[0-9.]*|perl|ruby|node|php)([[:space:];&|()<>]|$)'; then
    echo "refuse"; return 1
  fi

  # Output piped to netcat exfiltrates data off-host.
  if printf '%s' "$bare" | grep -qE '\|[[:space:]]*([^[:space:]]*/)?(nc|ncat|netcat)([[:space:];&|()<>]|$)'; then
    echo "refuse"; return 1
  fi

  # Raw block-device write — dd target or shell redirect onto a disk device wipes it.
  # Scoped to real device families (incl. SD/eMMC mmcblk, mdadm md, device-mapper dm-)
  # so dd/redirect to /dev/null or a regular file stays ok.
  if printf '%s' "$bare" | grep -qE '(of=|>[[:space:]]*)/dev/(sd|hd|vd|nvme|disk|mapper|loop|xvd|mmcblk|md|dm-)'; then
    echo "refuse"; return 1
  fi

  # Filesystem format destroys everything on a partition. Optional path prefix catches a
  # path-qualified invocation (/sbin/mkfs.ext4) that a bare-name anchor would miss.
  if printf '%s' "$bare" | grep -qE '(^|[[:space:];&|(){`\\$<>])([^[:space:];&|(){`<>]*/)?(mkfs|mke2fs)'; then
    echo "refuse"; return 1
  fi

  # find ... -delete mass-removes matched files. Both tokens required so a plain find
  # search (no -delete) is not refused; optional path prefix catches /usr/bin/find.
  if printf '%s' "$bare" | grep -qE '(^|[[:space:];&|(){`\\$<>])([^[:space:];&|(){`<>]*/)?find([[:space:];&|()<>]|$)' \
     && printf '%s' "$bare" | grep -qE '[[:space:]]-delete([[:space:];&|()<>]|$)'; then
    echo "refuse"; return 1
  fi

  # shred overwrites then unlinks — irrecoverable.
  if printf '%s' "$bare" | grep -qE '(^|[[:space:];&|(){`\\$<>])([^[:space:];&|(){`<>]*/)?shred([[:space:];&|()<>]|$)'; then
    echo "refuse"; return 1
  fi

  # truncate to zero size destroys file contents in place. Non-zero sizes are allowed.
  # Optional path prefix catches /usr/bin/truncate; size matcher covers -s 0, -s0,
  # --size 0, and --size=0.
  if printf '%s' "$bare" | grep -qE '(^|[[:space:];&|(){`\\$<>])([^[:space:];&|(){`<>]*/)?truncate([[:space:];&|()<>]|$)' \
     && printf '%s' "$bare" | grep -qE '(-s[[:space:]]*0|--size[[:space:]]*=?[[:space:]]*0)([[:space:];&|()<>]|$)'; then
    echo "refuse"; return 1
  fi

  # Recursive chmod to a zero mode locks an entire tree out of access. Scoped to the
  # zero lock-out (000/00/0 octal short forms) so ordinary recursive permission changes
  # are not refused; optional path prefix catches /bin/chmod.
  if printf '%s' "$bare" | grep -qE '(^|[[:space:];&|(){`\\$<>])([^[:space:];&|(){`<>]*/)?chmod([[:space:];&|()<>]|$)' \
     && printf '%s' "$bare" | grep -qE '(-R|--recursive)([[:space:];&|()<>]|$)' \
     && printf '%s' "$bare" | grep -qE '(^|[[:space:]])(000|00|0)([[:space:];&|()<>]|$)'; then
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
  # A quote or backslash inside the scheme ('postgres'ql://) still gives the shell a URL,
  # so every URL the shell sees must also appear as plain text here.
  local seen_urls plain_urls
  seen_urls=$(printf '%s' "$bare" | grep -oE 'postgres(ql)?://' | wc -l)
  plain_urls=$(printf '%s' "$cmd" | grep -oE 'postgres(ql)?://' | wc -l)
  if [[ "$seen_urls" -ne "$plain_urls" ]]; then
    echo "refuse"; return 1
  fi
  if printf '%s' "$cmd" | grep -qE 'postgres(ql)?://'; then
    # Check every URL: one safe URL must not vouch for a second, real one.
    # A URL ends at whitespace, quotes or shell punctuation, so `A=url1;B=url2` is two URLs.
    # Each URL is read twice: cut at the first punctuation, and with the user:pass part kept
    # whole. `p&ss@prod` and `prod;x@localhost` each fail one of the two readings.
    # Known limit: a dotted user name with & in the password is refused too; run it by hand.
    # Refuse what this check cannot read safely: encoded text (%), several hosts (,),
    # a backslash (the shell drops it, so ho\st= is host=), and query keys that move
    # the connection (host, hostaddr, dbname, service).
    if printf '%s' "$cmd" | grep -qE 'postgres(ql)?://[^[:space:];|<>()]*[%,#\\]' \
      || printf '%s' "$cmd" | grep -qiE 'postgres(ql)?://[^[:space:];|<>()]*[?&](host|hostaddr|dbname|service)='; then
      echo "refuse"; return 1
    fi
    # A URL with nothing after the scheme leaves the host to PGHOST or -h, and a quoted
    # URL with a space in it (a password such as "p ss") is cut before its real host.
    if printf '%s' "$cmd" | grep -qE 'postgres(ql)?://([[:space:];&|<>()"'"'"'`]|$)' \
      || printf '%s' "$cmd" | grep -qE '["'"'"']postgres(ql)?://[^"'"'"']*[[:space:]]'; then
      echo "refuse"; return 1
    fi
    # A quote inside the URL (not just around it) hides where the host really ends.
    if printf '%s' "$cmd" | grep -qE 'postgres(ql)?://[^[:space:];&|<>()]*["'"'"'`][^[:space:];&|<>()"'"'"'`]'; then
      echo "refuse"; return 1
    fi
    local url rest authority db_path db_host db_name host_ok
    while IFS= read -r url; do
      # Split scheme://[user@]host[:port][/dbname][?query]; the query never feeds dbname.
      rest=${url#*://}
      authority=${rest%%/*}
      # Two @ signs leave it unclear which part is the host.
      if [[ "$authority" == *@*@* ]]; then echo "refuse"; return 1; fi
      # Some URL parsers end the host part at ? or #, so prod?@localhost may mean prod.
      if [[ "$authority" == *[?#]*@* ]]; then echo "refuse"; return 1; fi
      db_host=${authority##*@}
      # A ? after the host starts the query, so any later / is not a dbname path.
      if [[ "$db_host" == *\?* ]]; then db_path=""; else db_path=${rest:${#authority}}; fi
      db_host=${db_host%%[:?]*}
      db_path=${db_path%%\?*}
      db_name=${db_path#/}
      # Shell expansion in the name ($_test is an empty variable) hides the real name.
      if [[ "$db_name" == *[\$\{\}\*\[~]* ]]; then echo "refuse"; return 1; fi

      # Allowed hosts: localhost, 127.0.0.1, or a plain single-label name that starts
      # with a letter, such as a container. Anything else is remote: IPv6, a number
      # (2130706433 and 0x7f000001 are IPv4 addresses), and an empty host, which psql
      # fills from PGHOST or -h.
      host_ok=0
      if [[ "$db_host" == "localhost" || "$db_host" == "127.0.0.1" ]]; then
        host_ok=1
      elif [[ "$db_host" =~ ^[A-Za-z][A-Za-z0-9_-]*$ ]]; then
        host_ok=1
      fi

      # Non-allowlisted host: dbname must end with _test or _ci (anchored suffix, not substring)
      if [[ "$host_ok" -eq 0 ]] && ! printf '%s' "$db_name" | grep -qE '_test$|_ci$'; then
        echo "refuse"; return 1
      fi
    done < <(printf '%s' "$cmd" | grep -oE 'postgres(ql)?://[^[:space:];&|<>()"'"'"'`]+'
             printf '%s' "$cmd" | grep -oE 'postgres(ql)?://([^[:space:]/@]*@)?[^[:space:];&|<>()"'"'"'`]+')
  fi

  echo "ok"; return 0
}

case "${1:-}" in
  screen-cmd) shift; screen-cmd "$@" ;;
  *) echo "usage: $0 screen-cmd <shell-string>" >&2; exit 64 ;;
esac
