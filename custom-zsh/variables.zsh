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
