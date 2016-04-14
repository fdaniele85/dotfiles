#! /bin/bash

# Create backup dir 
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR=$(echo $DIR | sed 's_/scripts__')

if [[ ! -d "$DIR/backups" ]]
then
    echo "Creating backup dir '$DIR/backups'"
    mkdir "$DIR/backups"
fi

# Install programs
for file in $DIR/scripts/installers/*.sh
do
    name=$(basename $file | sed 's/\.sh//')
    read -p "Do you wish to install '$name'? [y/n] " yn
    case $yn in
        [Yy]* )
	    bash "$file" "$DIR/backups"
	    ;;
    esac
done

bash "$DIR/scripts/link.sh" "$DIR"
