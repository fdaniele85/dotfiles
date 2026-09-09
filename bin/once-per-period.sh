#!/usr/bin/env bash

# Library usage (the calling script should use `set -e` or otherwise exit non-zero
# when its work fails):
#
#   source /path/to/once-per-period.sh
#   once_per_period "$SPOOL_FILE"
#
# On an already completed period, once_per_period exits the calling script with 0.
# Otherwise it records the period when the calling script exits successfully.
once_per_period() {
  _OPP_SPOOL="${1:?Usage: once_per_period SPOOL_FILE}"
  _OPP_PERIOD_FMT="${PERIOD_FMT:-%F}"
  LOG_FILE="${LOG_FILE:-/dev/null}"
  export LOG_FILE
  _OPP_LOG_FILE="$LOG_FILE"

  if [ "${USE_UTC:-0}" = "1" ]; then
    _OPP_KEY="$(date -u +"$_OPP_PERIOD_FMT")"
  else
    _OPP_KEY="$(date +"$_OPP_PERIOD_FMT")"
  fi

  if [ "${FORCE:-0}" -ne 1 ]; then
    if [ -f "$_OPP_SPOOL" ] && [ "$(cat "$_OPP_SPOOL" 2>/dev/null || true)" = "$_OPP_KEY" ]; then
      _once_per_period_log "skip: period '$_OPP_KEY' already done (spool: $_OPP_SPOOL)"
      exit 0
    fi
  else
    _once_per_period_log "force: ignoring spool for period '$_OPP_KEY' (spool: $_OPP_SPOOL)"
  fi

  trap '_once_per_period_on_exit "$?"' EXIT
}

_once_per_period_log() {
  printf "%s [%s] %s\n" "$(date '+%F %T')" "once-per-period" "$*" | tee -a "$_OPP_LOG_FILE"
}

_once_per_period_on_exit() {
  _OPP_RC="$1"
  trap - EXIT

  if [ "$_OPP_RC" -eq 0 ]; then
    _OPP_DIR="$(dirname -- "$_OPP_SPOOL")"
    [ -d "$_OPP_DIR" ] || mkdir -p -- "$_OPP_DIR" || exit "$?"
    _OPP_TMP="$(mktemp "${_OPP_SPOOL}".XXXXXX)" || exit "$?"
    printf '%s\n' "$_OPP_KEY" > "$_OPP_TMP" || exit "$?"
    mv -f -- "$_OPP_TMP" "$_OPP_SPOOL" || exit "$?"
    chmod 0644 "$_OPP_SPOOL" 2>/dev/null || true
  fi

  exit "$_OPP_RC"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
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
fi
