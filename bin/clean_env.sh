#!/usr/bin/env zsh
set -e

ENVRC_FILE=".envrc"

if [[ ! -f "$ENVRC_FILE" ]]; then
  print "❌ Nessun file .envrc trovato. Esco."
  exit 1
fi

# Estrai il path del virtualenv dalla riga con "VENV_DIR="
VENV_PATH=$(grep '^VENV_DIR=' "$ENVRC_FILE" | cut -d'"' -f2)

if [[ -z "$VENV_PATH" ]]; then
  print "❌ Impossibile determinare il virtualenv da .envrc"
  exit 1
fi

print "⚠️ Stai per eliminare SOLO la directory dell’ambiente virtuale:"
print "   $VENV_PATH"
print -n "Confermi? [s/N] "
read CONFIRM

if [[ "$CONFIRM" != (s|S) ]]; then
  print "❌ Operazione annullata."
  exit 1
fi

if [[ -d "$VENV_PATH" ]]; then
  print "🧹 Rimuovo virtualenv..."
  rm -rf "$VENV_PATH"
else
  print "ℹ️ Ambiente già assente"
fi

print "✅ Ambiente virtuale rimosso. .envrc lasciato intatto."
