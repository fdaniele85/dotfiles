#! /bin/bash

if [[ ! -d "$HOME/.oh-my-zsh" ]]
then
    read -p "Do you wish to install oh-my-zsh?" yn
    case $yn in
        [Yy]* )
            cd
            sh -c "$(wget https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh -O -)"
            cd -
	          break;;
        * )
            break;;
    esac
done

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR=$(echo $DIR | sed 's_/scripts__')

if [[ ! -d "$DIR/backups" ]]
then
    echo "Creating backup dir '$DIR/backups'"
    mkdir "$DIR/backups"
fi

bash "$DIR/scripts/link.sh" "$DIR"
