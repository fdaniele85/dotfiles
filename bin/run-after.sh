#!/usr/bin/env bash
# run-after: esegue un comando solo se è passato un certo intervallo
# Uso:
#   run-after [-f] [-h] INTERVAL SPOOL -- command [args...]
#
# INTERVAL: numero con unità opzionale: s (secondi), m (minuti), h (ore), d (giorni)
#           esempi: 300, 5m, 2h, 1d
# SPOOL:    file dove salvare l'ultimo timestamp (epoch) su esecuzione riuscita
#
# Env:
#   LOG_FILE  percorso del log; default /dev/stdout (stampa anche a video)
#
# Comportamento:
#   - se il tempo trascorso dall'ultimo successo >= INTERVAL → esegue
#   - altrimenti salta e logga "skip"; exit 0
#   - con -f forza l'esecuzione (ignora l'intervallo) ma aggiorna lo spool solo se rc==0

set -euo pipefail

FORCE=0
while getopts ":fh" opt; do
  case "$opt" in
    f) FORCE=1 ;;
    h)
      cat <<'USAGE'
Usage: run-after [-f] INTERVAL SPOOL -- command [args...]
  INTERVAL: N[smhd]  (s=sec, m=min, h=ore, d=giorni; default s)
  SPOOL:    file che contiene l'ultimo epoch su successo
  -f:       forza l'esecuzione ignorando l'intervallo
USAGE
      exit 0 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; exit 64 ;;
  esac
done
shift $((OPTIND-1))

INTERVAL_RAW="${1:?Usage: run-after [-f] INTERVAL SPOOL -- command [args...]}"; shift
SPOOL="${1:?Usage: run-after [-f] INTERVAL SPOOL -- command [args...]}"; shift
[ "${1:-}" = "--" ] && shift
[ "$#" -gt 0 ] || { echo "Error: missing command" >&2; exit 64; }

# Logging setup
LOG_FILE="${LOG_FILE:-/dev/stdout}"
log(){ printf "%s [%s] %s\n" "$(date '+%F %T')" "run-after" "$*" | tee -a "$LOG_FILE"; }

# Parse INTERVAL_RAW (N + optional unit)
parse_interval() {
  local s="$1"
  local num unit
  if [[ "$s" =~ ^([0-9]+)([smhdSMHD]?)$ ]]; then
    num="${BASH_REMATCH[1]}"; unit="${BASH_REMATCH[2],,}"
    case "${unit:-s}" in
      s|"") echo "$num" ;;
      m) echo $(( num * 60 )) ;;
      h) echo $(( num * 3600 )) ;;
      d) echo $(( num * 86400 )) ;;
      *) echo "Invalid unit in interval: $s" >&2; exit 64 ;;
    esac
  else
    echo "Invalid INTERVAL format: $s" >&2; exit 64
  fi
}

INTERVAL_SECS=$(parse_interval "$INTERVAL_RAW")
NOW=$(date +%s)

# Leggi lo spool (epoch). Se mancante o non numerico → considera come mai eseguito.
LAST=0
if [[ -f "$SPOOL" ]]; then
  if read -r t <"$SPOOL" && [[ "$t" =~ ^[0-9]+$ ]]; then
    LAST="$t"
  else
    log "warning: spool non valido, lo ignoro ($SPOOL)"
  fi
fi

SHOULD_RUN=0
if [[ $FORCE -eq 1 ]]; then
  log "force: ignoro intervallo di $INTERVAL_SECS s (spool: $SPOOL)"
  SHOULD_RUN=1
else
  ELAPSED=$(( NOW - LAST ))
  if [[ $LAST -eq 0 ]]; then
    log "first-run: nessun timestamp nello spool ($SPOOL)"
    SHOULD_RUN=1
  elif [[ $ELAPSED -ge $INTERVAL_SECS ]]; then
    log "ok: trascorsi ${ELAPSED}s (>= ${INTERVAL_SECS}s)"
    SHOULD_RUN=1
  else
    REMAIN=$(( INTERVAL_SECS - ELAPSED ))
    log "skip: mancano ${REMAIN}s prima del prossimo run (elapsed=${ELAPSED}s, interval=${INTERVAL_SECS}s)"
    exit 0
  fi
fi

# Esecuzione del comando con propagazione di LOG_FILE
LOG_FILE="$LOG_FILE" "$@"
rc=$?

if [[ $rc -eq 0 ]]; then
  dir="$(dirname -- "$SPOOL")"
  [[ -d "$dir" ]] || mkdir -p -- "$dir"
  tmp="$(mktemp "${SPOOL}".XXXXXX)"
  printf '%s\n' "$NOW" >"$tmp"
  mv -f -- "$tmp" "$SPOOL"
  chmod 0644 "$SPOOL" 2>/dev/null || true
  log "done: aggiornato spool a $NOW"
else
  log "command failed (rc=$rc): $*"
fi

exit $rc
