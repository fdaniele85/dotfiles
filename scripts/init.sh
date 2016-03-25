#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR=$(echo $DIR | sed 's_/scripts__')

if [[ ! -d "$DIR/backups" ]]
then
    echo "Creating backup dir '$DIR/backups'"
    mkdir "$DIR/backups"
fi
