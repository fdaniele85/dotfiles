#!/usr/bin/env zsh

macchina=$1
if [[ "$macchina" == "localhost" || "$macchina" == "" ]]; then
	tail -f /tmp/log*
else
	ssh $macchina "tail -f /tmp/log*"
fi
