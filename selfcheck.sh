#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Continuous integration script for the dotfiles repository.

# TODO: Shellcheck myself

################################################################################
# Run shellcheck for a given script.
################################################################################
shcheck() {
  shellcheck "$1"
}

################################################################################
# Run shellcheck for a given script.
################################################################################
main() {
  shcheck "setup.sh" || return 1
  shcheck "bin/weather_status.sh" || return 1
  echo "*** SUCCESS! ***"
}

main "$*"; exit
