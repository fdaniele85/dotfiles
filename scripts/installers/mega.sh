#!/bin/bash

# If you're reading this on the GitHub gist, scroll down for instructions.
# If not, go to https://gist.github.com/1071034

echo "Enter the URL for the Mega deb package:"
read url

echo "Downloading Mega"
wget -O /tmp/mega.deb "$url"

sudo dpkg -i /tmp/mega.deb
sudo apt-get install -f
