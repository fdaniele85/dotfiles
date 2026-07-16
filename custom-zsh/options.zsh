setopt NO_HUP

compdef tarssh=scp
compdef trasferisci=rsync

# inizializza zoxide (crea le funzioni z, zi, ecc.)
eval "$(zoxide init zsh)"