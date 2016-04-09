# Variables
DROPBOX_PATH="$HOME/Dropbox"
export DROPBOX_PATH

if [[ -d "/usr/local/java/ssj" ]]
then
    export SSJHOME=/usr/local/java/ssj
    . $SSJHOME/Ssj.sh
fi

UPDATE_DOTFILES_DAYS=1