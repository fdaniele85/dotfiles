#!/usr/bin/env bash
#
# notify-run.sh — esegue un comando e notifica inizio/fine via telegram-send.
# Il retry NON è gestito qui: se ti serve, componi con run-one-until-success
# (pacchetto "run-one"), che oltretutto evita istanze duplicate dello stesso
# comando (utile da cron/n8n).
#
# Uso:
#   notify-run.sh [-l "etichetta"] -- comando arg1 arg2 ...
#
# Esempi:
#   # esecuzione singola, notifica su successo/fallimento
#   notify-run.sh -- rsync -aP --remove-source-files "Twin Peaks" studio:Video/
#
#   # con retry fino a successo (delegato a run-one-until-success)
#   notify-run.sh -- run-one-until-success rsync -aP --remove-source-files "Twin Peaks" studio:Video/
#
#   # con etichetta custom per la notifica
#   notify-run.sh -l "Backup Twin Peaks" -- run-one-until-success rsync -aP "Twin Peaks" studio:Video/
#
# Opzioni:
#   -l "TESTO"    Etichetta da usare nelle notifiche (default: il comando stesso)
#   -h            Mostra questo aiuto

set -uo pipefail

label=""

usage() {
    grep '^#' "$0" | sed -n '2,20p' | sed 's/^# \{0,1\}//'
    exit 1
}

format_elapsed() {
    local total_seconds="$1"
    local hours=$((total_seconds / 3600))
    local minutes=$(((total_seconds % 3600) / 60))
    local seconds=$((total_seconds % 60))

    if (( hours > 0 )); then
        printf '%d:%02d:%02d' "$hours" "$minutes" "$seconds"
    elif (( minutes > 0 )); then
        printf '%d:%02d' "$minutes" "$seconds"
    else
        printf '%d' "$seconds"
    fi
}

while getopts ":l:h" opt; do
    case $opt in
        l) label="$OPTARG" ;;
        h) usage ;;
        \?) echo "Opzione non valida: -$OPTARG" >&2; usage ;;
        :) echo "L'opzione -$OPTARG richiede un argomento" >&2; usage ;;
    esac
done
shift $((OPTIND - 1))

[[ "${1:-}" == "--" ]] && shift

if [[ $# -eq 0 ]]; then
    echo "Errore: nessun comando specificato." >&2
    usage
fi

cmd=("$@")
[[ -z "$label" ]] && label="${cmd[*]}"

telegram-send "🚀 Avvio: $label"

start_ts=$(date +%s)
"${cmd[@]}"
status=$?
elapsed_seconds=$(( $(date +%s) - start_ts ))
elapsed="$(format_elapsed "$elapsed_seconds")"

if [[ $status -eq 0 ]]; then
    telegram-send "✅ Completato: $label (in $elapsed)"
else
    telegram-send "❌ Fallito: $label (exit $status, dopo $elapsed)"
fi

exit "$status"
