#!/bin/sh
set -e
stow -d "$HOME/.dotfiles/link/daniele-dell" -t "$HOME" home
systemctl --user daemon-reload
systemctl --user enable --now $(ls $HOME/.dotfiles/link/unused/home/.config/systemd/user/*.timer | xargs -n1 basename)
loginctl enable-linger "$USER"