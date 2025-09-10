#!/bin/bash

# === PARTE 1: parsing degli argomenti ===
DEFAULT_ARCHIVE="not_used.tar.gz"
OUT_ARCHIVE=""
ITEMS=()
DRY_RUN=false

# Stampa help
print_help() {
  cat << EOF
Uso: $0 [OPZIONI] elemento1 [elemento2 ...]

Opzioni:
  -h, --help           Mostra questo messaggio di aiuto e termina
  -d, --dry-run        Mostra le operazioni senza eseguirle
  -a, --archive FILE   Specifica il nome (e path) dell'archivio di output (default: $DEFAULT_ARCHIVE)

Esempi:
  $0 --archive backup.tar.gz cartella1 file2.txt
  $0 -d file1.txt dir2/
EOF
}

# Parsing argomenti
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_help
      exit 0
      ;;
    -d|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -a|--archive)
      OUT_ARCHIVE="$2"
      shift 2
      ;;
    --*)
      echo "Opzione sconosciuta: $1"
      print_help
      exit 1
      ;;
    *)
      ITEMS+=("$1")
      shift
      ;;
  esac
done

# Imposta archivio di default se non specificato
if [[ -z "$OUT_ARCHIVE" ]]; then
  OUT_ARCHIVE="$DEFAULT_ARCHIVE"
fi
# Aggiunge estensione se manca
if [[ "$OUT_ARCHIVE" != *.tar.gz ]]; then
  OUT_ARCHIVE="${OUT_ARCHIVE}.tar.gz"
fi

# Verifica elementi da archiviare
if [ "${#ITEMS[@]}" -eq 0 ]; then
  echo "Errore: nessun file o cartella specificata."
  print_help
  exit 1
fi

# Dry-run: anteprima senza operazioni
if [ "$DRY_RUN" = true ]; then
  echo "[*] Modalità dry-run attiva: nessuna modifica verrà applicata"
  if [ -f "$OUT_ARCHIVE" ]; then
    echo "[*] Archivio ESISTENTE, aggiungerò elementi a: $OUT_ARCHIVE"
  else
    echo "[*] Archivio NON esistente, verrà creato: $OUT_ARCHIVE"
  fi
  echo "[*] Elementi da processare: ${ITEMS[*]}"
  exit 0
fi

# === OPERAZIONI REALI ===

# Crea dir temporanea
TMP_DIR=$(mktemp -d)

# Estrai contenuto precedente (read-only)
if [ -f "$OUT_ARCHIVE" ]; then
  echo "[*] Estrazione archivio esistente in $TMP_DIR"
  tar -xzf "$OUT_ARCHIVE" -C "$TMP_DIR" || { echo "❌ Errore estrazione"; rm -rf "$TMP_DIR"; exit 1; }
fi

# Copia elementi (no overwrite)
for item in "${ITEMS[@]}"; do
  if [ ! -e "$item" ]; then
    echo "⚠️  Non trovato: $item"
    continue
  fi
  echo "[*] Aggiungo: $item"
  if [ -d "$item" ]; then
    rsync -a --ignore-existing "$item/" "$TMP_DIR/$item/"
  else
    mkdir -p "$TMP_DIR/$(dirname "$item")"
    cp -n "$item" "$TMP_DIR/$item"
  fi
done

# Ricrea archivio senza la cartella corrente
cd "$TMP_DIR"
tar -czf "$OLDPWD/$OUT_ARCHIVE" *
STATUS=$?
cd - > /dev/null

# Pulisce temp
echo "[*] Pulizia directory temporanea"
rm -rf "$TMP_DIR"

# Se successo, rimuovi originali
if [ $STATUS -eq 0 ]; then
  echo "✅ Archivio creato: $OUT_ARCHIVE"
  for item in "${ITEMS[@]}"; do
    if [ -e "$item" ]; then
      echo "[*] Rimuovo originale: $item"
      rm -rf "$item"
    fi
  done
  echo "🗑️  Operazione completata"
else
  echo "❌ Errore creazione archivio. Originali conservati."
  exit 2
fi
