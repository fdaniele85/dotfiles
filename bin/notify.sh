#! /bin/bash

t="$1"
m="$2"

if [[ -z "$t" ]]; then
	notify-send -i /usr/share/ntfy/logo.png "$m"
else
	notify-send -i /usr/share/ntfy/logo.png "$t" "$m"
fi