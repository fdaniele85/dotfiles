#! /usr/bin/zsh

wait_for_sync=0
for arg in "$@"; do
	case "$arg" in
		-w|--wait) wait_for_sync=1 ;;
		-h|--help)
			printf 'Uso: %s [-w|--wait]\n  -w, --wait  Attende una sincronizzazione prima di terminare.\n' "${0:t}"
			exit 0
			;;
		*)
			printf 'Opzione non riconosciuta: %s\n' "$arg" >&2
			exit 1
			;;
	esac
done

i=0
clear
while [[ 1 ]]; do
	q=$((3*LINES/4))
	current_status=$(dropbox status 2> /dev/null)
	s=$(printf '%s\n' "$current_status" | grep -E 'Sincronizzazione|Syncing|Connessione|Avvio')
	if [[ -n $s ]]; then
		wait_for_sync=0
	elif ((wait_for_sync)); then
		s=$current_status
	else
		break
	fi

	if [[ "$s" != "$last" ]]; then
		if ((i >= q)); then
			clear
			i=0
		else
			((i++))
		fi
		echo "\r$s"
		last="$s"
	fi

	sleep 1
done

dropbox status 2> /dev/null
