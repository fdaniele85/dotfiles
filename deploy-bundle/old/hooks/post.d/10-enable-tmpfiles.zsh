#!/usr/bin/env zsh
set -euo pipefail

# Se siamo root, non fare nulla: questo è da utente.
if [[ $(id -u) -eq 0 ]]; then
  echo "post: enable-tmpfiles → skip (serve user-install)" >&2
  exit 0
fi

systemctl --user enable systemd-tmpfiles-clean.timer
systemctl --user enable systemd-tmpfiles-setup.service
