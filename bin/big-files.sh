#!/usr/bin/env bash
set -euo pipefail

# valori di default
num_files=10
dirs=()

# parsing degli argomenti
while getopts "n:" opt; do
  case "$opt" in
    n) num_files="$OPTARG" ;;
    *) 
       echo "Uso: $0 [-n numero] [cartella1 cartella2 ...]"
       exit 1
       ;;
  esac
done
shift $((OPTIND -1))

# cartelle da processare
if [ $# -eq 0 ]; then
  dirs=(".")
else
  dirs=("$@")
fi

# stampa i file più grandi
find "${dirs[@]}" -type f -printf "%s %p\n" 2>/dev/null \
  | sort -nr \
  | head -n "$num_files" \
  | numfmt --to=iec --suffix=B --padding=7 --field=1
