#!/usr/bin/env zsh
set -euo pipefail
SCRIPT_DIR=${0:A:h}
HOOKS_DIR="$SCRIPT_DIR/hooks"
PHASE=""
HOST=""
DRYRUN=0; VERBOSE=0; FORCE=0
STAMP_DIR="$SCRIPT_DIR/.stamps/$HOST"

usage(){ echo "Usage: $0 --phase {pre|post|user} --host HOST [--dry-run|-n] [--verbose|-v] [--force]"; }

while [[ $# -gt 0 ]]; do case "$1" in
  --phase) PHASE="$2"; shift;;
  --host) HOST="$2"; shift;;
  -n|--dry-run) DRYRUN=1;;
  -v|--verbose) VERBOSE=1;;
  --force) FORCE=1;;
  -h|--help) usage; exit 0;;
  *) echo "Unknown: $1" >&2; usage; exit 64;;
esac; shift; done

[[ -z "$PHASE" || -z "$HOST" ]] && { usage; exit 64; }

DIR="$HOOKS_DIR/${PHASE}.d"
[[ -d "$DIR" ]] || exit 0

log(){ [[ $VERBOSE -eq 1 ]] && echo "$@"; }
stamp_of(){ local p="$1"; print -r -- "$STAMP_DIR/$(basename "$p").stamp"; }
checksum(){ sha256sum "$1" | awk '{print $1}'; }

mkdir -p "$STAMP_DIR"

# Ordina per nome (10-…, 20-…)
for f in "$DIR"/*.zsh(.N); do
  # match host
  base="${f:t}"                      # es: 10-enable@server-*.zsh
  pattern="${base##*@}"              # dopo @
  if [[ "$base" == *"@"* ]]; then
    pattern="${pattern%.zsh}"
    [[ "$HOST" == ${(~)pattern} ]] || { log "skip $base (host $HOST != $pattern)"; continue; }
  fi

  # run-once by checksum
  st="$(stamp_of "$f")"
  cs="$(checksum "$f")"
  if [[ -f "$st" && "$(<"$st")" == "$cs" && $FORCE -eq 0 ]]; then
    log "OK (already run): ${base}"
    continue
  fi

  if (( DRYRUN )); then
    echo "[DRY] hook ${PHASE}: ${base}"
    continue
  fi

  log "→ hook ${PHASE}: ${base}"
  ZDOTDIR="$HOME" zsh -eu "$f"
  print -r -- "$cs" > "$st"
  log "✓ done ${base}"
done
