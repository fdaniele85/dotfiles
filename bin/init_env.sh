#!/usr/bin/env zsh
set -e

ENVRC_FILE=".envrc"

# 1. Recupera o genera il path del virtualenv
if [[ -f "$ENVRC_FILE" ]]; then
  print "🔄 File .envrc già presente. Uso il path specificato lì."
  VENV_PATH=$(grep '^VENV_DIR=' "$ENVRC_FILE" | cut -d'"' -f2)
  if [[ -z "$VENV_PATH" ]]; then
    print "❌ Errore: impossibile determinare VENV_PATH da .envrc"
    exit 1
  fi
else
  # Calcola un nuovo path univoco
  VENV_BASE="${VENV_HOME:-$HOME/.venvs}"
  PROJECT_NAME="${PWD:t}"  # basename
  PROJECT_HASH=$(print -n "$PWD" | sha256sum | cut -c1-12)
  VENV_NAME="${PROJECT_NAME}_${PROJECT_HASH}"
  VENV_PATH="${VENV_BASE}/${VENV_NAME}"

  print "📝 Creo nuovo .envrc con:"
  print "   VENV_DIR=$VENV_PATH"
  print "VENV_DIR=\"$VENV_PATH\"" > "$ENVRC_FILE"
  print "source \"\$VENV_DIR/bin/activate\"" >> "$ENVRC_FILE"
fi

# 2. Crea il virtualenv se non esiste
if [[ ! -d "$VENV_PATH" ]]; then
  print "🛠️ Creo virtualenv in $VENV_PATH"
  python3 -m venv "$VENV_PATH"
else
  print "✔️ Virtualenv già presente"
fi

# 3. Autorizza direnv
if (( $+commands[direnv] )); then
  direnv allow
else
  print "⚠️ direnv non installato — installalo con: sudo apt install direnv"
fi

# 4. Installa requirements se presenti
if [[ -f "requirements.txt" ]]; then
  print "📦 Installo pacchetti da requirements.txt"
  "$VENV_PATH/bin/pip" install --upgrade pip
  "$VENV_PATH/bin/pip" install -r requirements.txt
fi

print "✅ Ambiente pronto: $VENV_PATH"
