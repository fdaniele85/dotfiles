#! /bin/bash

back_dir=$1

if [[ ! -d "$back_dir/emacs.d.bak" ]]
then
    mkdir "$back_dir/emacs.d.bak"
    mv ~/.emacs.d "$back_dir/emacs.d.bak"

    git clone https://github.com/syl20bnr/spacemacs ~/.emacs.d
fi
