#! /bin/zsh

zparseopts -D -E r=ren d:=d

d=$d[2]
if [[ -z "$d" ]]; then
	d="today"
fi

for dir in $*; do
	if [[ -d "$dir" ]]; then
		author=$(echo $dir | sed 's/^[0-9]* - //;s/ - .*//')
		title=$(echo $dir | sed 's/^[0-9]* - //;s/^[^-]* - //;s/ - .*//')
		cd "$dir"
		echo $title
		i=1
		if [[ $ren[1] == "-r" ]]; then
			quanti=$(ls *.mp3 | wc -l)
			digits=1
			if ((quanti > 9)); then
				digits=02
			fi
			if ((quanti >= 99)); then
				digits=03
			fi
			if ((quanti > 999)); then
				digits=04
			fi
			for f in *.mp3; do
				name=$(printf "$title %${digits}d.mp3" $i)
				((i++))
				mv "$f" "$name"
			done
		fi
		
		tutti=$(ls *.mp3 | wc -l)
		i=0
		for file in *.mp3; do
			t=$(echo "${file:r}" | sed 's/^[[:digit:]]* - //')

			data=$(date "+%Y:%m:%d" -d "$d+${i}days")
			((i++))
			mid3v2 -T "$i/$tutti" -t "${file:r}" -y "$data" "$file"
		done
		eyeD3 -a "$author" -b "$author" -A "$title" *.mp3
		if [[ -e "cover.jpg" ]]; then
			eyeD3 --add-image="cover.jpg":FRONT_COVER *.mp3
		fi
		cd ..
	fi
done