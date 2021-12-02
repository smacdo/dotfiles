#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Installs and configures a new Fedora (server or desktop) for my use.
################################################################################
# NOTE: This script was written on a managed Fedora installation, which altered
#       the base image. It will need to be improved to work for regular out of
#       the box Fedora installs.
################################################################################

################################################################################
#
################################################################################
main() {
  parse_args "$@"

  # Root is required for this script.
  die_if_not_root

  # Make sure dnf is up to date before installing packages
  # dnf update

  # Modes
  # setup_base || return 2

  if [ "${MODE_GNOME}" = 1 ]; then
    setup_desktop || return 2
  fi
}

################################################################################
# Base setup
################################################################################
setup_base() {
  ##############################################################################
  # Install basic packages required for most environments (desktop, server,
  # development, etc).
  ##############################################################################
  ## Vim enhanced
  # Fedora ships a minimal version of vim out of the box (no syntax highlighting
  # no term gui, etc). This package has what we would expect from vim running in
  # the terminal.
  dnf -y install vim-enhanced

  # htop is a nicer terminal process monitor than top.
  dnf -f install htop

  # fzf is a swiss army knife for terminal based selection of lines with
  # fuzzy searching.
  dnf -f install fzf

  # ripgrep is a faster grep./
  dnf -f install ripgrep
}

################################################################################
# Desktop setup
################################################################################
setup_desktop() {
  # Restore close/minimize/maximize buttons to title bar (WHY GNOME?!)
  echo "Applying gnome settings"
  gsettings set org.gnome.desktop.wm.preferences button-layout ":minimize,maximize,close"

  ## Visual Studio Code
  # Ref: https://code.visualstudio.com/docs/setup/linux#_rhel-fedora-and-centos-based-distributions
  echo "Installing Visual Studio Code..."

  sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
  sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'

  dnf check-update
  sudo dnf install code
}

################################################################################
# Prints help
################################################################################
print_usage() {
  echo "Usage: $0 path/to/dotfile/dir modes..."
  echo "where the first argument is a path to the dotfiles git checkout dir "\
    "and mode is any of the following:"
  echo "  (empty)          Base setup, no additional special changes"
  echo "  desktop          Gnome based desktop installation"
  echo "  cpp              Tools for C++ development (clang, gcc etc)"
}

#==============================================================================#
# Startup                                                                      #
#==============================================================================#
DOTFILE_ROOT=${S_DOTFILE_ROOT:-$2}

if [ -z "${DOTFILE_ROOT}" ]; then
  echo "ERROR: Expect environment variable S_DOTFILE_ROOT not found"
  echo "You can pass the value by re-running the command as follows: "
  echo "sudo fedora.sh -d path/to/dotfile/root ...other_params..." 
  print_usage
  exit
fi

if [ ! -d "${DOTFILE_ROOT}" ]; then
  echo "ERROR: Dotfile root is expected to a be a directory!"
  exit
fi

# Pull in shared functions and functionality.
. "${DOTFILE_ROOT}/postsetup/sharedfuncs.sh" || exit

main "$@"; exit
