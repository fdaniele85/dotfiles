#! /bin/bash

DIR="$1"
backup_dir="$DIR/backups"
symlink_dir="$DIR/link"

for file in "$symlink_dir"/*.symlink
do
    name=$(basename $file | sed 's/.symlink//')
    if [[ -e "$HOME/.$name" ]]
    then
        mv "$HOME/.$name" "$backup_dir/"
    fi

    echo "Linking '.$name'..."
    ln -s "$file" "$HOME/.$name"
done
