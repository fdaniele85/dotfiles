#!/bin/zsh
convertsecs() {
 ((h=${1}/3600))
 ((m=(${1}%3600)/60))
 ((s=${1}%60))
 printf "%02d:%02d:%02d\n" $h $m $s
}

SELF=$$
SCRIPT_NAME="${0:t}"
SLEEP_SECONDS=30

matching_pids() {
	local pattern="$1"
	local pid
	local comm
	local args

	for pid in ${(f)"$(pgrep -f -- "$pattern")"}; do
		[[ -z "$pid" || "$pid" = "$SELF" ]] && continue
		comm=$(ps -p "$pid" -o comm= 2>/dev/null) || continue
		args=$(ps -p "$pid" -o args= 2>/dev/null) || continue
		[[ "$comm" = "pgrep" ]] && continue
		[[ "$args" == *"$SCRIPT_NAME"* ]] && continue
		print "$pid $args"
	done
}

while getopts "s:" opt; do
	case "$opt" in
		s)
			SLEEP_SECONDS="$OPTARG"
			;;
		*)
			echo "Uso: $0 [-s secondi] comando"
			exit 1
			;;
	esac
done

shift $((OPTIND - 1))

if [[ -z "$1" ]]; then
	echo "Necessario comando"
	exit 1
fi

if ! [[ "$SLEEP_SECONDS" =~ '^[0-9]+$' ]] || (( SLEEP_SECONDS <= 0 )); then
	echo "Valore -s non valido: $SLEEP_SECONDS"
	exit 1
fi

if [[ -z "$(matching_pids "$1")" ]]; then
	echo "Il comando non sta girando"
	exit 2
fi

inizio=$(date +%s)
while true; do
	pids="$(matching_pids "$1")"
	[[ -z "$pids" ]] && break
	ora=$(date +%s)
	secondi=$((ora-inizio))
	print -n "\rAspetto la fine di $1 da $(convertsecs $secondi)"
	sleep "$SLEEP_SECONDS"
done

print "\nTerminato, spengo..."
poweroff
