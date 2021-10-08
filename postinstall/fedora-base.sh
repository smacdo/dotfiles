#!/bin/bash
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Installs and configures a new Fedora (server or desktop) for my use.
################################################################################
# NOTE: This script was written on a managed Fedora installation, which altered
#       the base image. It will need to be improved to work for regular out of
#       the box Fedora installs.
################################################################################
# Don't run if not superuser.
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (sudo)"
    exit 1
fi

# Make sure dnf is up to date before installing packages
dnf update

## Vim enhanced
# Fedora ships a minimal version of vim out of the box (no syntax highlighting,
# no term gui, etc). This package has what we would expect from vim running in
# the terminal.
dnf -y install vim-enhanced

# htop is a nicer terminal process monitor than top.
dnf -f install htop
