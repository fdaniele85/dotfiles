#!/usr/bin/env bash
set -euo pipefail

FORCE=0
# parse options: -f to force execution even if spool matches current period
while getopts ":fh" opt; do
  case "$opt" in
    f) FORCE=1 ;;
    h)
      echo "Usage: $0 [-f] SPOOL_FILE -- command [args...]"; exit 0 ;;
    :) echo "Option -$OPTARG requires an argument" >&2; exit 64 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; echo "Usage: $0 [-f] SPOOL_FILE -- command [args...]"; exit 64 ;;
  esac
done
shift $((OPTIND-1))

SPOOL="${1:?Usage: $0 [-f] SPOOL_FILE -- command [args...]}"
shift
[ "${1:-}" = "--" ] && shift
[ "$#" -gt 0 ] || { echo "Error: missing command"; exit 64; }

PERIOD_FMT="${PERIOD_FMT:-%F}"
if [ "${USE_UTC:-0}" = "1" ]; then
  KEY="$(date -u +"$PERIOD_FMT")"
else
  KEY="$(date +"$PERIOD_FMT")"
fi

LOG_FILE="${LOG_FILE:-/dev/null}"
log() {
  printf "%s [%s] %s
" "$(date '+%F %T')" "once-per-period" "$*" | tee -a "$LOG_FILE"
}

# Decide se eseguire in base allo spool (a meno di forza)
if [ "$FORCE" -ne 1 ]; then
  if [ -f "$SPOOL" ] && [ "$(cat "$SPOOL" 2>/dev/null || true)" = "$KEY" ]; then
    log "skip: period '$KEY' already done (spool: $SPOOL)"
    exit 0
  fi
else
  log "force: ignoring spool for period '$KEY' (spool: $SPOOL)"
fi

# eseguo il comando propagando LOG_FILE
LOG_FILE="$LOG_FILE" "$@"
rc=$?

if [ $rc -eq 0 ]; then
  dir="$(dirname -- "$SPOOL")"
  [ -d "$dir" ] || mkdir -p -- "$dir"
  tmp="$(mktemp "${SPOOL}".XXXXXX)"
  printf '%s
' "$KEY" > "$tmp"
  mv -f -- "$tmp" "$SPOOL"
  chmod 0644 "$SPOOL" 2>/dev/null || true
fi

exit $rc
