#!/usr/bin/env zsh

# host="192.168.1.13"
# port=22

# remote_keys=$(ssh-keyscan -T 3 -p $port $host 2>/dev/null) || exit 1
# [[ -z $remote_keys ]] && exit 1

# while IFS= read -r line; do
#   grep -Fq "$line" ~/.ssh/known_hosts && exit 0
# done <<< "$remote_keys"

# exit 1

if [[ $1 == "--internal" ]]; then
  host="192.168.1.13"
else
  host="100.64.0.3"
fi
port=22

# deve esistere known_hosts con almeno una chiave
[[ -s ~/.ssh/known_hosts ]] || exit 1

# prendi tutte le chiavi remote (può essere più di una)
remote_keys=$(ssh-keyscan -T 3 -p $port $host 2>/dev/null) || exit 1
[[ -z $remote_keys ]] && exit 1

# estrai tutti i fingerprint noti dal known_hosts
known_fps=$(ssh-keygen -lf ~/.ssh/known_hosts 2>/dev/null | awk '{print $2}')
[[ -z $known_fps ]] && exit 1

# per ogni chiave remota, calcola il fingerprint e confrontalo con quelli noti
while IFS= read -r line; do
  fp=$(printf "%s\n" "$line" | ssh-keygen -lf - 2>/dev/null | awk '{print $2}')
  [[ -z $fp ]] && continue
  printf "%s\n" "$known_fps" | grep -Fxq "$fp" && exit 0
done <<< "$remote_keys"

exit 1
