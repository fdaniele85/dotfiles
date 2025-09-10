#! /bin/zsh

dir=$1
if [[ -z "$dir" ]]; then
	dir=$(ls | grep _splitted)
fi

name=$(echo $dir | sed 's/_splitted//')
while [[ ! -z "$(ps aux | grep split_m4b | grep -v grep)" ]]; do
	clear
	tail -n3 "$name.chapters.txt"
	echo
	ls -lh "$dir" | tail -n 3
	sleep 1
done
telegram-send "Finito split_m4b"