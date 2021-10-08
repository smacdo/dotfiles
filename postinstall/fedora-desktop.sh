#!/bin/bash

# Restore close/minimize/maximize buttons to title bar (WHY GNOME?!)
gsettings set org.gnome.desktop.wm.preferences button-layout ":minimize,maximize,close"

## Visual Studio Code
# Ref: https://code.visualstudio.com/docs/setup/linux#_rhel-fedora-and-centos-based-distributions
echo "Installing Visual Studio Code..."

sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'

dnf check-update
sudo dnf install code
