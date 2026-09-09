#!/usr/bin/env zsh

[[ $# -le 1 ]] || exit 2

target=${1:-hp}
[[ -n $target && $target != -* ]] || exit 2

if ssh -T \
  -o BatchMode=yes \
  -o ConnectTimeout=3 \
  -o ConnectionAttempts=1 \
  -o RemoteCommand=none \
  -o StrictHostKeyChecking=yes \
  -o UpdateHostKeys=no \
  "$target" true </dev/null >/dev/null 2>&1; then
  exit 0
fi

exit 1
