#! /bin/zsh

if [[ "$1" == "-f" ]]; then
	if [[ -e "$2" ]]; then
		cat "$2" | while read alb; do
			/home/daniele/.venvs/scripts_1553aca88f67/bin/spotdl --dont-filter-results --output "{album-artist}/{year} - {album}/Disc {disc-number}/{track-number} - {title}.{output-ext}" --bitrate 320k $alb
		done
	else
		echo "File '$2' non esistente"
		exit 1
	fi
else
	for alb in $*; do
		/home/daniele/.venvs/scripts_1553aca88f67/bin/spotdl --dont-filter-results --output "{album-artist}/{year} - {album}/Disc {disc-number}/{track-number} - {title}.{output-ext}" --bitrate 320k $alb
	done
fi