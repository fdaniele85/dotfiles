#! /bin/bash

wget -O /tmp/nixnote.deb "http://downloads.sourceforge.net/project/nevernote/NixNote2%20-%20Beta%207/nixnote2-2.0-beta7_amd64.deb?r=https%3A%2F%2Fsourceforge.net%2Fprojects%2Fnevernote%2F&ts=1460642873&use_mirror=tenet"

sudo dpkg -i /tmp/nixnote.deb
sudo apt-get install -f
rm -f /tmp/nixnote.deb
