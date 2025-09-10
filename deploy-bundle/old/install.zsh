#!/usr/bin/env zsh
set -euo pipefail
SCRIPT_DIR=${0:A:h}
MANIFEST="$SCRIPT_DIR/manifest.tsv"

# Opzioni
DRYRUN=0; VERBOSE=0; ONLY_PATTERN=""; ONLY_TAG=""
HOST="$(hostname -s)"
FORCE=0

usage(){
  echo "Usage: sudo $0 [--dry-run|-n] [--verbose|-v] [--only PATTERN] [--only-tag TAG] [--force]"
}

while [[ $# -gt 0 ]]; do case "$1" in
  -n|--dry-run) DRYRUN=1;;
  -v|--verbose) VERBOSE=1;;
  --only) ONLY_PATTERN="$2"; shift;;
  --only-tag) ONLY_TAG="$2"; shift;;
  --force) FORCE=1;;
  -h|--help) usage; exit 0;;
  *) echo "Unknown: $1" >&2; usage; exit 64;;
esac; shift; done

log(){ [[ $VERBOSE -eq 1 ]] && echo "$@"; }
require_root(){ [[ $(id -u) -eq 0 ]] || { echo "Serve root." >&2; exit 1; } }
require_root

same_content(){ local s="$1" d="$2"; [[ -f "$d" ]] || return 1; cmp -s -- "$s" "$d" }

ensure_dir(){ install -d -- "$(dirname -- "$1")"; }

validate_tmp(){ local tmp="$1" dst="$2" validate="$3"
  if [[ -n "$validate" ]]; then eval "${validate//\{TARGET\}/$tmp}" || return 1; fi
  if [[ "$dst" == /etc/systemd/system/* ]] && command -v systemd-analyze >/dev/null; then
    systemd-analyze verify "$tmp" || return 1
  fi
  return 0
}

RELOAD_SYSTEMD=0

install_one(){ local src="$1" dst="$2" owner="$3" group="$4" mode="$5" validate="$6"
  [[ -f "$src" ]] || { echo "Sorgente mancante: $src" >&2; return 1; }
  local need=0
  same_content "$src" "$dst" || need=1
  if [[ -e "$dst" ]]; then
    local cm co cg; cm=$(stat -c "%a" -- "$dst"); co=$(stat -c "%U" -- "$dst"); cg=$(stat -c "%G" -- "$dst")
    [[ "$cm" != "${mode##0}" || "$co" != "$owner" || "$cg" != "$group" ]] && need=1
  else need=1; fi

  (( need==0 && FORCE==0 )) && { log "OK: $dst"; return 0; }

  if (( DRYRUN )); then
    echo "[DRY] install $src -> $dst ($owner:$group $mode)"
    [[ -n "$validate" || "$dst" == /etc/systemd/system/* ]] && echo "[DRY] validate"
    return 0
  fi

  ensure_dir "$dst"
  local tmp; tmp="$(mktemp -- "$(dirname -- "$dst")/.${${dst:t}}.XXXXXX")"
  install -m "$mode" -o "$owner" -g "$group" -- "$src" "$tmp"
  validate_tmp "$tmp" "$dst" "$validate" || { echo "Validazione FAIL: $dst" >&2; rm -f -- "$tmp"; return 1; }
  mv -f -- "$tmp" "$dst"
  echo "Installato: $dst ($owner:$group $mode)"
  [[ "$dst" == /etc/systemd/system/* ]] && RELOAD_SYSTEMD=1
}

# Carica env per host (facoltativo)
if [[ -f "$SCRIPT_DIR/hosts/default.env" ]]; then set -a; source "$SCRIPT_DIR/hosts/default.env"; set +a; fi
if [[ -f "$SCRIPT_DIR/hosts/${HOST}.env" ]]; then set -a; source "$SCRIPT_DIR/hosts/${HOST}.env"; set +a; fi

# 1) HOOK PRE
"$SCRIPT_DIR/run-hooks.zsh" --phase pre --host "$HOST" ${VERBOSE:+--verbose} ${DRYRUN:+--dry-run} ${FORCE:+--force}

# 2) INSTALL FILES
while IFS=$'\t' read -r SRC DST OWNER GROUP MODE VALIDATE WHENHOST TAGS || [[ -n "${SRC:-}" ]]; do
  [[ -z "${SRC:-}" || "${SRC[1]}" = \#* ]] && continue
  # filtro --only
  [[ -n "$ONLY_PATTERN" && "$SRC$DST" != *"$ONLY_PATTERN"* ]] && continue
  # filtro tag
  if [[ -n "$ONLY_TAG" ]]; then
    print -r -- "${TAGS:-}" | grep -qw -- "$ONLY_TAG" || continue
  fi
  # filtro host
  local wh="${WHENHOST:-*}"
  [[ $HOST == ${~wh} ]] || continue

  install_one "$SCRIPT_DIR/$SRC" "$DST" "$OWNER" "$GROUP" "$MODE" "${VALIDATE:-}"
done < <(sed -e 's/\r$//' "$MANIFEST")

# 3) daemon-reload se necessario
if (( !DRYRUN && RELOAD_SYSTEMD==1 )); then
  command -v systemctl >/dev/null 2>&1 && systemctl daemon-reload || true
  echo "Eseguito: systemctl daemon-reload"
fi

# 4) HOOK POST
"$SCRIPT_DIR/run-hooks.zsh" --phase post --host "$HOST" ${VERBOSE:+--verbose} ${DRYRUN:+--dry-run} ${FORCE:+--force}
