#!/bin/bash

# If you're reading this on the GitHub gist, scroll down for instructions.
# If not, go to https://gist.github.com/1071034

echo "Enter the URL for the Dropbox deb package:"
read dropbox_url

echo "Downloading Dropbox..."
wget -O /tmp/dropbox.deb "$dropbox_url"

sudo dpkg -i /tmp/dropbox.deb
sudo apt-get install -f
