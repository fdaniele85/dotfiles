#!/usr/bin/env zsh
set -euo pipefail

# Controllo argomenti
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <archive-file>" >&2
  exit 1
fi
ARCHIVE=$1

echo "Archivio: '$ARCHIVE'"

# Creo tempdir e garantisco cleanup
TMPDIR=$(mktemp -d)
echo "Tempdir: $TMPDIR"
cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT INT TERM

# 1) Estrazione completa con bsdtar
echo "Estrazione in corso..."
bsdtar --extract --file="$ARCHIVE" --directory="$TMPDIR"

# Debug: elenco dei file estratti
echo "File estratti (primi 20):"
find "$TMPDIR" -maxdepth 2 | head -n20

# 2) Trovo la prima immagine
echo "Ricerca prima immagine..."
FILE=$(find "$TMPDIR" -type f \
  \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.gif' -o -iname '*.bmp' \) \
  | sort \
  | head -n1 || true)

if [[ -z "$FILE" ]]; then
  echo "Errore: nessuna immagine trovata in '$TMPDIR'" >&2
  exit 2
fi

echo "Trovato file immagine: '$FILE'"

# 3) Copia su /tmp/cover.jpg
DEST="/tmp/cover.jpg"
cp "$FILE" "$DEST"
echo "Cover copiata in $DEST"
open /tmp/cover.jpg