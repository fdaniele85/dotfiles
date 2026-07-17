#!/usr/bin/env bash
set -euo pipefail

export ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$ROOT_DIR/backups"
INSTALLERS_DIR="$ROOT_DIR/scripts/installers"
HOST="$(hostname -s)"

mkdir -p "$BACKUP_DIR"

if ! command -v stow >/dev/null 2>&1; then
    echo "stow non trovato. Installo GNU Stow."
    sudo apt install stow
fi

command -v stow >/dev/null 2>&1 || {
    echo "stow non trovato anche dopo l'installazione." >&2
    exit 1
}


run_installers() {
    local dir="$1"
    local label="$2"

    [[ -d "$dir" ]] || return 0

    shopt -s nullglob
    local installers=("$dir"/*.sh)
    shopt -u nullglob

    (( ${#installers[@]} )) || return 0

    echo "Running ${label} installers"
    local installer
    for installer in "${installers[@]}"; do
        echo "-> $(basename "$installer")"
        bash "$installer" "$BACKUP_DIR"
    done
}

run_installers "$INSTALLERS_DIR/all" "common"
run_installers "$INSTALLERS_DIR/$HOST" "host '$HOST'"

echo "Linking dotfiles with stow"
stow -d "$ROOT_DIR/link" -t "$HOME" home
