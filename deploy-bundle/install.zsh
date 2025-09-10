#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
MANIFEST="${SCRIPT_DIR}/manifest.tsv"

DRYRUN=0
VERBOSE=0

usage() {
  echo "Usage: $0 [-n|--dry-run] [-v|--verbose] [--manifest PATH]"
}

# --- parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run) DRYRUN=1 ;;
    -v|--verbose) VERBOSE=1 ;;
    --manifest) MANIFEST="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 64 ;;
  esac
  shift
done

[[ -f "$MANIFEST" ]] || { echo "Manifest non trovato: $MANIFEST" >&2; exit 1; }

log() { [[ $VERBOSE -eq 1 ]] && print -r -- "$@"; }

# espansione semplice di ~ e variabili ambiente
expand_path() {
  local p="$1"
  # espandi ~ all'inizio
  [[ "$p" == "~/"* ]] && p="${HOME}/${p#~/}"
  # espandi variabili ${VAR}
  p="${(e)p}"
  # normalizza se esiste
  [[ -e "$p" ]] && p="${p:A}"
  print -r -- "$p"
}

current_user="$(id -un)"

# leggi TSV (tab), ignora CR e commenti
while IFS=$'\t' read -r USER_FIELD ORIG_FIELD DEST_FIELD SCRIPT_FIELD REST || [[ -n "${USER_FIELD:-}" ]]; do
  # ripulisci CR
  USER_FIELD="${USER_FIELD//$'\r'/}"
  ORIG_FIELD="${ORIG_FIELD//$'\r'/}"
  DEST_FIELD="${DEST_FIELD//$'\r'/}"
  SCRIPT_FIELD="${SCRIPT_FIELD//$'\r'/}"

  # salta vuote o commenti
  [[ -z "${USER_FIELD:-}" ]] && continue
  [[ "${USER_FIELD[1]}" == \#* ]] && continue

  # espandi percorsi
  local user="$USER_FIELD"
  local orig dest script
  orig="$(expand_path "$ORIG_FIELD")"
  dest="$(expand_path "$DEST_FIELD")"
  script="$(expand_path "$SCRIPT_FIELD")"

  # filtro user
  if [[ "$user" != "$current_user" ]]; then
    log "skip (user mismatch): $user != $current_user → $orig → $dest"
    continue
  fi

  # controlla differenza file (se dest manca → diverso)
  need=0
  if [[ ! -f "$dest" ]]; then
    need=1
  else
    if ! cmp -s -- "$orig" "$dest"; then
      need=1
    fi
  fi

  if (( need == 0 )); then
    log "ok (nessuna differenza): $dest"
    continue
  fi

  # prepara argv per lo script
  # Passiamo sempre: --orig, --dest, --user
  argv=( --orig "$orig" --dest "$dest" --user "$current_user" )
  (( VERBOSE )) && argv=( --verbose $argv )
  (( DRYRUN ))  && argv=( --dry-run  $argv )

  if (( DRYRUN )); then
    echo "[DRY-RUN] Eseguirei: $script ${argv[@]}"
  else
    echo "Eseguo: $script ${argv[@]}"
    # assicurati che lo script sia eseguibile
    if [[ ! -x "$script" ]]; then
      # se non eseguibile ma leggibile, prova a lanciarlo con zsh
      if [[ -r "$script" ]]; then
        ZDOTDIR="$HOME" zsh -eu -- "$script" "${argv[@]}"
      else
        echo "Script non eseguibile/leggibile: $script" >&2
        exit 1
      fi
    else
      "$script" "${argv[@]}"
    fi
  fi

done < <(sed -e 's/\r$//' -- "$MANIFEST")
