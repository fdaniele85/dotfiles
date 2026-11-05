# Variables
DROPBOX_PATH="$HOME/Dropbox"
export DROPBOX_PATH

if [[ -d "/usr/local/java/ssj" ]]
then
    export SSJHOME=/usr/local/java/ssj
    . $SSJHOME/Ssj.sh
fi

export UPDATE_DOTFILES_DAYS=15

#export PATH=/usr/local/texlive/2016/bin/x86_64-linux:$PATH

export PATH=".:/home/daniele/.dotfiles/bin:$PATH"
export VISUAL="micro"

if [[ -d /home/daniele/envs/beets/ ]]; then
	export PATH="$PATH:/home/daniele/envs/beets/bin/"
fi

if [[ -d /home/daniele/.local/bin/ ]]; then
    export PATH="$PATH:/home/daniele/.local/bin/"
fi

if [[ -d /home/daniele/.lmstudio/bin/ ]]; then
    export PATH="/home/daniele/.lmstudio/bin:$PATH"
fi

export MANPATH="$HOME/.dotfiles/man:$MANPATH"

export SSH_AUTH_SOCK="$HOME/.var/app/com.bitwarden.desktop/data/.bitwarden-ssh-agent.sock"


export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

setopt HIST_IGNORE_SPACE
