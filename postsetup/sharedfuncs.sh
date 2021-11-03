#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Shared functions for postsetup scripts for different *nix distros.
###############################################################################
# Configure formatted text output if available.
# 1. Check if stdout is a terminal
if test -t 1; then
  # 2. Check if colors are supported.
  colorCount=$(tput colors)

  if test -n "${colorCount}" && test "${colorCount}" -ge 0; then
    normal="$(tput sgr0)"
    bold="$(tput bold)"
    red="$(tput setaf 1)"
  fi
fi

###############################################################################
# Prints error text to the console.
###############################################################################
error() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S%z') ${bold}${red}ERROR${normal}]: "\
    "${red}$*${normal}" >&2
}

###############################################################################
# Prints error text to the console and then exits the process.
###############################################################################
die_error() {
  error "$@"
  exit 1
}

###############################################################################
# Terminates process if user is not root.
###############################################################################
die_if_not_root() {
  if [ "$(id -u)" != 0 ]; then
    die_error "This script must be run as root (sudo)"
  fi
}

###############################################################################
# Command line help text.
###############################################################################
print_help() {
  echo "TODO: HELP"
}

###############################################################################
# Handle command line option processing.
#
#
###############################################################################
parse_args() {
  echo "HOLA"
  while getopts "hd:sg:" option; do
    case "$option" in
      h) # display help.
        print_help
        exit
        ;;
      d) # dotfiles path
        _IGNORE_DOTFILE_ROOT=$OPTARG;;
      s) # Scenario: server
        MODE_SERVER=1
        ;;
      g) # Scenario: gnome desktop
        MODE_GNOME=1
        ;;
      \?) # unknown option
        die_error "Unknown option";;
    esac
  done
  echo "DOOOOOOOOOOOOOONE"
}


