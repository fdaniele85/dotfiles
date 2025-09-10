alias rm='rm -i'
#alias ps='ps aux|grep -v ps|grep -v grep|more'
alias cl='clear'
alias x+='chmod +x'
alias x-='chmod -x'
alias w+='chmod +w'
alias w-='chmod -w'
alias cls='cl;ls'
alias h='history'
#alias ..='cd ..'
alias la='ls -Alv' # show hidden files
alias ls='ls -hFNv --color' # add colors for filetype recognition
alias n="nautilus . &"
alias xd="xdg-open ."
alias rimuoviLog="find $HOME/Dropbox/linux_files/logs/ -mtime +5 -exec rm -f {} \;"
alias "cs=xclip -selection clipboard"
alias "vs=xclip -o -selection clipboard"
alias "st=subl"

# alert: notifica a fine comando (notify-send + telegram-send).
# -n => no Telegram (solo notify-send)
alert() {
    emulate -L zsh
    set -o pipefail

    local send_telegram=1
    local OPTIND opt
    while getopts ":nh" opt; do
        case $opt in
            n) send_telegram=0 ;;                        # no telegram
            h) echo "Uso: alert [-n] comando [args...]"; return 0 ;;
            \?) echo "Opzione non valida: -$OPTARG" >&2; return 2 ;;
        esac
    done
    shift $((OPTIND-1))

    if (( $# == 0 )); then
        echo "Uso: alert [-n] comando [args...]" >&2
        return 2
    fi

    local start end elapsed exit_code
    start=$(date +%s)
    "$@"
    exit_code=$?
    end=$(date +%s)
    elapsed=$(( end - start ))

    # secondi -> h m s
    local h=$(( elapsed / 3600 ))
    local m=$(( (elapsed % 3600) / 60 ))
    local s=$(( elapsed % 60 ))
    local duration=""
    [[ $h -gt 0 ]] && duration+="${h}h "
    [[ $m -gt 0 ]] && duration+="${m}m "
    duration+="${s}s"

    local cmd="$*"
    local summary body msg
    if [ $exit_code -eq 0 ]; then
        summary="✅ Comando completato"
        body="$cmd
⏱ Durata: $duration"
        msg="✅ Comando completato: $cmd
⏱ Durata: $duration"
    else
        summary="❌ Comando fallito (exit $exit_code)"
        body="$cmd
⏱ Durata: $duration"
        msg="❌ Comando fallito (exit $exit_code): $cmd
⏱ Durata: $duration"
    fi

    # Notifica desktop (se disponibile)
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "$summary" "$body"
    fi

    # Telegram (se non disabilitato)
    if (( send_telegram == 1 )) && command -v telegram-send >/dev/null 2>&1; then
        telegram-send "$msg" >/dev/null 2>&1 &
    fi

    return $exit_code
}
