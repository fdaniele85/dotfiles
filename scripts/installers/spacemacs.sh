#! /bin/bash

back_dir=$1

cp -r ~/.emacs.d "$bask_dir/emacs.d.bak"

git clone https://github.com/syl20bnr/spacemacs ~/.emacs.d
