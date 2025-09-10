#! /bin/zsh

convertsecs() {
 ((h=${1}/3600))
 ((m=(${1}%3600)/60))
 ((s=${1}%60))
 printf "%02d:%02d:%02d\n" $h $m $s
}

if [[ -z "$1" ]]; then
	echo "Necessario comando"
	exit 1
fi

if [[ -z "$(pgrep -- $1)" ]]; then
	echo "Il comando non sta girando"
	exit 2
fi

user_id=$(id -u)
if ((user_id != 0)); then
	echo "Bisogna eseguirlo come amministratore"
	exit 3
fi

inizio=$(date +%s)
#clear
i=0
while [[ ! -z "$(pgrep -- $1)" ]]; do
	ora=$(date +%s)
	secondi=$((ora-inizio))

	echo -n "\rAspetto la fine di $1 da $(convertsecs $secondi)"
	sleep 30
	((i++))
done
poweroff