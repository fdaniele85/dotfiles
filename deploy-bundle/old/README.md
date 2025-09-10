# Deploy bundle (sudoers)
Contenuto:
- files/etc/sudoers.d/vpn.sudoers
- manifest.tsv
- install.zsh (idempotente, valida con `visudo`)

Uso:
  cd deploy-bundle
  sudo ./install.zsh --dry-run --verbose
  sudo ./install.zsh

Nota: per aggiungere service file systemd, mettili in files/… e nel manifest con destinazione /etc/systemd/system/*.service.
L’installer li verifica con `systemd-analyze verify` e poi fa `systemctl daemon-reload`.
