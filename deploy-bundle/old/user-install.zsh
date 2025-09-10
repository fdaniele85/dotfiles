#!/usr/bin/env zsh
set -euo pipefail
SCRIPT_DIR=${0:A:h}
HOST="$(hostname -s)"
DRYRUN=0; VERBOSE=0; ONLY_PATTERN=""; ONLY_TAG=""; FORCE=0

while [[ $# -gt 0 ]]; do case "$1" in
  -n|--dry-run) DRYRUN=1;; -v|--verbose) VERBOSE=1;;
  --only) ONLY_PATTERN="$2"; shift;;
  --only-tag) ONLY_TAG="$2"; shift;;
  --force) FORCE=1;;
  -h|--help) echo "Usage: $0 [--dry-run|-n] [--verbose|-v] [--only PATTERN] [--only-tag TAG] [--force]"; exit 0;;
  *) echo "Unknown: $1"; exit 64;;
esac; shift; done

# Hook user (no root)
"$SCRIPT_DIR/run-hooks.zsh" --phase user --host "$HOST" ${VERBOSE:+--verbose} ${DRYRUN:+--dry-run} ${FORCE:+--force}
