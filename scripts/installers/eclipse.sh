#!/bin/bash

# If you're reading this on the GitHub gist, scroll down for instructions.
# If not, go to https://gist.github.com/1071034

icon_url="http://shaun.boyblack.co.za/blog/wp-content/uploads/2009/05/maceclipse4.zip"

eclipse_bin="#!/bin/sh
export ECLIPSE_HOME='/opt/eclipse'
\$ECLIPSE_HOME/eclipse \$*"

eclipse_desktop="[Desktop Entry]
Encoding=UTF-8
Name=Eclipse
Comment=Eclipse IDE
Exec=eclipse
Icon=/opt/eclipse/icon.xpm
Terminal=false
Type=Application
Categories=GNOME;Application;Development;
StartupNotify=true"

echo "Enter the URL for the Eclipse gzipped tarball:"
read eclipse_url

echo "Installing dependencies..."
sudo apt-get install imagemagick openjdk-8-jre

echo "Downloading Eclipse..."
wget -O eclipse.tar.gz "$eclipse_url"

echo "Downloading improved icon..."
wget -O icon.zip "$icon_url"

tar xvf eclipse.tar.gz
unzip icon.zip MacEclipse4/EclipseLogo512.png
convert MacEclipse4/EclipseLogo512.png eclipse/icon.xpm
sudo mv eclipse /opt/eclipse
sudo touch /usr/bin/eclipse
sudo chmod 755 /usr/bin/eclipse
echo -e "$eclipse_bin" | sudo tee /usr/bin/eclipse
echo -e "$eclipse_desktop" | sudo tee /usr/share/applications/eclipse.desktop
rm -f eclipse.tar.gz
