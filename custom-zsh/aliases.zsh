alias rm='rm -i'
#alias ps='ps aux|grep -v ps|grep -v grep|more'
alias cl='clear'
alias x+='chmod +x'
alias x-='chmod -x'
alias w+='chmod +w'
alias w-='chmod -w'
alias cls='cl;ls'
alias h='history'
#alias ..='cd ..'
alias la='ls -Alv' # show hidden files
alias ls='ls -hFNv --color' # add colors for filetype recognition
#alias "copy=xclip -selection clipboard"
#alias "pasta=xclip -o -selection clipboard"
alias "st=subl"
alias trash="gio trash"
alias copia-tags="exiftool -overwrite_original -extractEmbedded -TagsFromFile"

tempe () {
  if [[ $# -eq 1 ]]; then
    mkdir -p "/tmp/$1"
    cd "/tmp/$1"
  else
    cd "$(mktemp -d)"
  fi
  chmod -R 0700 .
}

mkcd () {
  mkdir -p "$1"
  cd "$1"
}

trim() {
  sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed -z 's/\n$//'
}

xd() {
  local q="${1-.}"
  xdg-open "$q"
}

alias okular='flatpak run org.kde.okular'

tarzst() {
    local opt_remove opt_verbose opt_level

    zparseopts -D \
        r=opt_remove \
        v=opt_verbose \
        l:=opt_level \
        || { echo "Usage: tarzst [-r] [-v] [-l level] <directory>"; return 1 }

    if [[ $# -ne 1 ]]; then
        echo "Usage: tarzst [-r] [-v] [-l level] <directory>"
        return 1
    fi

    local DIR=$1
    local LEVEL=${opt_level[-1]:-10}
    local REMOVE=${opt_remove:+--remove-files}
    local VERBOSE=${opt_verbose:+-v}

    if [[ ! -d $DIR ]]; then
        echo "Error: $DIR is not a directory"
        return 1
    fi

    local BASENAME=$(basename "$DIR")
    tar --use-compress-program="zstd -${LEVEL}" $REMOVE $VERBOSE -cf "${BASENAME}.tar.zst" "$DIR"
}

alias trasferisci='rsync -a --partial --info=progress2 --no-i-r'