#!/bin/bash

# If you're reading this on the GitHub gist, scroll down for instructions.
# If not, go to https://gist.github.com/1071034

echo "Enter the URL for the Mendeley deb package:"
read mendeley_url

echo "Downloading Mendeley"
wget -O /tmp/mendeley.deb "$mendeley_url"

sudo dpkg -i /tmp/mendeley.deb
sudo apt-get install -f
