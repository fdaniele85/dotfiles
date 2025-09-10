#! /bin/zsh

convertsecs() {
	((h=${1}/3600))
	((m=(${1}%3600)/60))
	((s=${1}%60))
	printf "%02d:%02d:%02d\n" $h $m $s
}


zparseopts -D -E c=cue

file=$1

echo $file

chap="${file:r}.chapters.txt"
if [[ -z "$cue" ]]; then
	php $HOME/Sync/scripts/m4b-tool-nuovo.phar meta "$file" --export-chapters
	grep -v "^#" "$chap" | sponge "$chap"
else
	cue_file="${file:r}.cue"
	i=1
	cat $cue_file | grep INDEX | sed 's/[[:space:]]*$//' | cut -d' ' -f5 | while read line; do
		min=$(echo $line | cut -d: -f1)
		sec=$(echo $line | cut -d: -f2)
		out=$(convertsecs $((min*60+sec)))
		printf "$out Capitolo %02d\n" $i
		((i++))
	done > $chap
fi
php $HOME/Sync/scripts/m4b-tool.phar split --audio-format mp3 --audio-bitrate 256k --audio-channels 2 --audio-samplerate 44100 "$file"
