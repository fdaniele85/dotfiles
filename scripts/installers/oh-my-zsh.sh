#! /bin/bash

if [[ -d "$HOME/.oh-my-zsh" ]]
then
    read -p "Zsh is already installed, do you want to overwrite it? " yn
    case $yn in
	[Yy]* )
	    cd
	    sh -c "$(wget https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh -O -)"
	    cd -
	    ;;
    esac
fi
