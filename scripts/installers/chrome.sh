#!/bin/bash

# If you're reading this on the GitHub gist, scroll down for instructions.
# If not, go to https://gist.github.com/1071034

echo "Enter the URL for the Chrome deb package:"
read chrome_url

echo "Downloading Chrome"
wget -O /tmp/chrome.deb "$chrome_url"

sudo dpkg -i /tmp/chrome.deb
sudo apt-get install -f
