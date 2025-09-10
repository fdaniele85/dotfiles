#! /usr/bin/zsh

i=0
clear
while [[ 1 ]]; do
	q=$((3*LINES/4))
	s=$(dropbox status 2> /dev/null | egrep 'Sincronizzazione|Syncing|Connessione|Avvio')
	if [[ ! $s ]]; then
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